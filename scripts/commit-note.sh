#!/bin/sh
# PostToolUse(Write|Edit) 훅. notes/<폴더>/*.html 이 저장되면 "<폴더>: <파일명>" 으로 커밋·푸시한다.
# self-study 는 .gitignore 대상이라 check-ignore 에서 걸러진다.
# 목록이 노트와 어긋나면 발행이 깨지므로 notes/index.html 을 다시 만들어 같은 커밋에 넣는다.
root=$(git rev-parse --show-toplevel) || exit 0
cd "$root" || exit 0

f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
rel=${f#"$root"/}
case "$rel" in
  notes/*/*.html) ;;
  *) exit 0 ;;
esac
git check-ignore -q "$rel" && exit 0

.venv/bin/python scripts/build-notes-index.py >/dev/null
git add "$rel" notes/index.html || exit 0
git diff --cached --quiet -- "$rel" notes/index.html && exit 0

dir=$(basename "$(dirname "$rel")")
git commit -q -m "$dir: $(basename "$rel")" -- "$rel" notes/index.html || exit 0
git push -q || echo "push 실패: $rel 은 커밋됐지만 푸시 안 됨"
