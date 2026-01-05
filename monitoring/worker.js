/**
 * Cloudflare Worker for Monitoring VPN Tools API
 * 
 * Features:
 * 1. Status Page: Visit the Worker URL to see system stats.
 * 2. Uptime Check: Setup a Cron Trigger to check health and alert Telegram on failure.
 * 
 * Config:
 * Edit the constants below or use Wrangler secrets.
 */

const CONFIG = {
  API_URL: "http://api.vortex-xx.biz.id/stats", // Ganti dengan URL API Anda
  TELEGRAM_BOT_TOKEN: 8226873424:AAHpLcqrc2hgEXo1SV7DRbenjJH9dxa0YQc,         // Token Bot Telegram untuk Alert
  TELEGRAM_CHAT_ID: 5361605327,             // ID Akun Telegram Anda untuk terima alert
  ALERT_THRESHOLD_MS: 5000                      // Alert jika latency > 5 detik
};

export default {
  async fetch(request, env, ctx) {
    // 1. Status Page Logic
    try {
      const start = Date.now();
      const response = await fetch(CONFIG.API_URL, {
        headers: { "User-Agent": "CF-Monitor/1.0" }
      });
      const latency = Date.now() - start;

      if (response.ok) {
        const data = await response.json();
        return new Response(renderSuccess(data, latency), {
          headers: { "Content-Type": "text/html" },
        });
      } else {
        return new Response(renderError(response.status, latency), {
          headers: { "Content-Type": "text/html" },
        });
      }
    } catch (e) {
      return new Response(renderError(e.message, 0), {
        headers: { "Content-Type": "text/html" },
      });
    }
  },

  async scheduled(event, env, ctx) {
    // 2. Cron Job Logic (Scheduled Monitoring)
    try {
      const response = await fetch(CONFIG.API_URL);
      if (!response.ok) {
        await sendTelegramAlert(env, `⚠️ *DOWN ALERT*\nVPN API returned status: ${response.status}`);
      }
    } catch (e) {
      await sendTelegramAlert(env, `🚨 *CRITICAL ALERT*\nVPN API Unreachable!\nError: ${e.message}`);
    }
  }
};

// Helper: Send Telegram Message
async function sendTelegramAlert(env, text) {
  const token = env.TELEGRAM_BOT_TOKEN || CONFIG.TELEGRAM_BOT_TOKEN;
  const chatId = env.TELEGRAM_CHAT_ID || CONFIG.TELEGRAM_CHAT_ID;
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  
  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown"
    })
  });
}

// Helper: Render HTML Success Page
function renderSuccess(data, latency) {
  return `
  <!DOCTYPE html>
  <html>
  <head>
    <title>API Status: Operational</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: -apple-system, sans-serif; background: #f0fdf4; color: #166534; padding: 2rem; }
      .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); max-width: 600px; margin: 0 auto; }
      .status { font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem; color: #15803d; }
      .metric { margin: 0.5rem 0; font-size: 1.1rem; }
      pre { background: #f3f4f6; padding: 1rem; border-radius: 8px; overflow-x: auto; color: #333; font-size: 0.9rem; }
    </style>
  </head>
  <body>
    <div class="card">
      <div class="status">✅ System Operational</div>
      <div class="metric">⏱️ Latency: ${latency}ms</div>
      <div class="metric">⏳ Uptime: ${data.uptime_human}</div>
      <div class="metric">💻 CPU: ${data.system.cpu_percent}%</div>
      <div class="metric">🧠 RAM: ${data.system.ram_percent}%</div>
      <br>
      <strong>Traffic Stats:</strong>
      <pre>${JSON.stringify(data.traffic, null, 2)}</pre>
    </div>
  </body>
  </html>
  `;
}

// Helper: Render HTML Error Page
function renderError(error, latency) {
  return `
  <!DOCTYPE html>
  <html>
  <head>
    <title>API Status: DOWN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: -apple-system, sans-serif; background: #fef2f2; color: #991b1b; padding: 2rem; }
      .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); max-width: 600px; margin: 0 auto; }
      .status { font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem; color: #dc2626; }
    </style>
  </head>
  <body>
    <div class="card">
      <div class="status">❌ System Critical</div>
      <p>The API is currently unreachable.</p>
      <p><strong>Error:</strong> ${error}</p>
      <p>Latency: ${latency}ms</p>
    </div>
  </body>
  </html>
  `;
}
