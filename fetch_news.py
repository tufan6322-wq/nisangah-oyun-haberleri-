"""
fetch_news.py
-----------------------------------------------------------
Oyun haberi RSS kaynaklarından başlık + kısa özet + kaynak linkini
çeker ve sitenin okuduğu articles.json dosyasını günceller.

ÖNEMLİ (telif hakkı): Bu script haberlerin TAMAMINI kopyalamaz.
Sadece başlık, kısa bir özet (RSS'in kendi özeti) ve kaynağa giden
link alınır. Trafiği/okuyucuyu asıl habere yönlendirmek SEO ve
yasal açıdan doğru olan yöntemdir. Tam metni birebir yayınlamak
telif ihlali sayılabilir.

Kurulum:
    pip install feedparser

Çalıştırma:
    python fetch_news.py

Bu script'i düzenli çalıştırmak için (elle her seferinde çalıştırmak
yerine) GitHub Actions kullanabilirsin — aynı klasördeki
.github/workflows/update-news.yml dosyasına bak.
"""

import json
import re
import feedparser
from datetime import datetime, timezone

# Türkçe oyun haberi kaynakları. Buradaki listeyi dilediğin kaynaklarla
# değiştirebilir/genişletebilirsin.
# NOT: Bu URL'leri zaman zaman kendin de kontrol et — RSS adresleri değişebilir.
FEEDS = [
    {"url": "https://www.oyungunlugu.com/rss.xml", "source": "Oyun Günlüğü", "category": "Genel"},
]

MAX_PER_FEED = 6
OUTPUT_FILE = "articles.json"


def clean_summary(raw_html, limit=160):
    """RSS özetindeki HTML etiketlerini temizler ve kısaltır."""
    text = re.sub("<[^<]+?>", "", raw_html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def fetch_all():
    articles = []
    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as e:
            print(f"[UYARI] {feed['source']} çekilemedi: {e}")
            continue

        for entry in parsed.entries[:MAX_PER_FEED]:
            articles.append({
                "title": entry.get("title", "").strip(),
                "category": feed["category"],
                "source": feed["source"],
                "url": entry.get("link", "#"),
                "summary": clean_summary(entry.get("summary", "")),
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
