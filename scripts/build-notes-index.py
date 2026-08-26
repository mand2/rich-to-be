#!/usr/bin/env python3
"""notes/ 안의 노트 HTML 을 훑어 notes/index.html 의 목록 블록을 채운다.

GitHub Pages 워크플로(.github/workflows/pages.yml)가 빌드 때 돌린다.
손으로 돌려도 된다 — 결과를 커밋하면 로컬에서 열어도 목록이 보인다.

    scripts/build-notes-index.py
    scripts/build-notes-index.py --selftest
"""
import html
import json
import re
import sys
from pathlib import Path

NOTES = Path(__file__).resolve().parent.parent / "notes"
START = "<!-- notes-index:start"
END = "<!-- notes-index:end -->"
DESC_MAX = 140

# ponytail: 두 스킬의 HTML 템플릿 class 이름에 기댄다 (conclusion / top3 / meta).
# 템플릿이 바뀌면 여기도 바꾼다. 못 찾으면 그냥 desc 를 비우고 넘어가므로 빌드는 안 깨진다.
RE_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
RE_CONCLUSION = re.compile(r'<div class="conclusion">(.*?)</div>', re.S)
RE_TOP3 = re.compile(r'<section class="top3">(.*?)</section>', re.S)
RE_BOLD = re.compile(r"<b>(.*?)</b>", re.S)
RE_TAG_SPAN = re.compile(r'<span class="tag">.*?</span>', re.S)
RE_META = re.compile(r'<div class="meta">(.*?)</div>', re.S)


RE_BLOCK = re.compile(r"</?(?:p|div|br|li|ul|ol|h[1-6]|section|blockquote|tr|td|th)\b[^>]*>", re.I)


def text(fragment):
    """태그를 걷어내고 공백을 접는다. 블록 태그만 공백으로 바꾼다 — <b>구조</b>를 가 '구조 를' 이 되면 안 된다."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", RE_BLOCK.sub(" ", fragment)))).strip()


def clip(s, limit=DESC_MAX):
    if len(s) <= limit:
        return s
    return s[:limit].rsplit(" ", 1)[0].rstrip(" ,.·—-") + "…"


def describe(src):
    """스터디 노트는 '한 줄 결론', 브리핑은 헤드라인 3줄, 없으면 출처 줄."""
    m = RE_CONCLUSION.search(src)
    if m:
        body = RE_TAG_SPAN.sub("", m.group(1))
        first = re.search(r"<p>(.*?)</p>", body, re.S)
        return clip(text(first.group(1) if first else body))

    m = RE_TOP3.search(src)
    if m:
        heads = [text(b) for b in RE_BOLD.findall(m.group(1))]
        if heads:
            return clip(" · ".join(heads))

    m = RE_META.search(src)
    return clip(text(m.group(1))) if m else ""


def entry(path):
    src = path.read_text(encoding="utf-8")
    m = RE_H1.search(src)
    out = {"file": path.relative_to(NOTES).as_posix()}
    if m:
        out["title"] = text(m.group(1))
    desc = describe(src)
    if desc:
        out["desc"] = desc
    return out


def collect():
    return [entry(p) for p in sorted(NOTES.glob("*/*.html")) if p.name != "index.html"]


def write_index(entries):
    index = NOTES / "index.html"
    src = index.read_text(encoding="utf-8")
    a, b = src.index(START), src.index(END)
    block = '%s — scripts/build-notes-index.py 가 채운다. 손으로 고치지 마세요. -->\n<script type="application/json" id="note-files">\n%s\n</script>\n' % (
        START,
        json.dumps(entries, ensure_ascii=False, indent=1),
    )
    index.write_text(src[:a] + block + src[b:], encoding="utf-8")
    return index


def selftest():
    assert text("<b>가</b> 나  <a href='#'>다</a>") == "가 나 다"
    assert text("<b>구조</b>를 짰다") == "구조를 짰다"
    assert text("<p>가</p><p>나</p>") == "가 나"
    assert clip("abcdef", 4) == "abcde…" or clip("abcdef", 4).endswith("…")
    assert describe('<div class="conclusion"><span class="tag">한 줄 결론</span>수급 때문이다.</div>') == "수급 때문이다."
    assert describe('<section class="top3"><ol><li><b>가</b> — x</li><li><b>나</b></li></ol></section>') == "가 · 나"
    assert describe('<div class="meta">채널 · 15분</div>') == "채널 · 15분"
    assert describe("<p>아무것도 없음</p>") == ""

    got = collect()
    assert got, "notes/*/*.html 을 하나도 못 찾았다"
    assert all(e["file"].count("/") == 1 for e in got), got
    assert all(e.get("title") for e in got), [e for e in got if not e.get("title")]
    assert all(e.get("desc") for e in got), [e for e in got if not e.get("desc")]
    print("OK — %d notes" % len(got))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        entries = collect()
        print("%s ← %d notes" % (write_index(entries), len(entries)))
