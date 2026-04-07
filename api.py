import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Scraper bileşenlerini içe aktar
import scraper
import auth
from browser_manager import BrowserManager
import config

app = FastAPI(title="Seeking Alpha Scraper API")

# UI dosyaları için statik dizin
os.makedirs("ui", exist_ok=True)
app.mount("/static", StaticFiles(directory="ui"), name="static")

# Çıktı dosyaları için statik dizin
os.makedirs(config.OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR), name="output")

# ─── Log Yakalama ve WebSocket Yayını ──────────────────────────

from rich.console import Console
from rich.theme import Theme

class LogStream:
    """Terminal çıktılarını yakalayıp WebSocket'e gönderir."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop = asyncio.get_event_loop()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def broadcast_sync(self, message: str):
        """Senkron koddan çağrılabilen yayıncı."""
        if self.active_connections:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

log_stream = LogStream()

# Rich Console için özel Proxy
class WebConsoleWriter:
    def write(self, text):
        if text.strip():
            asyncio.create_task(log_stream.broadcast(text))
    
    def flush(self):
        """Rich Console bu metodu bekler."""
        pass

# Scraper ve Auth konsollarını yönlendir
custom_console = Console(file=WebConsoleWriter(), force_terminal=True, width=100)
scraper.console = custom_console
auth.console = custom_console

# ─── Modeller ──────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    symbols: List[str]
    include_content: bool = False
    max_articles: int = 5

# ─── Scraper Görevi ───────────────────────────────────────────

async def run_scraper_task(request: ScrapeRequest):
    await log_stream.broadcast(f"🚀 {', '.join(request.symbols)} için işlem başlatıldı...")
    
    async def ensure_login(bm: BrowserManager) -> bool:
        """
        auth.login() artık hem cookie yüklemeyi hem de aktif oturum kontrolünü merkezi olarak yapıyor.
        """
        success = await auth.login(bm.page, bm)
        if success:
            await bm.save_cookies()
        return success

    bm = BrowserManager()
    try:
        page = await bm.start(headless=True)
        if not await ensure_login(bm):
            await log_stream.broadcast("❌ Giriş başarısız!")
            return

        for symbol in request.symbols:
            await log_stream.broadcast(f"📊 {symbol} verileri çekiliyor...")
            
            # Özet
            await scraper.scrape_stock_summary(page, symbol)
            
            # Makaleler
            await scraper.scrape_latest_articles(
                page, symbol, 
                max_articles=request.max_articles,
                include_content=request.include_content
            )
            
            # Finansallar
            await scraper.scrape_financials(page, symbol)
            
            # Derecelendirmeler
            await scraper.scrape_ratings(page, symbol)
            
            await log_stream.broadcast(f"✅ {symbol} tamamlandı.")

    except Exception as e:
        await log_stream.broadcast(f"🚨 Hata oluştu: {str(e)}")
    finally:
        await bm.close()
        await log_stream.broadcast("🏁 İşlem sona erdi.")

# ─── API Endpoints ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("ui/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scraper_task, request)
    return {"message": "Scrape task started", "symbols": request.symbols}

@app.get("/api/results")
async def list_results():
    files = []
    if os.path.exists(config.OUTPUT_DIR):
        for f in os.listdir(config.OUTPUT_DIR):
            if f.endswith(('.json', '.csv')):
                stats = os.stat(os.path.join(config.OUTPUT_DIR, f))
                files.append({
                    "name": f,
                    "size": f"{stats.st_size / 1024:.1f} KB",
                    "date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
    return sorted(files, key=lambda x: x['date'], reverse=True)

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await log_stream.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_stream.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
