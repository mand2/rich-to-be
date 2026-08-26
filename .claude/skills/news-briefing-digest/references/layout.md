# 레이아웃 & CSS

## 설계 의도

이 문서는 **스캔용**이다. 스터디 노트는 정독을 전제로 여백을 넉넉히 썼지만, 다이제스트는 반대다. 한 화면에 최대한 많이 보이되 꼭지 경계가 명확해야 한다. 밀도를 올리고, 구분은 여백이 아니라 선과 배경으로 만든다.

읽는 순서가 아니라 **고르는 순서**로 설계한다. 헤드라인 3개와 숫자를 먼저 보고, 분야 라벨로 자기 관심사를 찾고, 그 안에서 카드 제목만 훑다가 하나를 정독한다. 이 동선이 막히지 않게 한다.

## 색

포인트 컬러 하나 + 회색조. 분야 그룹마다 색을 다르게 주고 싶은 유혹이 있는데, **하지 않는다.** 그룹이 4개면 색이 4개가 되고 문서가 산만해진다. 그룹 구분은 라벨과 선으로 충분하다.

포인트 컬러는 채널 성격에 맞게: 경제·금융 `#1d4ed8` / 종합뉴스 `#b91c1c` / 기술 `#0f766e` / 산업 `#c2410c`

`--flag` 색(주황 계열)은 '왜 중요한가'와 '진행자' 라벨에만 쓴다. 이 두 가지가 다이제스트의 부가가치이므로 눈에 걸려야 한다.

## 뼈대

```html
<div class="brief">

  <header>
    <div class="date">2026. 8. 26<span>수</span></div>
    <h1>한국경제신문 30분 만에 읽기</h1>
    <div class="meta">한경 코리아마켓 · 임현우의 모닝루틴 · <a href="...">원본 영상</a></div>
  </header>

  <section class="top3">
    <h2>오늘의 헤드라인</h2>
    <ol>
      <li><b>공정위, 쿠팡 조사 거부에 빈손 철수</b> — 사상 초유의 조사 무산.</li>
      <li><b>SK하이닉스 성과급 자사주 안건 부결</b> — 원점 재논의.</li>
      <li><b>엔비디아 실적 발표</b> — 마진 75% 사수가 관건.</li>
    </ol>
  </section>

  <section class="figures">
    <div class="fig"><b>43% → 16%</b><span>유암코 부실채권 점유율</span></div>
    <div class="fig"><b>400% + 1270만원</b><span>현대차 성과급 합의</span></div>
  </section>

  <section class="group">
    <h2>정책·규제</h2>
    <article class="item">
      <h3>공정위, 쿠팡 조사 거부에 사상 초유의 '빈손' 철수 <time>12:04</time></h3>
      <p>…</p>
      <p class="why"><b>왜 중요한가</b> 조사 거부 선례가 생기면 …</p>
      <p class="host"><b>진행자</b> 과징금보다 제도 정비가 먼저라는 시각.</p>
    </article>
  </section>

  <section class="briefs">
    <h2>단신</h2>
    <ul>
      <li>삼성 파운드리, 엔비디아 '그록3' 양산 돌입 <time>21:30</time></li>
    </ul>
  </section>

  <section class="tickers">
    <h2>언급된 기업</h2>
    <p>LG생활건강 · 아모레퍼시픽 · 쿠팡 · SK하이닉스 · 현대차 · 엔비디아 · SK이노베이션</p>
  </section>

  <section class="watch">
    <h2>오늘 확인할 것</h2>
    <ul><li><b>엔비디아 실적 발표</b> — 한국시간 오전, 마진율과 가이던스</li></ul>
  </section>

  <footer>방송 자막을 바탕으로 정리. 투자 판단의 근거가 아닙니다.</footer>
</div>
```

## CSS

```css
:root {
  --accent: #1d4ed8;
  --flag: #b45309;
  --ink: #16181d;
  --muted: #6b7280;
  --line: #e5e3de;
  --wash: #f7f6f3;
}
* { box-sizing: border-box; }
body { margin: 0; background: #fff; }
.brief {
  max-width: 760px; margin: 0 auto; padding: 30px 28px;
  font-family: Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  color: var(--ink); font-size: 14.5px; line-height: 1.62; word-break: keep-all;
}

/* 날짜가 주인공 */
header { border-bottom: 2px solid var(--ink); padding-bottom: 16px; margin-bottom: 22px; }
.date {
  font-size: 30px; font-weight: 800; letter-spacing: -.03em; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.date span {
  font-size: 13px; font-weight: 600; color: var(--muted);
  margin-left: 9px; letter-spacing: 0;
}
header h1 { font-size: 17px; font-weight: 600; margin: 9px 0 5px; }
.meta { font-size: 12.5px; color: var(--muted); }
.meta a { color: var(--muted); }

h2 {
  font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--accent);
  margin: 0 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--line);
}

/* 헤드라인 3 */
.top3 { background: var(--wash); padding: 15px 17px; margin-bottom: 20px; }
.top3 h2 { border: none; padding: 0; }
.top3 ol { margin: 0; padding-left: 19px; }
.top3 li { margin-bottom: 6px; }
.top3 li:last-child { margin-bottom: 0; }

/* 숫자 */
.figures {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 9px; margin-bottom: 26px;
}
.fig { border: 1px solid var(--line); border-radius: 4px; padding: 9px 11px; }
.fig b {
  display: block; font-size: 16px; letter-spacing: -.02em;
  font-variant-numeric: tabular-nums; margin-bottom: 2px;
}
.fig span { font-size: 11.5px; color: var(--muted); line-height: 1.35; display: block; }

/* 꼭지 카드 */
.group { margin-bottom: 26px; }
.item { padding: 12px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.item h3 {
  font-size: 15.5px; margin: 0 0 5px; line-height: 1.45;
  display: flex; gap: 9px; align-items: baseline; justify-content: space-between;
}
.item p { margin: 0 0 5px; }
.item p:last-child { margin-bottom: 0; }
time {
  flex: none; font-size: 11.5px; font-weight: 600; color: var(--accent);
  font-variant-numeric: tabular-nums; letter-spacing: 0;
}

.why, .host {
  font-size: 13.5px; background: var(--wash); padding: 7px 10px;
  border-left: 2px solid var(--flag); border-radius: 0 3px 3px 0;
}
.why b, .host b {
  color: var(--flag); font-size: 10.5px; font-weight: 700;
  letter-spacing: .07em; margin-right: 6px;
}
.host { border-left-color: var(--muted); }
.host b { color: var(--muted); }

.briefs ul { margin: 0; padding-left: 17px; }
.briefs li { margin-bottom: 4px; font-size: 14px; }
.tickers p { margin: 0; font-size: 13.5px; color: #3f4450; }
.tickers, .briefs { margin-bottom: 22px; }
.watch ul { margin: 0; padding-left: 17px; }
.watch li { margin-bottom: 6px; }

footer {
  margin-top: 30px; padding-top: 12px; border-top: 1px solid var(--line);
  font-size: 11.5px; color: var(--muted);
}

@page { size: A4; margin: 13mm; }
.item, .fig, .top3, .why, .host { break-inside: avoid; page-break-inside: avoid; }
h1, h2, h3 { break-after: avoid; page-break-after: avoid; }
@media print {
  .brief { max-width: none; padding: 0; font-size: 10pt; }
  .group { margin-bottom: 18px; }
}
```

## 조정

- 꼭지가 15개를 넘으면 `.group`을 2단(`column-count: 2; column-gap: 24px`)으로 배치할 수 있다. 단 `.item`에 `break-inside: avoid`가 걸려 있어야 카드가 단 사이에서 쪼개지지 않는다.
- 마켓 마감 브리핑처럼 지수·환율이 중심이면 `.figures`를 헤더 바로 아래 최상단으로 올린다.
- 종합 뉴스라 '언급 종목'이 무의미하면 그 섹션은 통째로 뺀다. 억지로 채우지 않는다.
