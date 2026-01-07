/**
 * Premium Cloudflare Worker for Monitoring VPN Tools API
 * 
 * Features:
 * 1. SSR Dashboard: Fast initial load with server-side data.
 * 2. Smart Proxy: Bypasses Mixed Content and CORS issues.
 * 3. Resilience: 3-Strike rule before showing offline.
 * 4. Scheduled Alerts: Telegram notifications.
 */

const CONFIG = {
  API_URL: "http://api.vortex-xx.biz.id/stats", // Target API
  TELEGRAM_BOT_TOKEN: "YOUR_BOT_TOKEN",         // Telegram Token
  TELEGRAM_CHAT_ID: "YOUR_CHAT_ID",             // Telegram Chat ID
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // --- ROUTE 1: Proxy for Client-Side Polling ---
    if (url.pathname === "/api-proxy") {
      try {
        const apiResponse = await fetch(CONFIG.API_URL, {
          headers: { "User-Agent": "VPN-Monitor-Worker/2.0" }
        });
        const data = await apiResponse.json();
        return new Response(JSON.stringify(data), {
          headers: { 
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
          },
          status: apiResponse.status
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { 
          status: 502,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
        });
      }
    }

    // --- ROUTE 2: Main Dashboard (SSR) ---
    let initialData = null;
    let ssrError = null;

    try {
      const response = await fetch(CONFIG.API_URL, {
        headers: { "User-Agent": "VPN-Monitor-Worker/2.0" }
      });
      if (response.ok) {
        initialData = await response.json();
      } else {
        ssrError = `Status ${response.status}`;
      }
    } catch (e) {
      ssrError = e.message;
    }

    const proxyUrl = url.origin + "/api-proxy";
    return new Response(renderDashboard(initialData, ssrError, proxyUrl), {
      headers: { "Content-Type": "text/html" },
    });
  },

  async scheduled(event, env, ctx) {
    // Scheduled logic remains the same (4x daily + alerts)
    let isDown = false;
    let data = null;

    try {
      const response = await fetch(CONFIG.API_URL, {
        headers: { "User-Agent": "VPN-Monitor-Bot/2.0" }
      });
      if (!response.ok) isDown = true;
      else data = await response.json();
    } catch (e) {
      isDown = true;
    }

    if (isDown) {
      await sendTelegramAlert(env, "⚠️ *MONITOR ALERT*: API is Unreachable!");
      return;
    }

    const hour = new Date().getUTCHours();
    if ([0, 6, 12, 18].includes(hour)) {
      const report = `📊 *Daily Report (Hour ${hour})*\n` +
                     `✅ Status: Operational\n` +
                     `⏱️ Uptime: ${data.uptime_human}\n` +
                     `💻 CPU: ${data.system.cpu_percent}%\n` +
                     `🧠 RAM: ${data.system.ram_percent}%`;
      await sendTelegramAlert(env, report);
    }
  }
};

async function sendTelegramAlert(env, text) {
  const token = env.TELEGRAM_BOT_TOKEN || CONFIG.TELEGRAM_BOT_TOKEN;
  const chatId = env.TELEGRAM_CHAT_ID || CONFIG.TELEGRAM_CHAT_ID;
  if(!token || !chatId) return;
  
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: text, parse_mode: "Markdown" })
  });
}

function renderDashboard(initialData, ssrError, proxyUrl) {
  const jsonPayload = initialData ? JSON.stringify(initialData) : "null";
  
  return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body { 
            background: radial-gradient(circle at top center, #1e293b, #0f172a); 
            color: #f8fafc; 
            font-family: 'Inter', sans-serif; 
        }
        .glass { 
            background: rgba(255, 255, 255, 0.03); 
            backdrop-filter: blur(16px); 
            border: 1px solid rgba(255, 255, 255, 0.05); 
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }
        .animate-fade-in { animation: fadeIn 0.5s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .bar-transition { transition: width 1s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.5s; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8 flex items-center justify-center">
    <div class="max-w-6xl w-full space-y-6 animate-fade-in">
        
        <!-- Navbar -->
        <div class="glass rounded-2xl p-6 flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center text-blue-400">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                </div>
                <div>
                    <h1 class="text-2xl font-bold tracking-tight">VPN Tools Monitor</h1>
                    <p class="text-slate-400 text-xs font-mono tracking-widest uppercase">Live Infrastructure Dashboard</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <span id="last-updated" class="text-xs text-slate-500 font-mono hidden md:block">Syncing...</span>
                <div id="status-pill" class="px-4 py-1.5 rounded-full text-xs font-bold bg-slate-800 text-slate-500 border border-slate-700 transition-all duration-300">
                    CONNECTING
                </div>
            </div>
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <!-- CPU Card -->
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition duration-500"></div>
                <div class="relative z-10">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-wider">CPU Load</h3>
                        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    </div>
                    <div class="flex items-baseline gap-1">
                        <span id="cpu-val" class="text-4xl font-extrabold">0</span>
                        <span class="text-sm text-slate-500 font-bold">%</span>
                    </div>
                    <div class="w-full bg-slate-800/50 h-2 rounded-full mt-4 overflow-hidden">
                        <div id="cpu-bar" class="h-full bg-blue-500 bar-transition" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <!-- RAM Card -->
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute inset-0 bg-purple-500/5 opacity-0 group-hover:opacity-100 transition duration-500"></div>
                <div class="relative z-10">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-wider">Memory</h3>
                        <svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
                    </div>
                    <div class="flex items-baseline gap-1">
                        <span id="ram-val" class="text-4xl font-extrabold">0</span>
                        <span class="text-sm text-slate-500 font-bold">%</span>
                    </div>
                    <div class="w-full bg-slate-800/50 h-2 rounded-full mt-4 overflow-hidden">
                        <div id="ram-bar" class="h-full bg-purple-500 bar-transition" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <!-- Disk Card -->
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute inset-0 bg-orange-500/5 opacity-0 group-hover:opacity-100 transition duration-500"></div>
                <div class="relative z-10">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-wider">Storage</h3>
                        <svg class="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                    </div>
                    <div class="flex items-baseline gap-1">
                        <span id="disk-val" class="text-4xl font-extrabold">0</span>
                        <span class="text-sm text-slate-500 font-bold">%</span>
                    </div>
                    <div class="w-full bg-slate-800/50 h-2 rounded-full mt-4 overflow-hidden">
                        <div id="disk-bar" class="h-full bg-orange-500 bar-transition" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <!-- Uptime Card -->
            <div class="glass p-6 rounded-2xl relative overflow-hidden group">
                <div class="absolute inset-0 bg-emerald-500/5 opacity-0 group-hover:opacity-100 transition duration-500"></div>
                <div class="relative z-10">
                    <div class="flex justify-between items-start mb-4">
                        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-wider">Uptime</h3>
                        <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_#10b981]"></div>
                    </div>
                    <div id="uptime-display" class="text-3xl font-mono font-bold text-emerald-400 tracking-tight mt-1">
                        00:00:00
                    </div>
                    <div class="text-xs text-slate-500 mt-3 flex items-center gap-1">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        Synced
                    </div>
                </div>
            </div>
        </div>

        <!-- Detail Sections -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Traffic Stats -->
            <div class="glass p-6 rounded-2xl lg:col-span-2">
                <h3 class="text-sm font-bold text-slate-300 mb-6 flex items-center gap-2 border-b border-slate-700/50 pb-4">
                    TRAFFIC ANALYTICS
                </h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4" id="traffic-grid">
                    <!-- Dynamic Content -->
                </div>
            </div>

            <!-- System Info -->
            <div class="glass p-6 rounded-2xl">
                <h3 class="text-sm font-bold text-slate-300 mb-6 flex items-center gap-2 border-b border-slate-700/50 pb-4">
                    SYSTEM HEALTH
                </h3>
                <ul class="space-y-4 text-sm">
                    <li class="flex justify-between">
                        <span class="text-slate-500">RAM Usage</span>
                        <span class="font-mono text-slate-300"><span id="ram-used">0</span> MB</span>
                    </li>
                    <li class="flex justify-between">
                        <span class="text-slate-500">Total Memory</span>
                        <span class="font-mono text-slate-300"><span id="ram-total">0</span> MB</span>
                    </li>
                    <li class="flex justify-between">
                        <span class="text-slate-500">Disk Used</span>
                        <span class="font-mono text-slate-300"><span id="disk-used">0</span> GB</span>
                    </li>
                    <li class="flex justify-between pt-2 border-t border-slate-700/50">
                        <span class="text-slate-500">Version</span>
                        <span id="ver" class="px-2 py-0.5 rounded-md bg-slate-800 text-xs font-mono text-blue-400">v0.0.0</span>
                    </li>
                </ul>
            </div>
        </div>

    </div>

    <script>
        // Configuration
        const POLLING_INTERVAL = 10000; // 10s (Reduced load)
        const STRIKE_LIMIT = 3;         // Failures before showing OFFLINE
        const API_PROXY = "${proxyUrl}";
        const INITIAL = ${jsonPayload};

        // State
        let uptimeSec = 0;
        let strikes = 0;
        let isUpdating = false;

        function init() {
            if (INITIAL) {
                render(INITIAL);
                setOnline(true);
            } else {
                setOnline(false, "INIT_FAIL");
            }

            // Start Loops
            setInterval(tickUptime, 1000);
            setInterval(fetchData, POLLING_INTERVAL);
        }

        async function fetchData() {
            if (isUpdating) return;
            isUpdating = true;

            try {
                const res = await fetch(API_PROXY);
                if (res.ok) {
                    const data = await res.json();
                    render(data);
                    
                    // Success resets strikes
                    if (strikes > 0) {
                        strikes = 0;
                        setOnline(true);
                    }
                } else {
                    handleFail(res.status);
                }
            } catch (e) {
                handleFail("NET_ERR");
            } finally {
                isUpdating = false;
            }
        }

        function handleFail(reason) {
            strikes++;
            console.warn(\`Fetch failed (\${strikes}/\${STRIKE_LIMIT}). Reason: \${reason}\`);
            
            if (strikes >= STRIKE_LIMIT) {
                setOnline(false, reason);
            }
        }

        function setOnline(isOnline, msg) {
            const badge = document.getElementById('status-pill');
            if (isOnline) {
                badge.className = "px-4 py-1.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all duration-500";
                badge.innerText = "SYSTEM ONLINE";
            } else {
                badge.className = "px-4 py-1.5 rounded-full text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/20 transition-all duration-500";
                badge.innerText = "OFFLINE " + (msg ? \`(\${msg})\` : "");
            }
        }

        function render(data) {
            // Update timestamp
            const now = new Date();
            document.getElementById('last-updated').innerText = now.toLocaleTimeString();

            // Sync uptime
            uptimeSec = Math.floor(data.uptime_seconds);

            // Metrics
            updateBar('cpu', data.system.cpu_percent);
            updateBar('ram', data.system.ram_percent);
            
            if(data.system.disk_percent !== undefined) {
                updateBar('disk', data.system.disk_percent);
                document.getElementById('disk-used').innerText = data.system.disk_used_gb;
            }

            // Info
            document.getElementById('ram-used').innerText = data.system.ram_used_mb;
            document.getElementById('ram-total').innerText = data.system.ram_total_mb;
            document.getElementById('ver').innerText = data.version;

            // Traffic Grid
            const grid = document.getElementById('traffic-grid');
            let html = "";
            for (const [k, v] of Object.entries(data.traffic)) {
                if(k === 'total_requests') continue;
                html += \`
                <div class="bg-slate-800/40 p-3 rounded-xl border border-slate-700/30">
                    <div class="text-[10px] uppercase text-slate-500 font-bold tracking-wider mb-1">\${k.replace('_requests', '')}</div>
                    <div class="font-mono text-xl text-blue-300">\${v}</div>
                </div>\`;
            }
            grid.innerHTML = html;
        }

        function updateBar(id, val) {
            const elVal = document.getElementById(id + '-val');
            const elBar = document.getElementById(id + '-bar');
            
            if(elVal) elVal.innerText = val;
            if(elBar) {
                elBar.style.width = val + "%";
                // Color logic
                elBar.className = \`h-full bar-transition \${val > 80 ? 'bg-red-500 shadow-[0_0_10px_#ef4444]' : val > 60 ? 'bg-orange-500' : id === 'ram' ? 'bg-purple-500' : id === 'disk' ? 'bg-orange-500' : 'bg-blue-500'}\`;
            }
        }

        function tickUptime() {
            if(uptimeSec > 0) {
                uptimeSec++;
                const h = Math.floor(uptimeSec / 3600);
                const m = Math.floor((uptimeSec % 3600) / 60);
                const s = Math.floor(uptimeSec % 60);
                const fmt = \`\${String(h).padStart(2,'0')}:\${String(m).padStart(2,'0')}:\${String(s).padStart(2,'0')}\`;
                document.getElementById('uptime-display').innerText = fmt;
            }
        }

        // Init
        init();
    </script>
</body>
</html>
  `;
}
