"""
Kişisel Gelişim Botu - günlük Telegram gönderisi.

Claude Code cloud routine'i, kurumsal ("Web Preview") ağ politikası yüzünden
api.telegram.org'a hiç ulaşamadığından (bkz. README) bu script GitHub Actions
üzerinde çalışacak şekilde yeniden yazıldı. Ağ çağrıları burada gerçek Python
kodu ile yapılıyor, bu yüzden aşağıdaki garanti-fallback mekanizması bir LLM
talimatına değil, gerçek try/except'e dayanıyor.
"""

import datetime
import json
import os
import sys
import urllib.parse

import requests
from anthropic import Anthropic

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
HTTP_TIMEOUT = 20

CATEGORY_BY_WEEKDAY = {
    1: "Tarih",
    2: "Bilim & Teknoloji",
    3: "Uzay & Fütürizm",
    4: "Felsefe & Psikoloji",
    5: "Sanat & Kültür",
    6: "Ekonomi & Toplum",
    7: "Gizemler & Keşifler",
}


def tg_send_message(text, reply_markup=None):
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return requests.post(f"{TG_API}/sendMessage", data=data, timeout=HTTP_TIMEOUT).json()


def tg_edit_message(message_id, text):
    data = {
        "chat_id": CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    return requests.post(f"{TG_API}/editMessageText", data=data, timeout=HTTP_TIMEOUT).json()


def tg_send_photo(photo_url, caption):
    data = {"chat_id": CHAT_ID, "photo": photo_url, "caption": caption, "parse_mode": "Markdown"}
    return requests.post(f"{TG_API}/sendPhoto", data=data, timeout=HTTP_TIMEOUT).json()


def tg_send_poll(question, options, correct_option_id):
    data = {
        "chat_id": CHAT_ID,
        "question": question[:300],
        "options": json.dumps(options),
        "type": "quiz",
        "is_anonymous": "true",
        "correct_option_id": correct_option_id,
    }
    return requests.post(f"{TG_API}/sendPoll", data=data, timeout=HTTP_TIMEOUT).json()


GENERATION_PROMPT = """Sen dünyanın en prestijli ansiklopedilerinin, tarihçilerinin, gelecek bilimcilerinin \
(fütüristler) ve teknik uzmanlarının ortak aklısın.

Kategori: {category}

Bu kategoride, önceden çok işlenmiş klişeleri (yapay zeka, iklim değişikliği gibi) ATLAYARAK \
spesifik ve çarpıcı bir konu seç. Sonra bu konu hakkında TÜRKÇE, akademik titizlikte, \
isim/tarih/teori içeren, sürükleyici bir analiz yaz.

SADECE aşağıdaki JSON şemasına birebir uyan, başka hiçbir açıklama/markdown code-fence içermeyen \
saf bir JSON nesnesi döndür:

{{
  "title": "Konu başlığı (kısa, çarpıcı)",
  "wikipedia_title_tr": "Türkçe Wikipedia'da olması muhtemel başlık (yoksa null)",
  "wikipedia_title_en": "İngilizce Wikipedia'da olması muhtemel başlık (görsel/kaynak için de kullanılacak)",
  "sections": [
    "Telegram Markdown metni - Bölüm 1 (Geçmiş). '🌐 *{{title}} - Kapsamlı ve Derinlemesine Analiz*' başlığıyla başlasın, sonra '⏳ *1. GEÇMİŞ: Kökenler, Kök Nedenler ve Tarihsel Gelişim*' ve *Doğuşu:*, *Kritik Kırılma Noktaları:*, *Gözden Kaçan Detaylar:* alt başlıklarını içersin. SADECE tek yıldız *bold* kullan, # veya ** KULLANMA. 4000 karakteri geçme.",
    "Telegram Markdown metni - Bölüm 2 (Günümüz). '📍 *2. GÜNÜMÜZ: Mevcut Durum, Etkiler ve Paradigmalar*' ve *Şu Anki Durum:*, *Temel Dinamikler:*, *Güncel Tartışmalar ve Krizler:* alt başlıklarını içersin. 4000 karakteri geçme.",
    "Telegram Markdown metni - Bölüm 3 (Gelecek + Genel Kültür). '🔮 *3. GELECEK: Projeksiyonlar, Trendler ve Senaryolar*' (*Kısa ve Orta Vadeli Trendler:*, *Uzun Vadeli Gelecek ve Fütürizm:*, *Fırsatlar ve Tehditler:*) VE ardından '🧠 *4. GENEL KÜLTÜR VE ENTELEKTÜEL NOTLAR*' (*Bilmeniz Gereken 3 Kavram/Terim:*, *Kültürel Etki:*, *Özet Çıkarım:*) bölümlerinin ikisini birden içersin. 4000 karakteri geçme."
  ],
  "quiz": {{
    "question": "Konuyla ilgili tek doğru cevaplı soru",
    "options": ["A şıkkı (max 90 karakter)", "B şıkkı", "C şıkkı", "D şıkkı"],
    "correct_option_id": 0
  }}
}}

correct_option_id, 0-3 arası doğru şıkkın index'i olmalı."""


def generate_content(category):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": GENERATION_PROMPT.format(category=category)}],
    )
    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise RuntimeError(f"Yanıtta text bloğu yok, gelen block tipleri: {[getattr(b, 'type', None) for b in response.content]}")
    raw = text_blocks[0].strip()

    # Extract JSON from markdown code fence if present
    if raw.startswith("```"):
        # Split by triple backticks and get the middle content
        parts = raw.split("```")
        if len(parts) >= 3:
            raw = parts[1].strip()
        elif len(parts) == 2:
            raw = parts[1].strip()

        # Remove language identifier (json, python, etc) if it's on the first line
        lines = raw.split("\n", 1)
        if lines[0].lower() in ("json", "python", "javascript", "py"):
            raw = lines[1] if len(lines) > 1 else ""
        raw = raw.strip()

    return json.loads(raw)


def find_wikipedia_link(title_tr, title_en):
    for lang, title in (("tr", title_tr), ("en", title_en)):
        if not title:
            continue
        url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
        try:
            r = requests.head(url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                return url
        except requests.RequestException:
            pass
    return None


def find_image(title_en):
    if not title_en:
        return None
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title_en.replace(' ', '_'))}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            thumb = r.json().get("thumbnail", {}).get("source")
            if thumb:
                return thumb
    except (requests.RequestException, ValueError):
        pass
    return None


def main():
    weekday = datetime.datetime.now(datetime.timezone.utc).isoweekday()
    category = CATEGORY_BY_WEEKDAY[weekday]

    placeholder_id = None
    try:
        resp = tg_send_message("⏳ Bugünkü analiz hazırlanıyor...")
        if resp.get("ok"):
            placeholder_id = resp["result"]["message_id"]
        else:
            print(f"[uyarı] placeholder gönderilemedi: {resp}", file=sys.stderr)
    except Exception as e:
        print(f"[uyarı] placeholder gönderilirken hata: {e}", file=sys.stderr)

    try:
        content = generate_content(category)
        title = content["title"]

        image_url = find_image(content.get("wikipedia_title_en"))
        if image_url:
            r = tg_send_photo(image_url, f"🌐 *{title}*")
            if not r.get("ok"):
                print(f"[uyarı] sendPhoto başarısız: {r}", file=sys.stderr)

        for i, part in enumerate(content["sections"]):
            if i == 0 and placeholder_id:
                r = tg_edit_message(placeholder_id, part)
            else:
                r = tg_send_message(part)
            if not r.get("ok"):
                raise RuntimeError(f"Telegram gönderimi başarısız (bölüm {i}): {r}")

        wiki_url = find_wikipedia_link(content.get("wikipedia_title_tr"), content.get("wikipedia_title_en"))
        scholar_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(title)}"
        buttons = []
        if wiki_url:
            buttons.append([{"text": "📖 Wikipedia Kaynağı", "url": wiki_url}])
        buttons.append([{"text": "🔬 Akademik Araştırmalar", "url": scholar_url}])
        tg_send_message("🔗 Derinlemesine incelemek için:", reply_markup={"inline_keyboard": buttons})

        quiz = content["quiz"]
        r = tg_send_poll(quiz["question"], quiz["options"], quiz["correct_option_id"])
        if not r.get("ok"):
            print(f"[uyarı] sendPoll başarısız: {r}", file=sys.stderr)

        print(f"Tamamlandı: {title}")

    except Exception as e:
        fallback_text = (
            f"⚠️ Bugünkü otomatik analiz üretilirken bir sorunla karşılaşıldı "
            f"({type(e).__name__}). Yarın normal şekilde devam edecek."
        )
        try:
            if placeholder_id:
                tg_edit_message(placeholder_id, fallback_text)
            else:
                tg_send_message(fallback_text)
        except Exception as inner:
            print(f"[kritik] fallback mesajı da gönderilemedi: {inner}", file=sys.stderr)
        print(f"[hata] {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
