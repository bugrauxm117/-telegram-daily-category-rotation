# Kişisel Gelişim Botu

Her gün saat 09:00'da (İstanbul saati) Telegram'a otomatik olarak, haftanın gününe göre değişen bir kategoriden derinlemesine bir "ansiklopedik analiz" gönderen bot. Bot: **@Ujum_gelisim_bot**

## Nasıl çalışıyor

Otomasyon **GitHub Actions** üzerinde çalışan bir Python script'i (`daily_post.py`) — her gün `06:00 UTC`'de (`09:00 Europe/Istanbul`) tetiklenir:

1. **Konu seçimi** — haftanın gününe göre sabit bir kategori (aşağıya bakın).
2. **İçerik üretimi** — Anthropic API'ye (Claude) tek bir çağrı yapılır; Claude, klişe olmayan spesifik bir konu seçip Türkçe, 4 bölümlü sabit yapıda (Geçmiş / Günümüz / Gelecek / Genel Kültür) bir metin ile bir quiz üretir, sonucu JSON olarak döner.
3. **Görsel** — Wikipedia REST API'sinden konunun özet görseli (varsa) çekilir.
4. **Kaynaklar** — Wikipedia (gerçek `HEAD` isteğiyle doğrulanmış) ve Google Scholar linkleri buton olarak eklenir.
5. **Gönderim** — placeholder mesaj → gerçek içerik (bölüm bölüm) → kaynak butonları → quiz anketi, sırayla Telegram Bot API üzerinden gönderilir.
6. **Garanti fallback** — her adım gerçek Python `try/except` içinde; herhangi bir şey patlarsa en baştaki placeholder mesajı bir uyarı metnine çevrilir, yani gün hiçbir zaman tamamen sessiz kalmaz.

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

## Neden Claude Code "scheduled routine" değil de GitHub Actions?

Bot ilk olarak bir Claude Code cloud "scheduled routine" (cron ile tetiklenen cloud agent) olarak kuruldu. Ancak bu hesabın bağlı olduğu organizasyonda **"Web (Preview)"** özelliği devre dışı bırakılmış durumda — bu yüzden o cloud environment'tan `api.telegram.org` dahil hiçbir dış adrese ağ isteği çıkamıyordu (proxy seviyesinde 403). Sonuç: routine sessizce hiçbir mesaj gönderemiyordu, ne ana içerik ne de "garanti" fallback mesajı — çünkü sorun mantık/prompt değil, ortamın ağ erişimiydi. Bu, prompt'u ne kadar sağlamlaştırırsak sağlamlaştıralım düzelmeyecek bir kısıtlamaydı.

Çözüm: aynı mantığı **GitHub Actions**'a (tam internet erişimi olan, ücretsiz, zamanlanmış bir ortam) taşımak — hem kısıtlamayı by-pass ediyor hem de artık gerçek Python kodu + gerçek `try/except` kullandığımız için "garanti fallback" gerçekten garanti oluyor (bir LLM'in talimata uyup uymamasına bağlı değil).

Eski routine (`trig_01X33WBXGuFK2FftgxPRW85x`, [routine-prompt.md](./routine-prompt.md)) devre dışı bırakıldı, referans olarak repoda duruyor.

## Kurulum

1. [@BotFather](https://t.me/BotFather) üzerinden bir Telegram botu oluşturup token alın.
2. Botla bir kere konuşup (`/start`) `chat_id`'nizi Telegram API'nin `getUpdates` endpoint'inden öğrenin.
3. [console.anthropic.com](https://console.anthropic.com) üzerinden bir Anthropic API key oluşturun.
4. GitHub reposunda **Settings → Secrets and variables → Actions** kısmına şu 3 secret'ı ekleyin:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `ANTHROPIC_API_KEY`
5. `.github/workflows/daily-post.yml` otomatik olarak her gün 06:00 UTC'de çalışır. Elle test etmek için: **Actions** sekmesi → "Daily Telegram Post" → **Run workflow**.
6. Yerelde test etmek isterseniz `.env.example` dosyasını `.env` olarak kopyalayıp değerleri girin, `pip install -r requirements.txt` sonrası `python daily_post.py` çalıştırın (`.env` asla commit edilmez).

## Notlar

- Secret'lar sadece GitHub Actions'ın kendi secret deposunda tutulur, kodda veya repoda asla açık metin olarak bulunmaz.
- Bir API key/token yanlışlıkla açığa çıkarsa (ör. bir sohbete yapıştırılırsa) hemen ilgili panelden (BotFather / console.anthropic.com) iptal edip yenisini oluşturun.
