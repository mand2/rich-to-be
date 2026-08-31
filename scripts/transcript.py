#!/usr/bin/env python3
"""YouTube 자막을 받아 타임스탬프가 찍힌 전문으로 만든다.

    .venv/bin/python scripts/transcript.py <URL|VIDEO_ID> [-o DIR]

출력 (기본 .work/<video_id>/):
    transcript.txt   전문 — 두 스킬이 통째로 읽는다
    meta.json        제목·저자·업로드일(KST)·길이·자막종류
"""

import argparse, json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 자동자막 표시지연 보정의 기본값(초). 영상 1개(aircAruvnKk)에서 수동 자막을
# 기준선으로 잰 값 — 중앙값 +2.24s, 92%가 같은 방향(늦음)이라 계통 오차로 본다.
# 보정 후 잔차 중앙값 1.01s.
#
# ponytail: 영상별 자동 측정은 불가능하다. 측정하려면 같은 언어의 수동 자막이
# 기준선으로 필요한데, 그게 있으면 애초에 자동 자막을 쓰지 않는다. 그래서
# 사람이 --probe 로 초반 구간을 받아 영상과 대조한 뒤 --lag 로 넘기는 구조로 둔다.
AUTO_CAPTION_LAG = 2.2
PROBE_SECONDS = 120      # --probe 로 뽑아 볼 초반 구간


def video_id(s):
    """URL 또는 ID 문자열에서 11자 video id를 뽑는다."""
    if re.fullmatch(r"[\w-]{11}", s):
        return s
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([\w-]{11})", s)
    if not m:
        sys.exit(f"video id를 찾을 수 없음: {s}")
    return m.group(1)


def hhmmss(sec):
    s = max(0, int(sec))
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


def pick_track(tracks, langs):
    """사람이 쓴 자막을 자동생성보다 우선. 언어는 주어진 순서대로."""
    for generated in (False, True):
        for lang in langs:
            for t in tracks:
                if t.language_code == lang and t.is_generated == generated:
                    return t
    for generated in (False, True):          # 지정 언어가 없으면 아무거나
        for t in tracks:
            if t.is_generated == generated:
                return t
    sys.exit("자막 없음 — 이 영상은 처리할 수 없다")


def to_lines(snippets, lag=0.0):
    """(초, 텍스트) 목록으로. lag만큼 타임스탬프를 앞당긴다."""
    out = []
    for x in snippets:
        text = " ".join(x.text.split())
        if text:
            out.append((max(0.0, x.start - lag), text))
    return out


def oembed(vid):
    url = (f"https://www.youtube.com/oembed?format=json"
           f"&url=https://www.youtube.com/watch?v={vid}")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            d = json.load(r)
        return d.get("title", vid), d.get("author_name", "")
    except Exception:
        return vid, ""          # 제목을 못 얻어도 자막 처리는 계속한다


RE_UPLOAD = re.compile(r'"uploadDate":"([^"]+)"')
KST = timezone(timedelta(hours=9))


def to_kst_date(iso):
    """업로드 시각(오프셋 포함)을 KST 날짜로. 시각은 버린다.

    ponytail: 채널이 대부분 한국이라 KST 로 고정한다. 미국 채널의 날짜가
    하루 밀려 보이면 그때 기준 시간대를 인자로 뺄 것."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KST).strftime("%Y-%m-%d")


def upload_date(vid):
    """watch 페이지에서 업로드일을 긁는다. oembed 는 날짜를 안 준다."""
    req = urllib.request.Request(
        f"https://www.youtube.com/watch?v={vid}",
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ko"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            m = RE_UPLOAD.search(r.read().decode("utf-8", "replace"))
        return to_kst_date(m.group(1)) if m else ""
    except Exception:
        return ""               # 날짜를 못 얻어도 자막 처리는 계속한다


def slug(title):
    s = re.sub(r"[^\w가-힣ㄱ-ㅎㅏ-ㅣ\s-]", "", title).strip()
    return re.sub(r"\s+", "-", s)[:60] or "untitled"


def probe(vid, track, snippets, lag):
    """초반 구간을 보정 전/후로 나란히 출력한다.

    영상별 지연을 자막만으로 자동 측정할 방법은 없다 — 기준선이 되는 같은 언어의
    수동 자막이 필요한데, 그게 있으면 자동 자막을 쓸 이유가 없기 때문이다.
    그래서 사람이 영상 초반을 직접 듣고 대조하도록 재료만 뽑아 준다.
    """
    if lag is None:
        lag = AUTO_CAPTION_LAG if track.is_generated else 0.0
    print(f"# {vid} | {track.language_code} | "
          f"{'자동생성' if track.is_generated else '수동'} 자막")
    if not track.is_generated:
        print("# 수동 자막이라 지연 보정이 필요 없다. --lag 를 건드리지 마라.\n")
    else:
        print(f"# 아래 '보정후' 시각에 그 말이 실제로 나오는지 영상에서 확인하라.\n"
              f"#   말이 아직 안 나왔으면 → --lag 를 {lag}보다 줄여라\n"
              f"#   말이 이미 지나갔으면 → --lag 를 {lag}보다 늘려라\n")
    print(f"{'원본':>9}  {'보정후':>9}   내용")
    for x in snippets:
        if x.start > PROBE_SECONDS:
            break
        text = " ".join(x.text.split())
        if text:
            print(f"{hhmmss(x.start):>9}  {hhmmss(max(0.0, x.start - lag)):>9}   {text}")
    print(f"\n# 현재 적용값: --lag {lag}"
          f"{'  (기본값)' if lag == AUTO_CAPTION_LAG else ''}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url", nargs="?", help="YouTube URL 또는 video id")
    p.add_argument("-o", "--outdir", default=None)
    p.add_argument("--lang", default="ko,en", help="선호 언어 순서 (기본 ko,en)")
    p.add_argument("--lag", type=float, default=None,
                   help=f"자동자막 표시지연 보정(초). 미지정 시 자동자막이면 {AUTO_CAPTION_LAG}")
    p.add_argument("--probe", action="store_true",
                   help=f"초반 {PROBE_SECONDS}초만 출력하고 끝낸다. 영상과 대조해 --lag 를 정하는 용도")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        return selftest()
    if not a.url:
        p.error("url이 필요하다 (또는 --selftest)")

    from youtube_transcript_api import YouTubeTranscriptApi

    vid = video_id(a.url)
    api = YouTubeTranscriptApi()
    track = pick_track(list(api.list(vid)), a.lang.split(","))
    snippets = track.fetch().snippets

    if a.probe:
        return probe(vid, track, snippets, a.lag)

    lag = a.lag if a.lag is not None else (AUTO_CAPTION_LAG if track.is_generated else 0.0)
    lines = to_lines(snippets, lag)
    if not lines:
        sys.exit("자막이 비어 있다")

    title, author = oembed(vid)
    out = Path(a.outdir or f".work/{vid}")
    out.mkdir(parents=True, exist_ok=True)

    body = "\n".join(f"[{hhmmss(t)}] {x}" for t, x in lines)
    (out / "transcript.txt").write_text(body + "\n", encoding="utf-8")

    meta = {
        "video_id": vid, "title": title, "author": author,
        "upload_date": upload_date(vid),
        "url": f"https://www.youtube.com/watch?v={vid}",
        "duration": hhmmss(lines[-1][0]),
        "language": track.language_code,
        "auto_generated": track.is_generated,
        "lag_correction_sec": lag,
        "lag_source": ("사용자 지정" if a.lag is not None
                       else "기본값(미측정)" if track.is_generated else "불필요(수동 자막)"),
        "slug": slug(title),
        "outdir": str(out),
    }
    if track.is_generated and a.lag is None:
        print(f"※ 자동자막이라 기본 보정 {AUTO_CAPTION_LAG}초를 적용했다. 영상별로 다를 수 있다.\n"
              f"  초반을 영상과 대조하려면:  --probe\n"
              f"  값을 바꿔 다시 뽑으려면:   --lag <초>\n", file=sys.stderr)
    (out / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False, indent=2))


def selftest():
    assert to_kst_date("2026-08-21T23:00:02-07:00") == "2026-08-22"   # PT 밤 → KST 다음 날
    assert to_kst_date("2026-08-26T00:30:00Z") == "2026-08-26"
    assert RE_UPLOAD.search('x"uploadDate":"2026-01-02T03:04:05Z",y').group(1).startswith("2026-01-02")
    assert video_id("https://www.youtube.com/watch?v=aircAruvnKk") == "aircAruvnKk"
    assert video_id("https://youtu.be/aircAruvnKk?t=30") == "aircAruvnKk"
    assert video_id("aircAruvnKk") == "aircAruvnKk"
    assert hhmmss(0) == "00:00:00" and hhmmss(3661) == "01:01:01"
    assert hhmmss(-5) == "00:00:00"          # 지연 보정이 0 밑으로 내려가도 안전

    # 지연 보정
    class S:
        def __init__(s, start, text): s.start, s.text = start, text
    assert to_lines([S(5.0, "hi")], AUTO_CAPTION_LAG)[0][0] == 5.0 - AUTO_CAPTION_LAG
    assert to_lines([S(5.0, "hi")])[0][0] == 5.0       # 기본값은 보정 없음
    assert to_lines([S(1.0, "hi")], 9.0)[0][0] == 0.0  # 0 밑으로 안 내려간다
    assert to_lines([S(1.0, "  ")]) == []              # 빈 줄은 버린다

    # 자막 선택: 수동 > 자동, 언어는 준 순서대로
    class T:
        def __init__(s, lc, gen): s.language_code, s.is_generated = lc, gen
    ko_auto, en_man, ko_man = T("ko", True), T("en", False), T("ko", False)
    assert pick_track([ko_auto, en_man], ["ko", "en"]) is en_man    # 수동이 먼저
    assert pick_track([ko_auto, ko_man], ["ko"]) is ko_man
    assert pick_track([ko_auto], ["ko", "en"]) is ko_auto
    assert pick_track([ko_auto], ["ja"]) is ko_auto                 # 지정 언어가 없으면 아무거나

    assert slug("But what is a neural network? | Deep learning") \
        == "But-what-is-a-neural-network-Deep-learning"
    print("selftest OK")


if __name__ == "__main__":
    main()
