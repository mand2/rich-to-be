#!/usr/bin/env python3
"""발행된 노트 링크를 슬랙 채널에 올린다. 외부 의존성 0 (urllib 만 쓴다).

채널엔 "<파일명> 정리" 만 뜨고 Pages 링크는 그 메시지의 스레드 답글로 [노트 제목](링크) 꼴로 들어간다.
한 번에 여러 개를 보내면 첫 메시지가 스레드 부모가 되고 나머지는 전부 그 스레드에 달린다.

--daily 는 매일 밤 Actions(daily-slack.yml, KST 21:00) 가 부른다 — 지난 24시간 main 에 들어온
first-parent 커밋(PR 머지·직접 푸시)마다 추가된 노트를 모아 "오늘의 정리 >>>" 한 글을 올리고,
커밋당 답글 하나(그 커밋의 노트 링크들)를 그 스레드에 단다. 새 노트가 없으면 아무것도 안 보낸다.

리포 루트 .env 에 두 줄 (환경변수로 이미 있으면 그쪽이 이긴다). .env.example 참고:

    SLACK_BOT_TOKEN=xoxb-...   # scope: chat:write
    SLACK_CHANNEL=C0XXXXXXX    # 봇을 채널에 /invite 해 둘 것
    SLACK_MENTION_GROUP=S0X... # 선택. 멘션으로 시작한 건의 답글에 부를 사용자 그룹 ID

    .venv/bin/python scripts/slack.py notes/morning-routine/260826_한경-모닝루틴.html
    .venv/bin/python scripts/slack.py --daily            # 지난 24시간 main 의 새 노트를 한 스레드로
    .venv/bin/python scripts/slack.py --selftest

Pages 아티팩트의 루트가 notes/ 라서 notes/ 아래 경로가 그대로 URL 경로가 된다.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://slack.com/api/"
YOUTUBE = re.compile(r"(?:youtube\.com/watch\?\S*?v=|youtu\.be/|youtube\.com/live/)([\w-]{11})")
# 멘션으로 시작한 노트는 이 태그로 원본 스레드를 들고 다닌다. 심는 건 슬랙 멘션 스킬.
THREAD_META = re.compile(r'<meta\s+name="slack-thread"\s+content="([\d.]+)"')
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
# 슬랙으로 보내는 노트 폴더. self-study 는 gitignore 라 애초에 git 에 없다.
NOTE_GLOBS = ("notes/morning-routine/*.html", "notes/invest/*.html", "notes/real-estate/*.html")
# ponytail: --daily 의 창. daily-slack.yml 의 cron 이 하루 한 번이라 24시간 — cron 주기를 바꾸면 같이 바꾼다.
# 커밋 시각 기준이라 실행 시각 정각 부근의 머지는 다음 날로 밀릴 수 있다 (상태 파일을 두지 않는 대가).
DAILY_SINCE = "24 hours ago"
# ponytail: 멘션 스캔 깊이. 오래된 멘션이 잘려 안 보이면 올린다 (SKILL.md 도 이 값을 가리킨다).
HISTORY_LIMIT = 50
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
# ponytail: CI 는 deploy-pages 의 page_url 을 NOTES_BASE_URL 로 넘긴다. 이 기본값은 로컬 실행용 —
# 리포/계정이 바뀌면 여기도 바꾼다.
BASE_URL = "https://mand2.github.io/rich-to-be/"


def dotenv(path=ENV_FILE):
    """KEY=VALUE 만 읽는다. 따옴표는 벗기고, # 로 시작하는 줄과 빈 줄은 버린다."""
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("\"'")
    return out


def call(method, token, **params):
    """Slack Web API 폼 호출. ok:false 면 예외."""
    req = urllib.request.Request(
        API + method,
        data=urllib.parse.urlencode(params).encode(),
        headers={"Authorization": f"Bearer {token}"},
    )
    body = json.load(urllib.request.urlopen(req))
    if not body.get("ok"):
        raise RuntimeError(f"{method}: {body.get('error')} {body.get('response_metadata', '')}")
    return body


def note_url(path, base=BASE_URL):
    """notes/invest/x.html -> <base>invest/x.html. 한글 파일명은 퍼센트 인코딩한다."""
    parts = Path(path).parts
    rel = parts[parts.index("notes") + 1:] if "notes" in parts else parts[-1:]
    return base.rstrip("/") + "/" + "/".join(urllib.parse.quote(p) for p in rel)


def note_thread(path):
    """노트 HTML 에 심어둔 원본 슬랙 스레드 ts. 없거나 파일이 없으면 None."""
    p = Path(path)
    m = THREAD_META.search(p.read_text(errors="ignore")) if p.exists() else None
    return m and m.group(1)


def note_link(path, url):
    """슬랙 mrkdwn 링크. 제목은 노트의 <h1>, 없으면 파일명.

    마크다운 [제목](링크) 는 슬랙 API 로 보내면 링크가 안 되고 글자 그대로 뜬다 —
    같은 것을 슬랙에서 그리는 표기가 <링크|제목> 이다.
    """
    p = Path(path)
    m = H1.search(p.read_text(errors="ignore")) if p.exists() else None
    title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", m.group(1)))).strip() if m else p.stem
    return f"<{url}|{esc(title)}>"


def esc(text):
    """슬랙 텍스트 이스케이프. &, <, > 만 바꾸면 된다."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def git(*args, run=subprocess.check_output):
    return run(["git", "-c", "core.quotePath=false", *args], text=True)


def daily_batches(since=DAILY_SINCE, ref="main", run=subprocess.check_output):
    """지난 창의 main first-parent 커밋마다 (sha, 제목, 추가된 노트 경로들). 오래된 것부터.

    first-parent 만 보면 PR 머지는 머지 커밋 하나로, 직접 푸시는 그 커밋으로 잡힌다 —
    PR 안의 개별 커밋은 안 센다. 노트는 첫 부모와의 diff 에서 추가(A)된 것만.
    """
    log = git("log", "--first-parent", "--reverse", f"--since={since}", "--format=%H%x09%s", ref, run=run)
    out = []
    for line in log.splitlines():
        sha, _, subject = line.partition("\t")
        files = git("diff", "--name-only", "--diff-filter=A", f"{sha}^", sha, "--", *NOTE_GLOBS, run=run)
        out.append((sha, subject, [Path(f) for f in files.splitlines() if f]))
    return out


def daily(batches, token, channel, base=BASE_URL, group=""):
    """"오늘의 정리 >>>" 한 글 + 커밋당 답글 하나. 노트가 하나도 없으면 아무것도 안 보내고 None.

    답글은 그 커밋에 들어간 노트 링크만 한 줄씩 — PR 번호·커밋 제목은 안 쓴다 (2026-09-29, 읽는 사람이 원치 않음).
    멘션으로 시작한 노트(slack-thread 태그)는 요청자가 기다리는 원본 스레드에도 링크를 단다 —
    일일 스레드와 중복이지만 요청자는 자기 스레드에서 바로 받는다.
    """
    batches = [(sha, subject, files) for sha, subject, files in batches if files]
    if not batches:
        return None
    root = call("chat.postMessage", token, channel=channel, text=esc("오늘의 정리 >>>"))["ts"]
    for _sha, _subject, files in batches:
        links = [note_link(p, note_url(p, base)) for p in files]
        call("chat.postMessage", token, channel=channel, text="\n".join(links), thread_ts=root)
        for p, link in zip(files, links):
            origin = note_thread(p)
            if origin:
                call("chat.postMessage", token, channel=channel,
                     text=f"<!subteam^{group}>\n{link}" if group else link, thread_ts=origin)
    return root


def mentions(token, channel):
    """봇이 멘션된 스레드 목록. 부모·답글 어디에 유튜브 링크가 있어도 찾는다.

    상태 파일은 두지 않는다 — 슬랙 자체가 상태다. 봇이 이미 링크를 답글로 단 스레드는 done=True.
    """
    bot = call("auth.test", token)["user_id"]
    out = []
    for m in call("conversations.history", token, channel=channel, limit=HISTORY_LIMIT)["messages"]:
        msgs = (call("conversations.replies", token, channel=channel, ts=m["ts"])["messages"]
                if m.get("reply_count") else [m])
        # subtype 이 붙은 건 채널 참여/봇 알림 같은 시스템 메시지다 — 사람이 부른 게 아니다
        hit = next((t for t in msgs
                    if f"<@{bot}>" in t.get("text", "") and not t.get("subtype") and t.get("user") != bot), None)
        if not hit:
            continue
        vids = [v for t in msgs for v in YOUTUBE.findall(t.get("text", ""))]
        out.append({
            "thread_ts": m["ts"],
            "video": f"https://www.youtube.com/watch?v={vids[0]}" if vids else None,
            "text": " ".join(hit.get("text", "").split())[:70],
            "done": any(t.get("user") == bot and "http" in t.get("text", "") for t in msgs),
        })
    return out


def post(path, token, channel, base=BASE_URL, thread_ts=None, group=""):
    """제목을 올리고 링크는 그 스레드 답글로 넣는다. thread_ts 가 있으면 그 스레드에 이어 단다.

    노트에 slack-thread 태그가 있으면(멘션으로 시작한 건) 새 글을 만들지 않고
    요청이 걸린 그 스레드에 링크만 답글로 단다. 채널 스레드 체인은 건드리지 않는다.

    group 은 멘션으로 시작한 노트(slack-thread 태그)의 답글에만 붙는다 — 사람이 봇을 불러
    요청한 건이라 알릴 대상이 있다. 액션이 자동 발행하는 건은 채널에 조용히 쌓이게 둔다.

    반환은 (링크, 스레드 부모 ts) — 다음 파일에 그대로 넘기면 같은 스레드로 모인다.
    """
    url = note_url(path, base)
    link = note_link(path, url)
    origin = note_thread(path)
    if origin:
        call("chat.postMessage", token, channel=channel,
             text=f"<!subteam^{group}>\n{link}" if group else link, thread_ts=origin)
        return url, thread_ts
    body = call("chat.postMessage", token, channel=channel, text=f"{Path(path).stem} 정리",
                **({"thread_ts": thread_ts} if thread_ts else {}))
    root = thread_ts or body["ts"]
    call("chat.postMessage", token, channel=channel, text=link, thread_ts=root)
    return url, root


def selftest():
    assert note_url("notes/invest/260826_a.html") == "https://mand2.github.io/rich-to-be/invest/260826_a.html"
    assert note_url("/x/notes/morning-routine/한글.html", "http://e.com") == "http://e.com/morning-routine/%ED%95%9C%EA%B8%80.html"
    assert note_url("bare.html", "http://e.com/") == "http://e.com/bare.html"
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write('# 주석\nSLACK_BOT_TOKEN="xoxb-1"\n\nSLACK_CHANNEL = C0X \nBROKEN\n')
    assert dotenv(Path(f.name)) == {"SLACK_BOT_TOKEN": "xoxb-1", "SLACK_CHANNEL": "C0X"}

    assert YOUTUBE.findall("보세요 <https://www.youtube.com/watch?v=Bu0xNDLNabc&t=3s>") == ["Bu0xNDLNabc"]
    assert YOUTUBE.findall("https://youtu.be/aBcDeFgHiJk 랑 youtube.com/live/12345678901") == ["aBcDeFgHiJk", "12345678901"]
    assert YOUTUBE.findall("링크 없음") == []
    assert note_thread("notes/does-not-exist.html") is None
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as g:
        g.write('<meta name="slack-thread" content="1787897791.593189">')
    assert note_thread(g.name) == "1787897791.593189"
    # 링크 제목은 <h1>, 없으면 파일명. 슬랙 특수문자는 이스케이프
    assert note_link("notes/does-not-exist.html", "http://e.com/x") == "<http://e.com/x|does-not-exist>"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as h:
        h.write("<h1>\n삼성 &amp; <b>SK</b> 정리\n</h1>")
    assert note_link(h.name, "http://e.com/x") == "<http://e.com/x|삼성 &amp; SK 정리>", note_link(h.name, "u")

    global call
    real, sent = call, []
    call = lambda m, tok, **kw: (sent.append(kw), {"ok": True, "ts": f"t{len(sent)}"})[1]
    try:
        _, root = post("notes/invest/a.html", "x", "C0X", "http://e.com")
        assert root == "t1", root
        _, root2 = post("notes/invest/b.html", "x", "C0X", "http://e.com", root)
        assert root2 == root
        # 제목은 채널(첫 건)·같은 스레드(둘째 건), 링크는 늘 스레드 답글
        assert [(s["text"], s.get("thread_ts")) for s in sent] == [
            ("a 정리", None), ("<http://e.com/invest/a.html|a>", "t1"),
            ("b 정리", "t1"), ("<http://e.com/invest/b.html|b>", "t1"),
        ], sent
        # 멘션 노트는 새 글 없이 원본 스레드에 링크만, 채널 체인(root)은 그대로 넘어간다
        # 액션이 자동 발행하는 건은 group 을 줘도 멘션하지 않는다
        sent.clear()
        post("notes/invest/c.html", "x", "C0X", "http://e.com", group="S0G")
        assert [s["text"] for s in sent] == ["c 정리", "<http://e.com/invest/c.html|c>"], sent

        _, root3 = post(g.name, "x", "C0X", "http://e.com", root)
        assert root3 == root
        assert sent[-1] == {"channel": "C0X",
                            "text": f"<http://e.com/{Path(g.name).name}|{Path(g.name).stem}>",
                            "thread_ts": "1787897791.593189"}, sent[-1]
        # 멘션으로 시작한 건만 그룹을 부른다
        post(g.name, "x", "C0X", "http://e.com", root, group="S0G")
        assert sent[-1]["text"] == (
            f"<!subteam^S0G>\n<http://e.com/{Path(g.name).name}|{Path(g.name).stem}>"), sent[-1]

        # --daily: 커밋마다 답글 하나, 노트 없는 커밋은 건너뛰고, 멘션 건은 원본 스레드에도
        sent.clear()
        batches = [
            ("s1", "Merge pull request #11 from mand2/feature/x", [Path("notes/invest/a.html"), Path("notes/invest/b.html")]),
            ("s2", "fix: <스크립트> & 정리", []),
            ("s3", "invest: c.html", [Path("notes/invest/c.html"), Path(g.name)]),
        ]
        root = daily(batches, "x", "C0X", "http://e.com", group="S0G")
        assert root == "t1", root
        # 답글엔 PR 번호·커밋 제목 없이 노트 링크만
        assert [(s["text"], s.get("thread_ts")) for s in sent] == [
            ("오늘의 정리 &gt;&gt;&gt;", None),
            ("<http://e.com/invest/a.html|a>\n<http://e.com/invest/b.html|b>", "t1"),
            (f"<http://e.com/invest/c.html|c>\n<http://e.com/{Path(g.name).name}|{Path(g.name).stem}>", "t1"),
            (f"<!subteam^S0G>\n<http://e.com/{Path(g.name).name}|{Path(g.name).stem}>", "1787897791.593189"),
        ], sent
        # 새 노트가 없으면 아무것도 안 보낸다
        sent.clear()
        assert daily([("s2", "chore", [])], "x", "C0X") is None and sent == []
    finally:
        call = real

    # daily_batches: git 을 흉내 내 first-parent 로그 → 커밋별 추가 노트. 노트 없는 커밋도 (빈 목록으로) 남긴다
    def fake_git(cmd, text=True):
        if cmd[3] == "log":
            assert "--first-parent" in cmd and "--reverse" in cmd and f"--since={DAILY_SINCE}" in cmd, cmd
            return "aaa\tMerge pull request #9 from x\nbbb\tfix: 버튼\n"
        assert cmd[3:6] == ["diff", "--name-only", "--diff-filter=A"] and cmd[8] == "--" and tuple(cmd[9:]) == NOTE_GLOBS, cmd
        return {"aaa^": "notes/invest/260929_한글.html\n", "bbb^": ""}[cmd[6]]
    assert daily_batches(run=fake_git) == [
        ("aaa", "Merge pull request #9 from x", [Path("notes/invest/260929_한글.html")]),
        ("bbb", "fix: 버튼", []),
    ], daily_batches(run=fake_git)
    assert daily_batches(run=lambda cmd, text=True: "") == []
    print("ok")


def main():
    # .env 를 환경변수로 올려 두면 뒤의 default= 하나로 CI(환경변수)와 로컬(.env)이 같은 경로를 탄다.
    # 이미 있는 환경변수가 이긴다 — CI 는 시크릿을 그쪽으로 넘긴다.
    for k, v in dotenv().items():
        os.environ.setdefault(k, v)

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--channel", default=os.environ.get("SLACK_CHANNEL"))
    ap.add_argument("--group", default=os.environ.get("SLACK_MENTION_GROUP") or "", help="멘션할 사용자 그룹 ID")
    ap.add_argument("--base-url", default=os.environ.get("NOTES_BASE_URL") or BASE_URL)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mentions", action="store_true", help="봇이 멘션된 스레드를 탭 구분으로 출력")
    ap.add_argument("--daily", action="store_true", help="지난 24시간 main 의 새 노트를 '오늘의 정리' 스레드 하나로")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not (token and a.channel):
        sys.exit(".env 의 SLACK_BOT_TOKEN / SLACK_CHANNEL(--channel) 이 있어야 한다")
    if a.mentions:
        for i, m in enumerate(mentions(token, a.channel), 1):
            print(f"{i}\t{'done' if m['done'] else 'new'}\t{m['thread_ts']}\t{m['video'] or '-'}\t{m['text']}")
        return
    if a.daily:
        root = daily(daily_batches(), token, a.channel, a.base_url, a.group)
        print(f"오늘의 정리 -> {root}" if root else "지난 24시간에 새 노트 없음")
        return
    if not a.paths:
        sys.exit("보낼 노트 파일 경로가 있어야 한다")
    ts = None
    for p in a.paths:
        url, ts = post(p, token, a.channel, a.base_url, ts, a.group)   # 첫 메시지가 스레드 부모
        print(f"{p} -> {url}")


if __name__ == "__main__":
    main()
