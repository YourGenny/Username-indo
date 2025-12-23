#!/usr/bin/env python3
import os
import sys
import logging
import requests
import time
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Get token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    sys.exit(1)

# Configuration
CHANNEL_USERNAME = "@NetFusionTG"
GROUP_USERNAME = "@YourNetFusion"
SAVE_GROUP_ID = -1003648617588
API_BASE = "https://teradl.tiiny.io/"

# Data storage
user_data = {}

CREDIT = "🤖 Terabox Downloader Bot\n📢 @NetFusionTG\n👥 @YourNetFusion"

# ========== SYNC FUNCTIONS (NO async) ==========
def start(update: Update, context: CallbackContext):
    """Handle /start command"""
    user = update.effective_user
    update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"🤖 **Terabox Downloader Bot**\n\n"
        f"📌 **How to use:**\n"
        f"1. Send Terabox link in DM\n"
        f"2. Or use /genny <link> in groups\n\n"
        f"{CREDIT}"
    )

def genny(update: Update, context: CallbackContext):
    """Handle /genny command"""
    if not context.args:
        update.message.reply_text("Usage: /genny <terabox-link>")
        return
    
    link = context.args[0]
    update.message.reply_text(f"🔍 Processing: {link[:50]}...")
    
    # Get direct link from Terabox API
    try:
        params = {'key': 'RushVx', 'link': link}
        response = requests.get(API_BASE, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                file_data = data["data"][0]
                direct_link = file_data.get("download", "")
                title = file_data.get("title", "Video")
                size = file_data.get("size", "Unknown")
                
                if direct_link:
                    # Create buttons
                    keyboard = [
                        [InlineKeyboardButton("📥 Direct Download", url=direct_link)],
                        [InlineKeyboardButton("📲 Telegram Download", callback_data="tg_download")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    update.message.reply_text(
                        f"✅ **Download Ready!**\n\n"
                        f"📁 {title}\n"
                        f"📦 {size}\n\n"
                        f"{CREDIT}",
                        reply_markup=reply_markup
                    )
                    
                    # Save to context for callback
                    context.user_data['direct_link'] = direct_link
                    context.user_data['title'] = title
                    return
        
        update.message.reply_text("❌ Could not get download link")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ Error processing link")

def handle_text(update: Update, context: CallbackContext):
    """Handle text messages (for DM)"""
    if update.message.chat.type != "private":
        return
    
    text = update.message.text.strip()
    
    # Check if it's a Terabox link
    if any(domain in text.lower() for domain in ['terabox.com', 'terabox.app', '1024tera.com']):
        # Simulate /genny command
        context.args = [text]
        genny(update, context)

def button_callback(update: Update, context: CallbackContext):
    """Handle button clicks"""
    query = update.callback_query
    query.answer()
    
    if query.data == "tg_download":
        direct_link = context.user_data.get('direct_link', '')
        title = context.user_data.get('title', 'Video')
        
        if direct_link:
            query.edit_message_text(
                f"📥 Downloading via Telegram...\n\n"
                f"📁 {title}\n"
                f"🔗 {direct_link[:50]}...\n\n"
                f"⚠️ Large files may take time"
            )
        else:
            query.edit_message_text("❌ Download link expired")

def help_command(update: Update, context: CallbackContext):
    """Handle /help command"""
    update.message.reply_text(
        "🤖 **Terabox Bot Help**\n\n"
        "📌 **Commands:**\n"
        "/start - Start bot\n"
        "/genny <link> - Download link\n"
        "/help - This help\n\n"
        "📌 **Direct Use:**\n"
        "Send Terabox link in private chat\n\n"
        f"{CREDIT}"
    )

def main():
    """Main function"""
    logger.info("🚀 Starting Terabox Bot...")
    
    try:
        # Create updater with error handling
        updater = Updater(
            BOT_TOKEN,
            use_context=True,
            request_kwargs={
                'read_timeout': 30,
                'connect_timeout': 30
            }
        )
        
        dispatcher = updater.dispatcher
        
        # Add handlers (ALL must be SYNC functions)
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("genny", genny))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
        dispatcher.add_handler(CallbackQueryHandler(button_callback))
        
        # Start with clean state
        updater.start_polling(
            drop_pending_updates=True,
            timeout=15,
            clean=True
        )
        
        logger.info("✅ Bot started successfully!")
        print("=" * 60)
        print("🤖 TERABOX DOWNLOADER BOT")
        print("=" * 60)
        print(f"✅ Bot Token: Loaded")
        print(f"✅ Python: {sys.version.split()[0]}")
        print(f"📢 Channel: {CHANNEL_USERNAME}")
        print(f"👥 Group: {GROUP_USERNAME}")
        print("=" * 60)
        print("✅ Bot is ready to use!")
        print("=" * 60)
        
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()