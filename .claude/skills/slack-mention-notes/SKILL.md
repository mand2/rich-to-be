---
name: slack-mention-notes
description: 슬랙에서 봇(@rich-bot)이 멘션된 스레드를 훑어 거기 걸린 유튜브 링크로 노트를 만든다. 고른 건마다 worktree 격리 서브에이전트가 붙어 병렬로 돌고, 발행된 Pages 링크는 요청이 걸린 그 스레드에 답글로 돌아간다. 사용자가 "슬랙 멘션 확인", "슬랙에 요청 온 거 처리", "멘션 걸린 거 정리해줘", "슬랙에서 가져와서 요약" 이라고 하면 이 스킬을 쓴다. 유튜브 링크를 직접 붙여 주는 단일 건은 이 스킬이 아니라 youtube-study-note · news-briefing-digest 를 쓴다.
---

# 슬랙 멘션 → 노트

슬랙에서 링크를 눈으로 보고 손으로 옮겨 붙이던 걸 없앤다.
**상시 리스너가 아니다** — 사용자가 이 스킬을 부를 때만 슬랙을 읽는다. Socket Mode·Events API 는 쓰지 않는다.

## 1. 멘션 스캔

```sh
.venv/bin/python scripts/slack.py --mentions
```

탭 구분 5열이 나온다: `번호 · new|done · thread_ts · 유튜브URL(없으면 -) · 멘션 문구`.
`done` 은 그 스레드에 봇이 이미 링크를 답글로 단 건이다 — 상태 파일은 없고 **슬랙 자체가 상태다.**

읽은 그대로 표로 보여준다. **링크가 `-` 인 줄은 처리할 수 없다** (스레드 어디에도 유튜브 링크가 없다) — 목록에는 남기되 그 이유를 한 줄로 붙인다.

## 2. 한 번에 묻는다

질문 라운드는 **한 번**이다. 번호와 폴더를 같이 받는다:

> 몇 번을 돌릴까요? 각각 폴더도 같이 골라 주세요 — **invest / real-estate / morning-routine**

**서브에이전트는 사용자에게 못 묻는다.** 그래서 `youtube-study-note` 가 평소 본문 전에 묻는 폴더 질문이 여기로 올라온다. `self-study` 는 이 경로에 없다 — gitignore 라 발행이 안 되고 스레드에 돌려줄 링크가 생기지 않는다.

답이 비어 오는 항목이 있으면 되묻지 말고 기본값(`invest`)으로 진행하고 그렇게 했다고 밝힌다.

## 3. 건당 서브에이전트 (worktree 격리)

고른 건 수만큼 `Agent` 를 **한 메시지에 동시에** 띄운다. 반드시 `isolation: "worktree"` 를 준다.

**worktree 가 아니면 발행이 깨진다.** `scripts/commit-note.sh` 는 tool_input 을 안 보고 `git status` 로 더러운 노트를 **전부** 커밋한다. 작업 디렉토리를 공유하면 에이전트 A 의 Write 훅이 에이전트 B 의 **쓰다 만 노트**를 같이 커밋·푸시한다. worktree 안에서는 `git rev-parse --show-toplevel` 이 그 worktree 를 가리켜 훅이 자기 것만 자기 브랜치에 커밋한다 (2026-08-31 실측).

에이전트 프롬프트에 반드시 넣을 것:

- `.venv` 는 gitignore 라 **worktree 에 없다.** 첫 줄에서 만들게 한다 —
  `[ -e .venv ] || ln -s /Users/ymac/IdeaProjects/ai-projects/rich-to-be/.venv .venv`
- 유튜브 URL, 저장 폴더, 원본 `thread_ts`
- 영상 유형에 따라 `news-briefing-digest`(꼭지 나열형) 또는 `youtube-study-note`(단일 주제 해설) 를 **Skill 툴로 부르고 그 스킬을 그대로 따를 것**. 폴더는 이미 정해졌으니 되묻지 말 것
- 노트 HTML `<head>` 에 원본 스레드를 심을 것:
  `<meta name="slack-thread" content="<thread_ts>">`
  이게 있어야 발행 후 링크가 채널 새 글이 아니라 **그 스레드 답글**로 간다
- **푸시하지 말 것.** 훅의 `push 실패: 커밋은 됐지만 푸시 안 됨` 은 정상이다 (worktree 브랜치엔 upstream 이 없다)
- 보고는 만든 파일 경로 하나

에이전트 보고를 그대로 믿지 마라 — 파일이 실제로 생겼는지 메인 세션이 확인한다.

## 4. 메인으로 모으고 한 번만 푸시

각 에이전트는 `worktree-agent-<id>` 브랜치에 커밋 1개를 남긴다. main 은 그동안 안 움직였지만 브랜치가 여럿이라 **두 번째부터는 ff 머지가 안 된다.** 각 커밋이 서로 다른 새 파일 하나씩이라 cherry-pick 이 충돌 없이 끝난다:

```sh
git worktree list                      # 브랜치 이름 확인
git cherry-pick <branch1> <branch2> …   # 고른 순서대로
git push                                # 푸시는 마지막에 한 번
git worktree remove --force .claude/worktrees/agent-<id>
git branch -D worktree-agent-<id>
```

푸시 1회 → Actions 런 1회다. 여러 번 푸시하면 `pages.yml` 이 이미 겪은 "6초 간격 푸시" 문제로 돌아간다.

## 5. 확인

Actions 의 `slack` 잡이 새로 추가된 노트를 골라 `slack.py` 로 보내고, `slack-thread` 태그가 있는 건은 새 글 없이 **원본 스레드에 링크만** 답글로 단다.

사용자에게는 처리한 건 목록과 각각의 스레드 ts 만 알린다. 슬랙 화면 확인은 사용자가 직접 한다.

## 지키는 것

`CLAUDE.md` 의 "절대 지키는 것" 이 그대로 적용된다 — 자막에 없는 것을 만들지 않고, 자막 수치를 임의로 교정하지 않고, 타임스탬프를 추정하지 않는다. 서브에이전트에게도 같은 제약이 걸린다 (worktree 안에도 `CLAUDE.md` 가 있다).

<!-- ponytail: 멘션 스캔은 conversations.history 기본 50건. 오래된 멘션이 잘려 안 보이면 slack.py 의 HISTORY_LIMIT 을 올린다.
     채널은 SLACK_CHANNEL 하나만 본다 — DM·멀티채널은 스코프(im:history 등)와 채널 목록 관리가 붙어서 안 넣었다. -->
