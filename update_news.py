#!/usr/bin/env python3
"""
Claude 없이, GitHub Actions 크론으로 주기 실행되는 뉴스 수집 스크립트.

- Google 뉴스 RSS만 사용 (API 키 불필요, 완전 무료).
- 엔진 소식 / 이외 소식 / 공모전(국내·해외) 네 묶음을 각각 검색어 여러 개로 모음.
- 최근 7일 이내 기사만 남기고, data.json을 다시 씀 (index.html이 이 파일을 읽음).

한계:
- 기사별 "왜 봐야 하는지" 한 줄은 AI가 쓰는 게 아니라, 묶음별로 고정된 문구를 붙임.
  (개인화된 한 줄이 꼭 필요하면 README의 "Claude API로 업그레이드하기" 참고)
- 공모전 마감일은 기사 제목에서 날짜 패턴을 찾아 best-effort로만 추출함.
  못 찾으면 "확인 필요"로 표시되니, 지원 전 원문에서 꼭 확인할 것.
- Google 뉴스 링크는 news.google.com을 한 번 거쳐 원문으로 리다이렉트됨 (정상 동작).
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

MAX_AGE_DAYS = 7
MAX_PER_FEED = 6
TIMEOUT = 15

FEEDS = {
    "engine": {
        "reason": "생성 엔진 자체의 업데이트 소식이에요.",
        "queries": [
            "Kling Seedance 나노바나나 업데이트",
            "Veo Runway Sora Midjourney 업데이트",
            "Gemini image model update",
            "Stable Diffusion Flux Ideogram new model",
        ],
    },
    "other": {
        "reason": "생성형 AI 업계 전반의 소식이에요.",
        "queries": [
            "생성형 AI 산업 뉴스",
            "generative AI industry news",
            "AI 저작권 규제 뉴스",
            "AI 영상 광고 제작 사례",
        ],
    },
    "kr": {
        "reason": "지금 지원할 수 있는 국내 AI 공모전이에요.",
        "contest": True,
        "queries": ["AI 공모전 접수", "AI 영상 공모전 모집"],
    },
    "intl": {
        "reason": "지금 지원할 수 있는 해외 AI 공모전이에요.",
        "contest": True,
        "queries": ["AI film festival submissions open", "AI video contest call for entries"],
    },
}

SKIP_HOSTS = {"wikipedia.org", "youtube.com", "reddit.com", "namu.wiki", "x.com", "twitter.com", "facebook.com", "instagram.com"}

DEADLINE_PATTERNS = [
    re.compile(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})"),
    re.compile(r"(\d{1,2})월\s*(\d{1,2})일"),
]


def fetch_rss(query, lang="ko"):
    hl, gl, ceid = ("ko", "KR", "KR:ko") if lang == "ko" else ("en-US", "US", "US:en")
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": hl, "gl": gl, "ceid": ceid}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; daily-ai-bot/1.0)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def parse_items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        desc = (item.findtext("description") or "")
        source_el = item.find("source")
        source_name = (source_el.text or "").strip() if source_el is not None else ""
        source_url = source_el.get("url") if source_el is not None else None
        ts = None
        if pub:
            try:
                ts = parsedate_to_datetime(pub)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                ts = None
        host = ""
        try:
            host = urllib.parse.urlparse(source_url or link).hostname or ""
            host = host[4:] if host.startswith("www.") else host
        except Exception:
            pass
        out.append({
            "title": title, "url": link, "host": host or source_name,
            "ts": ts, "desc": desc,
        })
    return out


def extract_deadline(text, now):
    for pat in DEADLINE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        groups = m.groups()
        try:
            if len(groups) == 3:
                y, mo, d = (int(g) for g in groups)
            else:
                mo, d = (int(g) for g in groups)
                y = now.year
                cand = datetime(y, mo, d, tzinfo=timezone.utc)
                if cand < now - timedelta(days=3):
                    y += 1
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except Exception:
            continue
    return None


def collect(feed_id, cfg, now):
    lang = "ko" if feed_id in ("engine", "other", "kr") else "en"
    seen, items = set(), []
    for q in cfg["queries"]:
        try:
            raw = fetch_rss(q, lang=lang)
            parsed = parse_items(raw)
        except Exception as e:
            print(f"[warn] {feed_id!r} query {q!r} failed: {e}", file=sys.stderr)
            continue
        for it in parsed:
            if not it["url"] or it["url"] in seen:
                continue
            if it["host"] and any(it["host"] == h or it["host"].endswith("." + h) for h in SKIP_HOSTS):
                continue
            if it["ts"] and (now - it["ts"]) > timedelta(days=MAX_AGE_DAYS):
                continue
            if it["ts"] and it["ts"] > now + timedelta(days=1):
                continue
            seen.add(it["url"])
            items.append(it)

    items.sort(key=lambda x: x["ts"] or now, reverse=True)
    items = items[:MAX_PER_FEED]

    out = []
    for it in items:
        date_iso = (it["ts"] or now).isoformat()
        if cfg.get("contest"):
            deadline = extract_deadline(it["title"] + " " + it["desc"], now)
            out.append({
                "feed": feed_id, "name": it["title"], "organizer": "", "field": "",
                "deadline": deadline, "reason": cfg["reason"], "host": it["host"], "url": it["url"],
            })
        else:
            out.append({
                "feed": feed_id, "title": it["title"], "reason": cfg["reason"],
                "host": it["host"], "url": it["url"], "date": date_iso,
            })
    return out


def main():
    now = datetime.now(timezone.utc)
    all_items = []
    for feed_id, cfg in FEEDS.items():
        all_items.extend(collect(feed_id, cfg, now))

    data = {"generatedAt": now.isoformat(), "items": all_items}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(all_items)} items to data.json")


if __name__ == "__main__":
    main()
