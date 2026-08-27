# rich-to-be

유튜브 영상을 한 장짜리 HTML 문서로 정리하는 [Claude Code](https://claude.com/claude-code) 스킬 두 개.

- **`news-briefing-digest`** — 꼭지가 여럿인 뉴스 브리핑(조간·모닝루틴·마켓 브리핑)을 아침에 훑는 다이제스트로
- **`youtube-study-note`** — 단일 주제 해설·강의를 다시 안 봐도 되는 학습 자료로

산출물은 `notes/<폴더>/{yyMMdd}_<slug>.html` 이다 (날짜는 영상 방송일). 폴더는 셋뿐이다 — 모닝루틴 `notes/morning-routine/`, 투자 노트 `notes/invest/`, 개인 공부용 `notes/self-study/`. 브라우저에서 인쇄(Ctrl/Cmd+P) → PDF 로 저장하면 A4 한 문서가 된다.

## 설치

```sh
git clone <이 리포> && cd rich-to-be
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/transcript.py --selftest   # OK 나오면 끝
```

Python 3.11+ 면 된다. `.venv` 경로는 고정이다 — 스킬이 `.venv/bin/python` 을 그대로 호출한다.

## 쓰는 법

리포 루트에서 `claude` 를 띄우고 유튜브 URL과 함께 정리해 달라고 하면 된다. 영상 성격에 따라 Claude가 둘 중 하나를 고른다.

```
> https://www.youtube.com/watch?v=... 이 영상 정리해줘
```

각 스킬의 `SKILL.md` 가 절차의 정본이다. 자동생성 자막이면 기본 지연 보정값 2.2초를 묻지 않고 적용하고, 노트에 그렇게 밝힌다.

스크립트만 따로 쓸 수도 있다:

```sh
.venv/bin/python scripts/transcript.py "<URL>"          # 자막 받기
.venv/bin/python scripts/transcript.py "<URL>" --probe  # 자막 지연 확인
.venv/bin/python scripts/slack.py <노트.html>           # 슬랙 채널에 링크 보내기 (.env 는 .env.example 참고)
```

채널엔 `<파일명> 정리` 만 뜨고 Pages 링크는 그 메시지의 **스레드 답글**로 들어간다 — 채널에 링크 프리뷰가 쌓이지 않는다. 여러 개를 한 번에 보내면 전부 첫 메시지의 스레드로 모인다.

슬랙은 **평소엔 손으로 안 돌린다** — 푸시하면 CI 가 보낸다(아래). 직접 돌리는 건 CI 가 건너뛴 경우(브랜치 첫 푸시·force push)뿐이다.

## 발행

`notes/` 는 GitHub Pages 로 나간다. `notes/self-study/` 는 gitignore 라 커밋도 발행도 안 된다.

목록(`notes/index.html`)은 손으로 고치는 파일이고, 거기 들어가는 데이터 `notes/notes.js` 는 발행할 때 Actions 가 만든다 — gitignore 대상이라 커밋하지 않는다. 로컬에서 목록을 열어 보고 싶을 때만 직접 돌린다.

```sh
.venv/bin/python scripts/build-notes-index.py   # notes/notes.js 생성 (커밋 안 함)
```

main 에 푸시하면 GitHub Actions(`.github/workflows/pages.yml`)가 `notes/` 만 아티팩트로 올려 발행한다. `scripts/` 나 `CLAUDE.md` 는 사이트에 올라가지 않는다.

발행이 끝나면 같은 워크플로의 `slack` 잡이 **그 푸시에서 새로 추가된**(`--diff-filter=A`) `morning-routine` · `invest` 노트만 골라 `slack.py` 로 링크를 보낸다. self-study 는 안 보낸다. 발행 잡과 분리돼 있어서 슬랙만 `gh run rerun --failed` 로 다시 돌릴 수 있다.

리포 시크릿 두 개가 필요하다 (Settings → Secrets and variables → Actions). 로컬 `.env` 와 같은 값이고, 봇을 채널에 초대해 둬야 한다.

| 시크릿 | 값 |
|---|---|
| `SLACK_BOT_TOKEN` | `xoxb-...` — scope `chat:write` |
| `SLACK_CHANNEL` | `C0XXXXXXX` |

## 한계

- **한국어/영어 자막이 있는 영상만** 된다. 자막이 없으면 아무것도 못 한다.
- 자동생성 자막의 지연 보정값은 사람이 영상과 대조해야 정확하다. 기본값 2.2초는 측정값이 아니다. 어긋나 보이면 `--probe` 로 확인하고 `--lag` 로 다시 받는다.
- `notes/` 의 기존 노트는 예시로 커밋돼 있다. 본인 리포로 쓸 거면 지우면 된다 — 목록은 발행 때 다시 만들어진다.

자세한 개발 규칙은 `CLAUDE.md` 에 있다. 폐기된 대안(NotebookLM 자동화, yt-dlp, YouTube Data API v3)의 검토 기록은 git 이력에 있다.
