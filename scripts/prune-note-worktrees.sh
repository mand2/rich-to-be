#!/bin/sh
# SessionStart 훅. PR 이 머지된 스킬 격리 워크트리와 그 로컬 브랜치를 치운다.
# 머지는 보통 다른 세션이 끝난 뒤에 일어나므로 세션 시작 때 쓸어담는 게 유일한 타이밍이다.
# 리모트 브랜치는 GitHub 의 delete_branch_on_merge 가 머지 시점에 지운다 — 여기서 안 건드린다.
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0

# 워크트리 안에서는 자기 자신을 지울 수 없다. main 워크트리에서만 돈다.
[ "$(git rev-parse --absolute-git-dir)" = "$(git rev-parse --path-format=absolute --git-common-dir)" ] || exit 0
# 머지 여부는 gh 로만 확인한다. squash 머지는 커밋 sha 가 안 남아 ancestor 검사로는 못 잡는다.
command -v gh >/dev/null 2>&1 || exit 0

tab=$(printf '\t')
git worktree list --porcelain |
  awk '/^worktree /{w=substr($0,10)} /^branch /{print w"\t"substr($0,8)}' |
  while IFS="$tab" read -r wt br; do
    # .claude/worktrees/ 밑만 본다. 손으로 만든 워크트리는 남의 것이다.
    case "$wt" in "$root"/.claude/worktrees/*) ;; *) continue ;; esac
    b=${br#refs/heads/}
    [ "$(gh pr view "$b" --json state -q .state 2>/dev/null)" = MERGED ] || continue
    # 커밋 안 한 게 하나라도 있으면 --force 가 날린다. 그런 워크트리는 남긴다.
    # gitignore 된 .venv 심볼릭 링크나 notes.js 는 -uall 에도 안 잡히므로 걸리지 않는다.
    if [ -n "$(git -C "$wt" status --porcelain -uall)" ]; then
      echo "정리 건너뜀 ($b): 커밋 안 한 변경분이 있다"
      continue
    fi
    git worktree remove --force "$wt" 2>/dev/null &&
      git branch -qD "$b" 2>/dev/null &&
      echo "정리: $b"
  done
exit 0
