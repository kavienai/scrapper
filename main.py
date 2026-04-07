"""
╔══════════════════════════════════════════════════════════════╗
║          SEEKING ALPHA SCRAPER - Ana Uygulama                ║
║                                                              ║
║  Kullanım:                                                   ║
║    python main.py                      → İnteraktif menü     ║
║    python main.py --symbol AAPL        → Tek hisse çek       ║
║    python main.py --symbols AAPL,MSFT  → Çoklu hisse çek     ║
║    python main.py --articles TSLA      → Makaleleri çek       ║
║    python main.py --all AAPL           → Tüm verileri çek     ║
╚══════════════════════════════════════════════════════════════╝
"""
import asyncio
import argparse
import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.markdown import Markdown

from browser_manager import BrowserManager
from auth import login, is_logged_in
from scraper import (
    scrape_stock_summary,
    scrape_latest_articles,
    scrape_financials,
    scrape_ratings,
    save_to_json,
    save_to_csv,
)
import config

console = Console()


# ═══════════════════════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════════════════════

BANNER = """
[bold cyan]
 ███████╗ █████╗     ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗ 
 ██╔════╝██╔══██╗    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
 ███████╗███████║    ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
 ╚════██║██╔══██║    ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
 ███████║██║  ██║    ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
 ╚══════╝╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
[/]
[dim]Seeking Alpha Veri Çekme Aracı v1.0[/]
"""


# ═══════════════════════════════════════════════════════════════
#  GİRİŞ YAP (Cookie kontrolü ile)
# ═══════════════════════════════════════════════════════════════

async def ensure_login(bm: BrowserManager) -> bool:
    """
    auth.login() artık hem cookie yüklemeyi hem de aktif oturum kontrolünü merkezi olarak yapıyor.
    """
    success = await login(bm.page, bm)
    if success:
        await bm.save_cookies()
    return success


# ═══════════════════════════════════════════════════════════════
#  İNTERAKTİF MENÜ
# ═══════════════════════════════════════════════════════════════

async def interactive_menu(bm: BrowserManager):
    """Kullanıcıya interaktif bir menü sunar."""
    while True:
        console.print("\n")
        console.print(Panel(
            "[bold white]1.[/] 📊 Hisse özeti çek\n"
            "[bold white]2.[/] 📰 Son makaleleri çek\n"
            "[bold white]3.[/] 💰 Finansal verileri çek\n"
            "[bold white]4.[/] ⭐ Derecelendirmeleri çek\n"
            "[bold white]5.[/] 🔄 Tüm verileri çek (hepsi)\n"
            "[bold white]6.[/] 📋 Birden fazla hisse çek\n"
            "[bold white]0.[/] 🚪 Çıkış",
            title="[bold cyan]📋 Menü[/]",
            border_style="cyan",
        ))

        choice = Prompt.ask(
            "[bold yellow]Seçiminiz[/]",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="1",
        )

        if choice == "0":
            console.print("[dim]👋 Çıkılıyor...[/]")
            break

        if choice == "6":
            symbols_input = Prompt.ask(
                "[bold yellow]Hisse sembolleri (virgülle ayırın)[/]",
                default="AAPL,MSFT,GOOGL",
            )
            symbols = [s.strip().upper() for s in symbols_input.split(",")]
        else:
            symbol = Prompt.ask(
                "[bold yellow]Hisse sembolü[/]",
                default="AAPL",
            )
            symbols = [symbol.upper()]

        # İçerik de çekilsin mi?
        include_content = False
        if choice in ("2", "5", "6"):
            include_content = Confirm.ask(
                "[bold yellow]Makale içerikleri de çekilsin mi? (Yavaşlatır)[/]",
                default=False
            )

        all_results = []

        for sym in symbols:
            if choice in ("1", "5", "6"):
                result = await scrape_stock_summary(bm.page, sym)
                if result:
                    all_results.append(result)

            if choice in ("2", "5"):
                articles = await scrape_latest_articles(
                    bm.page, sym, include_content=include_content
                )
                if articles:
                    save_to_json(
                        articles,
                        f"{sym}_articles_{datetime.now():%Y%m%d_%H%M}.json",
                    )

            if choice in ("3", "5"):
                financials = await scrape_financials(bm.page, sym)
                if financials:
                    save_to_json(
                        financials,
                        f"{sym}_financials_{datetime.now():%Y%m%d_%H%M}.json",
                    )

            if choice in ("4", "5"):
                ratings = await scrape_ratings(bm.page, sym)
                if ratings:
                    save_to_json(
                        ratings,
                        f"{sym}_ratings_{datetime.now():%Y%m%d_%H%M}.json",
                    )

            # Hızlı istek atıp yakalanmamak için bekle
            if len(symbols) > 1:
                console.print(
                    f"[dim]⏳ Sonraki hisse için "
                    f"{config.BETWEEN_REQUESTS}s bekleniyor...[/]"
                )
                await asyncio.sleep(config.BETWEEN_REQUESTS)

        # Toplu sonuçları kaydet
        if all_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            save_to_json(all_results, f"stocks_{timestamp}.json")

            if len(all_results) > 1:
                save_to_csv(all_results, f"stocks_{timestamp}.csv")


# ═══════════════════════════════════════════════════════════════
#  KOMUT SATIRI ARGÜMANLARI
# ═══════════════════════════════════════════════════════════════

def parse_args():
    """Komut satırı argümanlarını ayrıştır."""
    parser = argparse.ArgumentParser(
        description="Seeking Alpha Web Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python main.py                        İnteraktif menü
  python main.py --symbol AAPL          Tek hisse özeti
  python main.py --symbols AAPL,MSFT    Çoklu hisse
  python main.py --articles TSLA        TSLA makaleleri
  python main.py --all AAPL             AAPL tüm veriler
        """,
    )

    parser.add_argument("--symbol", "-s", type=str, help="Tek hisse sembolü")
    parser.add_argument(
        "--symbols", "-S", type=str, help="Virgülle ayrılmış hisse sembolleri"
    )
    parser.add_argument(
        "--articles", "-a", type=str, help="Makaleleri çekilecek hisse"
    )
    parser.add_argument(
        "--financials", "-f", type=str, help="Finansal verileri çekilecek hisse"
    )
    parser.add_argument(
        "--all", "-A", type=str, help="Tüm verileri çekilecek hisse"
    )
    parser.add_argument(
        "--content", "-C", action="store_true",
        help="Makale içeriklerini de çek"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Tarayıcıyı görünmez modda çalıştır"
    )

    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════
#  ANA FONKSİYON
# ═══════════════════════════════════════════════════════════════

async def main():
    """Ana uygulama akışı."""
    args = parse_args()

    # Headless mod argümanla override edilebilir
    if args.headless:
        config.HEADLESS = True

    console.print(BANNER)
    console.print(
        Panel(
            f"[dim]📅 {datetime.now():%d.%m.%Y %H:%M}\n"
            f"📧 Hesap: {config.SA_EMAIL or '(ayarlanmamış)'}\n"
            f"🖥️  Mod: {'Görünmez' if config.HEADLESS else 'Görünür'} Tarayıcı[/]",
            title="[bold cyan]Oturum Bilgisi[/]",
            border_style="dim",
        )
    )

    bm = BrowserManager()

    try:
        await bm.start()

        # Giriş yap
        logged_in = await ensure_login(bm)
        if not logged_in:
            console.print(
                "\n[bold red]❌ Giriş yapılamadı. "
                "Lütfen .env dosyasındaki bilgileri kontrol edin.[/]"
            )
            return

        # ─── Komut satırı modu ────────────────────────────────
        if args.symbol:
            result = await scrape_stock_summary(bm.page, args.symbol)
            if result:
                save_to_json(result, f"{args.symbol.upper()}_summary.json")

        elif args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(",")]
            results = []
            for sym in symbols:
                result = await scrape_stock_summary(bm.page, sym)
                if result:
                    results.append(result)
                await asyncio.sleep(config.BETWEEN_REQUESTS)
            if results:
                save_to_json(results, "multi_stocks.json")
                save_to_csv(results, "multi_stocks.csv")

        elif args.articles:
            articles = await scrape_latest_articles(
                bm.page, args.articles, include_content=args.content
            )
            if articles:
                save_to_json(articles, f"{args.articles.upper()}_articles.json")

        elif args.financials:
            financials = await scrape_financials(bm.page, args.financials)
            if financials:
                save_to_json(
                    financials, f"{args.financials.upper()}_financials.json"
                )

        elif args.all:
            sym = args.all.upper()
            console.print(f"\n[bold cyan]🔄 {sym} için tüm veriler çekiliyor...[/]")

            summary = await scrape_stock_summary(bm.page, sym)
            articles = await scrape_latest_articles(
                bm.page, sym, include_content=args.content
            )
            financials = await scrape_financials(bm.page, sym)
            ratings = await scrape_ratings(bm.page, sym)

            all_data = {
                "symbol": sym,
                "timestamp": datetime.now().isoformat(),
                "summary": summary,
                "articles": articles,
                "financials": financials,
                "ratings": ratings,
            }
            save_to_json(all_data, f"{sym}_complete.json")

        else:
            # İnteraktif menü
            await interactive_menu(bm)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  İşlem kullanıcı tarafından iptal edildi.[/]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Beklenmeyen hata: {e}[/]")
        import traceback
        traceback.print_exc()
    finally:
        await bm.close()
        console.print("\n[bold green]✅ Program sonlandı.[/]")


if __name__ == "__main__":
    asyncio.run(main())
