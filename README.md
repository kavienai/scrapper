# 🕷️ Seeking Alpha Scraper

Seeking Alpha'ya otomatik giriş yapıp hisse senedi verilerini çeken Python uygulaması.

## ✨ Özellikler

- 🔐 **Otomatik Giriş** — Email/şifre ile login, cookie kaydetme
- 📊 **Hisse Özeti** — Fiyat, değişim, piyasa değeri
- 📰 **Makale Çekme** — Son analizler ve makaleler
- 💰 **Finansal Veriler** — Temel metrikler (EPS, P/E, vb.)
- ⭐ **Derecelendirmeler** — Quant Rating, Analist görüşleri
- 🍪 **Cookie Yönetimi** — Tekrar tekrar giriş yapmak gerekmez
- 💾 **JSON/CSV Export** — Verileri dosyaya kaydetme
- 🎨 **Rich Terminal** — Güzel renkli tablo çıktıları

## 🚀 Kurulum

```bash
# 1. Sanal ortam oluştur
python -m venv .venv

# 2. Aktif et
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Kütüphaneleri kur
pip install -r requirements.txt

# 4. Playwright tarayıcısını indir
playwright install chromium
```

## ⚙️ Yapılandırma

`.env.example` dosyasını `.env` olarak kopyalayıp bilgileri girin:

```bash
copy .env.example .env
```

`.env` dosyasını düzenleyin:
```
SA_EMAIL=senin_emailin@example.com
SA_PASSWORD=senin_sifren
```

## 📖 Kullanım

### İnteraktif Menü
```bash
python main.py
```

### Komut Satırı
```bash
# Tek hisse
python main.py --symbol AAPL

# Birden fazla hisse
python main.py --symbols AAPL,MSFT,GOOGL,TSLA

# Makale çek
python main.py --articles TSLA

# Finansal veriler
python main.py --financials NVDA

# Tüm veriler (özet + makaleler + finansal + rating)
python main.py --all AAPL

# Görünmez tarayıcı modunda
python main.py --symbol AAPL --headless
```

## 📁 Proje Yapısı

```
scraping/
├── main.py              # Ana uygulama (CLI + Menü)
├── browser_manager.py   # Playwright tarayıcı yönetimi
├── auth.py              # Login / Oturum yönetimi
├── scraper.py           # Veri çekme fonksiyonları
├── config.py            # Yapılandırma ayarları
├── requirements.txt     # Python bağımlılıkları
├── .env                 # Giriş bilgileri (git'e eklenmez!)
├── .env.example         # Örnek .env dosyası
├── cookies/             # Kaydedilmiş oturum çerezleri
└── output/              # Çekilen veriler (JSON/CSV)
```

## ⚠️ Önemli Notlar

1. **Captcha**: Seeking Alpha Cloudflare koruması kullanır. İlk girişte captcha çıkabilir — tarayıcı açık modda `(headless=False)` çalıştırıp manuel olarak çözmeniz gerekir. Sonrasında cookie kaydedilir.

2. **Hız Limiti**: Çok hızlı istek atmayın. Kod otomatik olarak istekler arasında 3 saniye bekler.

3. **Selector Değişimi**: Seeking Alpha site yapısını sık değiştirir. Veri çekilemezse, Chrome DevTools ile güncel selector'ları bulup `scraper.py`'daki listelere ekleyebilirsiniz.

4. **Premium İçerik**: Bazı veriler sadece premium üyelere açıktır.

## 📜 Yasal Uyarı

Bu araç **eğitim amaçlıdır**. Kullanmadan önce Seeking Alpha'nın kullanım koşullarını okuyun. Aşırı kullanım hesap kapatılmasına neden olabilir.
