"""
Seeking Alpha Scraper - Veri Çekme (Scraper) Modülü
Giriş yaptıktan sonra istenilen verileri ayıklar.
"""
import asyncio
import json
import csv
import os
from datetime import datetime
from playwright.async_api import Page
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import config
from auth import check_and_solve_captcha

console = Console()


# ═══════════════════════════════════════════════════════════════
#  İNSAN BENZERİ DAVRANIŞLAR
# ═══════════════════════════════════════════════════════════════

async def human_like_scroll(page: Page):
    """Sayfayı insan gibi rastgele aşağı yukarı kaydırır."""
    if not config.HUMAN_SCROLL:
        return
        
    console.print("[dim]      🖱️  Sayfa okunuyor (scroll simülasyonu)...[/]")
    try:
        # Rastgele mesafelere kaydır
        import random
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(300, 800)
            await page.mouse.wheel(0, scroll_amount)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Bazen biraz yukarı geri çık
            if random.random() > 0.7:
                await page.mouse.wheel(0, -200)
                await asyncio.sleep(0.5)
                
        # Başlangıca veya makul bir yere geri dönme (isteğe bağlı)
        await asyncio.sleep(config.MIN_STAY_TIME)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  HİSSE BİLGİSİ ÇEK
# ═══════════════════════════════════════════════════════════════

async def scrape_stock_summary(page: Page, symbol: str) -> dict | None:
    """
    Bir hisse senedinin özet bilgilerini çeker.
    
    Args:
        page: Playwright sayfa nesnesi
        symbol: Hisse sembolü (Örn: AAPL, MSFT, TSLA)
    
    Returns:
        dict: Hisse bilgileri veya None
    """
    url = f"{config.BASE_URL}/symbol/{symbol.upper()}"
    console.print(f"\n[bold cyan]📊 {symbol.upper()} bilgileri çekiliyor...[/]")
    console.print(f"[dim]   URL: {url}[/]")

    try:
        await page.goto(url, wait_until="load",
                        timeout=config.PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Captcha kontrolü
        await check_and_solve_captcha(page)
        
        # Scroll simülasyonu
        await human_like_scroll(page)

        data = {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "url": url,
        }

        # ─── Fiyat Bilgisi ────────────────────────────────────
        price_selectors = [
            '[data-test-id="symbol-price"]',
            '[data-test-id="quote-price"]',
            '.symbol-page-header [class*="price"]',
            'span[class*="primaryPrice"]',
            'span[data-test-id="price"]',
        ]

        for selector in price_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and text[0].isdigit() or text.startswith("$"):
                        data["price"] = text
                        break
            except Exception:
                continue

        # ─── Fiyat Değişimi ───────────────────────────────────
        change_selectors = [
            '[data-test-id="symbol-change"]',
            '[data-test-id="quote-change"]',
            'span[class*="change"]',
        ]

        for selector in change_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        data["change"] = text
                        break
            except Exception:
                continue

        # ─── Piyasa Değeri ────────────────────────────────────
        market_cap_selectors = [
            '[data-test-id="market-cap"]',
            'td:has-text("Market Cap") + td',
        ]

        for selector in market_cap_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        data["market_cap"] = text
                        break
            except Exception:
                continue

        # ─── Genel sayfa metninden veri çıkarmayı dene ────────
        # Eğer belirli selectorlar çalışmazsa, tüm sayfadan metin al
        if "price" not in data:
            try:
                # Sayfadaki büyük yazıları tarıyoruz
                all_text = await page.inner_text("main")
                lines = [l.strip() for l in all_text.split("\n") if l.strip()]
                
                # İlk dolar işareti olan satırı bul
                for line in lines[:30]:
                    if "$" in line and any(c.isdigit() for c in line):
                        data["price_raw"] = line
                        break
            except Exception:
                pass

        # ─── Sayfa Başlığı ────────────────────────────────────
        try:
            title = await page.title()
            data["page_title"] = title
        except Exception:
            pass

        # ─── Sonuçları göster ─────────────────────────────────
        _display_stock_data(data)
        return data

    except Exception as e:
        console.print(f"[bold red]❌ {symbol} verisi çekilemedi: {e}[/]")
        return None


# ═══════════════════════════════════════════════════════════════
#  MAKALE BAŞLIKLARINI ÇEK
# ═══════════════════════════════════════════════════════════════

async def scrape_latest_articles(page: Page, symbol: str,
                                  max_articles: int = 10,
                                  include_content: bool = False) -> list[dict]:
    """
    Bir hisse için en son makaleleri çeker.
    
    Args:
        page: Playwright sayfa nesnesi
        symbol: Hisse sembolü
        max_articles: Çekilecek max makale sayısı
        include_content: Makale içeriklerini de çek? (yavaşlatır)
    
    Returns:
        list[dict]: Makale listesi
    """
    url = f"{config.BASE_URL}/symbol/{symbol.upper()}/analysis"
    console.print(
        f"\n[bold cyan]📰 {symbol.upper()} makaleleri çekiliyor...[/]"
    )

    try:
        await page.goto(url, wait_until="load",
                        timeout=config.PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Captcha kontrolü
        await check_and_solve_captcha(page)
        
        # Scroll simülasyonu
        await human_like_scroll(page)

        articles = []

        # Makale linklerini bul
        article_selectors = [
            'article a[data-test-id="post-list-item-title"]',
            'a[data-test-id="article-title-link"]',
            '[data-test-id="post-list"] a[href*="/article/"]',
            'a[href*="/article/"]',
        ]

        links = []
        for selector in article_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    links = elements
                    break
            except Exception:
                continue

        for i, link in enumerate(links[:max_articles]):
            try:
                title = (await link.inner_text()).strip()
                href = await link.get_attribute("href")

                if title and href:
                    article = {
                        "index": i + 1,
                        "title": title,
                        "url": f"{config.BASE_URL}{href}" if href.startswith("/") else href,
                    }
                    articles.append(article)
            except Exception:
                continue

        # İçerikleri de çek (ikinci adım)
        if include_content and articles:
            console.print(f"[dim]   ℹ️  {len(articles)} makalenin içeriği çekilecek...[/]")
            for article in articles:
                # Bot engeline takılmamak için bekle
                await asyncio.sleep(config.BETWEEN_REQUESTS)
                content = await scrape_article_content(page, article["url"])
                article["content"] = content

        # Tabloyu göster
        if articles:
            _display_articles(articles, symbol, show_content_preview=include_content)
        else:
            console.print("[yellow]⚠️  Makale bulunamadı. "
                          "Site yapısı değişmiş olabilir.[/]")

        return articles

    except Exception as e:
        console.print(f"[bold red]❌ Makale çekme hatası: {e}[/]")
        return []


# ═══════════════════════════════════════════════════════════════
#  MAKALE İÇERİĞİNİ ÇEK (Detay)
# ═══════════════════════════════════════════════════════════════

async def scrape_article_content(page: Page, url: str) -> str:
    """Tek bir makalenin içeriğini çeker."""
    console.print(f"[dim]      📄 İçerik çekiliyor: {url[:60]}...[/]")
    
    try:
        await page.goto(url, wait_until="load", timeout=config.PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Captcha kontrolü
        await check_and_solve_captcha(page)
        
        # Scroll simülasyonu
        await human_like_scroll(page)
        
        # İçerik konteynerını bul
        content_selectors = [
            '[data-test-id="article-content"]',
            '.article-body',
            'article section[class*="content"]',
            'div[class*="article-content"]',
        ]
        
        content_el = None
        for selector in content_selectors:
            content_el = await page.query_selector(selector)
            if content_el:
                break
        
        if not content_el:
            # Yedek: Makale ana bölümünü almayı dene
            content_el = await page.query_selector('article')
            
        if content_el:
            # Paragrafları ve listeleri al
            paragraphs = await content_el.query_selector_all('p, li')
            text_parts = []
            for p in paragraphs:
                txt = (await p.inner_text()).strip()
                if txt:
                    text_parts.append(txt)
            
            return "\n\n".join(text_parts)
        
        return "İçerik bulunamadı."
        
    except Exception as e:
        return f"Hata: {str(e)}"


# ═══════════════════════════════════════════════════════════════
#  FİNANSAL VERİLERİ ÇEK (Gelir Tablosu vb.)
# ═══════════════════════════════════════════════════════════════

async def scrape_financials(page: Page, symbol: str) -> dict | None:
    """
    Bir hissenin temel finansal verilerini çeker.
    (EPS, P/E, Dividend Yield, Revenue vb.)
    """
    url = f"{config.BASE_URL}/symbol/{symbol.upper()}/valuation/metrics"
    console.print(
        f"\n[bold cyan]💰 {symbol.upper()} finansal verileri çekiliyor...[/]"
    )

    try:
        await page.goto(url, wait_until="load",
                        timeout=config.PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Captcha kontrolü
        await check_and_solve_captcha(page)
        
        # Scroll simülasyonu
        await human_like_scroll(page)

        financials = {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
        }

        # Tablodaki satırları çek
        try:
            rows = await page.query_selector_all("table tbody tr")
            for row in rows[:20]:  # İlk 20 satır
                cells = await row.query_selector_all("td")
                if len(cells) >= 2:
                    label = (await cells[0].inner_text()).strip()
                    value = (await cells[1].inner_text()).strip()
                    if label and value:
                        financials["metrics"][label] = value
        except Exception:
            pass

        if financials["metrics"]:
            _display_financials(financials)
        else:
            console.print("[yellow]⚠️  Finansal veri bulunamadı. "
                          "Premium üyelik gerekebilir.[/]")

        return financials

    except Exception as e:
        console.print(f"[bold red]❌ Finansal veri hatası: {e}[/]")
        return None


# ═══════════════════════════════════════════════════════════════
#  ANALİST DERECELENDİRMELERİ
# ═══════════════════════════════════════════════════════════════

async def scrape_ratings(page: Page, symbol: str) -> dict | None:
    """
    Seeking Alpha'nın hisse derecelendirmelerini çeker.
    (Quant Rating, SA Authors, Wall Street vb.)
    """
    url = f"{config.BASE_URL}/symbol/{symbol.upper()}"
    console.print(
        f"\n[bold cyan]⭐ {symbol.upper()} derecelendirmeleri çekiliyor...[/]"
    )

    try:
        await page.goto(url, wait_until="load",
                        timeout=config.PAGE_LOAD_TIMEOUT)
        await page.wait_for_timeout(3000)
        
        # Captcha kontrolü
        await check_and_solve_captcha(page)
        
        # Scroll simülasyonu
        await human_like_scroll(page)

        ratings = {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "ratings": {},
        }

        # Rating kartlarını bul
        rating_selectors = [
            '[data-test-id="rating-card"]',
            '[class*="ratingCard"]',
            '[class*="rating"]',
        ]

        for selector in rating_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    text = (await el.inner_text()).strip()
                    if text:
                        lines = text.split("\n")
                        if len(lines) >= 2:
                            ratings["ratings"][lines[0].strip()] = lines[1].strip()
            except Exception:
                continue

        if ratings["ratings"]:
            _display_ratings(ratings)

        return ratings

    except Exception as e:
        console.print(f"[bold red]❌ Derecelendirme hatası: {e}[/]")
        return None


# ═══════════════════════════════════════════════════════════════
#  VERİ KAYDETME
# ═══════════════════════════════════════════════════════════════

def save_to_json(data: dict | list, filename: str):
    """Veriyi JSON dosyasına kaydet."""
    filepath = os.path.join(config.OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"[green]💾 JSON kaydedildi → {filepath}[/]")


def save_to_csv(data: list[dict], filename: str):
    """Veriyi CSV dosyasına kaydet."""
    if not data:
        return

    filepath = os.path.join(config.OUTPUT_DIR, filename)
    keys = data[0].keys()

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    console.print(f"[green]💾 CSV kaydedildi → {filepath}[/]")


# ═══════════════════════════════════════════════════════════════
#  GÖRÜNTÜLEME (Rich Table)
# ═══════════════════════════════════════════════════════════════

def _display_stock_data(data: dict):
    """Hisse verilerini güzel bir tablo olarak göster."""
    table = Table(
        title=f"📊 {data.get('symbol', '???')} Özet",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
    )
    table.add_column("Alan", style="bold white", width=20)
    table.add_column("Değer", style="green", width=30)

    display_keys = {
        "price": "💵 Fiyat",
        "change": "📈 Değişim",
        "market_cap": "🏢 Piyasa Değeri",
        "price_raw": "💵 Ham Fiyat",
        "page_title": "📄 Sayfa Başlığı",
    }

    for key, label in display_keys.items():
        if key in data:
            table.add_row(label, str(data[key]))

    console.print(table)


def _display_articles(articles: list[dict], symbol: str, show_content_preview: bool = False):
    """Makaleleri güzel bir tablo olarak göster."""
    table = Table(
        title=f"📰 {symbol.upper()} Son Makaleler",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Başlık", style="white", width=60)
    
    if show_content_preview:
        table.add_column("İçerik Önizleme", style="italic", width=50)
    else:
        table.add_column("URL", style="dim cyan", width=40)

    for article in articles:
        if show_content_preview:
            content = article.get("content", "Yok")
            preview = (content[:50] + "...") if len(content) > 50 else content
            table.add_row(
                str(article["index"]),
                article["title"][:60],
                preview,
            )
        else:
            table.add_row(
                str(article["index"]),
                article["title"][:60],
                article["url"][:40] + "...",
            )

    console.print(table)


def _display_financials(data: dict):
    """Finansal verileri güzel bir tablo olarak göster."""
    table = Table(
        title=f"💰 {data['symbol']} Finansal Metrikler",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
    )
    table.add_column("Metrik", style="bold white", width=30)
    table.add_column("Değer", style="green", width=20)

    for label, value in data["metrics"].items():
        table.add_row(label, value)

    console.print(table)


def _display_ratings(data: dict):
    """Derecelendirmeleri güzel bir tablo olarak göster."""
    table = Table(
        title=f"⭐ {data['symbol']} Derecelendirmeler",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
    )
    table.add_column("Kaynak", style="bold white", width=25)
    table.add_column("Derece", style="green", width=20)

    for source, rating in data["ratings"].items():
        table.add_row(source, rating)

    console.print(table)
