#!/usr/bin/env python3
"""발행된 노트 링크를 슬랙 채널에 올린다. 파일당 "<파일명> 정리 >>> <링크>" 한 줄. 외부 의존성 0 (urllib 만 쓴다).

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


def post(path, token, channel, base=BASE_URL):
    url = note_url(path, base)
    call("chat.postMessage", token, channel=channel, text=f"{Path(path).stem} 정리 >>> {url}")
    return url


def selftest():
    assert note_url("notes/invest/260826_a.html") == "https://mand2.github.io/rich-to-be/invest/260826_a.html"
    assert note_url("/x/notes/morning-routine/한글.html", "http://e.com") == "http://e.com/morning-routine/%ED%95%9C%EA%B8%80.html"
    assert note_url("bare.html", "http://e.com/") == "http://e.com/bare.html"
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write('# 주석\nSLACK_BOT_TOKEN="xoxb-1"\n\nSLACK_CHANNEL = C0X \nBROKEN\n')
    assert dotenv(Path(f.name)) == {"SLACK_BOT_TOKEN": "xoxb-1", "SLACK_CHANNEL": "C0X"}
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
    for p in a.paths:
        print(f"{p} -> {post(p, token, a.channel, a.base_url)}")


if __name__ == "__main__":
    main()
