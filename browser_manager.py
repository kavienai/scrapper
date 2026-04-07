"""
Seeking Alpha Scraper - Tarayıcı Yönetimi
Manuel stealth teknikleri ile bot korumasını aşan tarayıcı oturumu yönetimi.
Cookie kaydetme/yükleme desteği ile tekrar tekrar giriş yapmayı önler.

NOT: playwright-stealth paketi güncel Playwright ile uyumsuz olduğu için
stealth bypass'lar burada doğrudan init_script olarak uygulanıyor.
"""
import json
import os
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext
from rich.console import Console

import config

console = Console()

# ─── Manuel Stealth Script ──────────────────────────────────────
# Bu script, Playwright'ın bot olarak algılanmasını engelleyen
# JavaScript override'larını uygular. playwright-stealth'in bozuk
# versiyonu yerine temiz, minimal bir implementasyon.
STEALTH_INIT_SCRIPT = """
// 1. navigator.webdriver flag'ini gizle
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Chrome runtime objesi ekle (gerçek Chrome'da var)
if (!window.chrome) {
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
}

// 3. navigator.plugins (boş olması bot belirtisi)
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        { name: 'Native Client', filename: 'internal-nacl-plugin' },
    ],
});

// 4. navigator.languages (boş olması bot belirtisi)
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// 5. permissions query override
if (navigator.permissions) {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = (parameters) => {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return originalQuery(parameters);
    };
}

// 6. WebGL vendor/renderer (headless tespiti engellemek için)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};

// 7. window.outerWidth/outerHeight (headless modda 0 olur)
if (window.outerWidth === 0) {
    Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
}
if (window.outerHeight === 0) {
    Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 85 });
}

// 8. Connection rtt (bot tespiti için kullanılır)
if (navigator.connection) {
    Object.defineProperty(navigator.connection, 'rtt', { get: () => 100 });
}
"""


class BrowserManager:
    """Playwright tarayıcı oturumunu yönetir."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self, headless: Optional[bool] = None):
        """
        Tarayıcıyı başlat ve stealth modunu aktif et.
        Args:
            headless: Opsiyonel olarak config değerini geçersiz kılar.
        """
        console.print("[bold cyan]🌐 Tarayıcı başlatılıyor...[/]")
        
        # Headless değerini belirle (Argüman > Config)
        final_headless = headless if headless is not None else config.HEADLESS

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=final_headless,
            slow_mo=config.SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Gerçek kullanıcı gibi görünen context oluştur
        self.context = await self.browser.new_context(
            user_agent=config.USER_AGENT,
            viewport=config.VIEWPORT,
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        # Manuel stealth scriptini context'e ekle
        # Bu script her yeni sayfada otomatik çalışır
        await self.context.add_init_script(STEALTH_INIT_SCRIPT)

        self.page = await self.context.new_page()

        console.print("[bold green]✅ Tarayıcı hazır (Stealth aktif)[/]")
        return self.page

    async def save_cookies(self):
        """Oturum çerezlerini dosyaya kaydet."""
        if self.context:
            cookies = await self.context.cookies()
            with open(config.COOKIES_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            console.print(
                f"[dim]🍪 {len(cookies)} çerez kaydedildi → {config.COOKIES_FILE}[/]"
            )

    async def load_cookies(self) -> bool:
        """Kaydedilmiş çerezleri yükle. Başarılıysa True döner."""
        if not os.path.exists(config.COOKIES_FILE):
            return False

        try:
            with open(config.COOKIES_FILE, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            if not cookies:
                return False

            await self.context.add_cookies(cookies)
            console.print(
                f"[dim]🍪 {len(cookies)} çerez yüklendi (önceki oturum)[/]"
            )
            return True
        except Exception as e:
            console.print(f"[yellow]⚠️  Çerez yükleme hatası: {e}[/]")
            return False

    async def close(self):
        """Tarayıcıyı kapat."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        console.print("[dim]🔒 Tarayıcı kapatıldı.[/]")
