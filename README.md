# Kişisel Gelişim Botu

Her gün saat 09:00'da (İstanbul saati) Telegram'a otomatik olarak, haftanın gününe göre değişen bir kategoriden derinlemesine bir "ansiklopedik analiz" gönderen bot. Bot: **@Ujum_gelisim_bot**

Otomasyon bir sunucuda çalışan geleneksel bir script değil — [Claude Code](https://claude.com/claude-code) "scheduled routine" (cron ile tetiklenen cloud agent) olarak çalışıyor. Her tetiklemede agent kendisi konu seçiyor, içerik yazıyor, görsel/kaynak arayıp doğruluyor ve Telegram'a gönderiyor.

## Nasıl çalışıyor

Routine ID: `trig_01X33WBXGuFK2FftgxPRW85x`
Yönetim: https://claude.ai/code/routines/trig_01X33WBXGuFK2FftgxPRW85x
Zamanlama: her gün `06:00 UTC` (`09:00 Europe/Istanbul`)

Her çalıştırmada agent sırayla:

1. **Konu seçimi** — haftanın gününe göre sabit bir kategoriden (aşağıya bakın) klişe olmayan, spesifik bir konu seçer.
2. **İçerik üretimi** — Türkçe, 4 bölümlü sabit bir yapıda (Geçmiş / Günümüz / Gelecek / Genel Kültür) derinlemesine bir metin yazar.
3. **Görsel** — Wikimedia Commons'ta ilgili bir görsel arar, göndermeden önce `curl` ile linkin gerçekten çalıştığını doğrular.
4. **Kaynaklar** — Wikipedia + Google Scholar (zorunlu) ve varsa Türkçe bir YouTube videosu bulup tıklanabilir buton olarak ekler.
5. **Quiz** — konuyla ilgili 4 şıklı bir Telegram anketi (quiz) hazırlar.
6. **Gönderim** — görsel, metin, kaynak butonları ve anketi sırayla Telegram Bot API üzerinden gönderir.

### Gün → kategori eşlemesi

| Gün | Kategori |
|---|---|
| Pazartesi | Tarih |
| Salı | Bilim & Teknoloji |
| Çarşamba | Uzay & Fütürizm |
| Perşembe | Felsefe & Psikoloji |
| Cuma | Sanat & Kültür |
| Cumartesi | Ekonomi & Toplum |
| Pazar | Gizemler & Keşifler |

## Kurulum

1. [@BotFather](https://t.me/BotFather) üzerinden bir Telegram botu oluşturup token alın.
2. Botla bir kere konuşup (`/start`) `chat_id`'nizi Telegram API'nin `getUpdates` endpoint'inden öğrenin.
3. `.env.example` dosyasını `.env` olarak kopyalayıp kendi token/chat_id değerlerinizi girin (`.env` asla commit edilmez, `.gitignore` içinde).
4. Routine'in prompt'unu güncellemek isterseniz [routine-prompt.md](./routine-prompt.md) dosyasını düzenleyip [claude.ai/code/routines](https://claude.ai/code/routines) üzerinden veya Claude Code'da `RemoteTrigger action: update` aracıyla routine'e geri yükleyebilirsiniz (dosyadaki `{{TELEGRAM_BOT_TOKEN}}` / `{{TELEGRAM_CHAT_ID}}` yer tutucularını gerçek değerlerle değiştirmeyi unutmayın).

## Notlar

- Routine'in prompt'u kendi içinde bot token ve chat_id'yi barındırıyor (cloud agent yerel `.env`'e erişemediği için) — bu yüzden token değişirse hem `.env` hem routine prompt'u güncellenmeli.
- Bu repo'da botun asıl "mantığı" kod olarak değil, routine'e verilen doğal dil talimatı (prompt) olarak yaşıyor; kod tabanında ayrı bir script/sunucu yok.
