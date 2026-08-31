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

# main 워크트리면 그대로 푸시한다.
if [ "$(git rev-parse --absolute-git-dir)" = "$(git rev-parse --path-format=absolute --git-common-dir)" ]; then
  git push -q || echo "push 실패: 커밋은 됐지만 푸시 안 됨"
  exit 0
fi

br=$(git rev-parse --abbrev-ref HEAD)

# 병렬 에이전트(slack-mention-notes)는 건마다 푸시하면 Actions 런이 건수만큼 돈다.
# 커밋만 남기고 메인 세션이 cherry-pick 해서 한 번에 푸시한다.
# ponytail: isolation:"worktree" 가 붙이는 브랜치 이름에 기댄다. 이름 규칙이 바뀌면 여기도 바뀐다.
case "$br" in worktree-agent-*) exit 0 ;; esac

# 그 밖의 워크트리(스킬 격리 브랜치)면 브랜치를 올리고 PR 을 연다.
# main 은 사람이 머지할 때 움직이고, 그때 pages.yml 이 돌아 발행된다.
git push -q -u origin "$br" || { echo "push 실패: 커밋은 됐지만 푸시 안 됨"; exit 0; }
command -v gh >/dev/null 2>&1 || { echo "브랜치 $br 푸시됨. gh 가 없어 PR 은 직접 열어라"; exit 0; }
# 열려 있는 PR 이 있을 때만 재사용한다. 닫힌 PR 이 남아 있어도 새로 연다.
url=$(gh pr view --json state,url -q 'select(.state == "OPEN") | .url' 2>/dev/null)
[ -n "$url" ] || url=$(gh pr create --base main --fill 2>/dev/null | tail -1)
if [ -n "$url" ]; then echo "PR: $url"; else echo "브랜치 $br 푸시됨. PR 생성 실패 — 직접 열어라"; fi
