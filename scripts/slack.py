#!/usr/bin/env python3
"""notes/*.html 을 슬랙 채널에 올린다. 파일당 "<파일명> 정리 >>>" 메시지 + 스레드에 파일. 외부 의존성 0 (urllib 만 쓴다).

리포 루트 .env 에 두 줄 (환경변수로 이미 있으면 그쪽이 이긴다). .env.example 참고:

    SLACK_BOT_TOKEN=xoxb-...   # scopes: files:write, chat:write
    SLACK_CHANNEL=C0XXXXXXX    # 봇을 채널에 /invite 해 둘 것

    .venv/bin/python scripts/slack.py notes/morning-routine/260826_한경-모닝루틴.html
    .venv/bin/python scripts/slack.py --selftest

files.upload 은 2025 년에 죽었다. getUploadURLExternal -> PUT -> completeUploadExternal 3단계가 현행이다.
"""
import argparse
import json
import mimetypes
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://slack.com/api/"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


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


def multipart(filename, blob):
    """upload_url 에 보낼 multipart/form-data 본문. (content_type, body)"""
    boundary = "----richtobe"  # ponytail: 고정 boundary. 노트 HTML 에 이 문자열이 들어갈 일이 없어서 충돌 검사를 뺐다.
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode()
    return f"multipart/form-data; boundary={boundary}", head + blob + f"\r\n--{boundary}--\r\n".encode()


def upload(path, token, channel):
    """채널에 "<파일명> 정리 >>>" 를 올리고, 그 스레드에 파일을 붙인다."""
    path = Path(path)
    blob = path.read_bytes()
    parent = call("chat.postMessage", token, channel=channel, text=f"{path.stem} 정리 >>>")
    slot = call("files.getUploadURLExternal", token, filename=path.name, length=len(blob))
    ctype, body = multipart(path.name, blob)
    urllib.request.urlopen(
        urllib.request.Request(slot["upload_url"], data=body, headers={"Content-Type": ctype})
    ).read()
    done = call(
        "files.completeUploadExternal",
        token,
        files=json.dumps([{"id": slot["file_id"], "title": path.stem}]),
        channel_id=channel,
        thread_ts=parent["ts"],
    )
    return done["files"][0].get("permalink", "")


def selftest():
    ctype, body = multipart("a b.html", b"<p>hi</p>")
    assert "boundary=----richtobe" in ctype
    assert b'filename="a b.html"' in body and b"Content-Type: text/html" in body
    assert body.endswith(b"\r\n------richtobe--\r\n") and b"<p>hi</p>\r\n--" in body
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write('# 주석\nSLACK_BOT_TOKEN="xoxb-1"\n\nSLACK_CHANNEL = C0X \nBROKEN\n')
    assert dotenv(Path(f.name)) == {"SLACK_BOT_TOKEN": "xoxb-1", "SLACK_CHANNEL": "C0X"}
    print("ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--channel", default=os.environ.get("SLACK_CHANNEL"))  # 없으면 .env
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
        print(f"{p} -> {upload(p, token, a.channel)}")


if __name__ == "__main__":
    main()
