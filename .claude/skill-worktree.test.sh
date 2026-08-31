#!/bin/sh
# skill-worktree.sh 검사. 임시 리포와 그 안의 worktree 에서 돌려 분기를 확인한다.
# 실행: sh .claude/skill-worktree.test.sh
set -e
SUT=$(cd "$(dirname "$0")" && pwd)/skill-worktree.sh
T=$(cd "$(mktemp -d)" && pwd -P)   # macOS: git 은 /private/var 로 풀어 쓴다
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

R="$T/repo"
mkdir -p "$R" && cd "$R"
git init -q -b main .
# 등록된 커스텀 스킬을 흉내낸다 — 훅은 이 디렉토리를 보고 격리 대상을 정한다
for s in news-briefing-digest youtube-study-note slack-mention-notes; do
  mkdir -p ".claude/skills/$s" && : > ".claude/skills/$s/SKILL.md"
done
git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
git worktree add -q "$T/wt" -b some-branch

run() { printf '%s' "$1" | sh "$SUT"; }

# 1. Skill 툴 호출(PreToolUse) — main 이면 deny
out=$(run '{"hook_event_name":"PreToolUse","tool_input":{"skill":"news-briefing-digest"}}')
case "$out" in *'"permissionDecision":"deny"'*) ;; *) fail "PreToolUse deny 안 나옴: $out" ;; esac
case "$out" in *'EnterWorktree(name: \"news-briefing-digest\")'*) ;; *) fail "이름 이스케이프 깨짐: $out" ;; esac

# 2. 슬래시 커맨드(UserPromptSubmit) — 같은 스킬이 프롬프트 앞머리로 와도 잡힌다
out=$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/news-briefing-digest https://youtu.be/x 모닝루틴"}')
case "$out" in *'"hookEventName":"UserPromptSubmit"'*) ;; *) fail "UserPromptSubmit 미탐지: $out" ;; esac
case "$out" in *additionalContext*) ;; *) fail "additionalContext 없음: $out" ;; esac

# 3. 다른 노트 스킬도 같다
out=$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/youtube-study-note https://youtu.be/x"}')
case "$out" in *additionalContext*) ;; *) fail "youtube-study-note 미탐지: $out" ;; esac

# 4. 이 리포에 등록 안 된 스킬은 통과 — 내장·플러그인 스킬이 여기 해당한다
[ -z "$(run '{"hook_event_name":"PreToolUse","tool_input":{"skill":"code-review"}}')" ] || fail "미등록 스킬을 막았다"
[ -z "$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/code-review high"}')" ] || fail "미등록 슬래시를 막았다"
[ -z "$(run '{"hook_event_name":"PreToolUse","tool_input":{"skill":"ponytail:ponytail"}}')" ] || fail "플러그인 스킬을 막았다"
[ -z "$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/ponytail:ponytail-help"}')" ] || fail "플러그인 슬래시를 막았다"

# 5. 등록돼 있어도 slack-mention-notes 는 예외 (스스로 worktree 를 띄운다)
[ -z "$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/slack-mention-notes"}')" ] || fail "slack-mention-notes 를 막았다"

# 6. 경로 탈출 시도는 SKILL.md 확인에서 걸린다
[ -z "$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/.."}')" ] || fail ".. 가 통과했다"

# 7. 슬래시로 시작하지 않는 평범한 프롬프트는 통과
[ -z "$(run '{"hook_event_name":"UserPromptSubmit","prompt":"이 영상 news-briefing-digest 로 정리해줘"}')" ] || fail "평범한 프롬프트를 막았다"

# 8. 이미 worktree 안이면 통과
cd "$T/wt"
[ -z "$(run '{"hook_event_name":"PreToolUse","tool_input":{"skill":"news-briefing-digest"}}')" ] || fail "worktree 안인데 막았다"
[ -z "$(run '{"hook_event_name":"UserPromptSubmit","prompt":"/news-briefing-digest https://youtu.be/x"}')" ] || fail "worktree 안인데 슬래시를 막았다"

# 9. git 리포가 아니면 통과
cd "$T"
[ -z "$(run '{"hook_event_name":"PreToolUse","tool_input":{"skill":"news-briefing-digest"}}')" ] || fail "리포 밖인데 막았다"

echo OK
