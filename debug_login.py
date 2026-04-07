"""Debug script - Manuel stealth ile login sayfasını test eder."""
import asyncio
from browser_manager import BrowserManager
import config

async def test():
    bm = BrowserManager()
    await bm.start()
    
    print(f"\n=== LOGIN URL: {config.LOGIN_URL} ===")
    
    # Sayfaya git
    await bm.page.goto(config.LOGIN_URL, wait_until="load", timeout=60000)
    
    # Sayfanın tam yüklenmesini bekle
    print("Sayfa yukleniyor...")
    for i in range(20):
        await bm.page.wait_for_timeout(1000)
        title = await bm.page.title()
        
        # Email input kontrol et
        email = await bm.page.query_selector('input[type="email"]')
        if email:
            print(f"\n✅ Form yuklendi! ({i+1}s)")
            break
        
        print(f"  [{i+1}s] Title: {title[:50]} | Bekleniyor...")
    
    # Son durum
    print(f"\nURL: {bm.page.url}")
    print(f"Title: {await bm.page.title()}")
    
    # Elementleri test et
    selectors = [
        ('input[type="email"]', "Email (type)"),
        ('#signInPasswordField', "Password (id)"),
        ('input[type="password"]', "Password (type)"),
        ('button:has-text("Sign in")', "Sign in button"),
    ]
    
    print("\n=== SELECTOR SONUCLARI ===")
    for selector, label in selectors:
        try:
            el = await bm.page.query_selector(selector)
            print(f"  {'✅' if el else '❌'} {label}: {'BULUNDU' if el else 'BULUNAMADI'}")
        except Exception as e:
            print(f"  ❌ {label}: HATA - {e}")
    
    # Console hatalarini kontrol et
    print("\n=== JS HATALARI (varsa) ===")
    
    # Screenshot al
    await bm.page.screenshot(path="debug_screenshot.png")
    print("\n📸 Screenshot: debug_screenshot.png")
    
    # Sayfayi acik tut
    print("\n⏳ Tarayici 30 saniye acik kalacak...")
    await bm.page.wait_for_timeout(30000)
    
    await bm.close()

asyncio.run(test())
