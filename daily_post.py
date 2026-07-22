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
import json5
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

CATEGORIES = [
    "Bilim & Uzay",
    "Tarih",
    "Sanat & Estetik",
    "Felsefe & Düşünce",
    "Psikoloji & İnsan Zihni",
    "Ekonomi & Toplum",
    "Teknoloji & Gelecek",
    "Matematik & Mantık",
]


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

KONU SEÇİMİ KRİTERLERİ (ÖNEMLİ):
1) EN TEMEL, EN ÖNEMLİ ve EN YAYGN BİLİNEN konuları tercih et (Sanat için Rönesans/Van Gogh, Tarih için Devrimmler/Roma, Bilim için Görelilik/Evrim/DNA gibi).
2) Uç, niş veya çok teknik konulardan kaçın (Von Neumann sondaları, Breakthrough Starshot gibi).
3) Eğitimli ama uzman olmayan birinin "bunu duydum, merak ediyordum" diyeceği konu olsun.
4) Kültürel, tarihsel veya bilimsel açıdan önemi YÜKSEK olmalı.
5) ŞU KONULAR ZATENİŞLENDİ, TEKRAR ETME: {already_posted}

Kategori: {category}
Daha önce işlenen: {already_posted}

Bu kategoride, yukarıdaki kriterler doğrultusunda, ÖN EME GELEN EN ÖNEMLİ bir konu seç (henüz işlenmemiş). \
Sonra bu konu hakkında TÜRKÇE, akademik titizlikte, isim/tarih/teori içeren, sürükleyici bir analiz yaz.

SADECE aşağıdaki JSON şemasına birebir uyan, başka hiçbir açıklama/markdown code-fence içermeyen \
saf bir JSON nesnesi döndür:

{{
  "title": "Konu başlığı (kısa, çarpıcı)",
  "wikipedia_title_tr": "Türkçe Wikipedia'da olması muhtemel başlık (yoksa null)",
  "wikipedia_title_en": "İngilizce Wikipedia'da olması muhtemel başlık (görsel/kaynak için de kullanılacak)",
  "youtube_search_query": "Türkçe YouTube araması için arama terimi",
  "sections": [
    "Telegram Markdown metni - Bölüm 1 (Geçmiş). '🌐 *{{title}} - Kapsamlı ve Derinlemesine Analiz*' başlığıyla başlasın, sonra '⏳ *1. GEÇMİŞ: Kökenler, Kök Nedenler ve Tarihsel Gelişim*' ve *Doğuşu:*, *Kritik Kırılma Noktaları:*, *Gözden Kaçan Detaylar:* alt başlıklarını içersin. SADECE tek yıldız *bold* kullan, # veya ** KULLANMA. 4000 karakteri geçme.",
    "Telegram Markdown metni - Bölüm 2 (Günümüz). '📍 *2. GÜNÜMÜZ: Mevcut Durum, Etkiler ve Paradigmalar*' ve *Şu Anki Durum:*, *Temel Dinamikler:*, *Güncel Tartışmalar ve Krizler:* alt başlıklarını içersin. 4000 karakteri geçme.",
    "Telegram Markdown metni - Bölüm 3 (Gelecek + Genel Kültür). '🔮 *3. GELECEK: Projeksiyonlar, Trendler ve Senaryolar*' (*Kısa ve Orta Vadeli Trendler:*, *Uzun Vadeli Gelecek ve Fütürizm:*, *Fırsatlar ve Tehditler:*) VE ardından '🧠 *4. GENEL KÜLTÜR VE ENTELEKTÜEL NOTLAR*' (*Bilmeniz Gereken 3 Kavram/Terim:*, *Kültürel Etki:*, *Özet Çıkarım:*) bölümlerinin ikisini birden içersin. 4000 karakteri geçme."
  ],
  "quiz": "Konuyla ilgili tek doğru cevaplı soru (max 300 karakter)|A şıkkı (max 90 karakter)|B şıkkı|C şıkkı|D şıkkı|0"
}}

correct_option_id, 0-3 arası doğru şıkkın index'i olmalı."""


def generate_content(category, already_posted="Hiçbiri"):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": GENERATION_PROMPT.format(category=category, already_posted=already_posted)}],
    )

    # Check if response was truncated
    stop_reason = response.stop_reason
    print(f"[debug] API stop_reason: {stop_reason}", file=sys.stderr)
    if stop_reason == "max_tokens":
        raise RuntimeError(f"[kritik] Yanıt max_tokens limitine çarptı, JSON eksik. max_tokens daha da artırılmalı.")

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

    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError as e:
        print(f"[debug] strict=False JSON başarısız: {e}", file=sys.stderr)
        try:
            print(f"[debug] Fallback: literal newline'ları escape et...", file=sys.stderr)
            raw_cleaned = raw.replace('\n', '\\n')
            return json.loads(raw_cleaned, strict=False)
        except json.JSONDecodeError as e2:
            print(f"[debug] Cleaned JSON de başarısız, json5 deniyor...", file=sys.stderr)
            try:
                return json5.loads(raw)
            except Exception as e3:
                print(f"[hata] Tüm parse yöntemleri başarısız", file=sys.stderr)
                print(f"[hata] Hatalar: json={e}, cleaned={e2}, json5={e3}", file=sys.stderr)
                print(f"[debug] Ham raw çıktı ({len(raw)} karakter):\n{raw}", file=sys.stderr)
                raise


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


def find_image(title_tr, title_en):
    methods_tried = []

    # Yöntem 1: Wikipedia REST API (thumbnail veya original)
    for lang, title in (("tr", title_tr), ("en", title_en)):
        if not title:
            continue
        try:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'))}"
            print(f"[debug] Yöntem 1: Wikipedia REST API ({lang})", file=sys.stderr)
            r = requests.get(url, timeout=10)
            methods_tried.append(f"Wikipedia-REST-{lang}")
            if r.status_code == 200:
                data = r.json()
                thumb = data.get("thumbnail", {}).get("source")
                original = data.get("originalimage", {}).get("source")
                image_url = original or thumb
                if image_url:
                    print(f"[debug] ✓ Görsel bulundu ({lang}): {image_url}", file=sys.stderr)
                    return image_url
        except Exception as e:
            print(f"[debug] Wikipedia REST ({lang}) hatası: {e}", file=sys.stderr)

    # Yöntem 2: Wikipedia pageimages API (original image)
    for lang, title in (("tr", title_tr), ("en", title_en)):
        if not title:
            continue
        try:
            url = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=pageimages&piprop=original&format=json"
            print(f"[debug] Yöntem 2: Wikipedia pageimages API ({lang})", file=sys.stderr)
            r = requests.get(url, timeout=10)
            methods_tried.append(f"Wikipedia-pageimages-{lang}")
            if r.status_code == 200:
                pages = r.json().get("query", {}).get("pages", {})
                for page in pages.values():
                    image_url = page.get("original", {}).get("source")
                    if image_url:
                        print(f"[debug] ✓ Görsel bulundu ({lang} pageimages): {image_url}", file=sys.stderr)
                        return image_url
        except Exception as e:
            print(f"[debug] Wikipedia pageimages ({lang}) hatası: {e}", file=sys.stderr)

    # Yöntem 3: Wikimedia Commons arama
    search_term = title_tr or title_en
    if search_term:
        try:
            url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(search_term)}&srnamespace=6&format=json&srlimit=10"
            print(f"[debug] Yöntem 3: Wikimedia Commons araması", file=sys.stderr)
            r = requests.get(url, timeout=10)
            methods_tried.append("Wikimedia-Commons")
            if r.status_code == 200:
                results = r.json().get("query", {}).get("search", [])
                print(f"[debug] Wikimedia sonuç: {len(results)} dosya", file=sys.stderr)
                for result in results:
                    title_found = result.get("title", "")
                    if any(title_found.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                        image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(title_found)}"
                        try:
                            img_check = requests.head(image_url, timeout=5)
                            if img_check.status_code == 200:
                                print(f"[debug] ✓ Görsel bulundu (Wikimedia): {title_found}", file=sys.stderr)
                                return image_url
                        except Exception as e:
                            print(f"[debug] Görsel doğrulama hatası: {e}", file=sys.stderr)
                            continue
        except Exception as e:
            print(f"[debug] Wikimedia hatası: {e}", file=sys.stderr)

    print(f"[debug] ✗ Fotoğraf bulunamadı (denenen yöntemler: {', '.join(methods_tried)})", file=sys.stderr)
    return None


def main():
    day_of_year = datetime.datetime.now(datetime.timezone.utc).timetuple().tm_yday
    category_index = (day_of_year - 1) % len(CATEGORIES)
    category = CATEGORIES[category_index]
    print(f"[debug] Gün {day_of_year}, Kategori indeksi: {category_index}, Seçilen kategori: {category}", file=sys.stderr)

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
        # Load posted topics
        posted_topics = {}
        if os.path.exists("posted_topics.json"):
            try:
                with open("posted_topics.json", "r", encoding="utf-8") as f:
                    posted_topics = json.load(f)
            except Exception as e:
                print(f"[uyarı] posted_topics.json okunamadı: {e}", file=sys.stderr)

        # Get already posted topics for this category
        already_posted_list = posted_topics.get(category, [])
        already_posted_str = ", ".join(already_posted_list[-15:]) if already_posted_list else "Hiçbiri"
        print(f"[debug] Kategori '{category}' daha önce işlenen konular: {already_posted_str}", file=sys.stderr)

        # Generate content with the list
        content = generate_content(category, already_posted_str)
        title = content["title"]
        print(f"[debug] Konu başlığı: {title}", file=sys.stderr)

        # Save the new topic
        if category not in posted_topics:
            posted_topics[category] = []
        posted_topics[category].append(title)
        try:
            with open("posted_topics.json", "w", encoding="utf-8") as f:
                json.dump(posted_topics, f, ensure_ascii=False, indent=2)
            print(f"[debug] Konu kaydı güncellendi", file=sys.stderr)
        except Exception as e:
            print(f"[uyarı] posted_topics.json yazılamadı: {e}", file=sys.stderr)

        image_url = find_image(content.get("wikipedia_title_tr"), content.get("wikipedia_title_en"))
        print(f"[debug] Fotoğraf URL: {image_url}", file=sys.stderr)
        if image_url:
            try:
                wiki_url = find_wikipedia_link(content.get("wikipedia_title_tr"), content.get("wikipedia_title_en"))
                caption = f"🌐 *{title}*"
                if wiki_url:
                    caption += f"\n[📖 Wikipedia]({wiki_url})"
                r = tg_send_photo(image_url, caption)
                if not r.get("ok"):
                    print(f"[uyarı] sendPhoto başarısız: {r}", file=sys.stderr)
                else:
                    print(f"[debug] Fotoğraf başarıyla gönderildi", file=sys.stderr)
            except Exception as e:
                print(f"[uyarı] fotoğraf gönderilirken hata: {e}", file=sys.stderr)

        for i, part in enumerate(content["sections"]):
            if i == 0 and placeholder_id:
                r = tg_edit_message(placeholder_id, part)
            else:
                r = tg_send_message(part)
            if not r.get("ok"):
                raise RuntimeError(f"Telegram gönderimi başarısız (bölüm {i}): {r}")

        wiki_url = find_wikipedia_link(content.get("wikipedia_title_tr"), content.get("wikipedia_title_en"))
        scholar_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(title)}"
        youtube_search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(content.get('youtube_search_query', ''))}"
        print(f"[debug] YouTube search URL: {youtube_search_url}", file=sys.stderr)
        buttons = []
        if wiki_url:
            buttons.append([{"text": "📖 Wikipedia Kaynağı", "url": wiki_url}])
        buttons.append([{"text": "🔬 Akademik Araştırmalar", "url": scholar_url}])
        buttons.append([{"text": "🎥 YouTube Arama", "url": youtube_search_url}])
        print(f"[debug] Button sayısı: {len(buttons)}", file=sys.stderr)
        tg_send_message("🔗 Derinlemesine incelemek için:", reply_markup={"inline_keyboard": buttons})

        quiz_parts = content["quiz"].split("|")
        if len(quiz_parts) >= 6:
            quiz_question = quiz_parts[0]
            quiz_options = quiz_parts[1:5]
            quiz_correct_id = int(quiz_parts[5])
            r = tg_send_poll(quiz_question, quiz_options, quiz_correct_id)
            if not r.get("ok"):
                print(f"[uyarı] sendPoll başarısız: {r}", file=sys.stderr)
        else:
            print(f"[uyarı] quiz format yanlış: {content['quiz']}", file=sys.stderr)

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
