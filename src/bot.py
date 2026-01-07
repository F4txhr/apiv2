from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
import logging
import asyncio
import io
import httpx
from src.checker import check_connection, get_geoip
from src.downloader import get_media_info
from src.parser import decode_if_base64, parse_link
from src.converter import to_clash, to_singbox
from src.scraper import get_free_accounts

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to VPN Tools Bot!\n\n"
        "Commands:\n"
        "/check <ip> - Check IP:Port\n"
        "/free - Get free VPN account\n\n"
        "📥 *Send me a config text or file* to convert it to Clash/Sing-box subscription!"
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <ip> or <ip>:<port>")
        return
    
    target = context.args[0]
    port = 80
    
    try:
        if ":" in target:
            target, port_str = target.split(":")
            port = int(port_str)
        
        # Notify user we are checking
        await update.message.reply_chat_action(action="typing")

        loop = asyncio.get_running_loop()
        status = await loop.run_in_executor(None, check_connection, target, port)
        geo = await get_geoip(target)
        
        msg = f"🔍 *Check Result:*\n"
        msg += f"Target: `{target}:{port}`\n"
        msg += f"Status: *{status['status'].upper()}* "
        msg += "✅" if status['status'] == 'open' else "❌"
        msg += "\n"

        if status.get('latency_ms'):
            msg += f"Latency: `{status['latency_ms']} ms`\n"
        
        if geo:
            msg += f"🌍 Location: {geo.get('city')}, {geo.get('country')}\n"
            msg += f"🏢 ISP: {geo.get('isp')}"
        else:
            msg += "🌍 Location: Unknown"
            
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error performing check: {str(e)}")

async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches system stats from the local API."""
    try:
        # We access the API container internally via Docker network
        url = "http://vpn-api:8000/stats"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                sys = data['system']
                msg = (
                    f"📊 *System Monitor*\n"
                    f"✅ Status: *Online*\n"
                    f"⏱️ Uptime: `{data['uptime_human']}`\n"
                    f"💻 CPU: `{sys['cpu_percent']}%`\n"
                    f"🧠 RAM: `{sys['ram_percent']}%` ({sys['ram_used_mb']}/{sys['ram_total_mb']} MB)\n"
                    f"🔄 Requests: `{data['traffic']['total_requests']}`"
                )
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await update.message.reply_text(f"⚠️ API Error: {resp.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Monitor Error: {str(e)}")

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads media info from URL."""
    if not context.args:
        await update.message.reply_text("Usage: /dl <url>")
        return
        
    url = context.args[0]
    await update.message.reply_chat_action(action="typing")
    
    try:
        # We call the function directly since we are in the same container, 
        # but running in executor to avoid blocking async loop
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, get_media_info, url)
        
        if info['status'] == 'error':
            await update.message.reply_text(f"❌ Error: {info['message']}")
            return
            
        # Format Message
        caption = f"🎬 *{info.get('title', 'Unknown Title')}*\n\n"
        caption += f"👤 *{info.get('uploader', 'Unknown Author')}*\n"
        caption += f"👁️ Views: `{info.get('view_count', 0)}` | ❤️ Likes: `{info.get('like_count', 0)}`\n"
        caption += f"⏱️ Duration: `{info.get('duration')}s`\n"
        caption += f"🏷️ Platform: #{info.get('platform')}\n"
        
        # Send Thumbnail if available
        if info.get('thumbnail'):
            await update.message.reply_photo(photo=info['thumbnail'], caption=caption, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, parse_mode="Markdown")
            
        # Send Download Links (Best few)
        formats = info.get('formats', [])
        # Filter for video/audio
        best_formats = []
        for f in formats:
            if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                 best_formats.append(f)
        
        # Sort by resolution (simple heuristic)
        best_formats.sort(key=lambda x: x.get('filesize') or 0, reverse=True)
        top_3 = best_formats[:3]
        
        if not top_3 and formats:
             # Fallback to whatever is there
             top_3 = formats[:3]

        links_msg = "⬇️ *Download Links:*\n"
        for fmt in top_3:
            res = fmt.get('resolution', 'Unknown')
            ext = fmt.get('ext', '')
            url = fmt.get('url', '')
            size = round((fmt.get('filesize') or 0) / 1024 / 1024, 2)
            links_msg += f"• [{res} ({ext}) - {size}MB]({url})\n"
            
        await update.message.reply_text(links_msg, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching free accounts...")
    accounts = await get_free_accounts()
    if not accounts:
        await update.message.reply_text("❌ No accounts found.")
        return
        
    parsed = []
    for link in accounts:
        p = parse_link(link)
        if p: parsed.append(p)
        
    config = to_clash(parsed)
    
    # Use BytesIO instead of file
    bio = io.BytesIO(config.encode('utf-8'))
    bio.name = "free_config.yaml"
    
    await update.message.reply_document(document=bio, caption="Here is your free subscription!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ""
    # Check if text or file
    if update.message.document:
        file = await update.message.document.get_file()
        byte_array = await file.download_as_bytearray()
        text = byte_array.decode('utf-8')
    elif update.message.text:
        text = update.message.text
    
    if not text:
        return

    # Try to process as subscription
    try:
        decoded = decode_if_base64(text)
        links = decoded.strip().splitlines()
        parsed_list = []
        for link in links:
            p = parse_link(link.strip())
            if p: parsed_list.append(p)
        
        if not parsed_list:
            await update.message.reply_text("❌ No valid VPN links found in your message.")
            return

        # Convert to Clash (Default)
        clash_config = to_clash(parsed_list)
        
        bio = io.BytesIO(clash_config.encode('utf-8'))
        bio.name = "converted.yaml"

        await update.message.reply_document(
            document=bio, 
            caption=f"✅ Converted {len(parsed_list)} accounts to Clash format."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing: {str(e)}")

def main():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN not set")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("dl", download_media))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()
