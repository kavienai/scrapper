"""
Seeking Alpha Scraper - Yapılandırma Dosyası
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Giriş Bilgileri ──────────────────────────────────────────
SA_EMAIL = os.getenv("SA_EMAIL", "")
SA_PASSWORD = os.getenv("SA_PASSWORD", "")

# ─── Tarayıcı Ayarları ────────────────────────────────────────
HEADLESS = False  # True yaparsanız tarayıcı görünmez modda çalışır
SLOW_MO = 50      # Her işlem arasında milisaniye bekleme (insan davranışı)
VIEWPORT = {"width": 1366, "height": 768}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# ─── Dosya Yolları ─────────────────────────────────────────────
COOKIES_DIR = os.path.join(os.path.dirname(__file__), "cookies")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
COOKIES_FILE = os.path.join(COOKIES_DIR, "sa_cookies.json")

# Klasörleri oluştur
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── URL'ler ───────────────────────────────────────────────────
BASE_URL = "https://seekingalpha.com"
LOGIN_URL = f"{BASE_URL}/account/login"

# ─── Zamanlama (saniye) ────────────────────────────────────────
PAGE_LOAD_TIMEOUT = 120000  # 120 saniye
LOGIN_WAIT = 5000           # Giriş sonrası bekleme
BETWEEN_REQUESTS = 3        # İstekler arası bekleme (saniye)
BETWEEN_ARTICLE_DELAY = 10.0  # Makale içerikleri arası bekleme (uzatıldı)
HUMAN_SCROLL = True         # Veri çekmeden önce sayfayı kaydır
MIN_STAY_TIME = 3           # Sayfada kalma süresi (saniye)
