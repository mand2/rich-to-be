#!/bin/sh
# PostToolUse(Write|Edit) 훅. notes/<폴더>/*.html 이 저장되면 커밋·푸시한다.
# tool_input 의 경로를 읽지 않고 git 에게 물어본다 — 한 턴에 노트를 여러 개 써도 다 잡히고,
# 경로 파싱이 없다. self-study 는 .gitignore 라 status 에 안 뜬다.
# 바뀐 노트가 없으면 즉시 빠지므로 노트와 무관한 Write/Edit 에서는 아무 일도 안 한다.
root=$(git rev-parse --show-toplevel) || exit 0
cd "$root" || exit 0

# quotePath=false 라야 한글 파일명이 8진 이스케이프로 안 나온다
files=$(git -c core.quotePath=false status --porcelain -uall -- 'notes/*/*.html')
[ -z "$files" ] && exit 0

# 목록이 노트와 어긋나면 발행이 깨지므로 index 를 다시 만들어 같은 커밋에 넣는다
.venv/bin/python scripts/build-notes-index.py >/dev/null
git add -A notes/ || exit 0
git diff --cached --quiet -- notes/ && exit 0

n=$(printf '%s\n' "$files" | wc -l | tr -d ' ')
one=$(printf '%s\n' "$files" | head -1 | cut -c4-)
if [ "$n" = 1 ]; then
  msg="$(basename "$(dirname "$one")"): $(basename "$one")"
else
  msg="notes: ${n}건 갱신"
fi

git commit -q -m "$msg" -- notes/ || exit 0
git push -q || echo "push 실패: 커밋은 됐지만 푸시 안 됨"
