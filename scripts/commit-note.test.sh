#!/bin/sh
# commit-note.sh 의 푸시 분기 검사. 임시 bare 리모트를 만들어 진짜 훅을 돌린다.
# gh 는 PATH 에서 가려 PR 생성 없이 푸시 동작만 본다. 실행: sh scripts/commit-note.test.sh
set -e
HOOK=$(cd "$(dirname "$0")" && pwd)/commit-note.sh
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH   # gh 없음 → PR 단계 건너뜀
fail() { echo "FAIL: $1"; exit 1; }
on_origin() { git --git-dir="$T/origin.git" rev-parse --verify -q "$1" >/dev/null; }

git init -q --bare "$T/origin.git"
git clone -q "$T/origin.git" "$T/work" 2>/dev/null
cd "$T/work"
git config user.email t@t; git config user.name t
mkdir -p notes/invest; echo x > notes/invest/seed.html
git add -A; git commit -qm seed; git branch -M main; git push -qu origin main
main0=$(git --git-dir="$T/origin.git" rev-parse main)

# 스킬 격리 워크트리: 브랜치만 올라가고 main 은 그대로여야 한다
for w in 1 2; do
  git worktree add -q "$T/wt$w" -b "skill$w" main
  cd "$T/wt$w"; git config user.email t@t; git config user.name t
  echo "n$w" > "notes/invest/n$w.html"
  sh "$HOOK" >/dev/null
  on_origin "refs/heads/skill$w" || fail "skill$w 브랜치가 안 올라감"
done
[ "$(git --git-dir="$T/origin.git" rev-parse main)" = "$main0" ] || fail "main 이 직접 움직였다 (PR 없이 반영됨)"

# 같은 브랜치에 두 번째 노트를 써도 같은 브랜치가 갱신될 뿐이다
cd "$T/wt1"; b1=$(git --git-dir="$T/origin.git" rev-parse refs/heads/skill1)
echo n1b > notes/invest/n1b.html; sh "$HOOK" >/dev/null
[ "$(git --git-dir="$T/origin.git" rev-parse refs/heads/skill1)" != "$b1" ] || fail "두 번째 커밋이 안 올라감"

# 에이전트 격리 브랜치: 커밋만 하고 아무것도 안 올린다
cd "$T/work"; git worktree add -q "$T/wta" -b worktree-agent-zz main
cd "$T/wta"; git config user.email t@t; git config user.name t
echo a > notes/invest/na.html; sh "$HOOK" >/dev/null
git diff --quiet HEAD -- notes/invest/na.html || fail "에이전트 브랜치에서 커밋이 안 됨"
on_origin refs/heads/worktree-agent-zz && fail "에이전트 브랜치가 푸시됨"


# --- PR 분기: gh 스텁으로 PR 없음 / 열림 / 닫힘 3가지
mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'STUB'
#!/bin/sh
[ "$1" = pr ] || exit 1
case "$2" in
  view)   [ "$PR_STATE" = OPEN ]   && { echo https://x/pr/1; exit 0; }
          [ "$PR_STATE" = CLOSED ] && exit 0          # select 가 걸러 빈 출력
          exit 1 ;;                                    # PR 자체가 없음
  create) echo x >> "$CREATED"; echo https://x/pr/new; exit 0 ;;
esac
STUB
chmod +x "$T/bin/gh"
PATH="$T/bin:$PATH"; export PATH
CREATED="$T/created"; export CREATED

n=0
for st in NONE OPEN CLOSED; do
  n=$((n + 1)); PR_STATE=$st; export PR_STATE
  : > "$CREATED"
  cd "$T/work"; git worktree add -q "$T/pr$n" -b "pr$n" main
  cd "$T/pr$n"; git config user.email t@t; git config user.name t
  echo p > "notes/invest/p$n.html"
  sh "$HOOK" > "$T/prout" 2>&1
  case $st in
    OPEN) [ -s "$CREATED" ] && fail "열린 PR 이 있는데 새로 만들었다"
          grep -q "PR: https://x/pr/1" "$T/prout" || fail "열린 PR 을 재사용해 알리지 않았다" ;;
    *)    [ -s "$CREATED" ] || fail "$st 인데 PR 을 안 만들었다" ;;
  esac
done

echo "commit-note.sh: 8 assertions ok"
