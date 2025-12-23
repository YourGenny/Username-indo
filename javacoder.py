#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ========== COMPATIBILITY FIX FOR PYTHON 3.11+ ==========
import sys

# Fix for imghdr module in Python 3.11+
if sys.version_info >= (3, 11):
    # Create imghdr replacement
    class ImghdrCompat:
        @staticmethod
        def what(file, h=None):
            """Simple image type detector for Python 3.11+"""
            if h is None:
                try:
                    with open(file, 'rb') as f:
                        h = f.read(32)
                except Exception:
                    return None
            
            if len(h) < 32:
                return None
            
            # Check for common image formats
            if h.startswith(b'\xff\xd8\xff'):
                return 'jpeg'
            elif h.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'png'
            elif h.startswith(b'GIF87a') or h.startswith(b'GIF89a'):
                return 'gif'
            elif h.startswith(b'BM'):
                return 'bmp'
            elif len(h) >= 10 and h[6:10] in (b'JFIF', b'Exif'):
                return 'jpeg'
            elif h.startswith(b'\x00\x00\x01\x00'):
                return 'ico'
            
            return None
    
    # Monkey patch to fix telegram-bot import
    sys.modules['imghdr'] = ImghdrCompat()

# ========== MAIN IMPORTS ==========
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import other modules
import requests
import time
import tempfile
import asyncio
import random
import math
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
import aiohttp
import aiofiles

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found in environment variables!")
    logger.error("Please add BOT_TOKEN in Railway Variables tab")
    sys.exit(1)

API_BASE = "https://teradl.tiiny.io/"

# Channel and group for mandatory subscription
CHANNEL_USERNAME = "@NetFusionTG"
GROUP_USERNAME = "@YourNetFusion"

# Groups where bot should work
ALLOWED_GROUPS = {
    -1003284051384: "Team Fx Main Group",
    -1002473112174: "Group One",
    -1003199415158: "Group Two"
}

# Special group for saving user info and links
SAVE_GROUP_ID = -1003648617588

# ================= SIZE LIMITS =================
DM_LIMIT_MB = 1024      # 1 GB for private chat
GROUP_LIMIT_MB = 999999 # unlimited for groups

COOLDOWN = 30  # 30 seconds cooldown

# Data storage
user_last = {}
sessions = {}
user_data = {}

CREDIT = (
    "╔══════════════════════╗\n"
    "║ 🤖 TERABOX DOWNLOADER ║\n"
    "╠══════════════════════╣\n"
    "║ • Creator: Genny 🎀  ║\n"
    "║ • Channel: @NetFusionTG ║\n"
    "║ • Group: @YourNetFusion ║\n"
    "╚══════════════════════╝"
)

# Use Railway's /tmp directory if available
DATA_FILE = "/tmp/user_data.json" if os.path.exists("/tmp") else "user_data.json"

# ========== HELPER FUNCTIONS ==========
def save_user_info(user_id, username, first_name, last_name, original_link, direct_link=None, title=None):
    """Save user information when they send a link"""
    user_data[str(user_id)] = {
        'username': username or 'No Username',
        'first_name': first_name or 'No First Name',
        'last_name': last_name or '',
        'original_link': original_link,
        'direct_link': direct_link or '',
        'title': title or 'Unknown',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'last_activity': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    # Save to file for persistence
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=2)
        logger.info(f"✅ Saved user data for {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def load_user_data():
    """Load user data from file"""
    global user_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                user_data = json.load(f)
                logger.info(f"✅ Loaded {len(user_data)} users from file")
        else:
            logger.info("ℹ️ No existing user data file found")
            user_data = {}
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
        user_data = {}

async def check_subscription(user_id, context):
    """Check if user is subscribed to channel and group"""
    try:
        # Check channel subscription
        try:
            channel_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if channel_member.status in ['left', 'kicked']:
                return False, "channel"
        except Exception as e:
            logger.error(f"Channel check error: {e}")
            return False, "channel"
        
        # Check group subscription
        try:
            group_member = await context.bot.get_chat_member(GROUP_USERNAME, user_id)
            if group_member.status in ['left', 'kicked']:
                return False, "group"
        except Exception as e:
            logger.error(f"Group check error: {e}")
            return False, "group"
        
        return True, "both"
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False, "channel"

def allowed(update):
    """Check if message is from allowed group or private chat"""
    if update.message.chat.type == "private":
        return True
    
    chat_id = update.message.chat.id
    return chat_id in ALLOWED_GROUPS

def deny(update):
    update.message.reply_text("❌ Bot sirf allowed groups me kaam karta hai")

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def format_size(bytes_size):
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size/1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size/(1024*1024):.1f} MB"
    else:
        return f"{bytes_size/(1024*1024*1024):.1f} GB"

def size_to_mb(size_str):
    """Convert size string to MB"""
    try:
        if not size_str:
            return 0
        size_str = str(size_str).lower()
        if "gb" in size_str:
            return float(size_str.replace("gb", "").strip()) * 1024
        if "mb" in size_str:
            return float(size_str.replace("mb", "").strip())
        if "kb" in size_str:
            return float(size_str.replace("kb", "").strip()) / 1024
        return float(size_str) / (1024 * 1024)  # Assume bytes
    except:
        return 0

# ========== SEND LINKS TO SAVE GROUP ==========
async def send_links_to_save_group(context, user_info, original_link, direct_link, title, size):
    """Send BOTH original and direct links to save group"""
    try:
        logger.info(f"📤 Sending links to save group")
        
        # Format the main message
        user_text = (
            f"👤 **USER REQUEST**\n\n"
            f"🆔 User ID: `{user_info['user_id']}`\n"
            f"👤 Name: {user_info['first_name']} {user_info.get('last_name', '')}\n"
            f"📛 Username: @{user_info.get('username', 'N/A')}\n"
            f"📅 Time: {user_info['timestamp']}\n\n"
            f"📁 **FILE DETAILS**\n"
            f"📝 Title: {title}\n"
            f"📦 Size: {size}\n\n"
            f"🔗 **ORIGINAL LINK**\n{original_link}\n\n"
            f"⬇️ **DIRECT DOWNLOAD LINK**\n{direct_link}\n\n"
            f"#Terabox #{user_info['user_id']} #Links"
        )
        
        # Send main message to save group
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=user_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
        
        # Send separate messages for easy copying
        await asyncio.sleep(1)
        
        # Send original link separately
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=f"🔗 **Original Terabox Link:**\n{original_link}\n\n#OriginalLink",
            disable_web_page_preview=False
        )
        
        await asyncio.sleep(1)
        
        # Send direct link separately
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=f"⬇️ **Direct Download Link:**\n{direct_link}\n\n#DirectLink",
            disable_web_page_preview=False
        )
        
        logger.info(f"✅ All links sent to save group")
        
    except Exception as e:
        logger.error(f"Error sending to save group: {e}")

# ========== TERABOX API FUNCTION ==========
def get_terabox_direct_link(link, max_retries=3):
    """Get direct download link from Terabox"""
    retries = 0
    
    while retries < max_retries:
        retries += 1
        logger.info(f"Attempt {retries}/{max_retries} for: {link[:50]}...")
        
        try:
            if retries > 1:
                time.sleep(random.uniform(1, 3))
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'application/json',
            }
            
            params = {'key': 'RushVx', 'link': link}
            response = requests.get(API_BASE, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if "data" in data and len(data["data"]) > 0:
                    file_data = data["data"][0]
                    download_url = file_data.get("download")
                    
                    if download_url and download_url.startswith("http"):
                        logger.info(f"✅ Link found on attempt {retries}")
                        return download_url, file_data.get("title", "Video"), file_data.get("size", "Unknown")
                        
        except Exception as e:
            logger.error(f"Error on attempt {retries}: {str(e)}")
        
        if retries < max_retries:
            time.sleep(2)
    
    logger.error(f"❌ All {max_retries} attempts failed")
    return None, None, None

# ========== SUBSCRIPTION CHECK ==========
async def check_and_require_subscription(update: Update, context: CallbackContext, user_id=None):
    if user_id is None:
        user_id = update.effective_user.id
    
    subscribed, where = await check_subscription(user_id, context)
    
    if not subscribed:
        buttons = []
        
        if where == "channel" or where == "both":
            buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/NetFusionTG")])
        
        if where == "group" or where == "both":
            buttons.append([InlineKeyboardButton("👥 Join Group", url=f"https://t.me/YourNetFusion")])
        
        buttons.append([InlineKeyboardButton("✅ I Have Joined", callback_data=f"check_{user_id}")])
        
        message_text = (
            f"❌ **Subscription Required**\n\n"
            f"To use this bot, you must join:\n"
            f"1. 📢 Channel: {CHANNEL_USERNAME}\n"
            f"2. 👥 Group: {GROUP_USERNAME}\n\n"
            f"👉 Join both then click 'I Have Joined' button"
        )
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        return False
    
    return True

# ========== PROCESS TERABOX LINK ==========
async def process_terabox_link(update: Update, context: CallbackContext, original_link, is_private=False):
    user = update.effective_user
    
    # Cooldown check
    uid = user.id
    now = time.time()
    if uid in user_last and now - user_last[uid] < COOLDOWN:
        await update.message.reply_text("⏳ Please wait 30 seconds before next request")
        return
    user_last[uid] = now
    
    msg = await update.message.reply_text("🔍 Processing your Terabox link...")
    
    # Get direct link
    direct_link, title, size = get_terabox_direct_link(original_link)
    
    if not direct_link:
        await msg.edit_text(
            "❌ Download link not found\n\n"
            "🔍 **Possible reasons:**\n"
            "1. Invalid link\n"
            "2. File not accessible\n"
            "3. Server busy\n\n"
            "🔄 Try again after some time"
        )
        return
    
    # Save user info
    user_info = {
        'user_id': user.id,
        'username': user.username or 'N/A',
        'first_name': user.first_name,
        'last_name': user.last_name or '',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save to local storage
    save_user_info(user.id, user.username, user.first_name, user.last_name, 
                   original_link, direct_link, title)
    
    # Store session
    sessions[uid] = {
        'url': direct_link,
        'title': title,
        'size': size,
        'user_info': user_info,
        'original_link': original_link
    }
    
    # Send links to save group
    try:
        await send_links_to_save_group(context, user_info, original_link, direct_link, title, size)
        logger.info(f"✅ Links saved for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to send links to save group: {e}")
    
    # Create buttons
    buttons = [
        [InlineKeyboardButton("📥 DIRECT DOWNLOAD", url=direct_link)]
    ]
    
    # Check file size and add Telegram download button if applicable
    size_mb = size_to_mb(size)
    chat_type = update.message.chat.type
    
    # DM → only if <= 1GB
    if chat_type == "private":
        if size_mb <= DM_LIMIT_MB:
            buttons.append(
                [InlineKeyboardButton("📲 TELEGRAM DOWNLOAD", callback_data=f"tg_{uid}")]
            )
    # GROUP → always allow
    else:
        buttons.append(
            [InlineKeyboardButton("📲 TELEGRAM DOWNLOAD", callback_data=f"tg_{uid}")]
        )
    
    await msg.edit_text(
        f"✅ **Download Ready!**\n\n"
        f"📁 Title: {title}\n"
        f"📦 Size: {size}\n\n"
        f"📌 **Choose download method:**\n\n"
        f"{CREDIT}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========== DOWNLOAD FUNCTION ==========
async def download_file_with_progress(url, message, context, file_name="Video"):
    """Download file with progress updates"""
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.terabox.com/',
        }
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    await message.edit_text(f"❌ Download failed: HTTP {response.status}")
                    return None
                
                total = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                
                # Use Railway's /tmp directory
                temp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
                with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix=".mp4") as f:
                    temp_path = f.name
                
                await message.edit_text(
                    f"🎬 **STARTING DOWNLOAD**\n\n"
                    f"📁 {file_name}\n"
                    f"📦 Size: {format_size(total)}\n"
                    f"⏳ Downloading...\n\n"
                    f"{CREDIT}"
                )
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024 * 512):
                        if chunk:
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress every 5%
                            percent = (downloaded / total * 100) if total > 0 else 0
                            if int(percent) % 5 == 0:  # Update every 5%
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                
                                if speed > 1024*1024:
                                    speed_text = f"{speed/(1024*1024):.1f} MB/s"
                                else:
                                    speed_text = f"{speed/1024:.1f} KB/s"
                                
                                await message.edit_text(
                                    f"📥 **DOWNLOADING...**\n\n"
                                    f"📁 {file_name}\n"
                                    f"📊 Progress: {percent:.1f}%\n"
                                    f"⚡ Speed: {speed_text}\n"
                                    f"⏱️ Time: {format_time(elapsed)}\n\n"
                                    f"{CREDIT}"
                                )
                
                total_time = time.time() - start_time
                
                await message.edit_text(
                    f"✅ **DOWNLOAD COMPLETE**\n\n"
                    f"🎬 File: {file_name}\n"
                    f"📦 Size: {format_size(total)}\n"
                    f"⏱️ Time: {format_time(total_time)}\n"
                    f"📤 Ready for Telegram upload\n\n"
                    f"{CREDIT}"
                )
                
                return temp_path
                
    except Exception as e:
        await message.edit_text(f"❌ Download error: {str(e)[:100]}")
        logger.error(f"Download error: {e}")
        return None

# ========== UPLOAD TO TELEGRAM ==========
async def upload_to_telegram(file_path, title, message, context, user_info=None):
    """Upload file to Telegram"""
    try:
        size_bytes = os.path.getsize(file_path)
        
        await message.edit_text(
            f"📤 **UPLOADING TO TELEGRAM**\n\n"
            f"📁 {title}\n"
            f"📦 Size: {format_size(size_bytes)}\n"
            f"⏳ Please wait...\n\n"
            f"{CREDIT}"
        )
        
        start_time = time.time()
        
        with open(file_path, "rb") as video_file:
            sent_message = await context.bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                caption=f"✅ **{title}**\n\n"
                       f"📦 Size: {format_size(size_bytes)}\n"
                       f"👤 Via Terabox Downloader Bot\n\n{CREDIT}",
                supports_streaming=True,
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300
            )
        
        upload_time = time.time() - start_time
        
        return True, upload_time, "Success", sent_message
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return False, 0, str(e), None

# ========== HANDLE TEXT MESSAGES ==========
async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages in private chat for direct Terabox links"""
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Check if it's a private chat
    if update.message.chat.type != "private":
        return
    
    # Check subscription first
    is_subscribed = await check_and_require_subscription(update, context)
    if not is_subscribed:
        return
    
    # Check if message contains a Terabox link
    terabox_domains = ['terabox.com', 'terabox.app', 'teraboxapp.com', '1024tera.com', 
                      'mirrobox.com', 'nephobox.com', '4funbox.com', 'terabox.fun']
    
    is_terabox_link = any(domain in message_text.lower() for domain in terabox_domains)
    
    if is_terabox_link:
        await process_terabox_link(update, context, message_text, is_private=True)

# ========== COMMAND HANDLERS ==========
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if update.message.chat.type == "private":
        welcome_msg = (
            f"👋 Hello {user.first_name}!\n\n"
            f"🤖 **Welcome to Terabox Downloader Bot**\n\n"
            f"{CREDIT}\n\n"
            f"📌 **To use this bot:**\n"
            f"1. Join our channel: {CHANNEL_USERNAME}\n"
            f"2. Join our group: {GROUP_USERNAME}\n"
            f"3. Then send Terabox links directly here\n\n"
            f"📌 **In groups:** Use /genny <terabox-link>\n\n"
            f"🔗 Example: https://terabox.com/s/..."
        )
        
        is_subscribed = await check_and_require_subscription(update, context)
        if not is_subscribed:
            return
        
        await update.message.reply_text(welcome_msg)
        return
    
    if not allowed(update):
        deny(update)
        return
    
    await update.message.reply_text(
        "🤖 **Terabox Downloader Ready**\n\n"
        "📌 **Usage:** /genny <terabox-link>\n\n"
        f"{CREDIT}"
    )

async def genny(update: Update, context: CallbackContext):
    user = update.effective_user
    
    # Check subscription
    is_subscribed = await check_and_require_subscription(update, context)
    if not is_subscribed:
        return
    
    if update.message.chat.type != "private":
        if not allowed(update):
            deny(update)
            return
    
    if not context.args:
        await update.message.reply_text("📌 **Usage:** /genny <terabox-link>\n\nExample: /genny https://terabox.com/s/...")
        return
    
    original_link = context.args[0].strip()
    await process_terabox_link(update, context, original_link, is_private=False)

# ========== CALLBACK HANDLER ==========
async def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    
    if q.data.startswith("check_"):
        check_user_id = int(q.data.split("_")[1])
        
        if check_user_id != user_id:
            await q.answer("This button is not for you!", show_alert=True)
            return
        
        is_subscribed = await check_and_require_subscription(update, context, user_id)
        if is_subscribed:
            await q.edit_message_text(
                f"✅ **Subscription Verified!**\n\n"
                f"You can now use the bot.\n"
                f"Send Terabox links directly in DM or use /genny in groups.\n\n"
                f"{CREDIT}"
            )
        return
    
    if not q.data.startswith("tg_"):
        return

    uid = int(q.data.split("_")[1])
    
    if uid != user_id:
        await q.answer("This download link is not for you!", show_alert=True)
        return
    
    if uid not in sessions:
        await q.edit_message_text("⚠️ Session expired. Please generate link again.")
        return

    is_subscribed = await check_and_require_subscription(update, context, user_id)
    if not is_subscribed:
        return
    
    session_data = sessions.pop(uid)
    direct_link = session_data['url']
    title = session_data.get('title', 'Video')
    file_size = session_data.get('size', 'Unknown')
    user_info = session_data.get('user_info', {})
    original_link = session_data.get('original_link', '')
    
    # Check file size before downloading
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(direct_link) as resp:
                content_length = resp.headers.get('Content-Length')
                if content_length:
                    size_bytes = int(content_length)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Check if file is too large
                    chat_type = q.message.chat.type
                    max_limit_mb = DM_LIMIT_MB if chat_type == "private" else GROUP_LIMIT_MB

                    if size_mb > max_limit_mb:
                        await q.edit_message_text(
                            f"❌ **File Too Large**\n\n"
                            f"📁 Title: {title}\n"
                            f"📦 Size: {format_size(size_bytes)}\n\n"
                            f"⚠️ Limits:\n"
                            f"• DM: 1 GB\n"
                            f"• Groups: Unlimited\n\n"
                            f"📥 Use Direct Download link instead\n\n"
                            f"{CREDIT}"
                        )
                        return
    except:
        pass
    
    await q.edit_message_text(f"🎬 **STARTING DOWNLOAD**\n\n📁 {title}\n📦 {file_size}")
    
    file_path = await download_file_with_progress(direct_link, q.message, context, title)
    
    if not file_path:
        return
    
    # Check file size after download
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    
    # Check size limits again
    chat_type = q.message.chat.type
    max_limit_mb = DM_LIMIT_MB if chat_type == "private" else GROUP_LIMIT_MB
    
    if size_mb > max_limit_mb:
        await q.edit_message_text(
            f"❌ **File Too Large**\n\n"
            f"📁 {title}\n"
            f"📦 {format_size(size_bytes)}\n\n"
            f"⚠️ DM: 1 GB | Group: Unlimited\n"
            f"📥 Use Direct Download\n\n{CREDIT}"
        )
        os.remove(file_path)
        return
    
    try:
        success, upload_time, speed_text, sent_message = await upload_to_telegram(
            file_path, title, q.message, context, user_info
        )
        
        if success:
            await asyncio.sleep(2)
            await q.message.delete()
        else:
            await q.edit_message_text(f"❌ Upload failed: {speed_text}")
            
    except Exception as e:
        error_msg = str(e)
        if "File too large" in error_msg:
            await q.edit_message_text("❌ File too large for Telegram\nUse Direct Download")
        elif "timed out" in error_msg:
            await q.edit_message_text("❌ Upload timeout! Slow connection.\nTry Direct Download")
        else:
            await q.edit_message_text(f"❌ Upload failed: {error_msg[:100]}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def help_command(update: Update, context: CallbackContext):
    is_subscribed = await check_and_require_subscription(update, context)
    if not is_subscribed:
        return
    
    help_text = (
        "🤖 **Terabox Downloader Bot Help**\n\n"
        "📌 **Available Commands:**\n"
        "/start - Start the bot\n"
        "/genny <link> - Download terabox link\n"
        "/help - Show this help\n\n"
        "📌 **How to use:**\n"
        "**In Private Chat:** Send Terabox links directly\n"
        "**In Groups:** Use /genny <terabox-link>\n\n"
        "📌 **Example Links:**\n"
        "• https://terabox.com/s/...\n"
        "• https://www.terabox.com/s/...\n\n"
        f"{CREDIT}"
    )
    await update.message.reply_text(help_text)

async def info_command(update: Update, context: CallbackContext):
    is_subscribed = await check_and_require_subscription(update, context)
    if not is_subscribed:
        return
    
    user = update.effective_user
    info_text = (
        f"👤 **Your Information**\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"📛 Name: {user.first_name} {user.last_name or ''}\n"
        f"🔗 Username: @{user.username or 'N/A'}\n\n"
        f"📊 **Bot Stats:**\n"
        f"👥 Total Users: {len(user_data)}\n"
        f"🔄 Active Sessions: {len(sessions)}\n\n"
        f"📌 **Subscription Status:** ✅ Subscribed\n\n"
        f"{CREDIT}"
    )
    await update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)

# ========== MAIN FUNCTION ==========
def main():
    """Main function to start the bot"""
    try:
        # Load user data
        load_user_data()
        
        # Create updater
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Add command handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("genny", genny))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("info", info_command))
        
        # Add message handler for text messages
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))
        
        # Add callback handler
        dp.add_handler(CallbackQueryHandler(buttons))
        
        # Start the bot
        print("=" * 60)
        print("🤖 TERABOX DOWNLOADER BOT STARTING...")
        print("=" * 60)
        print(f"✅ Bot Token: {'✓ Set' if BOT_TOKEN else '✗ Not Set'}")
        print(f"✅ Python Version: {sys.version}")
        print(f"📢 Channel: {CHANNEL_USERNAME}")
        print(f"👥 Group: {GROUP_USERNAME}")
        print(f"💾 Save Group: {SAVE_GROUP_ID}")
        print("=" * 60)
        print("✅ Bot is ready to use!")
        print("=" * 60)
        
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()