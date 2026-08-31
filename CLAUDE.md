# rich-to-be

유튜브 영상을 **한 장짜리 HTML 문서**로 정리하는 Claude Code 스킬 두 개. 리포의 산출물은 `notes/<폴더>/{yyMMdd}_<slug>.html` 이다 (날짜는 노트를 만든 날, 영상 방송일이 아니다). **폴더는 모닝루틴 `notes/morning-routine/` · 투자 노트 `notes/invest/` · 부동산 `notes/real-estate/` · 개인 공부용 `notes/self-study/` 넷뿐이다.** 스터디 노트 스킬은 투자·부동산·개인 공부용 중 어디인지 사용자에게 한 번 묻는다.

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

의존성을 추가하면 `.venv/bin/pip install` 로 넣는다. `.venv` 와 `.work/` 는 gitignore 대상이고, `notes/` 는 **산출물이므로 커밋한다** — 단 `notes/self-study/**` 는 gitignore 라 커밋도 발행도 되지 않는다.

## 공용 스크립트 (`scripts/`)

두 스킬이 같이 쓰므로 스킬 폴더 밖에 둔다. 한쪽 스킬 안에 넣으면 다른 쪽이 남의 폴더를 참조하게 된다.

| 파일 | 무엇 |
|---|---|
| `transcript.py` | 자막 받기. `.work/<video_id>/` 에 `transcript.txt`(전문) 와 `meta.json` 을 만든다 |
| `caption-lag.md` | 자동자막 지연 보정 절차 (기본 2.2초 자동 적용, 어긋날 때만 `--probe` → `--lag`) |
| `slack.py` | 발행된 노트 링크를 슬랙 채널에 전송. `.env` 에 `SLACK_BOT_TOKEN`(chat:write) + `SLACK_CHANNEL`, 봇을 채널에 초대해 둘 것. `SLACK_MENTION_GROUP` (사용자 그룹 ID)이 있으면 **멘션으로 시작한 건의 스레드 답글에만** `<!subteam^…>` 를 앞줄로 붙인다 — 액션이 자동 발행하는 건은 부르는 사람이 없으니 멘션도 없다. 채널엔 "<파일명> 정리" 만 올리고 **Pages 링크는 그 메시지의 스레드 답글**로 넣는다 (여러 개면 전부 첫 메시지 스레드로). **평소엔 손으로 안 돌린다** — 푸시하면 `pages.yml` 의 `slack` 잡이 새로 추가된 morning-routine · invest 노트만 골라 호출하고, 베이스 URL 을 `NOTES_BASE_URL` 로 넘긴다. 리포 시크릿에 같은 두 값이 있어야 한다. `--mentions` 는 반대로 **읽는** 쪽 — 봇이 멘션된 스레드와 거기 있는 유튜브 링크를 탭 구분으로 뱉는다 (`slack-mention-notes` 스킬이 쓴다). 노트 HTML 에 `<meta name="slack-thread" content="<ts>">` 가 있으면 채널에 새 글을 만들지 않고 **그 스레드에 링크만** 답글로 단다 |
| `build-notes-index.py` | 목록 데이터 `notes/notes.js` 를 만든다 (`index.html` 이 `<script src>` 로 읽는다). 노트의 `<h1>` 과 한 줄 결론·헤드라인을 파싱한다 |

## 파이프라인

```
transcript.py (자동자막이면 2.2초 자동 보정) → 본문 작성 → notes/<폴더>/{yyMMdd}_<slug>.html
```

**노트 파일은 Write 툴로 만들고 Edit 툴로 고친다. Bash 리다이렉트(`cat > ...`)로 쓰지 마라.** `.claude/settings.json` 의 `PostToolUse(Write|Edit)` 훅이 `scripts/commit-note.sh` 를 불러 커밋·푸시까지 하는데, Bash 로 쓰면 훅이 매칭될 툴 호출이 없어서 **발행이 조용히 멈춘다.** `.work/` 나 스크래치 파일은 Bash 로 써도 된다.

`.claude/skill-worktree.sh` 가 노트 스킬을 격리 worktree 로 몬다. 대상은 손으로 적은 목록이 아니라 **`.claude/skills/<이름>/SKILL.md` 가 있는 스킬**, 즉 이 리포에 등록된 커스텀 스킬이다 (`slack-mention-notes` 만 예외 — 스스로 worktree 에이전트를 띄운다). 내장·플러그인 스킬은 자연히 빠진다. **입구가 둘이라 훅도 둘에 걸린다** — `Skill` 툴 호출은 `PreToolUse`, `/스킬명` 슬래시 커맨드는 툴 호출이 없어 `UserPromptSubmit` 으로만 온다. 한쪽만 걸면 다른 쪽이 main 에서 그대로 돈다. 배선은 gitignore 되는 `.claude/settings.local.json` 에 있으니 클론한 곳에선 직접 넣어야 한다.

`commit-note.sh` 는 어디서 도는지에 따라 갈린다 — main 워크트리면 바로 푸시, `worktree-agent-*`(slack 병렬 에이전트) 면 커밋만, 그 밖의 워크트리면 브랜치를 올리고 PR 을 연다. 머지된 워크트리·브랜치는 `scripts/prune-note-worktrees.sh` 가 세션 시작 때 치우고, 리모트 브랜치는 GitHub 의 `delete_branch_on_merge` 가 지운다. 두 스크립트 다 옆에 `*.test.sh` 가 있다.

**노트 한 건은 전 과정을 메인 세션이 한다. 에이전트를 띄우지 않는다.** 자막 대조 검수 절은 두 스킬에서 제거됐다 — 되살릴 거면 git 이력에서 꺼내야 한다.

**예외는 `slack-mention-notes` 하나다.** 슬랙 멘션을 여러 건 골라 돌릴 때만 건당 worktree 격리 서브에이전트를 띄운다. worktree 여야 하는 이유는 `commit-note.sh` 가 tool_input 을 안 보고 `git status` 로 더러운 노트를 **전부** 커밋하기 때문이다 — 작업 디렉토리를 공유하면 에이전트 A 의 훅이 에이전트 B 의 쓰다 만 노트를 같이 커밋·푸시한다. worktree 안에서는 `git rev-parse --show-toplevel` 이 그 worktree 를 가리켜 훅이 자기 것만 커밋한다 (2026-08-31 실측).

## 발행 (`notes/index.html` + GitHub Pages)

**GitHub Actions 가 `notes/` 폴더만 아티팩트로 올려 발행한다** (`.github/workflows/pages.yml`). Pages Source 는 GitHub Actions 이고 Jekyll 은 쓰지 않는다.

**목록은 커밋하지 않는다.** 생성물은 `notes/notes.js` 하나뿐이고 gitignore 대상이다 — 발행할 때 Actions 가 `scripts/build-notes-index.py` 로 만든다. `index.html` 은 손으로 고치는 파일이라 노트를 써도 안 바뀐다. 로컬에서 목록을 보고 싶으면 스크립트를 직접 돌려라. 무엇을 어디서 파싱하는지는 그 스크립트가, 태그를 적는 `META` 는 `notes/index.html` 이 각각 문서다. 두 스킬 템플릿의 `conclusion` · `top3` · `meta` class 를 바꾸면 스크립트도 같이 고친다 — 못 찾아도 빌드는 안 깨지고 설명만 빈다.

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

`transcript.py` 는 스크립트 1개로 유지한다. 자막 받기·지연 보정·메타 수집을 파일로 쪼개지 않는다.

로직을 고치면 `--selftest` 의 assert도 함께 고친다 — `scripts/transcript.py` 와 `scripts/build-notes-index.py` 둘 다 `--selftest` 를 갖고 있다. 별도 테스트 프레임워크는 두지 않는다.

의도적으로 한계를 안고 가는 상수·휴리스틱에는 `ponytail:` 주석으로 **어디서 온 값인지와 재조정 조건**을 남긴다. 예: `AUTO_CAPTION_LAG`, 다이제스트의 카드 상한 12.

## 설계 배경

**폐기된 대안을 다시 제안하지 마라** — NotebookLM 자동화, yt-dlp, YouTube Data API v3 는 실측 후 버렸다. 근거(`docs/ideas/youtube-note-agents.md`), 스킬을 둘로 쪼갠 경위와 버린 코넬 모드(`tasks/split-youtube-note.md`) 는 삭제됐으니 필요하면 git 이력에서 꺼낸다.
