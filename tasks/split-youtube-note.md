# youtube-note 해체 — 브리핑 / 스터디 두 스킬로

대상: `.claude/skills/youtube-note/` 를 없애고 역할을 `news-briefing-digest`,
`youtube-study-note` 로 나눈다. 공용 스크립트는 `scripts/` 로 뺀다.

확정된 의도 (2026-08-26):

- **버린다**: 코넬 모드 전체(`glossary`·`outliner`·`section-note`·`synthesizer`·
  `8a-auditor-cornell` + 병렬 파이프라인), 워크트리 격리와 자동 커밋(1·10단계).
  → 강의 영상의 "복습용 전문 34~68KB" 는 대체재 없이 사라진다. `notes/` 에 이미
  커밋된 코넬 노트 5편은 그대로 둔다.
- **남긴다**: 진행 페이지(`web/`)와 `progress-server` 스킬. 단 새 파이프라인에
  맞춰 다시 배선한다.
- **검수(auditor)는 두 스킬에 새로 붙인다.** 지금 둘 다 없다.
- **규칙 파일은 스킬마다 복사본을 둔다.** 공용 폴더를 만들어 둘이 참조하게 하면
  지금 없애려는 결합이 그대로 재현된다. 20줄짜리 중복이 더 싸다.
- `caption-lag.md` 만 예외 — `transcript.py` 사용법 문서라 스크립트 옆에 둔다.

안 하는 것: 코넬 대체재 설계, `notes/` 기존 파일 재생성, 워크트리 복원,
스킬 트리거 정리(C안 — 별건).

검증 공통:

```sh
.venv/bin/python scripts/transcript.py --selftest
.venv/bin/python scripts/md2html.py --selftest
.venv/bin/python web/serve.py --selftest
```

마지막에 실주행 1회 + 브라우저 확인(사용자).

---

## 1. 공용 스크립트를 `scripts/` 로  `refactor/scripts-out`

두 스킬이 모두 `transcript.py` 를 쓴다. 한쪽 스킬 폴더에 두면 다른 쪽이 남의
폴더를 참조하는 현재 구조가 그대로 반복된다.

- [x] `transcript.py` → `scripts/transcript.py`
- [x] `md2html.py` + `note-page.html` → `scripts/` (기존 `notes/*.md` 재렌더용으로만 남긴다)
- [x] `references/caption-lag.md` → `scripts/caption-lag.md`
- [x] 각 파일 docstring 안의 자기 경로 갱신
- [x] 경로 참조 갱신: `CLAUDE.md`(10·19·44·73), `README.md`(12·25·31·32·41),
      `web/serve.py`(335), `progress-server/SKILL.md`(55), `tasks/todo.md`(3·15),
      `youtube-study-note/SKILL.md`(18), `news-briefing-digest/SKILL.md`(18)
- [x] `--selftest` 2개 통과

파일: `scripts/*`, 문서 7개 · 크기: M

## 2. 규칙과 검수를 두 스킬로 이관  `feat/skill-rules`

- [x] `rules-briefing.md` → `news-briefing-digest/references/rules.md`
- [x] `4c-briefing-news.md` 작성 규칙 6·7 을 위 파일에 병합
      (잘린 수치는 자리 통째로 `(자막 수치 불명확)`, HTML 엔티티 금지)
- [x] `4d` 개수 상한 근거를 남긴다 → 3절에 **카드 최대 12개** + `ponytail:` 주석으로 (별도 한계 절 대신)
- [x] `4b-outliner.md` 의 경계 규약 2개 → `news-briefing-digest` 2절(꼭지 경계)
      (전환 발화에서 경계를 찾는다 / 자막에 실제 있는 타임스탬프만, 추정 금지)
- [x] `rules-cornell.md` 에서 **한 줄만** → `youtube-study-note/references/rules.md`
      ("화자의 판단을 사실로 기록하는 것은 요약이지 판단이 아니다")
      나머지 평가·추천 금지는 04 인사이트와 충돌하므로 **가져오지 않는다**
- [x] `8b-auditor-briefing.md` 를 각색해 두 스킬에 검수 절 추가
      — 오탐 방지 목록을 스킬별로 다시 쓴다 (스터디 노트는 인사이트가 허용 항목)
- [x] 두 SKILL.md 에 검수 단계를 절로 추가하고 에이전트 `description` 을
      `auditor` 로 고정 (진행 페이지 단계 판정이 이 문자열을 쓴다)

파일: 두 스킬의 `SKILL.md` + `references/` · 크기: M · 의존: 1

## 3. 진행 페이지 재배선  `feat/web-rewire`

10단계 중 7개가 사라진다. 유형은 이제 출력 모드가 아니라 **어느 스킬을 부를지**만 정한다.

**못 잡는 단계는 그리지 않는다.** 본문 작성과 저장은 두 스킬 다 에이전트가 아니라
메인 세션이 하고, 저장 Write 가 검수보다 먼저 일어나 역행 가드에 검수가 먹힌다.
화면이 거짓말하느니 칸을 없앤다.

- [x] `STAGES` 를 3개로: `자막 확보 · 자막 지연 확인 · 검수`
- [x] `BASH_STAGE` → `--outline-only`(1) · `--probe`/`--lag`(2). 워크트리·git·md2html 제거
- [x] `AGENT_STAGE` → `auditor`(3) 한 줄
- [x] `EnterWorktree`/`ExitWorktree` 분기 제거
- [x] `index.html` 드롭다운 2개로: `뉴스 브리핑 다이제스트` / `스터디 노트`
- [x] `BRIEFING_SKIP`·`mode()`·`.skip` 통째로 제거 — 건너뛸 단계가 없다
- [x] `build_prompt` 를 스킬 지목 방식으로 (`SKILLS` 표: 선택지 → 폴더 이름)
- [x] **셀프테스트 앵커 교체** — SKILL.md 표 정규식 대신 `<option>` 이 `SKILLS` 의
      키와 같은지 + 그 값이 `.claude/skills/` 의 **실제 폴더**인지 검사. 정본이
      디렉터리라 드리프트가 구조적으로 안 난다. 단계 수도 페이지와 대조한다.
- [x] 페이지 제목 `youtube-note` → `영상 노트`
- [x] `web/serve.py --selftest` 통과 + `node --check` 로 페이지 스크립트 문법 확인

파일: `web/serve.py`, `web/index.html` · 크기: L · 의존: 2

## 4. 삭제 + 문서 정리  `chore/drop-youtube-note`

앞 셋이 끝나고 검증이 통과한 뒤에만 지운다.

- [x] `.claude/skills/youtube-note/` 삭제
- [x] `news-briefing-digest.skill` 번들 삭제 (압축 푼 것과 동일, 중복)
- [x] `CLAUDE.md` 재작성 — 파이프라인 다이어그램, 코넬/브리핑 2모드 설명,
      "세 곳이 같이 움직인다" 절, `rules-cornell.md` 참조를 전부 새 구조로
- [x] `README.md` 갱신
- [x] `progress-server/SKILL.md:55` 의 파이프라인 참조 갱신
- [x] `docs/ideas/youtube-note-agents.md` 는 **그대로 둔다** — 폐기된 대안
      (NotebookLM·yt-dlp·Data API v3) 기록이라 여전히 유효하다.
      해체 결정만 1줄 추가한다.

파일: `CLAUDE.md`, `README.md`, `progress-server/SKILL.md`, `docs/` · 크기: M · 의존: 3

---

## 결과

| # | 브랜치 | 커밋 |
|---|---|---|
| 1 | `refactor/scripts-out` | `e77dc12` Move shared scripts out of the youtube-note skill |
| 2 | `feat/skill-rules` | `c948b8f` Give both successor skills a rule set and an audit step |
| 3 | `feat/web-rewire` | `53e7576` Redraw the progress page for the two-skill pipeline |
| 4 | `chore/drop-youtube-note` | (이 커밋) Retire the youtube-note skill |

셀프테스트 3개 통과(`transcript.py`·`md2html.py`·`web/serve.py`), 기존 노트 재렌더
결과 무변화, 페이지 스크립트 `node --check` 통과.

**남은 확인: 실주행 1회 + 브라우저 (사용자).** 해체 후 헤드리스로 두 스킬을 돌린 적이
아직 없다. 특히 진행 페이지의 3단계가 실제 스트림에서 다 켜지는지 — `--probe` 를
안 타는 수동 자막 영상이면 2단계는 안 켜지는 것이 정상이다.
