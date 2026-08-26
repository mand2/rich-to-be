# 레이아웃 & CSS

스터디 노트 HTML을 쓸 때 이 문서의 규칙과 뼈대를 따른다.

## 디자인 원칙

**포인트 컬러 하나만 쓴다.** 영상 주제에 맞는 색 하나를 골라 `--accent`에 넣고, 섹션 번호·강조 박스 테두리·라벨에만 사용한다. 본문은 흑백을 유지한다. 색이 많아지면 노트가 아니라 인포그래픽이 되고, 읽는 문서로서의 밀도가 떨어진다.

주제별 예시: 금융·경제 `#1d4ed8` / 기술·개발 `#0f766e` / 건강·의학 `#be123c` / 역사·인문 `#92400e` / 환경 `#15803d`

**두 층위의 글자.** 정의·설명은 본문 크기, 비유나 보조 설명은 한 단계 작게 배경을 깔아 구분한다. 이 대비가 용어 사전을 훑어보기 쉽게 만든다.

**여백이 구조를 만든다.** 섹션 간 여백은 넉넉하게, 항목 내부는 촘촘하게. 밀도 차이만으로도 어디가 덩어리인지 보인다.

## 인쇄 규칙 (가장 중요)

A4 인쇄 시 카드가 페이지 경계에서 잘리면 문서가 망가진다. 아래 세 가지를 반드시 넣는다.

```css
.card, .term, .step, .insight { break-inside: avoid; page-break-inside: avoid; }
h2, h3 { break-after: avoid; page-break-after: avoid; }
@page { size: A4; margin: 14mm; }
```

`break-after: avoid`가 없으면 섹션 제목만 페이지 하단에 남고 내용이 다음 장으로 넘어간다.

화면용 그림자·호버 효과는 `@media print`에서 제거한다. 링크는 인쇄 시 URL이 튀어나오지 않게 `text-decoration` 정도만 남긴다.

## 뼈대

```html
<div class="note">

  <header>
    <div class="label">STUDY NOTE · 채권과 금리</div>
    <h1>미국 부채 40조 달러, 파산 걱정까지는 아닌 이유</h1>
    <div class="meta">이효석아카데미 · 2026.8.19 · 15분 36초 · <a href="...">원본 영상</a></div>
  </header>

  <div class="conclusion">
    <span class="tag">한 줄 결론</span>
    최근 미국 국채 금리 급등은 …
  </div>

  <section>
    <h2><span class="num">01</span> 먼저, 두 세상 이해하기</h2>
    <p class="sub">영상의 출발점 — 주식과 채권은 세상을 반대로 보는 사람들이 산다 <time>0:26–3:24</time></p>
    <div class="split">
      <div class="card"><h4>주식쟁이의 빨간 세상</h4><p>…</p></div>
      <div class="card"><h4>채권쟁이의 파란 세상</h4><p>…</p></div>
    </div>
    <p>…</p>
  </section>

  <section>
    <h2><span class="num">02</span> 용어 사전</h2>
    <p class="sub">영상에 등장한 개념을 쉬운 말로</p>
    <div class="term">
      <h4>채권 <em>bond</em></h4>
      <p>"돈 갚을게요"라고 써 준 종이. 정부가 발행하면 국채, 회사가 발행하면 회사채.</p>
      <p class="aside"><b>비유</b> — 1억을 빌리고 차용증을 써 주는 것. 그 차용증이 채권이다.</p>
    </div>
  </section>

  <section>
    <h2><span class="num">03</span> 영상의 논리 흐름</h2>
    <p class="sub">결론까지 가는 5단계</p>
    <div class="step">
      <div class="marker">1</div>
      <div class="body">
        <h4>이상 현상 발견 <time>9:47–10:14</time></h4>
        <p>…</p>
        <blockquote>"이건 뭔가 펀더멘탈이 안 먹히는 시장이었다라는 거지."</blockquote>
      </div>
    </div>
  </section>

  <section>
    <h2><span class="num">04</span> 인사이트</h2>
    <div class="insight"><h4>① 금리 상승에도 '종류'가 있다</h4><p>…</p></div>
  </section>

  <section>
    <h2><span class="num">05</span> 앞으로 지켜볼 것</h2>
    <ul class="watch"><li><b>8/28 엔비디아 실적</b> — …</li></ul>
  </section>

  <footer>유튜브 자동 생성 자막 전문을 바탕으로 정리. 발언자의 견해이며 …</footer>
</div>
```

## CSS

```css
:root {
  --accent: #1d4ed8;          /* 주제에 맞게 교체 */
  --ink: #16181d;
  --muted: #6b7280;
  --line: #e5e3de;
  --wash: #f7f6f3;
}
* { box-sizing: border-box; }
body { margin: 0; background: #fff; }
.note {
  max-width: 720px; margin: 0 auto; padding: 32px 28px;
  font-family: Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  color: var(--ink); font-size: 15px; line-height: 1.72;
  word-break: keep-all;      /* 한국어 줄바꿈이 단어 중간에서 끊기지 않게 */
}

header { border-bottom: 2px solid var(--ink); padding-bottom: 18px; margin-bottom: 26px; }
.label { font-size: 11px; letter-spacing: .14em; color: var(--accent); font-weight: 700; }
h1 { font-size: 27px; line-height: 1.3; margin: 10px 0 12px; letter-spacing: -.02em; }
.meta { font-size: 12.5px; color: var(--muted); }
.meta a { color: var(--muted); }

.conclusion {
  border-left: 3px solid var(--accent); background: var(--wash);
  padding: 16px 18px; margin-bottom: 34px; font-size: 15.5px;
}
.tag {
  display: block; font-size: 11px; font-weight: 700; letter-spacing: .1em;
  color: var(--accent); margin-bottom: 6px;
}

section { margin-bottom: 34px; }
h2 { font-size: 19px; margin: 0 0 4px; letter-spacing: -.01em; }
.num {
  display: inline-block; min-width: 26px; height: 22px; margin-right: 8px;
  background: var(--accent); color: #fff; font-size: 12px; font-weight: 700;
  text-align: center; line-height: 22px; border-radius: 3px;
}
.sub { font-size: 13px; color: var(--muted); margin: 0 0 16px; }
time { font-variant-numeric: tabular-nums; font-size: 12px; color: var(--accent); font-weight: 600; }

.split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.card { border: 1px solid var(--line); border-radius: 5px; padding: 14px 16px; }
.card h4 { margin: 0 0 8px; font-size: 14.5px; }
.card p { margin: 0; font-size: 14px; }

.term { border-top: 1px solid var(--line); padding: 13px 0; }
.term h4 { margin: 0 0 5px; font-size: 15px; }
.term h4 em { font-style: normal; font-weight: 400; font-size: 12.5px; color: var(--muted); }
.term p { margin: 0; }
.aside {
  margin-top: 7px !important; background: var(--wash); padding: 8px 11px;
  border-radius: 4px; font-size: 13.5px; color: #3f4450;
}
.aside b { color: var(--accent); font-weight: 700; }

.step { display: flex; gap: 14px; padding: 15px 0; border-top: 1px solid var(--line); }
.marker {
  flex: 0 0 26px; height: 26px; border-radius: 50%; background: var(--ink); color: #fff;
  font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.step .body { flex: 1; }
.step h4 { margin: 0 0 6px; font-size: 15px; display: flex; gap: 8px; align-items: baseline; }
.step p { margin: 0; }
blockquote {
  margin: 9px 0 0; padding-left: 12px; border-left: 2px solid var(--line);
  color: #3f4450; font-size: 14px;
}

.insight { padding: 12px 0; border-top: 1px solid var(--line); }
.insight h4 { margin: 0 0 4px; font-size: 15px; }
.insight p { margin: 0; font-size: 14.5px; }

.watch { margin: 0; padding-left: 18px; }
.watch li { margin-bottom: 9px; }

footer {
  margin-top: 38px; padding-top: 14px; border-top: 1px solid var(--line);
  font-size: 12px; color: var(--muted);
}

@page { size: A4; margin: 14mm; }
.card, .term, .step, .insight, .conclusion, blockquote { break-inside: avoid; page-break-inside: avoid; }
h1, h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
@media print {
  .note { max-width: none; padding: 0; font-size: 10.5pt; }
  section { margin-bottom: 22px; }
}
```

## 조정 가능한 것

- `.split`은 대비 구도가 있을 때만 쓴다. 없으면 일반 문단으로.
- 항목이 많은 용어 사전은 2단(`grid-template-columns: 1fr 1fr`)으로 배치해도 좋다. 단 인쇄 시 단이 어긋나므로 항목이 10개 이상일 때만.
- 영상에 숫자·비교가 많으면 표를 추가한다. 테두리는 `--line`, 헤더 행만 `--wash` 배경.
