# rich-to-be

유튜브 영상을 **한 장짜리 HTML 문서**로 정리하는 Claude Code 스킬 두 개. 리포의 산출물은 `notes/<폴더>/{yyMMdd}_<slug>.html` 이다 (날짜는 영상 방송일). **폴더는 모닝루틴 `notes/morning-routine/` · 투자 노트 `notes/invest/` · 개인 공부용 `notes/self-study/` 셋뿐이다.** 스터디 노트 스킬은 투자 노트인지 개인 공부용인지 사용자에게 한 번 묻는다.

| 스킬 | 대상 | 만드는 것 |
|---|---|---|
| `news-briefing-digest` | 꼭지 10~15개가 나열되는 뉴스 브리핑 (조간·모닝루틴·마켓 브리핑) | 스캔용 다이제스트 — 헤드라인 3줄, 숫자, 분야별 꼭지 카드, 종목 인덱스 |
| `youtube-study-note` | 단일 주제를 파는 해설·강의 | 학습 자료 — 용어 사전, 논리 흐름 분해, 인사이트, 관전 포인트 |

**둘의 차이는 요약 방식이 아니라 목적이다.** 다이제스트는 선별과 재배열, 스터디 노트는 재구성과 추상화다. 스터디 노트의 `04 인사이트` 는 영상 밖에도 통하는 원칙으로 한 단계 올리는 것이 요구 사항이고, 다이제스트는 중요도 재배열과 파급 효과 서술이 요구 사항이다. **각 스킬의 `references/rules.md` 가 규칙의 정본이고, 두 파일을 섞어 쓰지 마라.**

## 환경

Python은 **반드시 `.venv/bin/python`** 을 쓴다. `youtube-transcript-api` 가 여기에만 설치돼 있고, 시스템 python에는 없다.

```sh
.venv/bin/python scripts/transcript.py --selftest
```

의존성을 추가하면 `.venv/bin/pip install` 로 넣는다. `.venv` 와 `.work/` 는 gitignore 대상이고, `notes/` 는 **산출물이므로 커밋한다.**

## 공용 스크립트 (`scripts/`)

두 스킬이 같이 쓰므로 스킬 폴더 밖에 둔다. 한쪽 스킬 안에 넣으면 다른 쪽이 남의 폴더를 참조하게 된다.

| 파일 | 무엇 |
|---|---|
| `transcript.py` | 자막 받기. `.work/<video_id>/` 에 `transcript.txt` 와 `meta.json` 을 만든다 |
| `caption-lag.md` | 자동자막 지연 보정 절차 (기본 2.2초 자동 적용, 어긋날 때만 `--probe` → `--lag`) |
| `slack.py` | 만든 노트를 슬랙 채널에 업로드. `.env` 에 `SLACK_BOT_TOKEN`(files:write, chat:write) + `SLACK_CHANNEL`, 봇을 채널에 초대해 둘 것. 파일명 메시지 + 스레드에 파일 |
| `md2html.py` + `note-page.html` | `notes/*.md` → 자기완결 HTML. **기존 노트 재렌더 전용이다** — 새 노트는 스킬이 HTML 을 직접 쓴다 |

## 파이프라인

```
transcript.py --outline-only (자동자막이면 2.2초 자동 보정) → 본문 작성 → notes/{yyMMdd}_<slug>.html
```

**전 과정을 메인 세션이 한다. 에이전트를 띄우지 않는다.** 자막 대조 검수 절은 두 스킬에서 제거됐다 — 되살릴 거면 git 이력에서 꺼내야 한다.

## 진행 페이지 (`web/`)

`.venv/bin/python web/serve.py` 가 로컬 8765 포트에 진행 페이지를 띄운다. 링크·스킬·lag 을 받아 `claude -p --output-format stream-json` 으로 위 파이프라인을 헤드리스로 돌리고 **3단계**(자막 확보 · 자막 지연 확인 · 검수)를 그린다. **3단계는 더 이상 켜지지 않는다** — 검수 에이전트가 없어졌는데 `serve.py` 의 `AGENT_STAGE` 와 `index.html` 의 `STAGES` 는 그대로다. `--replay [로그]` 를 붙이면 `claude` 대신 지난 실행 로그를 되읽어 화면만 확인한다 (경로를 안 주면 `.work/last-run.jsonl`). 서버를 띄우고 내리는 절차는 `.claude/skills/progress-server/SKILL.md` 가 정본이다. 남은 일과 실측 기록은 `web/TODO.md` 에 있다.

**본문 작성과 저장은 단계로 두지 않는다.** 둘 다 메인 세션이 하고 진행 페이지가 잡을 수 있는 신호를 내지 않는다. **못 잡는 단계를 그려 두면 화면이 거짓말을 한다** — 지금 3단계가 정확히 그 상태다.

**세 곳이 같이 움직인다.** `web/index.html` 의 `<option>` ↔ `serve.py` 의 `SKILLS` 표 ↔ `.claude/skills/` 의 **실제 폴더 이름**. 스킬을 추가·개명하면 세 곳을 같이 고친다. SKILL.md 의 명령줄을 고치면 `BASH_STAGE` 도 고친다. `web/serve.py --selftest` 는 자기 문자열만 검사하므로 SKILL.md 와의 어긋남은 못 잡는다.

## 절대 지키는 것

**자막에 없는 것을 만들지 마라.** 사실·수치·고유명사·인과관계를 자막 밖에서 끌어오지 않는다. 배경 지식으로 보강하고 싶어도 하지 않는다. 이 문서들의 가치는 "영상에 있던 것만 담겨 있다"는 신뢰에서 나온다.

**자막 수치를 임의로 교정하지 마라.** 자동생성 자막이 틀려 보여도 실제 지식으로 고치는 것은 판단이다. 자릿수가 앞뒤로 안 맞으면 `(자막 수치 불명확)` 으로 표시하고, **잘린 수치를 그대로 옮겨 적고 표시만 붙이지 말고 그 자리를 통째로 대체한다.**

**화자의 판단을 사실로 기록하는 것은 허용된다.** "화자는 A가 B보다 빠르다고 설명"은 요약이지 판단이 아니다. 반대로 **화자 주장에 대한 사실 검증·반박은 금지**다.

**화자의 비유를 바꾸지 마라.** 더 나은 비유를 알고 있어도 쓰지 않는다 (스터디 노트).

**타임스탬프를 추정하지 마라.** 자막에 실제로 있는 시각만 쓴다.

## 자동생성 자막 지연

자동자막은 실제 발화보다 늦게 찍힌다. 기본 보정값은 `2.2초`이고, **이건 측정값이 아니라 기본값이다.**

**`auto_generated: true` 면 두 스킬 모두 이 값을 그대로 자동 적용한다. 확인을 요청하지 않는다.** 대신 노트에 `(미측정 기본값 2.2초 보정)` 이라고 밝힌다.

영상별 자동 측정은 불가능하다 — 기준선이 될 같은 언어의 수동 자막이 필요한데, 그게 있으면 애초에 자동자막을 쓰지 않기 때문이다. 그래서 타임스탬프가 어긋난다는 말이 나오면 그때만 사람이 확인한다:

```sh
scripts/transcript.py "<URL>" --probe      # 초반 120초를 원본/보정후 두 열로 출력
scripts/transcript.py "<URL>" --lag 3.5    # 영상과 대조한 값으로 재추출
```

전체 절차는 `scripts/caption-lag.md`.

## 코드 규칙

`transcript.py` 는 스크립트 1개로 유지한다. fetch와 split을 파일로 쪼개지 않는다.

로직을 고치면 `--selftest` 의 assert도 함께 고친다 — `scripts/transcript.py`, `scripts/md2html.py`, `web/serve.py` 셋 다 `--selftest` 를 갖고 있다. 별도 테스트 프레임워크는 두지 않는다.

의도적으로 한계를 안고 가는 상수·휴리스틱에는 `ponytail:` 주석으로 **어디서 온 값인지와 재조정 조건**을 남긴다. 예: `AUTO_CAPTION_LAG`, 다이제스트의 카드 상한 12.

## 설계 배경

`docs/ideas/youtube-note-agents.md` 에 실측 근거와 폐기된 대안(NotebookLM 자동화, yt-dlp, YouTube Data API v3)이 정리돼 있다. **같은 대안을 다시 제안하기 전에 그 문서를 먼저 읽어라.** `docs/youtube-note-plan.md` 는 그 이전 초안이라 일부 내용이 뒤집혔다.

두 스킬로 나누기 전에는 `youtube-note` 스킬 하나가 코넬 노트와 브리핑을 모두 만들었다. 해체 경위와 무엇을 버렸는지는 `tasks/split-youtube-note.md` 에 있다. **코넬 모드(구간 분할 + 병렬 `section-note` + `synthesizer`)는 계승자 없이 사라졌다** — 되살릴 거면 git 이력에서 꺼내야 한다.
