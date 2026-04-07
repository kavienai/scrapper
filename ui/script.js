// Seeking Alpha Scraper Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    // Icons initialization
    lucide.createIcons();

    // Elements
    const symbolsInput = document.getElementById('symbols');
    const includeContentCheckbox = document.getElementById('includeContent');
    const maxArticlesSlider = document.getElementById('maxArticles');
    const articleValueDisplay = document.getElementById('articleValue');
    const startBtn = document.getElementById('startBtn');
    const logTerminal = document.getElementById('logTerminal');
    const clearLogsBtn = document.getElementById('clearLogs');
    const resultsList = document.getElementById('resultsList');

    let ws = null;

    // --- Article Slider ---
    maxArticlesSlider.addEventListener('input', (e) => {
        articleValueDisplay.textContent = e.target.value;
    });

    // --- WebSocket Connection ---
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        
        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            addLog(event.data);
        };

        ws.onclose = () => {
            console.log('WS Connection closed. Reconnecting...');
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (err) => {
            console.error('WS Error:', err);
        };
    }

    // --- Log Management ---
    function addLog(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        const timestamp = new Date().toLocaleTimeString([], { hour12: false });
        
        // Basic ANSI color handling (simplified)
        let processedMsg = message
            .replace(/\[\d+m/g, '') // Remove [m color codes
            .replace(/✅/g, '<span class="text-green-400">✅</span>')
            .replace(/❌/g, '<span class="text-red-400">❌</span>')
            .replace(/⚠️/g, '<span class="text-yellow-400">⚠️</span>')
            .replace(/🚀/g, '<span class="text-cyan-400">🚀</span>');

        entry.innerHTML = `<span class="text-gray-600 mr-2 text-[10px]">[${timestamp}]</span> ${processedMsg}`;
        
        logTerminal.appendChild(entry);
        logTerminal.scrollTop = logTerminal.scrollHeight;

        // Auto-refresh results if process finished
        if (message.includes('🏁') || message.includes('tamamlandı')) {
            fetchResults();
        }
    }

    clearLogsBtn.addEventListener('click', () => {
        logTerminal.innerHTML = '<div class="text-gray-600 mb-4 cursor">_</div>';
    });

    // --- API Calls ---
    async function startScrape() {
        const symbolsStr = symbolsInput.value.trim();
        if (!symbolsStr) {
            addLog('⚠️ Lütfen en az bir sembol girin (Örn: AAPL)', 'warning');
            return;
        }

        const symbols = symbolsStr.split(',').map(s => s.trim().toUpperCase());
        const includeContent = includeContentCheckbox.checked;
        const maxArticles = parseInt(maxArticlesSlider.value);

        startBtn.disabled = true;
        startBtn.innerHTML = '<i data-lucide="loader-2" class="animate-spin w-5 mr-2"></i> Çalışıyor...';
        lucide.createIcons();

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols, include_content: includeContent, max_articles: maxArticles })
            });

            if (response.ok) {
                addLog(`🚀 Görev kuyruğa eklendi: ${symbols.join(', ')}`);
            } else {
                addLog('❌ Görev başlatılamadı!', 'error');
            }
        } catch (err) {
            addLog(`❌ Hata: ${err.message}`, 'error');
        } finally {
            // Butonu bir süre sonra aktifleştir (veya iş bittiğinde log stream üzerinden yap)
            setTimeout(() => {
                startBtn.disabled = false;
                startBtn.innerHTML = '<i data-lucide="play" class="w-5 mr-2"></i> İşlemi Başlat';
                lucide.createIcons();
            }, 5000);
        }
    }

    async function fetchResults() {
        try {
            const response = await fetch('/api/results');
            const files = await response.json();

            if (files.length === 0) {
                resultsList.innerHTML = '<div class="text-center py-8 text-gray-500 italic text-sm">Henüz sonuç yok.</div>';
                return;
            }

            resultsList.innerHTML = files.map(file => `
                <div class="result-card flex items-center justify-between group">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center border border-white/5">
                            <i data-lucide="${file.name.endsWith('.json') ? 'file-json' : 'file-spreadsheet'}" class="w-4 text-gray-400"></i>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-200">${file.name}</p>
                            <p class="text-[10px] text-gray-500">${file.date} • ${file.size}</p>
                        </div>
                    </div>
                    <a href="/output/${file.name}" download class="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-cyan-600 transition-all">
                        <i data-lucide="download" class="w-4 text-white"></i>
                    </a>
                </div>
            `).join('');
            
            lucide.createIcons();
        } catch (err) {
            console.error('Fetch results error:', err);
        }
    }

    // --- Init ---
    startBtn.addEventListener('click', startScrape);
    connectWebSocket();
    fetchResults();
});
