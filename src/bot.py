from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
import logging
import asyncio
from src.checker import check_connection, get_geoip
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
    
    with open("free_config.yaml", "w") as f:
        f.write(config)
        
    await update.message.reply_document(document=open("free_config.yaml", "rb"), caption="Here is your free subscription!")

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
        with open("converted.yaml", "w") as f:
            f.write(clash_config)
            
        await update.message.reply_document(
            document=open("converted.yaml", "rb"), 
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
    app.add_handler(CommandHandler("free", free))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()
