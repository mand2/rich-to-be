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

# 노트 파일만 담는다. notes/index.html 은 발행 때 Actions 가 채우므로 커밋하지 않는다
# — 로컬에서 build-notes-index.py 를 돌려 index 가 더러워져도 여기서 딸려 들어가지 않는다.
git add -A -- 'notes/*/*.html' || exit 0
git diff --cached --quiet -- 'notes/*/*.html' && exit 0

n=$(printf '%s\n' "$files" | wc -l | tr -d ' ')
one=$(printf '%s\n' "$files" | head -1 | cut -c4-)
if [ "$n" = 1 ]; then
  msg="$(basename "$(dirname "$one")"): $(basename "$one")"
else
  msg="notes: ${n}건 갱신"
fi

git commit -q -m "$msg" -- 'notes/*/*.html' || exit 0
git push -q || echo "push 실패: 커밋은 됐지만 푸시 안 됨"
