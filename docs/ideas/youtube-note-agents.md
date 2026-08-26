# YouTube 노트 — 에이전트 구조 refine

> **2026-08-26 추가.** 이 문서가 설계한 `youtube-note` 스킬 하나는 `news-briefing-digest` 와 `youtube-study-note` 둘로 해체됐다. 폐기된 대안(NotebookLM 자동화, yt-dlp, YouTube Data API v3)에 대한 판단은 그대로 유효하다. 해체 경위와 무엇을 버렸는지는 `tasks/split-youtube-note.md`.

`docs/youtube-note-plan.md` 의 후속. 계획서는 "스킬 1개 + NotebookLM 수동 복붙"으로 확정돼 있었다. 이 문서는 그 두 가지를 모두 뒤집는다.

## Problem Statement

> 긴 영상의 자막을, **뒷부분까지 앞부분과 같은 밀도로** 코넬 노트화하려면 어떻게 해야 하나?

단일 컨텍스트에서 구간 5개를 연속으로 쓰면 Part 4~5가 눈에 띄게 부실해진다. 이게 fan-out의 유일한 명분이다.

## 실측으로 확정된 것

추측이 아니라 이 세션에서 직접 돌려본 결과다. 대상: `aircAruvnKk` (3Blue1Brown, 18:40).

| 경로 | 결과 |
|---|---|
| YouTube timedtext API 직접 호출 | ❌ 0바이트. proof-of-origin 토큰 요구. 페이지 안에서 fetch해도 동일 |
| YouTube Data API v3 | ❌ `captions.download`는 **본인 소유 영상만**. 남의 영상 불가 |
| NotebookLM + cmux 브라우저 | ⚠️ 미검증. cmux 브라우저는 Chrome과 별도 프로필이라 Google 로그인부터 안 돼 있음 |
| yt-dlp | ✅ 작동. 단 VTT를 정규식으로 파싱 + 중복 제거 직접 구현 필요 (12줄) |
| **youtube-transcript-api** | ✅ **작동. yt-dlp와 바이트 단위 동일 결과(21,576 B / 286 snippet)** |

**결정: `youtube-transcript-api`.** yt-dlp와 결과물이 같은데 코드가 훨씬 짧다. `.start` / `.text` 구조체를 그대로 주므로 VTT 파싱이 통째로 사라진다. `is_generated` 플래그로 사람이 쓴 자막을 자동생성보다 우선 고르는 것도 공짜다.

제목은 이 라이브러리가 주지 않는다. **oEmbed로 메운다** — API 키도 의존성도 불필요:

```
https://www.youtube.com/oembed?url=<영상URL>&format=json  →  {"title": ..., "author_name": ...}
```

### NotebookLM을 버리는 이유

NotebookLM은 자막을 새로 만들지 않는다. **YouTube 자막 트랙을 그대로 가져온다.** 즉 브라우저를 자동화해 얻는 데이터는 위와 동일하다. 그 동일한 데이터를 위해 치르는 비용:

- Google 로그인 + 쿠키 이관 (1회) — cmux 브라우저는 Chrome과 별도 프로필
- 소스 인제스트 대기 30초~2분 (매회)
- 버튼 클릭용 element ref를 얻으려면 `snapshot --interactive` 필수. **회당 2~5k 토큰이고 파일 리다이렉트로 우회 불가**
- Google이 UI를 바꾸면 즉시 깨짐

회당 ~300 토큰 vs ~20~40k 토큰. 원래 계획서가 NotebookLM을 고른 이유는 "브라우저 자동화가 없으니 사람이 복붙할 창구가 필요해서"였다(계획서 10~11번 줄). NotebookLM은 **자동화의 대상이 아니라 자동화가 없을 때의 대안**이었고, 라이브러리 경로가 열린 지금 그 역할은 끝났다.

### 자동생성 자막 — 실측한 타임스탬프 오차

같은 영상의 자동생성 영어 자막은 500 snippet(수동 286)이고 문장 중간에서 끊긴다 — `'resolution of 28x 28 pixels. But your'` / `'brain has no trouble recognizing it as a'`. 구두점은 붙어 나오므로 구간 sub-agent가 산문으로 읽으며 흡수한다.

문제는 타임스탬프다. 수동 자막(문장 정렬됨)을 기준선으로 삼아 동일 문장 113개를 매칭해 측정했다:

| 지표 | 보정 전 | 상수 보정 후 |
|---|---|---|
| 중앙값 오차 | **+2.24s** | **1.01s** |
| 90퍼센타일 | 3.58s | — |
| 최대 | 7.32s | — |
| auto가 **늦은** 경우 | **92%** | — |

**자동자막은 늦게 찍힌다.** ASR 표시 지연이고, 92%가 한 방향이라 **계통 오차**다. 따라서 상수 `-2.2초`를 빼는 것만으로 잔차 중앙값이 1초로 떨어진다. 계획서 64번 줄의 행 첫머리 `[MM:SS]`는 이 보정을 넣으면 실용 정확도에 도달한다.

```python
# ponytail: 자동자막 표시지연 보정. 영상 1개(aircAruvnKk)에서 측정한 상수.
# 영상별로 다르면 수동/자동 자막이 모두 있는 영상으로 재측정해 조정할 것.
AUTO_CAPTION_LAG = 2.2
start = max(0.0, x.start - (AUTO_CAPTION_LAG if is_generated else 0.0))
```

수동 자막일 때는 보정하지 않는다 — 기준선 자체다.

## Recommended Direction

**1. 자막 수급은 에이전트가 아니라 스크립트다.**

원안의 "NotebookLM에서 자막을 뽑아오는 agent"는 판단이 필요 없는 결정론적 작업이다. 라이브러리 호출 20줄이면 끝난다. 에이전트로 감싸면 비용만 늘고 실패 모드만 늘어난다.

**2. 메인 에이전트는 자막 전문을 컨텍스트에 올리지 않는다.**

마지막 타임스탬프로 구간 수를 계산하고, 스크립트로 자막을 N개 파일로 쪼갠 뒤, 각 sub-agent에게 **파일 경로만** 넘긴다. 이게 없으면 fan-out을 해도 메인이 자막 전문을 다 먹어서 컨텍스트 절감이 0이 된다.

**3. 총정리는 두 역할로 쪼갠다.**

요약을 쓰는 에이전트와 규칙 위반을 잡는 에이전트는 관심사가 반대다. 한 에이전트에게 "요약도 하고 네 요약이 판단 금지를 어겼는지도 검사해라"라고 시키면 자기가 쓴 걸 자기가 통과시킨다.

**4. 요약은 `synthesizer`가 독점한다. `section-note`는 요약하지 않는다.**

계획서 61번 줄의 구간별 `**Summary**: 2~3줄` 행은 **삭제한다.** `section-note`는 코넬 2단 표(단서/필기)만 만들고, 요약이라는 행위는 전부 `synthesizer`로 몰아준다. 기록과 요약이 한 에이전트 안에 섞이면 기록 단계에서 이미 압축이 일어나 정보가 샌다.

연쇄 효과: `synthesizer`가 읽을 Summary 줄이 없어지므로 **노트 본문 전체를 읽는다.** 노트는 자막보다 압축돼 있어 60분 기준 ~6~9k 토큰이고, 감당 가능하다.

## 에이전트 구성

원안 4개 → 스크립트 2 + 에이전트 4.

| # | 이름 | 종류 | 입력 | 출력 |
|---|---|---|---|---|
| 1 | `fetch-transcript` | **스크립트** (원안 ①이 붕괴) | YouTube URL | `transcript.txt`, `meta.json`(제목·저자) |
| 2 | `split` | **스크립트** (원안 ②가 붕괴) | `transcript.txt` | `part-01.txt` … `part-NN.txt` |
| 3 | `glossary` | **에이전트 (1회, 폐기형)** | `transcript.txt` 전문 | 용어집 (원어–번역어 대응표) |
| 4 | `section-note` ×N | **에이전트 (병렬)** | `part-XX.txt` 경로 + 용어집 | `note-part-XX.md` — **표만, 요약 없음** |
| 5a | `synthesizer` | **에이전트** (원안 ④ 분할) | 노트 본문 전체 | 헤더 + 전체 흐름 섹션 |
| 5b | `auditor` | **에이전트** (원안 ④ 분할) | 완성 문서 + 용어집 | 수정 지시 목록 |

**순서**: 1 → 2 → 3 → 4(병렬) → 5a → 5b.

`auditor`가 마지막인 이유: `synthesizer`의 요약이 판단 금지를 어길 확률이 가장 높은 지점이다. 요약을 검수 대상에서 빼면 검수의 의미가 없다.

### `glossary` 에이전트 — 메인 컨텍스트를 지키는 방식

sub-agent를 병렬로 돌리면 용어 표기가 갈린다 (`역전파` vs `백프로퍼게이션`). 사전에 용어집을 만들어 넘기면 애초에 갈리지 않는다.

문제는 "용어집을 만들려면 자막 전문을 읽어야 한다"는 점이고, 이는 **"메인은 자막 전문을 올리지 않는다"** 원칙과 충돌하는 것처럼 보인다. 해법은 **전용 에이전트가 자기 컨텍스트에서 전문을 읽고 용어 목록만 뱉고 사라지는 것**이다. 자막은 sub-agent의 컨텍스트에 들어갔다 버려지고, 메인은 작은 용어집만 받는다. 원칙은 유지된다.

용어집은 `section-note`(표기 통일)와 `auditor`(위반 검출 기준) 양쪽이 쓴다.

### 삭제 — 영상 길이 확인 agent

`transcript.txt` 마지막 줄의 타임스탬프가 곧 영상 길이다. `ceil(길이 / 15분)`. 계획서 35~36번 줄에 이미 있는 산술 두 줄이고, 에이전트를 띄우는 오버헤드가 계산보다 크다.

### 분할 — 총정리 agent

- **5a `synthesizer`**: 전체 흐름 서술 + 구간 간 연결고리(`Part 2의 개념이 Part 4에서 확장됨`). `section-note`가 요약을 하지 않으므로 노트 본문 전체를 읽는다.
  - 제약: **시간순 흐름 서술만 허용, 중요도 순위 금지.** 계획서 76번 줄과 충돌하지 않으려면 이 선을 명시해야 한다. "이 영상의 핵심은 X다" 금지 / "X를 다룬 뒤 Y로 넘어간다" 허용.
- **5b `auditor`**: 판단 금지 위반(좋다/나쁘다/추천/주의), 용어집 대비 표기 일치, 표 포맷(`<br>` 누락, 셀 깨짐) 검증.

## 검증된 자막 수급 코드

```python
from youtube_transcript_api import YouTubeTranscriptApi
import json, urllib.request

def fetch(video_id, langs=("ko", "en")):
    api = YouTubeTranscriptApi()
    tracks = list(api.list(video_id))
    # 사람이 쓴 자막 우선, 없으면 자동생성
    for generated in (False, True):
        for lang in langs:
            for t in tracks:
                if t.language_code == lang and t.is_generated == generated:
                    return t.fetch().snippets, (lang, generated)
    raise SystemExit("자막 없음 — 이 영상은 처리 불가")

def ts(sec):
    s = int(sec)
    return f"[{s//3600:02d}:{s//60%60:02d}:{s%60:02d}]"

def title(video_id):
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    with urllib.request.urlopen(url) as r:
        return json.load(r)["title"]
```

`snippets`의 각 항목은 `.start`(초, float) / `.duration` / `.text`. 15분 버킷팅은 `int(x.start // 900)` 한 줄.

## Key Assumptions to Validate

- [~] ~~구간을 나눠 쓰면 뒷부분 품질이 올라가는가~~ → **검증하지 않기로 결정.** fan-out 구조를 그대로 간다.
- [x] ~~60초 오버랩이 경계 문맥 단절을 막는가~~ → **막지 못했다. 120초로 상향.** 60초로 돌린 첫 실행에서 경계 오기가 실제로 발생 — `[28:34]`에 한 번만 나온 "스트레이키즈"를 Part 3가 못 보고 "트와이스"로 적었다. 120초로 재실행하니 Part 2·3 모두 정확히 적었다.
- [ ] **auditor가 실제로 위반을 잡는다** — 판단성 표현을 일부러 섞은 노트를 넣고 검출되는지. 못 잡으면 사후 검수보다 사전 규칙 강화가 답이다.
- [ ] **한국어 자동생성 자막으로도 쓸 만한 노트가 나온다** — 이번 실측의 한국어 트랙은 사람이 번역한 것이었다. 자동생성 한국어는 미검증이고, 실제로 볼 영상은 그쪽일 가능성이 높다.
- [ ] **긴 영상에서 라이브러리가 버틴다** — 18분에서만 확인했다. 3시간짜리, 그리고 연속 호출 시 rate limit(yt-dlp 테스트 중 429를 한 번 봤다).

## MVP Scope

**전부 들어간다.** 파이프라인 6단계(스크립트 2 + 에이전트 4)가 곧 MVP다.

- `fetch-transcript` + `split` 스크립트 (위 코드 기반, **120초 오버랩**, 자동자막이면 2.2초 지연 보정)
- `glossary` 1회 실행
- `section-note` 병렬 실행 — **표만, Summary 행 없음**
- `synthesizer` + `auditor`
- 판단 금지 규칙은 계획서 68~86번 줄 그대로 승계 (61번 줄 Summary 행만 삭제)

`synthesizer` / `auditor`를 뒤로 미루자던 이전 초안은 철회한다. **이 둘이 없으면 프로젝트를 할 이유가 없다** — 구간별 노트만 흩어져 있는 건 자막을 표로 바꾼 것에 불과하고, 총정리와 규칙 검수가 붙어야 "구조적으로 파악한다"는 원래 목적(계획서 5번 줄)이 성립한다.

fan-out이 뒷부분 품질을 올리는지에 대한 대조 실행은 **하지 않기로 했다.** 구조를 그대로 간다.

## Not Doing (and Why)

- **NotebookLM 자동화** — 같은 자막을 60~100배 비싸게, 훨씬 잘 깨지는 방법으로 얻는다.
- **yt-dlp** — 작동은 하지만 youtube-transcript-api와 결과가 동일하고 VTT 파싱이 더 든다. 후자가 YouTube 차단에 막히면 1순위 대안.
- **YouTube Data API v3** — 남의 영상 자막을 못 준다. 검토 종료.
- **영상 길이 확인 에이전트** — 산술 2줄.
- **자막 없는 영상 대응** — 별도 STT가 필요하고 범위 밖. 스크립트가 명시적으로 실패한다.
- **Python CLI 이식** — 계획서 102번 줄 그대로. 프롬프트가 곧 결과물이다.

## 해결된 Open Questions

- ~~오버랩 60초가 맞나?~~ → **120초 확정, 중복 기재를 허용한다.** 60초는 경계에서 한 번만 언급된 고유명사를 놓쳐 오기를 냈다(위 참조). 중복 기재를 허용하므로 겹침을 늘리는 비용은 노트 길이뿐이다. "읽되 쓰지 말라"는 지시는 넣지 않는다.
- ~~용어 표기가 갈린다~~ → **사전 용어집 확정.** 전용 `glossary` 에이전트가 자막 전문을 자기 컨텍스트에서 읽고 용어집만 반환한 뒤 폐기된다. 메인 컨텍스트는 오염되지 않는다.
- ~~`youtube-transcript-api` 설치 위치~~ → **리포 내 `.venv/` 확정, 생성 완료.** Python 3.13.5 / youtube-transcript-api 1.2.4. `.gitignore`에 `.venv/` 추가. (`notes/`는 산출물이므로 커밋 대상 — gitignore하지 않는다.)
- ~~자동자막 타임스탬프 어긋남~~ → **실측 완료. 보정 전 중앙값 2.24초, 상수 보정 후 1.01초.** 92%가 한 방향(늦음)이라 계통 오차이며 `-2.2초` 상수로 보정한다. 위 "자동생성 자막" 절 참조.

## 남은 Open Questions

- ~~`AUTO_CAPTION_LAG = 2.2` 가 영상마다 다른가?~~ → **영상별 자동 측정은 불가능. 사람이 확인하는 절차로 확정.**
  측정하려면 같은 언어의 수동 자막이 기준선으로 필요한데, 그게 있으면 애초에 자동자막을 쓰지 않는다. 잴 수 있을 때는 필요 없고 필요할 때는 잴 수 없다.
  대신 `--probe` 가 초반 120초를 `원본 / 보정후` 두 열로 뽑아 주고, 사용자가 영상과 대조한 뒤 `--lag <초>` 로 넘긴다. 2.2초는 기본값으로만 남고 `meta.json` 의 `lag_source` 에 `기본값(미측정)` / `사용자 지정` 이 기록된다.
- **`glossary`가 값을 하는가?** 자막 전문을 한 번 더 읽는 비용(60분 ≈ 18k 토큰)을 치른다. `auditor`의 사후 통일만으로 충분하면 이 에이전트는 통째로 삭제 대상이다. 첫 실행에서 용어집 없이 한 번 돌려 표기가 실제로 갈리는지 확인할 것.
