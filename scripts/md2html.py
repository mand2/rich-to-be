#!/usr/bin/env python3
"""notes/*.md -> 자기완결 HTML. 외부 요청 0, 파일 하나만 건네면 열린다.

스타일과 페이지 껍데기는 옆의 note-page.html 에 있다. 스타일만 고칠 거면 그 파일만 열면 된다.

    .venv/bin/python scripts/md2html.py notes/*.md
    .venv/bin/python scripts/md2html.py --selftest
"""
import argparse
import html
import re
import sys
from pathlib import Path

import markdown
from markdown.extensions.toc import slugify_unicode

VIDEO_ID = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})")
WORD = re.compile(r"[0-9A-Za-z가-힣]+")
TIMESTAMP = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")
CELL_BULLETS = re.compile(r"<td>-\s+(.*?)</td>", re.S)
H2 = re.compile(r"(<h2\b[^>]*>.*?</h2>)", re.S)
TAGS = re.compile(r"<[^>]+>")
# 노트가 일부러 쓰는 raw 태그는 <br> 하나뿐이다. 자막·영상 제목·채널명은 업로더가 정하는
# 문자열이라 그 밖의 실행 가능한 HTML 이 보이면 노트를 타고 들어온 것으로 본다.
EXECUTABLE = re.compile(r"<script|\ssrc=|\son\w+\s*=", re.I)

TEMPLATE = Path(__file__).with_name("note-page.html")


def render(title: str, body: str) -> str:
    """포맷 파일에 제목·본문을 끼운다. CSS 의 중괄호 때문에 str.format 은 못 쓰므로
    자리표시자는 HTML 주석이다 — 덕분에 note-page.html 자체도 브라우저에서 그냥 열린다."""
    tpl = TEMPLATE.read_text(encoding="utf-8")
    return tpl.replace("<!--TITLE-->", title).replace("<!--BODY-->", body)


def to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def link_timestamps(body: str, video_id: str) -> str:
    """렌더된 HTML의 [MM:SS] 를 유튜브 링크로. <code> 안이든 밖이든 같은 정규식으로 처리된다."""
    def sub(m):
        return '<a href="https://youtu.be/{}?t={}">[{}]</a>'.format(
            video_id, to_seconds(m.group(1)), m.group(1)
        )
    return TIMESTAMP.sub(sub, body)


def cell_bullets(body: str) -> str:
    """표 셀의 `- a<br>- b` 를 진짜 <ul> 로. 마크다운 표는 블록 리스트를 못 담아서
    노트가 하이픈+<br> 로 쓰이는데, 그대로 두면 항목이 두 줄로 넘칠 때 행잉 인덴트가 없다.
    `<br>` 뒤가 `- ` 가 아니면(단서 열의 `<br>Q. …`) 항목 안의 줄바꿈으로 남긴다."""
    def sub(m):
        items = re.split(r"<br\s*/?>-\s+", m.group(1))
        return "<td><ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul></td>"
    return CELL_BULLETS.sub(sub, body)


def fold(title: str, body: str, hid: str = "") -> str:
    """표지에 얹는 접힘 블록 하나. 헤딩에서 왔으면 그 id 를 details 가 물려받아 목차
    링크와 기존 앵커가 그대로 살아 있게 한다.

    ponytail: 펼쳐 두는 것은 `전체 흐름` 하나뿐이고 제목 문자열로 판정한다 — 마무리 절
    이름이 바뀌면 여기도 바꿔라. 닫힌 블록도 목차 링크로 열린다(브라우저 details 자동 펼침)."""
    hid = f' id="{hid}"' if hid else ""
    return (f'<details class="fold"{hid}{" open" if title == "전체 흐름" else ""}>'
            f"<summary>{title}</summary>{body}</details>")


def fold_heading(head: str, rest: str) -> str:
    """`<h2 id=…>제목</h2>` + 본문 → 접힘 블록."""
    hid = re.search(r'id="([^"]*)"', head)
    return fold(TAGS.sub("", head).strip(), rest, hid.group(1) if hid else "")


def paginate(cover: str, body: str) -> str:
    """렌더된 본문을 Part 단위 쪽으로 자른다. `Part …` h2 가 새 쪽을 열고, 그 뒤에 오는
    나머지 h2(전체 흐름·구간 간 연결)는 쪽이 되지 않고 목차 바로 아래 접힘 블록으로 올라온다.
    첫 h2 앞의 머리말(출처·영상 길이 등)도 `기본 정보` 접힘 블록이 된다.
    표지는 늘 펼쳐 두고(`.page`), 넘기는 것은 Part 쪽뿐이다(`.page.flip`). Part 헤딩의 id 는
    건드리지 않는다 — 쪽은 자기 id 를 따로 갖고, 기존 `#part-3-…` 딥링크는 CSS 의
    `.flip:has(:target)` 가 받아준다."""
    chunks = H2.split(body)
    pages, folds = [""], []
    for head, rest in zip(chunks[1::2], chunks[2::2]):
        if TAGS.sub("", head).lstrip().startswith("Part "):
            pages.append(head + rest)
        else:
            folds.append(fold_heading(head, rest))
    # ponytail: 머리말을 접는 것은 쪽이 갈릴 때뿐이다. 브리핑 모드 노트는 Part 가 없고
    # h2 도 없어서, 무조건 접으면 문서 전체가 `기본 정보` 라는 닫힌 블록 하나가 된다.
    if chunks[0].strip():
        if len(pages) > 1:
            folds.append(fold("기본 정보", chunks[0]))
        else:
            cover += chunks[0]
    pages[0] = cover + "".join(folds)

    # 쪽이 하나뿐이어도(브리핑 모드) 표지는 종이로 감싼다 — 안 그러면 책상 위에 글자만 놓인다
    if len(pages) == 1:
        return f'<section class="page" id="cover">{pages[0]}</section>'

    ids = ["cover"] + [f"page-{i}" for i in range(1, len(pages))]
    # 쪽을 숨기면 Ctrl-F 가 못 찾는다. `#all` 을 주소창에 치면 전부 펼쳐진다 (인쇄는 자동)
    out = ['<span id="all"></span>',
           f'<section class="page" id="cover">{pages[0]}</section>']
    last = len(pages) - 1
    for n, (pid, content) in enumerate(zip(ids[1:], pages[1:])):
        nav = ['<nav class="pagenav">']
        if n:
            nav.append(f'<a class="prev" href="#{ids[n]}" aria-label="이전 Part">\u2039</a>')
        nav.append(f'<span class="pageno">Part {n + 1} / {last}</span>')
        if n + 1 < last:
            nav.append(f'<a class="next" href="#{ids[n + 2]}" aria-label="다음 Part">\u203a</a>')
        nav.append("</nav>")
        cls = "page flip first" if n == 0 else "page flip"
        out.append(f'<section class="{cls}" id="{pid}">{content}{"".join(nav)}</section>')
    return "".join(out)


def spacing_drift(text: str) -> list[tuple[str, str]]:
    """같은 말이 띄어 쓴 꼴과 붙여 쓴 꼴로 둘 다 나오는 자리를 찾는다. 구간을 병렬로 쓰면
    구간 제목과 본문 셀의 표기가 갈리는데(`보스턴다이내믹스` ↔ `보스턴 다이내믹스`), 사람이
    읽어야 보이는 그 어긋남을 여기서 공짜로 잡는다. 용어집은 안 받는다 — 두 꼴이 다 있을
    때만 걸리므로 문서 하나로 판정된다.

    ponytail: 양쪽 2글자 이상이라는 조건 하나로 조사·어미 잡음을 걷어낸다. 한글 교착 탓에
    `비전 에서` 같은 오탐이 남고, 앞말이 1글자인 진짜 어긋남(`탑 티어`)은 놓친다 — 실측
    노트 1건에서 5건 중 3건이 진짜였다. 잡음이 신호를 넘기면 어미 목록을 두거나 형태소
    분석을 붙여라. 경고일 뿐이니 변환은 어차피 계속된다."""
    tokens = WORD.findall(text)
    seen = set(tokens)
    return sorted({(a, b) for a, b in zip(tokens, tokens[1:])
                   if a + b in seen and len(a) > 1 and len(b) > 1})


def convert(text: str) -> str:
    md = markdown.Markdown(extensions=["tables", "toc", "sane_lists", "attr_list"],
                           # 기본 slugify 는 한글을 통째로 버려서 `#_1`, `#_2` 만 남는다
                           extension_configs={"toc": {"toc_depth": "2-3",
                                                     "slugify": slugify_unicode}})
    body = md.convert(text)
    # 변환된 HTML 은 file:// 로 열린다. 스크립트가 섞이면 노트 내용이 밖으로 나갈 수 있으므로
    # 조용히 걸러내지 않고 멈춘다 — 코드 펜스 안의 태그는 md 가 이미 이스케이프해서 안 걸린다.
    hit = EXECUTABLE.search(body)
    if hit:
        sys.exit(f"실행 가능한 HTML 이 노트에 있다: {body[hit.start():hit.start() + 60]!r}")
    title = next((line.lstrip("# ").strip() for line in text.splitlines()
                  if line.startswith("# ")), "노트")

    vid = VIDEO_ID.search(text)
    if vid:
        body = link_timestamps(body, vid.group(1))
    body = cell_bullets(body)

    # md.toc 는 이미 <div class="toc"> 로 감싸 나온다. 벗기지 않으면 박스가 두 겹으로
    # 그려지고 `.toc > ul` 이 한 단계 어긋나 최상위 항목 굵게가 안 먹는다.
    inner = re.sub(r'\A\s*<div class="toc">|</div>\s*\Z', "", md.toc).strip()
    toc = (f'<details class="toc" id="toc"><summary>목차</summary>{inner}</details>'
           if inner.count("<li>") > 1 else "")
    h1 = f"<h1>{html.escape(title)}</h1>"
    # 본문 첫 h1 은 md 가 이미 뽑아줬으므로 중복 제거하고 그 자리에 목차를 끼운다
    body = re.sub(r"<h1[^>]*>.*?</h1>", "", body, count=1, flags=re.S)
    return render(html.escape(title), paginate(h1 + toc, body))


def selftest():
    src = (
        "# 테스트 노트\n\n"
        "- **출처**: https://www.youtube.com/watch?v=62b87kW6cC8\n\n"
        "## Part 1 | 구간 제목\n\n"
        "| 단서 | 내용 |\n| --- | --- |\n"
        "| `[01:05]` **오프닝**<br>Q. 왜? | - 첫 줄<br>- 둘째 줄<br>  이어지는 줄 |\n"
    )
    out = convert(src)
    assert to_seconds("01:05") == 65 and to_seconds("1:02:03") == 3723
    assert "<table>" in out, "표 유지 실패"
    assert "<li>첫 줄</li>" in out, "셀 불릿 → 리스트 변환 실패"
    # `- ` 로 시작하지 않는 <br> 는 항목 안 줄바꿈으로 남는다
    assert "<li>둘째 줄<br>  이어지는 줄</li>" in out, "항목 내 개행 소실"
    assert "Q. 왜?<" in out and "<td><ul>" in out, "단서 열은 리스트로 바뀌면 안 된다"
    assert 'href="https://youtu.be/62b87kW6cC8?t=65"' in out, "타임스탬프 링크 실패"
    assert out.count("<h1") == 1, "h1 중복"
    toc_out = convert(src + "\n## Part 2 | 구간 제목\n\n본문\n")
    assert toc_out.count('class="toc"') == 1, "목차 박스 중첩"
    assert "<summary>목차</summary>" in toc_out and "<div" not in toc_out, "목차는 details 하나로"
    assert 'id="cover"' in toc_out, "표지 쪽 없음"
    # 쪽 분할: Part 마다 한 쪽, 나머지 h2 는 마무리 한 쪽에 모인다
    paged = convert(src + "\n## Part 2 | 구간 제목\n\n본문\n"
                    "\n## 전체 흐름\n\n본문\n\n## 구간 간 연결\n\n본문\n")
    assert paged.count('<section class="page') == 3, "표지+Part2 = 3쪽이어야 한다"
    assert 'id="page-3"' not in paged, "마무리가 쪽으로 남았다"
    # 마무리는 목차 바로 아래 접힘 블록으로 올라온다 (앵커는 details 가 물려받는다)
    cover_html = paged.split('class="page flip')[0]
    assert cover_html.count('<details class="fold"') == 3, "표지 접힘 블록은 마무리 2 + 기본 정보"
    assert cover_html.index('id="toc"') < cover_html.index('class="fold"'), "목차보다 위로 갔다"
    assert '<details class="fold" id="전체-흐름" open>' in paged, "전체 흐름은 펼쳐 둔다"
    assert '<details class="fold" id="구간-간-연결"><summary>' in paged, "나머지 마무리는 닫아 둔다"
    assert '<summary>구간 간 연결</summary>' in paged, "마무리 제목 소실"
    # 머리말(출처·영상 길이 등)은 `기본 정보` 로 접힌다
    assert '<details class="fold"><summary>기본 정보</summary>' in paged, "기본 정보 블록 없음"
    assert paged.index("기본 정보") < paged.index("62b87kW6cC8"), "머리말이 기본 정보 밖에 남았다"
    assert '<span id="all">' in paged and 'href="#all"' not in paged, "#all 은 앵커만, 링크는 없다"
    # 넘기는 것은 Part 쪽뿐 — 표지와 마무리는 flip 이 아니고 넘김줄도 없다
    assert paged.count('class="page flip') == 2, "Part 2쪽만 넘김 대상이어야 한다"
    assert '<section class="page" id="cover"' in paged, "표지가 넘김 대상이 됐다"

    assert paged.count('class="pagenav"') == 2, "넘김줄은 Part 쪽에만"
    assert paged.count('class="page flip first"') == 1, "기본으로 펼칠 첫 Part 표시 없음"
    assert 'class="prev"' not in paged.split('id="page-1"')[0], "표지에 이전 링크가 붙었다"
    assert 'class="next"' not in paged.split('id="page-2"')[1], "마지막 Part 에 다음 링크가 붙었다"
    one = convert("# 노\n\n본문\n")
    assert one.count('<section class="page"') == 1 and 'page flip' not in one, "h2 없는 문서는 표지 한 쪽"
    # 브리핑 모드: Part 가 없으면 머리말을 접지 않는다 (접으면 본문 전체가 닫힌다)
    brief = convert("# 노\n\n- **출처**: x\n\n### 요약\n\n- 한 줄\n")
    assert "기본 정보" not in brief, "Part 없는 문서를 접었다"
    assert "한 줄" in brief and '<section class="page" id="cover">' in brief
    # 소주제는 h4. 앵커는 얻되 목차에는 안 들어간다 (toc_depth 2-3)
    sub = convert(src + "\n#### 소주제\n\n본문\n\n## Part 2 | 구간 제목\n\n본문\n")
    assert '<h4 id="소주제">' in sub, "소주제 앵커 소실"
    assert 'href="#소주제"' not in sub, "소주제가 목차에 들어갔다"
    assert 'id="전체-흐름"' in convert("# 노\n\n## 전체 흐름\n\n본문\n"), "앵커에서 한글 소실"
    assert "<title>테스트 노트</title>" in out
    # 자기완결: 로드되는 외부 리소스가 없어야 한다 (본문 하이퍼링크는 무관)
    assert "<script" not in out and "<link" not in out and "src=" not in out
    # 출처 URL 없으면 링크 없이 텍스트로 남는다
    assert "youtu.be" not in convert("# 노\n\n`[01:05]` 본문\n")
    assert TEMPLATE.exists(), f"포맷 파일이 없다: {TEMPLATE}"
    # 주입된 raw HTML 은 변환을 멈춘다. <br> 와 코드 펜스 안의 태그는 통과한다
    for bad in ("<script>x</script>", "<img src=x onerror=y>", "<b onclick=x>y</b>"):
        try:
            convert(f"# 노\n\n{bad}\n")
        except SystemExit:
            pass
        else:
            raise AssertionError(f"거부됐어야 한다: {bad!r}")
    assert "<br>" in convert("# 노\n\n| a | b |\n| --- | --- |\n| x | y<br>z |\n")
    assert "&lt;script" in convert("# 노\n\n`<script>` 를 설명하는 문장\n")
    # 띄어쓰기 갈림: 두 꼴이 다 있을 때만 잡고, 조사가 붙은 것은 잡지 않는다
    assert spacing_drift("보스턴다이내믹스 로봇\n보스턴 다이내믹스 협력") == [("보스턴", "다이내믹스")]
    assert spacing_drift("보스턴 다이내믹스 로봇\n보스턴 다이내믹스 협력") == [], "한 꼴만 쓰면 잡지 마라"
    assert spacing_drift("축적을 한다\n데이터 축적을 한다") == [], "조사는 붙여 쓴 꼴이 아니다"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("-o", "--outdir", type=Path, help="기본: md 파일과 같은 폴더")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.files:
        ap.error("변환할 md 파일을 지정해라")

    for src in a.files:
        text = src.read_text(encoding="utf-8")
        dst = (a.outdir or src.parent) / (src.stem + ".html")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(convert(text), encoding="utf-8")
        print(f"{src} -> {dst}", file=sys.stderr)
        for word_a, word_b in spacing_drift(text):
            print(f"  띄어쓰기 갈림: `{word_a} {word_b}` ↔ `{word_a + word_b}`", file=sys.stderr)


if __name__ == "__main__":
    main()
