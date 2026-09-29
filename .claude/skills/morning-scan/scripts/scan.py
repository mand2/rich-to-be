#!/usr/bin/env python3
"""
경제 채널 모닝스캔 — 지난 24시간 유튜브 업로드를 훑어 HTML 한 장으로 만든다.

- YOUTUBE_API_KEY 는 환경변수, 없으면 리포 루트 .env 에서 읽는다. 키는 코드에도 출력에도 남지 않는다.
- 옆의 template.html 을 채워 <리포>/.work/morning-scan/morning-scan.html 을 쓴다.
- stdout 에 한 줄 요약과 새 영상 목록을 찍는다. 발행(Artifact)은 이 스크립트가 하지 않는다 — SKILL.md 가 한다.

표준 라이브러리만 쓴다. 하루 API 사용량 약 406유닛 (한도 10,000) — references/rules.md 참고.

    .venv/bin/python .claude/skills/morning-scan/scripts/scan.py            # 실행
    .venv/bin/python .claude/skills/morning-scan/scripts/scan.py --selftest # 네트워크 없이 로직 검증
    .venv/bin/python .claude/skills/morning-scan/scripts/scan.py --out X    # 출력 경로 지정
"""

import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3"
KST = timezone(timedelta(hours=9))

# ponytail: 쇼츠 판정은 재생시간뿐이다. 유튜브 API 가 쇼츠 여부를 안 주기 때문에 길이로 자른다.
# 180초는 쇼츠 상한(3분)에서 온 값이다. 3분 넘는 쇼츠가 카드에 끼거나 짧은 정규 영상이 걸러지면 조정한다.
SHORTS_MAX_SEC = 180
# ponytail: 24시간은 "매일 아침 9시 실행" 전제다. 실행 주기를 바꾸면 같이 바꾼다.
WINDOW_HOURS = 24
# ponytail: 한국 증시 정규장 개장 시각. 라이브 전용 채널의 "장 시작 N분 전 방송" 부제에만 쓴다.
MARKET_OPEN_KST = (9, 0)
# ponytail: bridge.py 가 127.0.0.1 에 묶는 포트. 임의로 고른 값이고 충돌하면 바꾼다 (template.html 은 이 값을 치환으로 받는다).
BRIDGE_PORT = 47821
# ponytail: 카드의 "정리하기" 기본 스킬. 제목에 이 단어가 있으면 news-briefing-digest, 아니면 youtube-study-note.
# 한경 모닝루틴 제목 패턴("… #모닝루틴")에서 온 값이다. 다른 브리핑 채널을 추가하면 키워드를 늘린다.
DIGEST_TITLE_KEYWORDS = ("모닝루틴",)
SKILL_LABEL = {
    "youtube-study-note": "스터디 노트",
    "news-briefing-digest": "다이제스트",
}

HERE = Path(__file__).resolve().parent


def find_root(start):
    """스크립트 위치에서 위로 올라가며 .git(디렉토리 또는 worktree 파일)이 있는 곳을 리포 루트로 본다."""
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    return start


ROOT = find_root(HERE)
DEFAULT_OUT = ROOT / ".work" / "morning-scan" / "morning-scan.html"

# rule: "live_only" | "video_only" | "video_and_live"
# 채널 추가·삭제·규칙 변경은 여기서 한다. channel_id / uploads 를 얻는 법은 references/rules.md.
CHANNELS = [
    {
        "name": "한경 코리아마켓",
        "handle": "@hk_koreamarket",
        "channel_id": "UCGCGxsbmG_9nincyI7xypow",
        "uploads": "UUGCGxsbmG_9nincyI7xypow",
        "rule": "live_only",
    },
    {
        "name": "박곰희TV",
        "handle": "@gomhee",
        "channel_id": "UCr7XsrSrvAn_WcU4kF99bbQ",
        "uploads": "UUr7XsrSrvAn_WcU4kF99bbQ",
        "rule": "video_only",
    },
    {
        "name": "박종훈의 지식한방",
        "handle": "@kpunch",
        "channel_id": "UCOB62fKRT7b73X7tRxMuN2g",
        "uploads": "UUOB62fKRT7b73X7tRxMuN2g",
        "rule": "video_only",
    },
    {
        "name": "소수몽키",
        "handle": "@sosumonkey",
        "channel_id": "UCC3yfxS5qC6PCwDzetUuEWg",
        "uploads": "UUC3yfxS5qC6PCwDzetUuEWg",
        "rule": "video_and_live",
    },
    {
        "name": "수페TV",
        "handle": "@supe-tv",
        "channel_id": "UCfnqgWlC5IvJEAPTmyjaixA",
        "uploads": "UUfnqgWlC5IvJEAPTmyjaixA",
        "rule": "video_only",
    },
]

RULE_LABEL = {
    "live_only": "라이브만",
    "video_only": "동영상만",
    "video_and_live": "동영상 + 라이브",
}

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def default_skill(title):
    """카드의 기본 정리 스킬. 브리핑 제목이면 다이제스트, 나머지는 스터디 노트."""
    if any(k in title for k in DIGEST_TITLE_KEYWORDS):
        return "news-briefing-digest"
    return "youtube-study-note"


class ScanError(RuntimeError):
    pass


# ------------------------------------------------------------------- env / key

def load_env_file(path):
    """KEY=VALUE 줄만 읽어 환경에 없는 것만 채운다. 따옴표는 벗긴다. python-dotenv 를 안 넣기 위한 최소 구현."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        os.environ.setdefault(k, v)


def api_key():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        load_env_file(ROOT / ".env")
        key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise ScanError(f"YOUTUBE_API_KEY 가 비어 있습니다. 환경변수로 주거나 {ROOT / '.env'} 에 적으세요.")
    return key


# ---------------------------------------------------------------- API helpers

def api_get(endpoint, params, key):
    params = dict(params)
    params["key"] = key
    url = f"{API}/{endpoint}?" + urllib.parse.urlencode(params, safe=",()/")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        safe_url = url.replace(key, "<KEY>")
        raise ScanError(f"{endpoint} 호출 실패 (HTTP {exc.code})\n  {safe_url}\n  {detail}") from exc
    except urllib.error.URLError as exc:
        raise ScanError(f"{endpoint} 호출 실패 (네트워크): {exc.reason}") from exc


def recent_uploads(channel, key):
    """업로드 재생목록 최근 10건. 1유닛."""
    data = api_get(
        "playlistItems",
        {
            "part": "snippet",
            "playlistId": channel["uploads"],
            "maxResults": 10,
            "fields": "items(snippet(title,publishedAt,resourceId/videoId))",
        },
        key,
    )
    out = []
    for item in data.get("items", []):
        snip = item.get("snippet", {})
        vid = snip.get("resourceId", {}).get("videoId")
        published = snip.get("publishedAt")
        if not vid or not published:
            continue
        out.append(
            {
                "video_id": vid,
                "title": snip.get("title", "").strip(),
                "published": parse_iso(published),
                "channel": channel,
            }
        )
    out.sort(key=lambda v: v["published"], reverse=True)
    return out


def durations_for(video_ids, key):
    """videos.list 는 한 번에 50개까지. {video_id: seconds} 반환. 호출당 1유닛."""
    result = {}
    ids = list(dict.fromkeys(video_ids))
    for start in range(0, len(ids), 50):
        chunk = ids[start:start + 50]
        data = api_get(
            "videos",
            {
                "part": "contentDetails",
                "id": ",".join(chunk),
                "fields": "items(id,contentDetails/duration)",
            },
            key,
        )
        for item in data.get("items", []):
            iso = item.get("contentDetails", {}).get("duration")
            if iso:
                result[item["id"]] = parse_duration(iso)
    return result


def completed_live_ids(channel, key):
    """해당 채널의 최근 '완료된 라이브 방송' videoId 집합. search 라 100유닛 — 필요한 채널만 부른다."""
    data = api_get(
        "search",
        {
            "part": "snippet",
            "channelId": channel["channel_id"],
            "eventType": "completed",
            "type": "video",
            "order": "date",
            "maxResults": 10,
            "fields": "items(id/videoId)",
        },
        key,
    )
    return {i["id"]["videoId"] for i in data.get("items", []) if i.get("id", {}).get("videoId")}


# ------------------------------------------------------------------ utilities

def parse_iso(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def parse_duration(iso):
    """PT1H18M39S -> 4719 (초)"""
    if not iso.startswith("PT"):
        return 0
    total, number = 0, ""
    for ch in iso[2:]:
        if ch.isdigit():
            number += ch
        elif ch in "HMS" and number:
            total += int(number) * {"H": 3600, "M": 60, "S": 1}[ch]
            number = ""
        else:
            number = ""
    return total


def fmt_duration(seconds):
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def fmt_ago(then, now):
    delta = now - then
    days = delta.days
    if days >= 1:
        return f"{days}일 전"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}시간 전"
    return "방금"


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def watch_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def passes_rule(rule, seconds, is_live):
    if seconds <= SHORTS_MAX_SEC:
        return False, "쇼츠"
    if rule == "live_only" and not is_live:
        return False, "라이브 아님"
    if rule == "video_only" and is_live:
        return False, "라이브"
    return True, None


# ------------------------------------------------------------------ rendering

def render_card(entry):
    subnote = ""
    if entry["subnote"]:
        subnote = f'\n        <p class="subnote">{esc(entry["subnote"])}</p>'
    kind_class = "kind live" if entry["is_live"] else "kind"
    kind_label = "라이브" if entry["is_live"] else "동영상"
    primary = entry["skill"]
    other = next(s for s in SKILL_LABEL if s != primary)
    # 카드 전체가 링크(.card-link 오버레이)이고, 버튼은 그 위에 뜬다. 버튼은 브리지가 살아 있을 때만 보인다 (template.html 의 JS).
    return f"""    <div class="card" data-v="{entry['video_id']}">
      <div class="body">
        <div class="meta-top">
          <span class="chan">{esc(entry['channel_name'])}</span>
          <span class="dot"></span>
          <span class="when">{entry['when']}</span>
        </div>
        <h3><a class="card-link" href="{watch_url(entry['video_id'])}" target="_blank" rel="noopener">{esc(entry['title'])}</a></h3>{subnote}
        <div class="actions">
          <button class="act primary" type="button" data-skill="{primary}">정리하기 · {SKILL_LABEL[primary]}</button>
          <button class="act" type="button" data-skill="{other}">{SKILL_LABEL[other]}로</button>
        </div>
      </div>
      <div class="runtime">
        <span class="d">{entry['duration']}</span>
        <span class="{kind_class}">{kind_label}</span>
      </div>
    </div>"""


def render_empty_feed():
    return '    <p class="empty">지난 24시간 새 영상 없음</p>'


def render_quiet(entry):
    return f"""    <a class="qrow" href="{watch_url(entry['video_id'])}" target="_blank" rel="noopener">
      <span class="qchan">{esc(entry['channel_name'])}</span>
      <span class="qtitle">{esc(entry['title'])}</span>
      <span class="qago">{entry['ago']}</span>
    </a>"""


def render_roster():
    cells = []
    for ch in CHANNELS:
        cells.append(
            f"""      <div class="rcell">
        <span class="rname">{esc(ch['name'])}</span>
        <span class="rfilter">{RULE_LABEL[ch['rule']]}</span>
      </div>"""
        )
    return "\n".join(cells)


# ----------------------------------------------------------------------- scan

def scan(key, now):
    """API 를 돌려 (fresh, quiet, filtered) 를 돌려준다. 렌더링은 안 한다."""
    window_start = now - timedelta(hours=WINDOW_HOURS)

    # 1) 채널별 최근 업로드
    uploads = {ch["name"]: recent_uploads(ch, key) for ch in CHANNELS}

    # 2) 재생시간 (채널당 최근 6건, 한 번에)
    wanted = []
    for items in uploads.values():
        wanted.extend(v["video_id"] for v in items[:6])
    durations = durations_for(wanted, key)

    # 3) 라이브 판별이 필요한 채널만 search 를 부른다 (video_and_live 는 어차피 다 통과)
    live_sets = {}
    for ch in CHANNELS:
        if ch["rule"] in ("live_only", "video_only"):
            live_sets[ch["name"]] = completed_live_ids(ch, key)
        else:
            live_sets[ch["name"]] = set()

    fresh, quiet, filtered = [], [], []

    for ch in CHANNELS:
        items = uploads[ch["name"]]
        live_ids = live_sets[ch["name"]]
        picked_any = False

        for video in items:
            seconds = durations.get(video["video_id"])
            if seconds is None:
                continue
            is_live = video["video_id"] in live_ids
            ok, reason = passes_rule(ch["rule"], seconds, is_live)
            in_window = video["published"] >= window_start

            if in_window and not ok:
                filtered.append(
                    {
                        "channel_name": ch["name"],
                        "title": video["title"],
                        "duration": fmt_duration(seconds),
                        "reason": reason,
                    }
                )
                continue
            if not ok:
                continue

            local = video["published"].astimezone(KST)
            if in_window:
                subnote = ""
                if ch["rule"] == "live_only":
                    open_at = local.replace(
                        hour=MARKET_OPEN_KST[0], minute=MARKET_OPEN_KST[1],
                        second=0, microsecond=0,
                    )
                    gap = int((open_at - local).total_seconds() // 60)
                    if 0 < gap <= 120:
                        subnote = f"장 시작 {gap}분 전 방송 시작."
                fresh.append(
                    {
                        "channel_name": ch["name"],
                        "title": video["title"],
                        "video_id": video["video_id"],
                        "published": video["published"],
                        "when": local.strftime("%m/%d %H:%M"),
                        "duration": fmt_duration(seconds),
                        "is_live": is_live,
                        "subnote": subnote,
                        "skill": default_skill(video["title"]),
                    }
                )
                picked_any = True
            elif not picked_any:
                # 창 밖이지만 규칙은 통과한 첫 영상 = 그 채널의 직전 업로드
                quiet.append(
                    {
                        "channel_name": ch["name"],
                        "title": video["title"],
                        "video_id": video["video_id"],
                        "published": video["published"],
                        "ago": fmt_ago(video["published"], now),
                    }
                )
                picked_any = True

    fresh.sort(key=lambda v: v["published"], reverse=True)
    quiet.sort(key=lambda v: v["published"], reverse=True)
    return fresh, quiet, filtered


def dateline_for(now):
    now_kst = now.astimezone(KST)
    return (
        f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일 "
        f"{WEEKDAY_KO[now_kst.weekday()]}요일 · {now_kst.strftime('%H:%M')} KST 기준"
    )


def render(fresh, quiet, filtered, dateline):
    if filtered:
        bits = ", ".join(
            f"{f['channel_name']} {f['duration']}({f['reason']})" for f in filtered
        )
        filtered_line = f"<br>\n    오늘 걸러낸 항목: {esc(bits)}"
    else:
        filtered_line = ""

    template = (HERE / "template.html").read_text(encoding="utf-8")
    return (
        template
        .replace("<!--DATELINE-->", esc(dateline))
        .replace("<!--NEWCOUNT-->", str(len(fresh)))
        .replace("<!--QUIETCOUNT-->", str(len(quiet)))
        .replace("<!--FEED-->", "\n\n".join(render_card(e) for e in fresh) or render_empty_feed())
        .replace("<!--QUIET-->", "\n\n".join(render_quiet(e) for e in quiet))
        .replace("<!--ROSTER-->", render_roster())
        .replace("<!--FILTERED-->", filtered_line)
        .replace("<!--BRIDGE_PORT-->", str(BRIDGE_PORT))
    )


def run(key, out_path, now=None):
    now = now or datetime.now(timezone.utc)
    fresh, quiet, filtered = scan(key, now)
    dateline = dateline_for(now)
    html = render(fresh, quiet, filtered, dateline)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    names = ", ".join(e["channel_name"] for e in fresh) if fresh else "없음"
    print(f"OK  {dateline}")
    print(f"    새 영상 {len(fresh)}건 ({names}) · 조용한 채널 {len(quiet)}곳 · 걸러냄 {len(filtered)}건")
    print(f"    -> {out_path}")
    for e in fresh:
        kind = "라이브" if e["is_live"] else "동영상"
        print(f"    - {e['channel_name']} · {e['title']} · {e['duration']} · {kind} · {watch_url(e['video_id'])}")
    for f in filtered:
        print(f"    x {f['channel_name']} · {f['title']} · {f['duration']} ({f['reason']})")
    return html


# ------------------------------------------------------------------- selftest

def selftest():
    """네트워크 대신 실제로 받아둔 응답을 주입한다. now 도 고정해 날짜가 지나도 결과가 같다."""
    global api_get

    uploads = {
        "UUGCGxsbmG_9nincyI7xypow": [
            ("GqTNwCSiS_k", "2026-09-03T23:42:53Z", "한국경제신문 30분 만에 읽기 | 20260904🌞#모닝루틴 | 환노출 vs 환헤지 ETF"),
            ("5j7Lu6Msfp0", "2026-09-03T09:00:21Z", "카스 vs 테라 당신의 선택은?"),
            ("ooSrteQzfdI", "2026-09-02T23:37:53Z", "한국경제신문 30분 만에 읽기 | 20260903🌞#모닝루틴"),
        ],
        "UUr7XsrSrvAn_WcU4kF99bbQ": [
            ("LEczVIueQAA", "2026-09-04T00:52:03Z", "🏦 만 원으로 채권 투자하는 법 #shorts"),
            ("AeCOMNl11v4", "2026-09-02T11:00:23Z", "⏳ 투자 기회를 잡기 위한 투자공부 방법 A to Z"),
        ],
        "UUOB62fKRT7b73X7tRxMuN2g": [
            ("e3jLOQUfkyI", "2026-09-02T11:20:27Z", "이란 전쟁이 끝날 3가지 신호 (박종훈의 지식한방)"),
        ],
        "UUC3yfxS5qC6PCwDzetUuEWg": [
            ("qXuK203LR5Y", "2026-08-31T11:43:00Z", "연준의 깜짝 긴축 선언에 흔들리는 증시, 9월의 악몽 반복될까"),
        ],
        "UUfnqgWlC5IvJEAPTmyjaixA": [
            ("XzP5Ed8NMsw", "2026-09-01T10:00:09Z", "이 순서로 연금 수령하면 노후준비 끝납니다."),
        ],
    }
    durations = {
        "GqTNwCSiS_k": "PT38M56S",
        "5j7Lu6Msfp0": "PT15S",
        "ooSrteQzfdI": "PT34M15S",
        "LEczVIueQAA": "PT1M1S",
        "AeCOMNl11v4": "PT1H18M39S",
        "e3jLOQUfkyI": "PT26M8S",
        "qXuK203LR5Y": "PT21M4S",
        "XzP5Ed8NMsw": "PT17M52S",
    }
    lives = {"UCGCGxsbmG_9nincyI7xypow": ["GqTNwCSiS_k", "ooSrteQzfdI"]}
    calls = []

    def fake_api_get(endpoint, params, key):
        calls.append(endpoint)
        assert key == "TEST", "키가 환경에서 안 왔다"
        if endpoint == "playlistItems":
            rows = uploads[params["playlistId"]]
            return {"items": [
                {"snippet": {"title": t, "publishedAt": p, "resourceId": {"videoId": v}}}
                for v, p, t in rows
            ]}
        if endpoint == "videos":
            ids = params["id"].split(",")
            return {"items": [
                {"id": i, "contentDetails": {"duration": durations[i]}}
                for i in ids if i in durations
            ]}
        if endpoint == "search":
            ids = lives.get(params["channelId"], [])
            return {"items": [{"id": {"videoId": i}} for i in ids]}
        raise AssertionError(f"unexpected endpoint {endpoint}")

    api_get = fake_api_get
    now = datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc)  # 09-04 10:00 KST

    with tempfile.TemporaryDirectory() as tmp:
        html = run("TEST", Path(tmp) / "out.html", now=now)

    checks = [
        ("새 영상 카드에 한경 라이브", "GqTNwCSiS_k" in html),
        ("38:56 재생시간", "38:56" in html),
        ("라이브 배지", 'class="kind live"' in html),
        ("15초 쇼츠 제외", "5j7Lu6Msfp0" not in html),
        ("1분 1초 쇼츠 제외", "LEczVIueQAA" not in html),
        ("어제 라이브는 창 밖", "ooSrteQzfdI" not in html),
        ("조용한 채널: 박종훈", "e3jLOQUfkyI" in html),
        ("조용한 채널: 박곰희", "AeCOMNl11v4" in html),
        ("조용한 채널: 소수몽키", "qXuK203LR5Y" in html),
        ("조용한 채널: 수페TV", "XzP5Ed8NMsw" in html),
        ("걸러낸 항목 표기", "걸러낸 항목" in html),
        ("장 시작 17분 전 문구 (08:42:53 → 09:00)", "장 시작 17분 전" in html),
        ("날짜줄 고정", "2026년 9월 4일 금요일 · 10:00 KST 기준" in html),
        ("치환 안 된 자리표시자 없음", "<!--" not in html),
        ("모닝루틴 카드 기본 스킬은 다이제스트", 'class="act primary" type="button" data-skill="news-briefing-digest"' in html),
        ("카드에 videoId 데이터 속성", 'data-v="GqTNwCSiS_k"' in html),
        ("브리지 포트 치환", f"const BRIDGE_PORT = {BRIDGE_PORT};" in html),
        ("default_skill", default_skill("이란 전쟁이 끝날 3가지 신호") == "youtube-study-note"
                          and default_skill("한국경제신문 30분 만에 읽기 | #모닝루틴") == "news-briefing-digest"),
        ("외부 이미지 없음", "i.ytimg.com" not in html),
        ("search 는 라이브 판별 채널 4곳만", calls.count("search") == 4),
        ("videos 는 한 번에", calls.count("videos") == 1),
        ("parse_duration", parse_duration("PT1H18M39S") == 4719 and parse_duration("PT15S") == 15),
        ("fmt_duration", fmt_duration(4719) == "1:18:39" and fmt_duration(15) == "0:15"),
    ]

    print()
    bad = 0
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        bad += 0 if ok else 1
    print()
    return bad == 0


# ----------------------------------------------------------------------- main

def main(argv):
    if "--selftest" in argv:
        sys.exit(0 if selftest() else 1)
    out = DEFAULT_OUT
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
    run(api_key(), out)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except ScanError as err:
        print(f"FAIL  {err}", file=sys.stderr)
        sys.exit(1)
