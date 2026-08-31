#!/bin/sh
# prune-note-worktrees.sh 검사. gh 를 스텁으로 갈아끼워 PR 상태를 흉내낸다.
# 실행: sh scripts/prune-note-worktrees.test.sh
set -e
SUT=$(cd "$(dirname "$0")" && pwd)/prune-note-worktrees.sh
T=$(cd "$(mktemp -d)" && pwd -P)   # macOS: git 은 /private/var 로 풀어 쓴다
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL: $1"; exit 1; }
R="$T/repo"; W="$R/.claude/worktrees"
has_wt() { git worktree list --porcelain | grep -qx "worktree $1"; }

# gh 스텁: MERGED_LIST 에 적힌 브랜치만 MERGED 로 답한다 (gh pr view <branch> ...)
mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'STUB'
#!/bin/sh
[ "$1" = pr ] && [ "$2" = view ] || exit 1
grep -qx "$3" "$MERGED_LIST" 2>/dev/null && echo MERGED || echo OPEN
STUB
chmod +x "$T/bin/gh"
PATH="$T/bin:/usr/bin:/bin:/usr/sbin:/sbin"; export PATH
MERGED_LIST="$T/merged.txt"; export MERGED_LIST

git init -q "$R"; cd "$R"
git config user.email t@t; git config user.name t
mkdir -p notes/invest; echo x > notes/invest/seed.html
printf '.venv\n' > .gitignore
git add -A; git commit -qm seed; git branch -M main

git worktree add -q "$W/merged"  -b merged  main
git worktree add -q "$W/open"    -b open    main
git worktree add -q "$W/dirty"   -b dirty   main
git worktree add -q "$T/outside" -b outside main       # .claude/worktrees/ 밖
printf 'merged\ndirty\noutside\n' > "$MERGED_LIST"

echo tweak >> "$W/dirty/scripts_stub.txt"              # 노트가 아닌 커밋 안 한 변경분
ln -s /nonexistent "$W/merged/.venv"                   # gitignore 대상 — 걸리면 안 된다

sh "$SUT" > "$T/out" 2>&1 || fail "스크립트가 죽었다"

if has_wt "$W/merged"; then fail "머지된 워크트리가 안 지워졌다"; fi
if git rev-parse --verify -q merged >/dev/null; then fail "머지된 브랜치가 안 지워졌다"; fi
has_wt "$W/open"    || fail "안 머지된 워크트리를 지웠다"
has_wt "$W/dirty"   || fail "커밋 안 한 변경분이 있는 워크트리를 지웠다"
has_wt "$T/outside" || fail ".claude/worktrees/ 밖 워크트리를 지웠다"
grep -q "정리 건너뜀 (dirty)" "$T/out" || fail "건너뛴 이유를 안 알렸다"

# 워크트리 안에서 돌리면 아무것도 안 한다
cd "$W/open"; sh "$SUT" >/dev/null
cd "$R"; has_wt "$W/open" || fail "워크트리 안에서 자기를 지웠다"

echo "prune-note-worktrees.sh: 7 assertions ok"
