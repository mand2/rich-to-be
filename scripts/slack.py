#!/usr/bin/env python3
"""발행된 노트 링크를 슬랙 채널에 올린다. 외부 의존성 0 (urllib 만 쓴다).

채널엔 "<파일명> 정리" 만 뜨고 Pages 링크는 그 메시지의 스레드 답글로 들어간다 — 채널에 링크 프리뷰가 쌓이지 않는다.
한 번에 여러 개를 보내면 첫 메시지가 스레드 부모가 되고 나머지는 전부 그 스레드에 달린다.

리포 루트 .env 에 두 줄 (환경변수로 이미 있으면 그쪽이 이긴다). .env.example 참고:

    SLACK_BOT_TOKEN=xoxb-...   # scope: chat:write
    SLACK_CHANNEL=C0XXXXXXX    # 봇을 채널에 /invite 해 둘 것

    .venv/bin/python scripts/slack.py notes/morning-routine/260826_한경-모닝루틴.html
    .venv/bin/python scripts/slack.py --selftest

Pages 아티팩트의 루트가 notes/ 라서 notes/ 아래 경로가 그대로 URL 경로가 된다.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://slack.com/api/"
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


def post(path, token, channel, base=BASE_URL, thread_ts=None):
    """제목을 올리고 링크는 그 스레드 답글로 넣는다. thread_ts 가 있으면 그 스레드에 이어 단다.

    반환은 (링크, 스레드 부모 ts) — 다음 파일에 그대로 넘기면 같은 스레드로 모인다.
    """
    url = note_url(path, base)
    body = call("chat.postMessage", token, channel=channel, text=f"{Path(path).stem} 정리",
                **({"thread_ts": thread_ts} if thread_ts else {}))
    root = thread_ts or body["ts"]
    call("chat.postMessage", token, channel=channel, text=url, thread_ts=root)
    return url, root


def selftest():
    assert note_url("notes/invest/260826_a.html") == "https://mand2.github.io/rich-to-be/invest/260826_a.html"
    assert note_url("/x/notes/morning-routine/한글.html", "http://e.com") == "http://e.com/morning-routine/%ED%95%9C%EA%B8%80.html"
    assert note_url("bare.html", "http://e.com/") == "http://e.com/bare.html"
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write('# 주석\nSLACK_BOT_TOKEN="xoxb-1"\n\nSLACK_CHANNEL = C0X \nBROKEN\n')
    assert dotenv(Path(f.name)) == {"SLACK_BOT_TOKEN": "xoxb-1", "SLACK_CHANNEL": "C0X"}

    global call
    real, sent = call, []
    call = lambda m, tok, **kw: (sent.append(kw), {"ok": True, "ts": f"t{len(sent)}"})[1]
    try:
        _, root = post("notes/invest/a.html", "x", "C0X", "http://e.com")
        assert root == "t1", root
        _, root2 = post("notes/invest/b.html", "x", "C0X", "http://e.com", root)
        assert root2 == root
    finally:
        call = real
    # 제목은 채널(첫 건)·같은 스레드(둘째 건), 링크는 늘 스레드 답글
    assert [(s["text"], s.get("thread_ts")) for s in sent] == [
        ("a 정리", None), ("http://e.com/invest/a.html", "t1"),
        ("b 정리", "t1"), ("http://e.com/invest/b.html", "t1"),
    ], sent
    print("ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--channel", default=os.environ.get("SLACK_CHANNEL"))  # 없으면 .env
    ap.add_argument("--base-url", default=os.environ.get("NOTES_BASE_URL") or BASE_URL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    env = dotenv()
    token = os.environ.get("SLACK_BOT_TOKEN") or env.get("SLACK_BOT_TOKEN")
    a.channel = a.channel or env.get("SLACK_CHANNEL")
    if not (a.paths and token and a.channel):
        sys.exit(".env 의 SLACK_BOT_TOKEN / SLACK_CHANNEL(--channel) 과 파일 경로가 있어야 한다")
    ts = None
    for p in a.paths:
        url, ts = post(p, token, a.channel, a.base_url, ts)   # 첫 메시지가 스레드 부모
        print(f"{p} -> {url}")


if __name__ == "__main__":
    main()
