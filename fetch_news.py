"""
fetch_news.py
-----------------------------------------------------------
Oyun haberi RSS kaynaklarından başlık + kısa özet + görsel + kaynak
linkini çeker ve sitenin okuduğu articles.json dosyasını günceller.

ÖNEMLİ (telif hakkı): Bu script haberlerin TAMAMINI kopyalamaz.
Sadece başlık, kısa bir özet (RSS'in kendi özeti), görsel ve kaynağa
giden link alınır. Trafiği/okuyucuyu asıl habere yönlendirmek SEO ve
yasal açıdan doğru olan yöntemdir. Tam metni birebir yayınlamak
telif ihlali sayılabilir.

Kurulum:
    pip install feedparser

Çalıştırma:
    python fetch_news.py

NOT: Aşağıdaki RSS adresleri yaygın kalıplara göre tahmin edilmiştir.
İlk çalıştırmada bazı kaynaklar hata verebilir (adres değişmiş ya da
farklı bir yapıdaysa) — GitHub Actions loglarında "[UYARI]" ile
başlayan satırları kontrol et, çalışmayan kaynağı düzelt ya da listeden
çıkar.
"""

import json
import re
import feedparser
from datetime import datetime, timezone, timedelta

# Türkçe oyun haberi kaynakları. Buradaki listeyi dilediğin kaynaklarla
# değiştirebilir/genişletebilirsin.
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
    """RSS özetindeki HTML etiketlerini temizler ve kısaltır."""
    text = re.sub("<[^<]+?>", "", raw_html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def extract_image(entry):
    """RSS girdisinden bir görsel URL'si bulmaya çalışır.
    Sırasıyla: media:content, media:thumbnail, enclosure, içerik
    içindeki ilk <img> etiketi kontrol edilir. Bulunamazsa None döner.
    """
    # media:content (çoğu haber sitesi bunu kullanır)
    media_content = entry.get("media_content")
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url

    # media:thumbnail
    media_thumb = entry.get("media_thumbnail")
    if media_thumb:
        url = media_thumb[0].get("url")
        if url:
            return url

    # enclosure (bazı feed'ler görseli burada verir)
    if entry.get("enclosures"):
        for enc in entry["enclosures"]:
            if enc.get("type", "").startswith("image") or enc.get("href", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                return enc.get("href")

    # içerik metninde geçen ilk <img src="...">
    raw_html = ""
    if entry.get("content"):
        raw_html = entry["content"][0].get("value", "")
    elif entry.get("summary"):
        raw_html = entry.get("summary", "")

    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_html)
    if match:
        return match.group(1)

    return None


MAX_AGE_DAYS = 90  # bu süreden eski haberler otomatik silinir


def load_existing():
    """articles.json dosyasında zaten var olan haberleri okur."""
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("articles", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def parse_date_safe(value):
    """RSS'in verdiği tarih string'ini karşılaştırılabilir bir datetime'a çevirir.
    Ayrıştıramazsa şu anı döner (yeni haber gibi davranır, silinmez)."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def fetch_new():
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
    existing = load_existing()
    new_articles = fetch_new()

    by_url = {a["url"]: a for a in existing}
    for a in new_articles:
        by_url[a["url"]] = a

    merged = list(by_url.values())

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    before_count = len(merged)
    merged = [a for a in merged if parse_date_safe(a.get("published")) >= cutoff]
    removed = before_count - len(merged)

    merged.sort(key=lambda a: parse_date_safe(a.get("published")), reverse=True)

    if not merged:
        print("Hiç haber yok, articles.json değiştirilmedi.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"articles": merged}, f, ensure_ascii=False, indent=2)

    print(f"{len(new_articles)} yeni haber tarandı, {removed} eski haber temizlendi, toplam {len(merged)} haber -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
