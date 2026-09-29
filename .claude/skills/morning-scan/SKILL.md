---
name: morning-scan
description: 팔로우하는 경제 유튜브 채널 5곳(한경 코리아마켓·박곰희TV·박종훈의 지식한방·소수몽키·수페TV)에 지난 24시간 동안 새 영상이 올라왔는지 확인해 고정된 Artifact 페이지 한 장을 갱신한다. 사용자가 "모닝스캔", "경제유튜브", "스케줄러", "스케쥴러", "스케줄", "새 영상 올라왔어?", "채널 업로드 확인", "오늘 뭐 올라왔나", "morning scan" 이라고 하면 이 스킬을 쓴다. 유튜브는 "유투브", "유튭", "youtube" 로 써도 같다 (경제유투브, 경제유튭, 경제youtube). 유튜브 링크나 자막이 같이 오지 않는 것이 기준이다. "브리핑" 이 들어간 요청은 이 스킬이 아니라 news-briefing-digest 다. 영상 내용은 보지 않는다 — 특정 영상을 정리·요약하려면 youtube-study-note · news-briefing-digest 를 쓴다.
---

# 경제 채널 모닝스캔

영상 **내용**이 아니라 **목록**을 보는 스킬이다. 자막을 받지 않고 요약도 하지 않는다. 채널 5곳의 최근 업로드를 YouTube API 로 받아 규칙(라이브만 / 동영상만 / 쇼츠 제외)으로 거르고, 결과 HTML 을 정해진 Artifact 페이지에 덮어쓴다.

채널 목록과 규칙은 `scripts/scan.py` 의 `CHANNELS` 가 정본이다. 설명은 `references/rules.md`.

리포 루트는 `/Users/ymac/IdeaProjects/ai-projects/rich-to-be` 다. 이 스킬은 main 에서 그대로 돈다 (worktree 격리 예외, 아래 "지키는 것"). 아래 경로는 전부 루트 기준이고, `scan.py` 는 자기 위치에서 루트를 찾으므로 cwd 와 무관하다.

## 1. 수집

```sh
.venv/bin/python .claude/skills/morning-scan/scripts/scan.py
```

- API 키는 스크립트가 리포 루트 `.env` 의 `YOUTUBE_API_KEY` 를 직접 읽는다. **키를 프롬프트·출력·보고에 옮기지 않는다.** 샌드박스 안에서도 네트워크가 된다 (2026-09-04 실측).
- 성공하면 stdout 첫 줄이 `OK` 로 시작하고, 이어서 건수 요약 줄 · `->` 출력 경로 줄 · 새 영상 `-` 줄들 · 걸러낸 항목 `x` 줄들이 온다. 결과물은 `.work/morning-scan/morning-scan.html` (gitignore).
- **API 호출이 하나라도 실패하면 부분 결과 없이 통째로 끝난다** — stderr 에 `FAIL` 로 시작하는 줄, exit 1. 그러면 **여기서 멈춘다.** 발행하지 않고 그 줄을 그대로 사용자에게 보인다. 원인별 대처는 `references/rules.md` 트러블슈팅.
- 스킬 인자에 `발행만` 이 있으면 이 단계를 건너뛴다 — `scripts/run.sh` 가 이미 돌려 놓은 경우다. 파일 확인은 `find .work/morning-scan -name morning-scan.html -mmin -1440` 한 줄이다 — 24시간 안에 갱신된 파일이 있으면 경로가 찍힌다. 안 찍히면 `FAIL  .work/morning-scan/morning-scan.html 이 없거나 24시간보다 오래됐다 — 발행만 모드인데 scan.py 가 안 돌았다` 로 보고하고 멈춘다 (어제 것을 오늘 것처럼 올리지 않는다).

## 1½. 오른쪽 패널 (cmux 안일 때만)

`CMUX_SURFACE_ID` 가 비어 있으면 이 절을 통째로 건너뛴다 (iTerm 등 다른 터미널, `발행만` 무인 모드).

1. 브리지를 백그라운드로 띄운다 — Bash 툴 `run_in_background: true`:
   ```sh
   .venv/bin/python .claude/skills/morning-scan/scripts/bridge.py
   ```
   stdout 첫 줄이 `OK` 면 된다. 이미 떠 있으면 대상 터미널만 이 세션으로 갱신하고 바로 끝난다 (그래도 `OK`). `FAIL` 이면 그 줄을 보고에 넣고 패널 없이 2 절로 간다 — 발행은 브리지와 무관하다.
2. 오른쪽 패널에 연다:
   ```sh
   ~/.claude/skills/cmux-viewer-pane/scripts/cmux-view open http://127.0.0.1:47821/ --replace
   ```
   포트는 `scan.py` 의 `BRIDGE_PORT`. **파일 경로가 아니라 브리지 URL 로 열어야 버튼이 산다** — 페이지 JS 가 `/health` 로 브리지를 확인하고 그때만 버튼을 보인다.
3. 사용자가 카드의 `정리하기` 버튼을 누르면 브리지가 이 터미널에 `/youtube-study-note <링크>` 또는 `/news-briefing-digest <링크>` 를 타이핑하고 Enter 를 친다. 그 다음은 평소 슬래시 커맨드와 같다 — 훅이 worktree 를 파고 스킬이 돈다. 기본 스킬은 제목에 `모닝루틴` 이 있으면 다이제스트, 아니면 스터디 노트 (`scan.py` `DIGEST_TITLE_KEYWORDS`). 작은 두 번째 버튼이 나머지 스킬이다. 눌린 명령이 다음 프롬프트로 들어오면 그냥 그 스킬을 돈다 — 모닝스캔이 시킨 게 아니라 사용자가 시킨 것이다.

Artifact 발행(2 절)은 그대로 한다. Artifact 쪽에선 외부 fetch 가 막혀 버튼이 자동으로 숨겨진다. (2026-09-29 cmux 안에서 실측: 패널→localhost fetch, `cmux send`→프롬프트 입력 둘 다 됨.)

## 2. 발행

대상 페이지: `https://claude.ai/code/artifact/ffbc40d7-2ff8-4417-b958-7b31e5095fa9`

1. `Read` 툴로 `.work/morning-scan/morning-scan.html` 을 읽는다. 내가 만들지 않은 파일은 읽어야 발행할 수 있다는 Artifact 툴 규칙 때문이지, 내용을 검토하려는 게 아니다. `artifact-design` 스킬은 로드하지 않는다 — HTML 을 쓰는 게 아니라 옮기는 것이다.
2. Artifact 툴 `action: "read"` 로 대상 URL 을 한 번 읽는다. 기존 페이지를 갱신하려면 읽기가 먼저여야 한다. 돌아온 내용은 볼 필요 없다.
3. Artifact 툴로 발행한다 — `file_path` 는 `/Users/ymac/IdeaProjects/ai-projects/rich-to-be/.work/morning-scan/morning-scan.html`, `url` 은 대상 페이지, `description` 은 `팔로우하는 경제 유튜브 채널 5곳의 지난 24시간 업로드 목록`. `favicon` · `title` · `capabilities` 는 넘기지 않는다 (기존 값 유지, `<title>` 은 HTML 안에 있다). **HTML 은 완성본이다. 내용을 새로 만들거나 고치지 않는다.**
4. 발행 결과에 실린 URL 이 대상과 같으면 끝이다.

실패는 셋으로 가른다:

- **"읽지 않은 아티팩트" 거부 · 버전 충돌** — 페이지는 살아 있다. 2 를 다시 하고 3 을 한 번 더 한다. 절대 `force` 를 쓰지 않는다. 두 번째도 안 되면 FAIL 로 보고한다.
- **Artifact 툴 자체가 없다** (`claude -p` print 모드가 그렇다, 2026-09-04 실측) — `FAIL  Artifact 툴이 없는 세션이라 발행 못 함. 파일은 .work/morning-scan/morning-scan.html 에 있으니 대화 세션에서 '/morning-scan 발행만'` 으로 보고하고 끝낸다.
- **대상 페이지가 없거나 내 것이 아니다** — 이때만 `url` 없이 새 Artifact 로 발행한다 (`favicon: "📡"`). 보고 첫 줄은 `FAIL  대상 페이지 갱신 실패 → 새 페이지 <새 URL>` 이고, 이 파일의 "대상 페이지" 주소를 새 URL 로 `Edit` 한 뒤 그 변경을 커밋해 달라고 알린다 (`commit-note.sh` 훅은 `notes/` 만 커밋하므로 SKILL.md 는 손으로 커밋해야 한다).

## 3. 보고

정상이면: `scan.py` 의 stdout 을 그대로 옮긴다 (`OK` 줄 · 건수 줄 · 새 영상 `-` 줄들 · 걸러낸 `x` 줄들) 그리고 발행된 URL 한 줄. `->` 경로 줄은 뺀다. 페이지 내용을 다시 서술하지 않는다. 1½ 절을 했으면 `오른쪽 패널: http://127.0.0.1:47821/ — 카드의 정리하기 버튼이 이 터미널에 스킬 명령을 넣는다` 한 줄을 더한다.

`발행만` 모드면 scan.py stdout 이 없다. `.work/morning-scan/run.log` 에서 마지막 `─────` 구분선 이후의 `OK` 부터 `x` 줄까지를 옮기고, 없으면 발행된 URL 만 보고한다.

문제가 있었으면 첫 줄이 `FAIL` 로 시작한다 (1·2 절의 문구 그대로). scan.py 의 FAIL 이면 `references/rules.md` 트러블슈팅에서 맞는 항목 한 줄을 사용자에게 같이 전한다. FAIL 보고에는 아래 마무리 줄을 붙이지 않는다.

끝에 한 줄만 덧붙인다 — 새 영상 중 정리할 게 있으면 링크를 주면 `youtube-study-note` · `news-briefing-digest` 로 노트를 만든다는 것. 오른쪽 패널을 열었으면 "링크를 주거나 패널의 정리하기 버튼을 누르면" 으로 쓴다. `발행만` 모드(무인)에선 이 줄을 뺀다 — 읽는 사람이 없다.

## 지키는 것

- 이 스킬은 `notes/` 를 쓰지 않으므로 worktree 격리 대상이 아니다 (`.claude/skill-worktree.sh` 의 `case` 예외). 격리되면 `.env` · `.venv` · `.work/` 가 없어 반드시 실패한다. 시작할 때 `git rev-parse --absolute-git-dir` 와 `git rev-parse --path-format=absolute --git-common-dir` 가 다르면 워크트리 안이다 — 멈추고 그렇게 보고한다.
- 새 영상이 있어도 자막을 받거나 내용을 요약하지 않는다. 그건 사용자가 다음에 링크를 주며 시키는 일이다.
- 채널·규칙·기준값을 바꾸려면 `scan.py` 를 고친다. 이 파일이나 references 에 목록을 복제하지 않는다. 고친 뒤 `--selftest` (`scan.py` · `bridge.py` 둘 다).
- 브리지는 127.0.0.1 전용이고, 터미널에 넣는 문자열은 `bridge.py` 의 `command_for()` 가 조립한 두 스킬 명령만이다 (스킬 이름 화이트리스트 + 11자 영상 ID). 임의 텍스트나 다른 명령을 보내는 기능을 추가하지 않는다 — 로컬 HTTP 요청이 터미널 입력으로 바뀌는 통로라서 좁게 유지하는 게 안전장치다.
- 무인 실행(매일 아침 9시 launchd/cron)은 `references/schedule.md`. 지금은 수집까지만 무인이다.
