#!/bin/sh
# PreToolUse(Skill) 훅. 스킬 작업은 main 이 아니라 격리 worktree 브랜치에서 하게 만든다.
# 훅은 세션의 cwd 를 못 바꾸므로 직접 worktree 를 만들지 않고, deny 로 되돌려
# EnterWorktree 를 먼저 부르게 시킨다 (EnterWorktree 가 새 브랜치까지 만들어 준다).
skill=$(jq -r '.tool_input.skill // empty')
[ -z "$skill" ] && exit 0

# 격리할 스킬만 적는다 (allowlist). 지금 작업물을 보는 스킬 — code-review, security-review,
# simplify, run — 을 넣으면 안 된다. worktree.baseRef 기본값이 fresh 라 새 워크트리는
# origin/main 에서 분기하고 커밋 안 된 변경분을 안 가져가서, 리뷰할 게 거기 없다.
# slack-mention-notes 도 빠져 있다 — 스스로 worktree 에이전트를 띄우므로 중첩되면 안 된다.
case "$skill" in
  youtube-study-note|news-briefing-digest) ;;
  *) exit 0 ;;
esac

# 이미 worktree 안이면 통과. git 리포가 아니면 EnterWorktree 도 못 쓰니 통과.
gd=$(git rev-parse --absolute-git-dir 2>/dev/null) || exit 0
[ "$gd" != "$(git rev-parse --path-format=absolute --git-common-dir)" ] && exit 0

name=$(printf '%s' "$skill" | tr -c 'A-Za-z0-9._-' '-')
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"main 워크트리다. EnterWorktree(name: \\"%s\\") 로 격리 브랜치에 먼저 들어간 뒤 이 스킬을 다시 호출해라."}}' "$name"
