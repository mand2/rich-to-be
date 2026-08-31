#!/bin/sh
# PreToolUse(Skill) · UserPromptSubmit 훅. 스킬 작업은 main 이 아니라 격리 worktree 브랜치에서 하게 만든다.
# 훅은 세션의 cwd 를 못 바꾸므로 직접 worktree 를 만들지 않고, EnterWorktree 를 먼저 부르게 시킨다
# (EnterWorktree 가 새 브랜치까지 만들어 준다).
#
# 입구가 둘이다. Skill 툴 호출은 PreToolUse 로 오지만, 같은 스킬을 /슬래시 커맨드로 부르면
# CLI 가 SKILL.md 를 프롬프트에 펼쳐 넣을 뿐 툴 호출이 없어서 UserPromptSubmit 으로만 온다.
# PreToolUse 만 걸어 두면 슬래시로 들어온 건이 main 에서 그대로 돌아간다
# (2026-08-31 실측: /news-briefing-digest 가 main 에 커밋 6개를 쌓고 PR 없이 푸시됨).
in=$(cat)

skill=$(printf '%s' "$in" | jq -r '.tool_input.skill // empty')
event=PreToolUse
if [ -z "$skill" ]; then
  event=UserPromptSubmit
  # "/news-briefing-digest <URL> 모닝루틴" 처럼 첫 줄 앞머리에 붙어 온다.
  # ponytail: 프롬프트 필드명이 하나로 확정 안 돼 후보 둘을 본다. 실측되면 하나로 줄여라.
  skill=$(printf '%s' "$in" | jq -r '.prompt // .user_prompt // empty' |
    sed -n '1s|^[[:space:]]*/\([A-Za-z0-9._-][A-Za-z0-9._-]*\).*|\1|p')
fi
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
q='\"'
reason="main 워크트리다. EnterWorktree(name: ${q}${name}${q}) 로 격리 브랜치에 먼저 들어간 뒤 이 스킬을 다시 호출해라."

if [ "$event" = PreToolUse ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}' "$reason"
else
  # ponytail: UserPromptSubmit 에는 deny 가 없어 지시만 컨텍스트로 넣는다 — 강제가 아니라 권고다.
  # 무시하고 main 에서 작업하는 일이 실제로 생기면 exit 2 + stderr 로 프롬프트를 통째로 막아라
  # (대신 사용자가 URL 을 다시 쳐야 한다).
  printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}' "$reason"
fi
