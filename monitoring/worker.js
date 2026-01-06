/**
 * Modern Cloudflare Worker for Monitoring VPN Tools API
 * 
 * Features:
 * 1. Modern Dashboard: Real-time uptime counter (client-side), 5s polling for stats.
 * 2. Scheduled Alerts: Sends status to Telegram 4x a day (Cron Trigger).
 * 3. Uptime Checks: Alerts immediately if API is DOWN.
 */

const CONFIG = {
  API_URL: "http://api.vortex-xx.biz.id/stats", // Ganti dengan URL API Anda
  TELEGRAM_BOT_TOKEN: "YOUR_BOT_TOKEN",         // Token Bot Telegram
  TELEGRAM_CHAT_ID: "YOUR_CHAT_ID",             // ID Akun Telegram
  CHECK_INTERVAL_SECONDS: 300                   // Internal interval check (optional logic)
};

export default {
  async fetch(request, env, ctx) {
    // Serve the Dashboard HTML
    return new Response(renderDashboard(CONFIG.API_URL), {
      headers: { "Content-Type": "text/html" },
    });
  },

  async scheduled(event, env, ctx) {
    // 1. Always check health first
    let statusMsg = "";
    let isDown = false;
    let data = null;

    try {
      const response = await fetch(CONFIG.API_URL);
      if (!response.ok) {
        isDown = true;
        statusMsg = `⚠️ *DOWN ALERT*\nAPI returned status: ${response.status}`;
      } else {
        data = await response.json();
      }
    } catch (e) {
      isDown = true;
      statusMsg = `🚨 *CRITICAL ALERT*\nAPI Unreachable: ${e.message}`;
    }

    if (isDown) {
      await sendTelegramAlert(env, statusMsg);
      return;
    }

    // 2. Schedule Logic (4x Daily)
    // Cloudflare Cron usually runs on UTC. 
    // We want roughly 4x a day. Assuming cron trigger is set to every hour or specifically set in wrangler.toml.
    // Here we check the current hour to see if we should send a report.
    // Target: 00, 06, 12, 18 UTC.
    const hour = new Date().getUTCHours();
    const allowedHours = [0, 6, 12, 18]; 
    
    // NOTE: For this to work precisely, the Cron Trigger in Cloudflare Dashboard 
    // should be set to "0 * * * *" (Every hour) or specifically "0 0,6,12,18 * * *".
    // If set to "every hour", we filter here.
    if (allowedHours.includes(hour)) {
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
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: text, parse_mode: "Markdown" })
  });
}

function renderDashboard(apiUrl) {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Tools Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .glass { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2); }
        body { background: #0f172a; color: #e2e8f0; }
    </style>
</head>
<body class="min-h-screen p-6">
    <div class="max-w-4xl mx-auto space-y-6">
        <!-- Header -->
        <div class="flex justify-between items-center glass p-6 rounded-xl">
            <div>
                <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">System Monitor</h1>
                <p class="text-slate-400 text-sm">Real-time Dashboard</p>
            </div>
            <div id="status-badge" class="px-4 py-2 rounded-full font-bold text-sm bg-slate-700 text-slate-300 animate-pulse">
                CONNECTING...
            </div>
        </div>

        <!-- Main Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <!-- CPU -->
            <div class="glass p-4 rounded-xl">
                <h3 class="text-slate-400 text-xs uppercase tracking-wider">CPU Usage</h3>
                <div class="flex items-end gap-2 mt-2">
                    <span id="cpu-val" class="text-3xl font-bold">0</span><span class="text-lg text-slate-500">%</span>
                </div>
                <div class="w-full bg-slate-700 h-2 rounded-full mt-3 overflow-hidden">
                    <div id="cpu-bar" class="h-full bg-blue-500 transition-all duration-500" style="width: 0%"></div>
                </div>
            </div>

            <!-- RAM -->
            <div class="glass p-4 rounded-xl">
                <h3 class="text-slate-400 text-xs uppercase tracking-wider">RAM Usage</h3>
                <div class="flex items-end gap-2 mt-2">
                    <span id="ram-val" class="text-3xl font-bold">0</span><span class="text-lg text-slate-500">%</span>
                </div>
                <div class="w-full bg-slate-700 h-2 rounded-full mt-3 overflow-hidden">
                    <div id="ram-bar" class="h-full bg-purple-500 transition-all duration-500" style="width: 0%"></div>
                </div>
            </div>
            
             <!-- Disk -->
            <div class="glass p-4 rounded-xl">
                <h3 class="text-slate-400 text-xs uppercase tracking-wider">Storage</h3>
                <div class="flex items-end gap-2 mt-2">
                    <span id="disk-val" class="text-3xl font-bold">0</span><span class="text-lg text-slate-500">%</span>
                </div>
                <div class="w-full bg-slate-700 h-2 rounded-full mt-3 overflow-hidden">
                    <div id="disk-bar" class="h-full bg-orange-500 transition-all duration-500" style="width: 0%"></div>
                </div>
            </div>

            <!-- Uptime -->
            <div class="glass p-4 rounded-xl">
                <h3 class="text-slate-400 text-xs uppercase tracking-wider">System Uptime</h3>
                <div id="uptime-display" class="text-2xl font-mono mt-2 text-emerald-400">00:00:00</div>
                <div class="text-xs text-slate-500 mt-1">Auto-incrementing</div>
            </div>
        </div>
        
        <!-- Detailed Info -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
             <div class="glass p-6 rounded-xl">
                <h3 class="text-lg font-semibold mb-4 border-b border-slate-700 pb-2">Network Traffic</h3>
                <ul class="space-y-3 text-sm" id="traffic-list">
                    <li class="flex justify-between"><span>Total Requests</span> <span class="text-blue-300">...</span></li>
                </ul>
             </div>
             
             <div class="glass p-6 rounded-xl">
                <h3 class="text-lg font-semibold mb-4 border-b border-slate-700 pb-2">System Info</h3>
                 <ul class="space-y-3 text-sm">
                    <li class="flex justify-between"><span>RAM Used</span> <span id="ram-used" class="text-slate-300">...</span></li>
                    <li class="flex justify-between"><span>RAM Total</span> <span id="ram-total" class="text-slate-300">...</span></li>
                    <li class="flex justify-between"><span>Disk Used</span> <span id="disk-used" class="text-slate-300">...</span></li>
                    <li class="flex justify-between"><span>Disk Total</span> <span id="disk-total" class="text-slate-300">...</span></li>
                    <li class="flex justify-between"><span>Version</span> <span id="ver" class="text-slate-300">...</span></li>
                </ul>
             </div>
        </div>
    </div>

    <script>
        const API_URL = "${apiUrl}";
        let uptimeSeconds = 0;
        let isFetching = false;

        // --- Client Side Uptime Logic ---
        function formatUptime(totalSeconds) {
            const h = Math.floor(totalSeconds / 3600);
            const m = Math.floor((totalSeconds % 3600) / 60);
            const s = Math.floor(totalSeconds % 60);
            return \`\${String(h).padStart(2, '0')}:\${String(m).padStart(2, '0')}:\${String(s).padStart(2, '0')}\`;
        }

        setInterval(() => {
            if(uptimeSeconds > 0) {
                uptimeSeconds++;
                document.getElementById('uptime-display').innerText = formatUptime(uptimeSeconds);
            }
        }, 1000);

        // --- Data Fetching Logic (Every 5s) ---
        async function fetchStats() {
            if (isFetching) return;
            isFetching = true;
            
            try {
                const res = await fetch(API_URL);
                if(res.ok) {
                    const data = await res.json();
                    updateUI(data);
                } else {
                    setStatus(false, res.status);
                }
            } catch(e) {
                setStatus(false, "ERR");
            } finally {
                isFetching = false;
            }
        }

        function setStatus(isUp, code) {
            const el = document.getElementById('status-badge');
            if(isUp) {
                el.className = "px-4 py-2 rounded-full font-bold text-sm bg-emerald-500/20 text-emerald-400 border border-emerald-500/50";
                el.innerText = "ONLINE";
            } else {
                el.className = "px-4 py-2 rounded-full font-bold text-sm bg-red-500/20 text-red-400 border border-red-500/50";
                el.innerText = "OFFLINE (" + code + ")";
            }
        }

        function updateUI(data) {
            setStatus(true);
            
            // Sync Uptime (Correct drift)
            uptimeSeconds = Math.floor(data.uptime_seconds);

            // CPU & RAM
            document.getElementById('cpu-val').innerText = data.system.cpu_percent;
            document.getElementById('cpu-bar').style.width = data.system.cpu_percent + "%";
            
            document.getElementById('ram-val').innerText = data.system.ram_percent;
            document.getElementById('ram-bar').style.width = data.system.ram_percent + "%";
            
            // Disk
            if(data.system.disk_percent) {
                document.getElementById('disk-val').innerText = data.system.disk_percent;
                document.getElementById('disk-bar').style.width = data.system.disk_percent + "%";
                document.getElementById('disk-used').innerText = data.system.disk_used_gb + " GB";
                document.getElementById('disk-total').innerText = data.system.disk_total_gb + " GB";
            }

            // Details
            document.getElementById('ram-used').innerText = data.system.ram_used_mb + " MB";
            document.getElementById('ram-total').innerText = data.system.ram_total_mb + " MB";
            document.getElementById('ver').innerText = data.version;

            // Traffic
            let trafficHtml = "";
            for (const [key, val] of Object.entries(data.traffic)) {
                trafficHtml += \`<li class="flex justify-between uppercase text-xs tracking-wider"><span class="text-slate-400">\${key.replace('_requests','')}</span> <span class="font-mono text-blue-300">\${val}</span></li>\`;
            }
            document.getElementById('traffic-list').innerHTML = trafficHtml;
        }

        // Init
        fetchStats();
        setInterval(fetchStats, 5000);
    </script>
</body>
</html>
  `;
}
