"""
Seeking Alpha Scraper - Giriş (Login) Modülü
Seeking Alpha'ya email/şifre ile giriş yapar.
Captcha çıkarsa kullanıcıyı bilgilendirir ve manuel çözüm bekler.
"""
import asyncio
import os
from typing import TYPE_CHECKING
from playwright.async_api import Page
from rich.console import Console

if TYPE_CHECKING:
    from browser_manager import BrowserManager

import config

console = Console()



async def is_logged_in(page: Page) -> bool:
    """
    Sayfada aktif bir oturum olup olmadığını kontrol eder.
    Negatif (Log in butonu) ve Pozitif (Çerezler/Avatar) göstergeleri birlikte değerlendirir.
    """
    try:
        # Sayfanın dinamik içeriklerinin yüklenmesi için kısa bir bekleme
        await page.wait_for_timeout(2000)

        # 1. NEGATİF KONTROL (Eğer "LOG IN" butonu varsa kesinlikle giriş yapılmamıştır)
        # Seeking Alpha'nın top-nav barındaki kesin selectorler:
        logout_indicators = [
            "button[aria-label='Login / Register']",
            "button[aria-label='Register']",
            'header button:has-text("Log in")',
            'header button:has-text("Create free account")',
            '[data-test-id="login-button"]',
        ]
        
        for selector in logout_indicators:
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    # console.print(f"[dim]   (Debug: Logout butonu bulundu: {selector})[/]")
                    return False
            except:
                continue

        # 2. ÇEREZ KONTROLÜ (En kesin teknik kanıt)
        # user_id çerezi giriş yapınca gelir, çıkış yapınca silinir.
        try:
            cookies = await page.context.cookies()
            has_user_cookie = any(c['name'] == 'user_id' and c['value'] != '' for c in cookies)
            if not has_user_cookie:
                # console.print("[dim]   (Debug: user_id çerezi bulunamadı)[/]")
                return False
        except:
            pass

        # 3. POZİTİF GÖRSEL GÖSTERGELER
        logged_in_indicators = [
            '[data-test-id="user-menu-button"]',
            '[data-test-id="user-avatar"]',
            'button:has-text("Sign Out")',
            'a:has-text("Sign Out")',
            'span:has-text("Your Membership")',
        ]
        for selector in logged_in_indicators:
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    return True
            except:
                continue

        # 4. JS FLAG KONTROLÜ
        try:
            is_logged_in_js = await page.evaluate("() => window.isUserLoggedIn === true || (window.currentUser && !!window.currentUser.id)")
            if is_logged_in_js:
                return True
        except:
            pass

        # Hiçbir pozitif gösterge yoksa giriş yapılmamış sayılır
        return False
    except Exception as e:
        console.print(f"[dim]   Oturum durum kontrolü hatası: {e}[/]")
        return False
    except Exception as e:
        console.print(f"[dim]   Oturum durum kontrolü hatası: {e}[/]")
        return False


async def check_and_solve_captcha(page: Page, max_retries: int = 3) -> bool:
    """
    Sayfada bir captcha/challenge olup olmadığını kontrol eder ve çözmeye çalışır.
    
    Returns:
        bool: Challenge bulundu ve çözüldü mü?
    """
    challenge_indicators = [
        '#challenge-form',
        'text="Prove you are not a robot"',
        'text="PRESS & HOLD"',
        'text="Press & Hold"',
        '#px-captcha',
        'div:has-text("Press & Hold")',
        '#challenge-container',
        'text="enable Javascript and cookies"',
        'text="Press and Hold"',
        'iframe[src*="captcha"]',
        'iframe[title*="captcha" i]',
        'h1:has-text("Verify")',
        'h1:has-text("Human")',
    ]
    
    challenge_found = False
    found_indicator = ""
    
    # Tüm frameleri (iframeler dahil) kontrol et
    all_frames = page.frames
    for frame in all_frames:
        for indicator in challenge_indicators:
            try:
                el = await frame.query_selector(indicator)
                if el and await el.is_visible():
                    challenge_found = True
                    found_indicator = indicator
                    # Debug için screenshot al
                    await page.screenshot(path="captcha_trace.png")
                    break
            except:
                continue
        if challenge_found: break

    if not challenge_found:
        return False

    console.print(f"[bold red]🛑 BOT SORGUSU TESPİT EDİLDİ! ({found_indicator})[/]")
    
    for attempt in range(max_retries):
        await simulate_keyboard_press_and_hold(page, tab_count=attempt+1)
        
        # Kısa bir süre bekle ve challenge'ın gidip gitmediğini kontrol et
        await page.wait_for_timeout(5000)
        still_there = False
        for indicator in challenge_indicators:
            try:
                el = await page.query_selector(indicator)
                if el and await el.is_visible():
                    still_there = True
                    break
            except:
                continue
        
        if not still_there:
            console.print("[bold green]   ✅ Bot sorgusu başarıyla geçildi.[/]")
            return True
        
        console.print(f"[yellow]   ⚠️  Yeniden deneniyor ({attempt + 2}/{max_retries})...[/]")
    
    console.print("[bold red]   ❌ Bot sorgusu otomatik aşılamadı. Lütfen MANUEL müdahale edin![/]")
    return False

async def simulate_keyboard_press_and_hold(page: Page, tab_count: int = 1):
    """
    HUMAN/PerimeterX 'Press & Hold' captcha'sını klavye simülasyonu ile aşmaya çalışır.
    """
    console.print(f"[bold yellow]⌨️  Keyboard bypass (Tab x{tab_count}) başlatılıyor...[/]")
    try:
        await page.bring_to_front()
        # Sayfaya bir kez tıkla (odağı al)
        await page.mouse.click(100, 100)
        await page.keyboard.press("Escape") # Varsa diyalogları kapat
        await page.wait_for_timeout(1000)
        
        # Enter ile sayfayı aktif et
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)
        
        # Butona ulaşmak için Tab bas
        for _ in range(tab_count):
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(1000)
        
        # Enter tuşuna basılı tut (Jitter ile)
        console.print("[yellow]   ⏳ Enter tuşuna basılı tutuluyor (insan taklidi)...[/]")
        await page.keyboard.down("Enter")
        
        import random
        total_hold_time = random.uniform(11.0, 14.0)
        elapsed = 0
        while elapsed < total_hold_time:
            # Rastgele bekleme aralıkları
            wait_time = random.uniform(0.05, 0.2)
            await asyncio.sleep(wait_time)
            elapsed += wait_time
            
        await page.keyboard.up("Enter")
        await page.wait_for_timeout(3000)
        
    except Exception as e:
        console.print(f"[red]   ❌ Simülasyon hatası: {e}[/]")

async def login(page: Page, bm) -> bool:
    """
    Seeking Alpha'ya giriş yapar.
    
    Returns:
    Önce mevcut oturumu kontrol eder, yoksa şifre ile giriş dener.
    """
    if not config.SA_EMAIL or not config.SA_PASSWORD:
        console.print(
            "[bold red]❌ Email veya şifre bulunamadı![/]\n"
            "[yellow]   .env dosyasına SA_EMAIL ve SA_PASSWORD ekleyin.[/]\n"
            "[dim]   Örnek: .env.example dosyasına bakın.[/]"
        )
        return False

    # ─── Oturum Kontrolü (Signed in ise devam et) ──────────────
    console.print("\n[bold cyan]🔍 Oturum kontrol ediliyor...[/]")
    
    # Çerezleri yüklemeyi dene
    await bm.load_cookies()
    
    # Korumalı bir sayfaya gitmeyi dene (Daha kesin sonuç verir)
    try:
        test_url = f"{config.BASE_URL}/account/user_settings"
        console.print(f"[dim]   ⏳ Giriş durumu test ediliyor ({test_url})...[/]")
        
        await page.goto(test_url, wait_until="domcontentloaded", timeout=config.PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Captcha çıkarsa çöz
        await check_and_solve_captcha(page)
        
        if await is_logged_in(page):
            console.print("[bold green]✅ Aktif oturum doğrulandı. Kazımaya geçiliyor.[/]")
            return True
            
        console.print("[yellow]⚠️  Aktif oturum geçerli değil. Giriş yapılıyor...[/]")
        
    except Exception as e:
        console.print(f"[dim]   Oturum kontrolünde hata (pas geçiliyor): {e}[/]")

    # ─── Full Login Akışı ──────────────────────────────────────
    console.print(f"\n[bold cyan]🔐 Giriş yapılıyor: {config.SA_EMAIL}[/]")

    try:
        # Login sayfasına git
        await page.goto(config.LOGIN_URL, wait_until="load",
                        timeout=config.PAGE_LOAD_TIMEOUT)
        # ─── Email alanını bul ve doldur ───────────────────────
        email_selectors = [
            'label:has-text("Email") input',
            'input[type="email"]',
            'input[name="email"]',
            '#email',
            'input.V4evW',
        ]

        # ─── Login Formunu Bekle (Cloudflare vb. için) ──────────
        console.print("[dim]   ⏳ Login formu bekleniyor...[/]")
        email_input = None
        for i in range(300):
            # Loop heartbeat (her 10 denemede bir log at)
            if i > 0 and i % 10 == 0:
                console.print(f"[dim]      ({i}/300) Form aranıyor...[/]")

            # Email alanını bulmayı dene
            for selector in email_selectors:
                try:
                    email_input = await page.query_selector(selector)
                    if email_input and await email_input.is_visible():
                        break
                except:
                    continue
            
            if email_input:
                break
            
            # Global captcha çözücüyü çağır
            await check_and_solve_captcha(page)
            
            await page.wait_for_timeout(1000)

        if not email_input:
            console.print("[red]❌ Email alanı bulunamadı. "
                          "Site yapısı değişmiş olabilir veya Cloudflare aşılamadı.[/]")
            # Hata ekranının görüntüsünü alalım
            await page.screenshot(path="login_error.png")
            console.print("[dim]📸 Hata görüntüsü kaydedildi: login_error.png[/]")
            return False

        # İnsan gibi yavaş yaz
        await email_input.click()
        await page.wait_for_timeout(300)
        await email_input.fill("")  # Önce temizle
        await page.keyboard.type(config.SA_EMAIL, delay=80)

        console.print("[dim]   📧 Email girildi[/]")

        # ─── Şifre alanını bul ve doldur ──────────────────────
        password_selectors = [
            'input#signInPasswordField',
            '#signInPasswordField',
            'input[name="password"]',
            'input[type="password"]',
        ]

        password_input = None
        for selector in password_selectors:
            try:
                password_input = await page.wait_for_selector(selector, timeout=5000)
                if password_input:
                    break
            except Exception:
                continue

        if not password_input:
            console.print("[red]❌ Şifre alanı bulunamadı.[/]")
            return False

        await password_input.click()
        await page.wait_for_timeout(300)
        await password_input.fill("")
        await page.keyboard.type(config.SA_PASSWORD, delay=90)

        console.print("[dim]   🔑 Şifre girildi[/]")

        # ─── Giriş Butonuna Tıkla ───────────────────────────
        # "Sign in with Google" butonuna basmamak için kesin selector kullanıyoruz
        submit_selectors = [
            'button[type="submit"]',
            'button[data-test-id="sign-in-button"]',
            'button:text-is("Sign in")',
            'button:text-is("Sign In")',
        ]
        
        login_button = None
        for selector in submit_selectors:
            try:
                login_button = await page.query_selector(selector)
                if login_button:
                    break
            except Exception:
                continue
        
        if login_button:
            await login_button.click()
            console.print("[dim]   🖱️  Giriş butonuna tıklandı[/]")
        else:
            # Buton bulunamazsa Enter bas
            await page.keyboard.press("Enter")
            console.print("[dim]   ⌨️  Enter ile giriş denendi[/]")

        # ─── Captcha kontrolü ─────────────────────────────────
        console.print(
            "\n[bold yellow]⏳ Giriş işleniyor... "
            "(Captcha çıkarsa lütfen tarayıcıda manuel çözün)[/]"
        )

        # Captcha çıkıp çıkmadığını kontrol et
        captcha_timeout = 60  # 60 saniye boyunca captcha bekle
        for i in range(captcha_timeout):
            await page.wait_for_timeout(1000)

            # Captcha iframe'i kontrol et
            captcha_selectors = [
                'iframe[src*="captcha"]',
                'iframe[src*="hcaptcha"]',
                'iframe[src*="recaptcha"]',
                '[class*="captcha"]',
            ]

            captcha_found = False
            for selector in captcha_selectors:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        captcha_found = True
                        break
                except Exception:
                    continue

            if captcha_found and i == 0:
                console.print(
                    "\n[bold red]🤖 CAPTCHA TESPİT EDİLDİ![/]\n"
                    "[yellow]   Lütfen açık olan tarayıcıda Captcha'yı çözün.\n"
                    "   60 saniye bekleniyor...[/]"
                )
                continue

            # Giriş başarılı mı kontrol et
            current_url = page.url
            if "/login" not in current_url.lower() and "/account/login" not in current_url.lower():
                console.print(
                    f"\n[bold green]✅ Giriş başarılı![/] → {current_url}"
                )
                return True

        # Timeout - giriş yapılamadı
        console.print(
            "\n[bold red]❌ Giriş zaman aşımına uğradı. "
            "Email/şifre doğru mu kontrol edin.[/]"
        )
        return False

    except Exception as e:
        console.print(f"\n[bold red]❌ Giriş hatası: {e}[/]")
        return False
