# 무인 실행 — 매일 아침 9시

`scripts/run.sh` 가 진입점이다. 손으로 부를 때는 이 문서가 필요 없다 — 스킬을 부르면 된다.

> **지금은 수집까지만 무인이다.** 2026-09-04 실측(claude 2.1.260): `claude -p` print 모드에는 Artifact 툴이 없고 `--allowedTools` · `--tools` 로도 안 생긴다. 그래서 `run.sh` 는 기본으로 `scan.py` 만 돌리고 발행을 건너뛴다. 발행은 대화 세션에서 `/morning-scan 발행만` 한 번이다. 무인 발행까지 원하면 발행 경로를 Artifact 가 아닌 것(예: `notes/` 에 넣어 GitHub Pages 로)으로 바꿔야 하고, 그건 이 스킬 범위 밖의 결정이다. print 모드에 Artifact 툴이 생기면 `.env` 에 `MORNING_SCAN_PUBLISH=claude` 를 넣으면 옛 경로가 켜진다.

## 왜 로컬인가

클라우드 예약 작업으로도 만들어 봤지만, 무인 실행에서는 외부 URL 호출이 사람의 승인을 요구해서 매번 막혔다. 로컬에서는 파이썬 표준 라이브러리의 HTTP 호출이 그냥 되고, 승인 절차도 응답 캐시도 없다. 대신 **아침 9시에 컴퓨터가 켜져 있어야 한다.** macOS launchd 는 맥이 자고 있었으면 깨어난 직후 놓친 작업을 실행해 주므로 대부분의 날은 잡힌다.

## run.sh 가 하는 일

1. 리포 루트로 이동하고 `PATH` 를 깐다 — launchd/cron 은 최소 PATH 만 물려주므로 `claude` 를 못 찾는다.
2. `.env` 를 source 한다. `CLAUDE_CODE_OAUTH_TOKEN` 이 여기서 환경으로 들어간다.
3. `scan.py` 를 돌린다. 여기서 실패하면 claude 를 부르지 않고 끝낸다 (토큰 낭비 없음).
4. `.env` 에 `MORNING_SCAN_PUBLISH=claude` 가 있을 때만 `claude -p "/morning-scan 발행만"` 을 부른다 (위 안내 참고 — 지금은 안 켠다). 출력이 `FAIL` 로 시작하면 exit 1.
5. 전부 `.work/morning-scan/run.log` 에 남긴다.

**키는 Claude 에게 노출되지 않는다.** `YOUTUBE_API_KEY` 는 `.env` → `scan.py` 로만 흐르고, Claude 는 완성된 HTML 파일을 발행할 뿐이다.

## 준비 (한 번만)

### 1. Claude 장기 토큰

```sh
claude setup-token
```

출력된 토큰을 리포 루트 `.env` 의 `CLAUDE_CODE_OAUTH_TOKEN=` 뒤에 붙인다. 유효기간 1년. 무인 실행에서 일반 로그인 세션이 만료되면 헤드리스 모드는 갱신 없이 그냥 실패하는데, 이 토큰이 그걸 막는다.

> `ANTHROPIC_API_KEY` 로 인증하면 Artifact 발행이 안 된다. 반드시 OAuth 토큰을 쓴다.

### 2. 손으로 한 번

```sh
.claude/skills/morning-scan/scripts/run.sh
```

정상이면:

```
[1/2] 유튜브 데이터 수집
OK  2026년 9월 5일 토요일 · 09:00 KST 기준
    새 영상 2건 (한경 코리아마켓, 소수몽키) · 조용한 채널 3곳 · 걸러냄 1건
    -> /Users/you/rich-to-be/.work/morning-scan/morning-scan.html
[2/2] 발행 건너뜀 — 대화 세션에서 '/morning-scan 발행만' 을 돌리면 위 파일이 Artifact 로 올라간다
```

여기서 실패하면 스케줄 걸기 전에 먼저 해결한다.

### 3. 스케줄 등록

#### macOS (launchd 권장)

`scripts/com.morningscan.daily.plist` 의 `__경로__` 를 리포 절대경로로 바꿔 LaunchAgents 에 넣는다:

```sh
sed "s|__경로__|$(pwd)|g" .claude/skills/morning-scan/scripts/com.morningscan.daily.plist \
  > ~/Library/LaunchAgents/com.morningscan.daily.plist
launchctl load ~/Library/LaunchAgents/com.morningscan.daily.plist
```

확인 / 즉시 실행 / 해제:

```sh
launchctl list | grep morningscan
launchctl start com.morningscan.daily
launchctl unload ~/Library/LaunchAgents/com.morningscan.daily.plist
```

plist 를 고친 뒤에는 반드시 `unload` → `load` 를 다시 해야 반영된다.

#### Linux / WSL (cron)

```
0 9 * * * /bin/bash /절대경로/rich-to-be/.claude/skills/morning-scan/scripts/run.sh
```

WSL 은 cron 데몬이 기본으로 꺼져 있다. `sudo service cron start` 로 켜고 부팅 시 자동 시작하도록 해 둔다.

## 문제가 생기면

먼저 `.work/morning-scan/run.log`.

**`FAIL  claude 를 찾을 수 없습니다`** — `which claude` 결과의 디렉토리를 `run.sh` 의 `export PATH=...` 줄에 더한다.

**`OAuth session expired`** — `claude setup-token` 을 다시 돌려 `.env` 의 토큰을 갱신한다. 1년마다.

**launchd 가 안 도는 것 같다** — `.work/morning-scan/launchd.err.log`. 비어 있으면 아예 실행이 안 된 것이니 `launchctl list | grep morningscan` 으로 등록 상태를 보고 plist 경로가 실제 경로와 맞는지 다시 본다.

수집 단계 오류는 `rules.md` 의 트러블슈팅.
