#!/usr/bin/env bash
# 경제 채널 모닝스캔 — launchd/cron 이 부르는 진입점. 손으로 쓸 땐 스킬을 부르면 되고 이 파일은 필요 없다.
# 1) scan.py 로 유튜브 데이터를 받아 .work/morning-scan/morning-scan.html 생성
# 2) claude -p 로 morning-scan 스킬을 "발행만" 모드로 불러 그 파일을 Artifact 로 발행
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

# launchd/cron 은 최소 PATH 만 물려준다. claude 를 찾으려면 직접 깔아줘야 한다.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

mkdir -p .work/morning-scan
LOG=".work/morning-scan/run.log"
exec > >(tee -a "$LOG") 2>&1

echo "─────────────────────────────────────────────"
echo "시작: $(date '+%Y-%m-%d %H:%M:%S %Z')"

if [ ! -f .env ]; then
  echo "FAIL  .env 파일이 없습니다. .env.example 을 복사해서 만드세요."
  exit 1
fi

# 키와 토큰은 여기서만 환경으로 들어간다. 로그에도 프롬프트에도 남지 않는다.
set -a
# shellcheck disable=SC1091
. ./.env
set +a

if [ ! -x .venv/bin/python ]; then
  echo "FAIL  .venv/bin/python 이 없습니다. 리포 루트에서 돌리고 있는지 확인하세요: $ROOT"
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "FAIL  claude 를 찾을 수 없습니다. 'which claude' 결과를 run.sh 의 PATH 에 추가하세요."
  exit 1
fi

echo "[1/2] 유튜브 데이터 수집"
.venv/bin/python .claude/skills/morning-scan/scripts/scan.py

# ponytail: 2026-09-04 실측(claude 2.1.260) — print 모드(-p)에는 Artifact 툴이 없다. --allowedTools/--tools 로도 안 생긴다.
# 그래서 기본은 수집까지만 하고, 발행은 대화 세션에서 "/morning-scan 발행만" 으로 한다.
# print 모드에 Artifact 툴이 생기면 .env 에 MORNING_SCAN_PUBLISH=claude 를 넣어 아래를 켜고, 한 번 돌려 FAIL 이 안 나는지 본다.
if [ "${MORNING_SCAN_PUBLISH:-}" = claude ]; then
  echo "[2/2] Artifact 발행 (claude -p)"
  out=$(claude -p "/morning-scan 발행만" 2>&1) || { echo "$out"; echo "FAIL  claude -p 종료 코드 오류"; exit 1; }
  echo "$out"
  case "$out" in FAIL*|*$'\n'FAIL*) echo "FAIL  발행 단계가 FAIL 을 보고했다"; exit 1 ;; esac
else
  echo "[2/2] 발행 건너뜀 — 대화 세션에서 '/morning-scan 발행만' 을 돌리면 위 파일이 Artifact 로 올라간다"
fi

echo "완료: $(date '+%Y-%m-%d %H:%M:%S %Z')"
