"""
fetch_news.py
-----------------------------------------------------------
Oyun haberi RSS kaynaklarından başlık + kısa özet + görsel + kaynak
linkini çeker ve sitenin okuduğu articles.json dosyasını günceller.

ÖNEMLİ (telif hakkı): Bu script haberlerin TAMAMINI kopyalamaz.
Sadece başlık, kısa bir özet (RSS'in kendi özeti), görsel ve kaynağa
giden link alınır.

Kurulum:
    pip install feedparser

Çalıştırma:
    python fetch_news.py
"""

import json
import re
import feedparser
from datetime import datetime, timezone

FEEDS = [
    {"url": "https://www.oyungunlugu.com/rss.xml", "source": "Oyun Günlüğü", "category": "Genel"},
    {"url": "https://shiftdelete.net/oyun/feed", "source": "ShiftDelete.Net", "category": "Genel"},
    {"url": "https://oyungezer.com.tr/rss", "source": "Oyungezer", "category": "Genel"},
]
# NOT: Webtekno, Donanımhaber ve Merlin'in Kazanı'nın herkese açık bir RSS
# beslemesi bulunamadı (siteler bunu kapatmış olabilir). İleride doğru
# adresleri bulunursa yukarıdaki listeye aynı formatta eklenebilir.

MAX_PER_FEED = 6
OUTPUT_FILE = "articles.json"


def clean_summary(raw_html, limit=160):
    text = re.sub("<[^<]+?>", "", raw_html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def extract_image(entry):
    media_content = entry.get("media_content")
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url

    media_thumb = entry.get("media_thumbnail")
    if media_thumb:
        url = media_thumb[0].get("url")
        if url:
            return url

    if entry.get("enclosures"):
        for enc in entry["enclosures"]:
            if enc.get("type", "").startswith("image") or enc.get("href", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                return enc.get("href")

    raw_html = ""
    if entry.get("content"):
        raw_html = entry["content"][0].get("value", "")
    elif entry.get("summary"):
        raw_html = entry.get("summary", "")

    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_html)
    if match:
        return match.group(1)

    return None


def fetch_all():
    articles = []
    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as e:
            print(f"[UYARI] {feed['source']} çekilemedi: {e}")
            continue

        if not parsed.entries:
            print(f"[UYARI] {feed['source']} için hiç haber bulunamadı (adres yanlış olabilir).")
            continue

        for entry in parsed.entries[:MAX_PER_FEED]:
            articles.append({
                "title": entry.get("title", "").strip(),
                "category": feed["category"],
                "source": feed["source"],
                "url": entry.get("link", "#"),
                "summary": clean_summary(entry.get("summary", "")),
                "image": extract_image(entry),
                "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
            })

    return articles


def main():
    articles = fetch_all()
    if not articles:
        print("Hiç haber çekilemedi, articles.json değiştirilmedi.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"articles": articles}, f, ensure_ascii=False, indent=2)

    print(f"{len(articles)} haber yazıldı -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
