#!/usr/bin/env python3
"""
모닝스캔 브리지 — cmux 브라우저 패널의 "정리하기" 버튼을 이 터미널의 스킬 호출로 바꾼다.

브라우저 패널 안의 페이지는 JS 라서 터미널을 직접 못 건드린다. 이 서버가 127.0.0.1 에서 버튼 클릭을 받아
`cmux send` 로 대상 터미널 서피스에 `/youtube-study-note <url>` 또는 `/news-briefing-digest <url>` 을 타이핑하고
Enter 를 친다. 그러면 Claude Code 가 평소처럼 그 스킬을 돈다. (2026-09-29 cmux 안에서 실측: 패널→localhost fetch,
cmux send→프롬프트 입력 둘 다 됨.)

    .venv/bin/python .claude/skills/morning-scan/scripts/bridge.py             # 띄우기 (백그라운드로)
    .venv/bin/python .claude/skills/morning-scan/scripts/bridge.py --selftest  # cmux 없이 로직 검증

- 페이지:   GET /            → .work/morning-scan/morning-scan.html 을 그대로 서빙 (요청마다 새로 읽는다)
- 상태:     GET /health      → "ok morning-scan-bridge"
- 버튼:     GET /note?v=<videoId>&skill=<스킬>  → cmux send 후 JSON
- 대상 터미널은 시작할 때 CMUX_SURFACE_ID 를 .work/morning-scan/bridge-target 에 적어 두고, /note 마다 그 파일을 읽는다.
  그래서 이미 떠 있는 브리지가 있으면 새로 띄우지 않고 파일만 갱신하고 끝낸다 — 새 세션의 터미널로 자연히 바뀐다.
- 포트는 scan.py 의 BRIDGE_PORT. 127.0.0.1 에만 묶는다.

터미널에 들어가는 문자열은 이 파일의 command_for() 가 조립한 것뿐이다 — 스킬 이름은 SKILL_LABEL 화이트리스트,
영상 ID 는 11자 [A-Za-z0-9_-] 만 통과한다. 외부에서 온 텍스트가 그대로 터미널로 가는 경로는 없다.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan import BRIDGE_PORT, DEFAULT_OUT, SKILL_LABEL, watch_url  # noqa: E402

TARGET_FILE = DEFAULT_OUT.parent / "bridge-target"
HEALTH_TEXT = "ok morning-scan-bridge"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# ponytail: 이 셸엔 cmux 가 PATH 에 없을 수 있다 (launchd·iTerm). 앱 번들 안의 CLI 를 두 번째 후보로 둔다.
CMUX_FALLBACK = "/Applications/cmux.app/Contents/Resources/bin/cmux"


class BridgeError(Exception):
    pass


def find_cmux():
    return shutil.which("cmux") or (CMUX_FALLBACK if os.path.exists(CMUX_FALLBACK) else None)


def command_for(video_id, skill):
    """버튼 요청을 터미널에 넣을 한 줄로 바꾼다. 검증도 여기서."""
    if skill not in SKILL_LABEL:
        raise BridgeError(f"모르는 스킬: {skill!r}")
    if not video_id or not VIDEO_ID.match(video_id):
        raise BridgeError(f"videoId 형식 오류: {video_id!r}")
    # 끝의 \n 은 리터럴 백슬래시-n 두 글자다. cmux send 가 Enter 로 해석한다.
    return f"/{skill} {watch_url(video_id)}\\n"


def read_target():
    try:
        surface = TARGET_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise BridgeError(f"{TARGET_FILE} 가 없다 — 브리지를 cmux 안에서 다시 띄운다")
    if not surface:
        raise BridgeError(f"{TARGET_FILE} 가 비어 있다")
    return surface


def send_to_terminal(text, surface=None, runner=None):
    surface = surface or read_target()
    cmux = find_cmux()
    if not cmux:
        raise BridgeError("cmux CLI 를 못 찾았다")
    runner = runner or subprocess.run
    try:
        runner([cmux, "send", "--surface", surface, "--", text],
               check=True, capture_output=True, text=True, timeout=10)
    except subprocess.CalledProcessError as err:
        raise BridgeError(f"cmux send 실패: {(err.stderr or err.stdout or '').strip()}")
    except subprocess.TimeoutExpired:
        raise BridgeError("cmux send 응답 없음 (10초)")
    return surface


class Handler(BaseHTTPRequestHandler):
    server_version = "morning-scan-bridge"

    def _reply(self, status, body, ctype="text/plain; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        # 페이지는 이 서버가 서빙하니 same-origin 이지만, file:// 로 연 경우도 통하게 둔다.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/health":
            return self._reply(200, HEALTH_TEXT)
        if url.path == "/":
            try:
                html = DEFAULT_OUT.read_bytes()
            except FileNotFoundError:
                return self._reply(404, f"{DEFAULT_OUT} 가 없다 — scan.py 를 먼저 돌린다")
            return self._reply(200, html, "text/html; charset=utf-8")
        if url.path == "/note":
            q = urllib.parse.parse_qs(url.query)
            try:
                text = command_for(q.get("v", [""])[0], q.get("skill", [""])[0])
                surface = send_to_terminal(text)
            except BridgeError as err:
                print(f"FAIL  {err}", flush=True)
                return self._reply(400, json.dumps({"ok": False, "error": str(err)}, ensure_ascii=False),
                                   "application/json; charset=utf-8")
            print(f"sent  {text[:-2]}  -> {surface}", flush=True)
            return self._reply(200, json.dumps({"ok": True, "sent": text[:-2], "surface": surface}, ensure_ascii=False),
                               "application/json; charset=utf-8")
        return self._reply(404, "not found")

    def log_message(self, *args):  # 기본 액세스 로그는 끈다. sent/FAIL 줄만 남긴다.
        pass


def already_running():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{BRIDGE_PORT}/health", timeout=1) as res:
            return res.read().decode("utf-8", "replace").startswith(HEALTH_TEXT)
    except (urllib.error.URLError, OSError):
        return False


def serve(surface):
    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    TARGET_FILE.write_text(surface + "\n", encoding="utf-8")
    if already_running():
        print(f"OK  브리지 이미 실행 중 — 대상만 {surface} 로 갱신. http://127.0.0.1:{BRIDGE_PORT}/", flush=True)
        return
    if not find_cmux():
        raise BridgeError("cmux CLI 를 못 찾았다 — cmux 안에서 돌리고 있는지 확인")
    httpd = ThreadingHTTPServer(("127.0.0.1", BRIDGE_PORT), Handler)
    print(f"OK  브리지 시작 http://127.0.0.1:{BRIDGE_PORT}/  -> {surface}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


# ------------------------------------------------------------------- selftest

def selftest():
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    def raises(fn):
        try:
            fn()
        except BridgeError:
            return True
        return False

    cmd = command_for("tsDTfVGqCeE", "youtube-study-note")
    surface = send_to_terminal(cmd, surface="surface:8", runner=fake_run)
    checks = [
        ("명령 형식", cmd == "/youtube-study-note https://www.youtube.com/watch?v=tsDTfVGqCeE\\n"),
        ("다이제스트 스킬", command_for("xfaUHclI_yE", "news-briefing-digest").startswith("/news-briefing-digest ")),
        ("Enter 는 리터럴 \\n 두 글자", cmd.endswith("\\n") and not cmd.endswith("\n")),
        ("모르는 스킬 거부", raises(lambda: command_for("tsDTfVGqCeE", "rm -rf"))),
        ("videoId 길이 검사", raises(lambda: command_for("short", "youtube-study-note"))),
        ("videoId 문자 검사 (셸 메타문자)", raises(lambda: command_for("a;b$(x)`c`", "youtube-study-note"))),
        ("cmux send 인자 (셸 없이 리스트)", bool(calls) and calls[0][1:5] == ["send", "--surface", "surface:8", "--"]),
        ("대상 서피스 반환", surface == "surface:8"),
        ("포트는 scan.py 와 공유", isinstance(BRIDGE_PORT, int) and 1024 < BRIDGE_PORT < 65536),
    ]
    print()
    bad = 0
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        bad += 0 if ok else 1
    print()
    return bad == 0


def main(argv):
    if "--selftest" in argv:
        sys.exit(0 if selftest() else 1)
    surface = os.environ.get("CMUX_SURFACE_ID", "").strip()
    if "--surface" in argv:
        surface = argv[argv.index("--surface") + 1]
    if not surface:
        raise BridgeError("CMUX_SURFACE_ID 가 비어 있다 — cmux 터미널이 아니면 브리지는 필요 없다")
    serve(surface)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except BridgeError as err:
        print(f"FAIL  {err}", file=sys.stderr)
        sys.exit(1)
