# 채널 · 규칙 · 트러블슈팅

정본은 `scripts/scan.py` 의 `CHANNELS` 와 상수다. 이 문서는 그것을 사람이 읽기 좋게 풀어 쓴 것이다. 두 곳이 어긋나면 코드가 맞다.

## 채널과 규칙

| 채널 | 핸들 | 규칙 |
|---|---|---|
| 한경 코리아마켓 | `@hk_koreamarket` | 라이브만 |
| 박곰희TV | `@gomhee` | 동영상만 |
| 박종훈의 지식한방 | `@kpunch` | 동영상만 |
| 소수몽키 | `@sosumonkey` | 동영상 + 라이브 |
| 수페TV | `@supe-tv` | 동영상만 |

- **쇼츠(3분 이하)는 전 채널 공통 제외.** YouTube API 가 쇼츠 여부를 안 주므로 재생시간으로 자른다 (`SHORTS_MAX_SEC = 180`).
- **재생시간 0초는 "예정"** — 아직 시작 안 한 예약 라이브다 (다음날 모닝루틴이 전날 밤에 미리 올라온다). 쇼츠보다 먼저 가르고, 카드에는 안 올리며 걸러낸 항목에 `(예정)` 으로 남긴다.
- **라이브 여부는 제목으로 추측하지 않는다.** `search.list(eventType=completed)` 가 돌려주는 "완료된 라이브 방송" 목록에 있으면 라이브다. `video_and_live` 채널은 이 조회를 건너뛴다 (어차피 다 통과).
- **24시간 창** (`WINDOW_HOURS = 24`). 창 안에 새 영상이 없는 채널은 "새 영상 없음" 절에 규칙을 통과한 **직전 업로드**를 보여준다.
- 창 안이지만 규칙에 걸린 영상은 푸터에 "오늘 걸러낸 항목" 으로 남긴다 — 왜 카드가 안 떴는지 확인할 수 있게.
- 라이브 전용 채널의 새 라이브가 장 시작(09:00 KST) 전 2시간 안에 시작됐으면 "장 시작 N분 전 방송 시작" 부제를 단다.

## API 사용량

하루 한 번 실행에 약 **406유닛** (한도 10,000).

| 호출 | 횟수 | 유닛 |
|---|---|---|
| `playlistItems.list` (채널별 최근 10건) | 5 | 5 |
| `videos.list` (재생시간, 최대 50개 묶음) | 1 | 1 |
| `search.list` (완료된 라이브) | 4 | 400 |

`search` 가 거의 전부다. 채널을 `live_only` / `video_only` 로 추가할 때마다 100유닛씩 는다.

## 채널 추가 · 삭제 · 규칙 변경

`scan.py` 의 `CHANNELS` 를 편집한다. 새 채널의 ID 는 핸들로 조회한다:

```sh
set -a; . ./.env; set +a
curl -s "https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&forHandle=@핸들&fields=items(id,snippet/title,contentDetails/relatedPlaylists/uploads)&key=$YOUTUBE_API_KEY"
```

`id` 가 `channel_id`, `uploads` 가 `uploads` 다. `rule` 은 `live_only` / `video_only` / `video_and_live` 중 하나.

바꾼 뒤에는 `--selftest` 가 그대로 통과하는지 본다 — 픽스처는 현재 5개 채널의 uploads ID 를 키로 쓰므로, 채널을 빼면 픽스처도 같이 고친다.

## 기준값

| 무엇 | 어디 |
|---|---|
| 수집 범위 | `scan.py` `WINDOW_HOURS` |
| 쇼츠 기준 | `scan.py` `SHORTS_MAX_SEC` |
| 장 시작 시각 | `scan.py` `MARKET_OPEN_KST` |
| 페이지 디자인 | `scripts/template.html` — `<!--FEED-->` 같은 주석이 데이터 자리. `scan.py` 는 안 건드려도 된다 |
| 실행 시각 (무인) | plist 의 `Hour`/`Minute` 또는 crontab 앞 두 필드 (`schedule.md`) |
| 브리지 포트 | `scan.py` `BRIDGE_PORT` — `bridge.py` 와 `template.html`(치환) 이 같이 쓴다 |
| 정리하기 기본 스킬 | `scan.py` `DIGEST_TITLE_KEYWORDS` — 제목에 있으면 다이제스트, 없으면 스터디 노트 |

## 정리하기 버튼 (cmux 안에서만)

카드마다 `정리하기 → 스터디 노트`(채운 색, 기본 스킬) / `다이제스트로 정리`(테두리만, 다른 스킬) 두 버튼이 있다. 모닝루틴 카드는 반대다. 브라우저 패널의 페이지는 JS 라서 터미널을 직접 못 건드리므로 `scripts/bridge.py` 가 사이에 선다.

```
버튼 클릭 → GET http://127.0.0.1:47821/note?v=<videoId>&skill=<스킬>
        → bridge.py 가 검증 후  cmux send --surface <이 터미널> "/<스킬> https://www.youtube.com/watch?v=<id>\n"
        → Claude Code 프롬프트에 슬래시 커맨드가 입력·제출됨 → 평소처럼 훅이 worktree 를 파고 스킬이 돈다
```

- 페이지는 브리지가 서빙한다 (`GET /` 가 `.work/morning-scan/morning-scan.html` 을 매번 새로 읽는다). 페이지 JS 는 `/health` 가 답할 때만 버튼을 보인다 — Artifact 페이지에선 외부 fetch 가 막혀 버튼이 없다.
- 대상 터미널은 `.work/morning-scan/bridge-target` 파일이다. 브리지를 다시 띄우면 서버는 그대로 두고 이 파일만 새 `CMUX_SURFACE_ID` 로 바꾼다. 세션을 옮겼는데 명령이 옛 터미널로 가면 이 파일을 본다.
- 터미널로 가는 문자열은 `command_for()` 가 조립한 것만이다. 스킬 이름은 `SKILL_LABEL` 화이트리스트, 영상 ID 는 `[A-Za-z0-9_-]{11}`. 셸을 거치지 않고 인자 리스트로 `cmux send` 를 부른다.
- 무인 실행(`run.sh`)은 브리지를 안 띄운다 — 볼 사람도 터미널도 없다.

## 트러블슈팅

**`FAIL  YOUTUBE_API_KEY 가 비어 있습니다`**
리포 루트 `.env` 에 `YOUTUBE_API_KEY=` 가 없다. `.env.example` 참고.

**`playlistItems 호출 실패 (HTTP 403)`**
키 문제다. Google Cloud Console 에서 키가 살아 있는지, YouTube Data API v3 가 사용 설정돼 있는지, 키 제한이 이 API 를 막고 있지 않은지 본다. 하루 할당량 초과일 수도 있다.

**`search 호출 실패 (HTTP 403)` 만 난다**
할당량 초과 가능성이 높다 — `search` 가 비싸다. 다음 날 자정(PT) 에 초기화된다.

**새 영상이 있는데 카드에 없다**
푸터의 "오늘 걸러낸 항목" 을 본다. 쇼츠(3분 이하)이거나 채널 규칙(라이브만/동영상만)에 걸린 것이다. 라이브인데 "라이브 아님" 으로 걸러졌다면 방송이 아직 "완료" 처리되지 않았거나 `search` 결과 10건 밖으로 밀린 것이다.

**패널에 카드는 있는데 정리하기 버튼이 없다**
브리지가 안 떠 있거나, 패널을 파일 경로로 열었다. `curl -s http://127.0.0.1:47821/health` 가 `ok morning-scan-bridge` 를 돌려주는지 보고, 패널은 `http://127.0.0.1:47821/` 로 다시 연다.

**버튼을 눌렀는데 터미널에 아무것도 안 들어온다**
`.work/morning-scan/bridge-target` 이 지금 세션의 `CMUX_SURFACE_ID` 인지 본다. 다르면 `bridge.py` 를 한 번 더 돌린다 (파일만 갱신하고 끝난다). 브리지 stdout 의 `FAIL` 줄에 `cmux send` 오류가 찍힌다.

**페이지는 그대로인데 실패 메시지도 없다**
`.work/morning-scan/morning-scan.html` 의 수정 시각을 본다. 파일이 새것이면 발행 단계 문제, 옛것이면 수집 단계 문제다.
