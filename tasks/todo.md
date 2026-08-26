# notes/*.html 파트별 페이지 넘김

대상: `scripts/md2html.py` + 새 포맷 파일 `scripts/note-page.html`.
산출물 `notes/*.html` 는 매 수정마다 재생성해 같이 커밋한다.

확정된 의도 (인터뷰 2026-08-20):

- 파일 하나 자기완결 HTML 그대로. 외부 요청 0.
- 쪽 구성: `표지(제목·목차) → Part 1…N → 마무리(전체 흐름·구간 간 연결)`.
- 한 파트의 소주제는 전부 그 한 쪽 안. 쪽이 길면 세로 스크롤 허용.
- 넘김은 JS 0줄, CSS `:target`. prev/next 는 앵커라 뒤로가기·북마크·딥링크가 따라온다.
- 종이·줄 스타일. **손글씨 폰트 없음**, 본문 글꼴은 현행 유지.
- 안 하는 것: 넘김 애니메이션, 고정 목차 바, `.claude/formats/` 공용 디렉터리, md 포맷 변경, 별도 뷰어 파일.

검증 공통: `.venv/bin/python scripts/md2html.py --selftest` + 재생성 후 브라우저 확인(사용자).

---

## 1. CSS·껍데기를 포맷 파일로  `feat/html-p1-template`

`CSS` 와 `PAGE` 가 파이썬 문자열 상수로 박혀 있어 스타일만 고쳐도 코드를 건드린다. 스킬 밖에서 읽기도 나쁘다.

- [x] `note-page.html` 에 `<head>`+CSS+본문 자리표시자를 담는다
- [x] 자리표시자는 HTML 주석(`<!--BODY-->`)으로 `str.replace` — CSS 의 `{}` 때문에 `str.format` 은 못 쓴다
- [x] `md2html.py` 는 런타임에 그 파일을 읽는다 (경로는 `__file__` 기준)
- [x] selftest assert: 포맷 파일이 없으면 명확히 실패

파일: `md2html.py`, `note-page.html`, `notes/*.html` · 크기: S

## 2. 파트별 쪽 분할 + prev/next  `feat/html-p2-paging`

- [x] 렌더된 body 를 `<section class="page">` 로 자른다 — `Part ` 로 시작하는 h2 = 새 쪽, 그 뒤 첫 비-Part h2 = 마무리 쪽(이후 비-Part h2 는 같은 쪽에 붙는다)
- [x] 표지 쪽 = h1 + 목차
- [x] 각 쪽 하단에 `← 이전 · 목차 · 다음 →` 앵커, 첫/끝에서는 해당 링크 없음
- [x] CSS `:target` 으로 한 쪽만 표시, 해시 없으면 표지
- [x] "전체 보기" 앵커 하나 + `@media print` 는 전부 펼침 (Ctrl-F 대비)
- [x] selftest assert: 쪽 수, 마무리 쪽 병합, 첫 쪽 네비, `<script` 없음 유지

파일: `md2html.py`, `note-page.html`, `notes/*.html` · 크기: M · 의존: 1

## 3. 종이 노트 스타일  `feat/html-p3-paper`

- [x] 크림 종이 바탕 + 가로 줄선, 다크모드는 어두운 종이로 대응
- [x] 코넬 좌측 세로 구분선(단서 열 경계와 맞춤)
- [x] 우하단 쪽번호 (`3 / 10`)
- [x] 모바일·인쇄에서 깨지지 않는지 확인

파일: `note-page.html`, `notes/*.html` · 크기: S · 의존: 2

---

## 결과

| # | 브랜치 | 커밋 |
|---|---|---|
| 1 | `feat/html-p1-template` | `b27ddd7` Move page shell and CSS into note-page.html |
| 2 | `feat/html-p2-paging` | `92a267b` Split notes into per-part pages with prev/next |
| 3 | `feat/html-p3-paper` | `915b019` Style note pages as ruled paper sheets |

`--selftest` 통과, `notes/*.html` 2개 재생성(각 10쪽 = 표지+Part 8+마무리).
**남은 확인: 브라우저 — 넘김·딥링크·전체 보기·인쇄·모바일, 그리고 줄노트 선이 거슬리지 않는지.**
