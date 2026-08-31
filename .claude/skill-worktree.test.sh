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
git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
git worktree add -q "$T/wt" -b some-branch

run() { printf '%s' "$1" | sh "$SUT"; }

# 1. Skill 툴 호출(PreToolUse) — main 이면 deny
out=$(run '{"tool_input":{"skill":"news-briefing-digest"}}')
case "$out" in *'"permissionDecision":"deny"'*) ;; *) fail "PreToolUse deny 안 나옴: $out" ;; esac
case "$out" in *'EnterWorktree(name: \"news-briefing-digest\")'*) ;; *) fail "이름 이스케이프 깨짐: $out" ;; esac

# 2. 슬래시 커맨드(UserPromptSubmit) — 같은 스킬이 프롬프트 앞머리로 와도 잡힌다
out=$(run '{"prompt":"/news-briefing-digest https://youtu.be/x 모닝루틴"}')
case "$out" in *'"hookEventName":"UserPromptSubmit"'*) ;; *) fail "UserPromptSubmit 미탐지: $out" ;; esac
case "$out" in *additionalContext*) ;; *) fail "additionalContext 없음: $out" ;; esac

# 3. 필드명이 user_prompt 로 와도 잡힌다 (실측 전 헤지)
out=$(run '{"user_prompt":"/youtube-study-note https://youtu.be/x"}')
case "$out" in *additionalContext*) ;; *) fail "user_prompt 미탐지: $out" ;; esac

# 4. allowlist 밖 스킬은 통과
[ -z "$(run '{"tool_input":{"skill":"code-review"}}')" ] || fail "allowlist 밖인데 막았다"
[ -z "$(run '{"prompt":"/code-review high"}')" ] || fail "슬래시 allowlist 밖인데 막았다"

# 5. 슬래시로 시작하지 않는 평범한 프롬프트는 통과
[ -z "$(run '{"prompt":"이 영상 news-briefing-digest 로 정리해줘"}')" ] || fail "평범한 프롬프트를 막았다"

# 6. 이미 worktree 안이면 통과
cd "$T/wt"
[ -z "$(run '{"tool_input":{"skill":"news-briefing-digest"}}')" ] || fail "worktree 안인데 막았다"
[ -z "$(run '{"prompt":"/news-briefing-digest https://youtu.be/x"}')" ] || fail "worktree 안인데 슬래시를 막았다"

# 7. git 리포가 아니면 통과
cd "$T"
[ -z "$(run '{"tool_input":{"skill":"news-briefing-digest"}}')" ] || fail "리포 밖인데 막았다"

echo OK
