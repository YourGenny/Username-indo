# TERABOX GROUP BOT – DIRECT + TG DOWNLOAD WITH PROGRESS

import requests, time, os, tempfile, asyncio, random, math, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
import aiohttp
import aiofiles
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
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

# Special group for saving user info and links (-1003648617588)
SAVE_GROUP_ID = -1003648617588

COOLDOWN = 30

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

# ---------- HELPER FUNCTIONS ----------
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
        with open('user_data.json', 'w') as f:
            json.dump(user_data, f, indent=2)
    except Exception as e:
        print(f"Error saving user data: {e}")

def load_user_data():
    """Load user data from file"""
    global user_data
    try:
        if os.path.exists('user_data.json'):
            with open('user_data.json', 'r') as f:
                user_data = json.load(f)
                print(f"Loaded {len(user_data)} users from file")
    except Exception as e:
        print(f"Error loading user data: {e}")
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
            print(f"Channel check error: {e}")
            return False, "channel"
        
        # Check group subscription
        try:
            group_member = await context.bot.get_chat_member(GROUP_USERNAME, user_id)
            if group_member.status in ['left', 'kicked']:
                return False, "group"
        except Exception as e:
            print(f"Group check error: {e}")
            return False, "group"
        
        return True, "both"
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False, "channel"

def allowed(update):
    """Check if message is from allowed group or private chat"""
    chat_type = update.message.chat.type
    chat_id = update.message.chat.id
    
    if chat_type == "private":
        return True
    
    return chat_type in ["group", "supergroup"] and chat_id in ALLOWED_GROUPS

def deny(update):
    update.message.reply_text("❌ Bot sirf allowed groups me kaam karta hai")

def progress_bar(percentage, length=10):
    filled = int(length * percentage // 100)
    bar = "▓" * filled + "░" * (length - filled)
    return bar

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

# ---------- SEND LINKS TO SAVE GROUP ----------
async def send_links_to_save_group(context, user_info, original_link, direct_link, title, size):
    """Send BOTH original and direct links to save group"""
    try:
        print(f"\n📤 SENDING LINKS TO SAVE GROUP {SAVE_GROUP_ID}")
        print(f"User: {user_info['first_name']} (ID: {user_info['user_id']})")
        print(f"Original Link: {original_link}")
        print(f"Direct Link: {direct_link}")
        
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
        print(f"✅ Main info sent to save group")
        
        # Send separate messages for easy copying
        await asyncio.sleep(1)
        
        # Send original link separately
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=f"🔗 **Original Terabox Link:**\n{original_link}\n\n#OriginalLink",
            disable_web_page_preview=False
        )
        print(f"✅ Original link sent separately")
        
        await asyncio.sleep(1)
        
        # Send direct link separately
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=f"⬇️ **Direct Download Link:**\n{direct_link}\n\n#DirectLink",
            disable_web_page_preview=False
        )
        print(f"✅ Direct link sent separately")
        
        print(f"✅ ALL LINKS SUCCESSFULLY SENT TO SAVE GROUP")
        
    except Exception as e:
        print(f"❌ Error sending to save group: {e}")
        # Try a simpler message
        try:
            simple_msg = f"User: {user_info['first_name']} (ID: {user_info['user_id']})\nOriginal: {original_link}\nDirect: {direct_link}"
            await context.bot.send_message(
                chat_id=SAVE_GROUP_ID,
                text=simple_msg
            )
        except:
            print(f"❌ Failed to send even simple message")

# ---------- FORWARD VIDEO TO SAVE GROUP ----------
async def forward_video_to_save_group(context, video_message, user_info, title, size, direct_link, original_link):
    """Forward video and ALL links to save group"""
    try:
        print(f"\n🎬 FORWARDING VIDEO TO SAVE GROUP {SAVE_GROUP_ID}")
        
        # First forward the video
        forwarded_msg = await context.bot.forward_message(
            chat_id=SAVE_GROUP_ID,
            from_chat_id=video_message.chat.id,
            message_id=video_message.message_id
        )
        print(f"✅ Video forwarded to save group")
        
        # Send video info with BOTH links
        video_info = (
            f"🎬 **VIDEO DOWNLOADED TO TELEGRAM**\n\n"
            f"📁 Title: {title}\n"
            f"📦 Size: {size}\n\n"
            f"👤 **USER INFO**\n"
            f"🆔 ID: `{user_info['user_id']}`\n"
            f"👤 Name: {user_info['first_name']}\n"
            f"📛 Username: @{user_info.get('username', 'N/A')}\n\n"
            f"🔗 **ORIGINAL TERABOX LINK**\n{original_link}\n\n"
            f"⬇️ **DIRECT DOWNLOAD LINK**\n{direct_link}\n\n"
            f"#VideoDownload #{user_info['user_id']}"
        )
        
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=video_info,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        
        # Send links separately for easy access
        await asyncio.sleep(1)
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=f"🔗 Original: {original_link}\n\n#LinkCopy",
            disable_web_page_preview=False
        )
        
        await asyncio.sleep(1)
        await context.bot.send_message(
            chat_id=SAVE_GROUP_ID,
            text=f"⬇️ Direct: {direct_link}\n\n#DirectDownload",
            disable_web_page_preview=False
        )
        
        print(f"✅ Video and ALL links forwarded to save group")
        return True
        
    except Exception as e:
        print(f"❌ Failed to forward video to save group: {e}")
        return False

# ---------- IMPROVED TERABOX API WITH RETRY ----------
def terabox_with_retry(link, max_retries=5):
    retries = 0
    
    while retries < max_retries:
        retries += 1
        print(f"Attempt {retries}/{max_retries} for link: {link}")
        
        try:
            if retries > 1:
                wait_time = random.uniform(1, 3)
                time.sleep(wait_time)
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            params = {'key': 'RushVx', 'link': link}
            r = requests.get(API_BASE, params=params, headers=headers, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                
                if "data" in data and len(data["data"]) > 0:
                    d = data["data"][0]
                    dl = d.get("download")
                    
                    if dl and dl.startswith("http"):
                        print(f"✅ Link found on attempt {retries}")
                        return dl, d.get("title", "Video"), d.get("size", "Unknown")
                        
        except Exception as e:
            print(f"❌ Error on attempt {retries}: {str(e)}")
        
        if retries < max_retries:
            print(f"🔄 Retrying in 2 seconds...")
            time.sleep(2)
    
    print(f"❌ All {max_retries} attempts failed")
    return None, None, None

# ---------- SUBSCRIPTION CHECK WITH BUTTONS ----------
async def check_and_require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
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

# ---------- PROCESS TERABOX LINK (COMMON FUNCTION) ----------
async def process_terabox_link(update: Update, context: ContextTypes.DEFAULT_TYPE, original_link, is_private=False):
    user = update.effective_user
    chat_id = update.message.chat.id
    
    # Cooldown check
    uid = user.id
    now = time.time()
    if uid in user_last and now - user_last[uid] < COOLDOWN:
        await update.message.reply_text("⏳ Please wait 30 seconds before next request")
        return
    user_last[uid] = now
    
    msg = await update.message.reply_text("🔍 Processing link (Attempt 1/5)...")
    
    async def update_progress_message(attempt, total):
        if attempt == 1:
            text = f"🔍 Processing link (Attempt {attempt}/{total})..."
        elif attempt < total:
            text = f"🔄 Retrying... (Attempt {attempt}/{total})"
        else:
            text = f"⏳ Last attempt... (Attempt {attempt}/{total})"
        
        try:
            await msg.edit_text(text)
        except:
            pass
    
    max_retries = 5
    direct_link, title, size = None, None, None
    
    for attempt in range(1, max_retries + 1):
        await update_progress_message(attempt, max_retries)
        direct_link, title, size = terabox_with_retry(original_link, max_retries=1)
        if direct_link:
            break
        if attempt < max_retries:
            await asyncio.sleep(2)
    
    if not direct_link:
        await msg.edit_text(
            "❌ Download link not found after 5 attempts\n\n"
            "🔍 **Troubleshooting:**\n"
            "1. Check your link\n"
            "2. Try after some time\n"
            "3. Use direct terabox links\n\n"
            "🔄 Try again after 1-2 minutes"
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
    
    # Save user data locally with ALL info
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
    
    # ✅ SEND BOTH LINKS TO SAVE GROUP IMMEDIATELY
    try:
        await send_links_to_save_group(context, user_info, original_link, direct_link, title, size)
        print(f"✅ BOTH LINKS sent to save group for user {user.id}")
    except Exception as e:
        print(f"❌ Failed to send links to save group: {e}")
    
    # Create buttons
    buttons = [
        [InlineKeyboardButton("📥 DIRECT DOWNLOAD", url=direct_link)],
        [InlineKeyboardButton("📲 TELEGRAM DOWNLOAD", callback_data=f"tg_{uid}")]
    ]
    
    await msg.edit_text(
        f"✅ **Download Ready!**\n\n"
        f"📁 Title: {title}\n"
        f"📦 Size: {size}\n\n"
        f"📌 **Choose download method:**\n\n"
        f"{CREDIT}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------- ENHANCED DOWNLOAD FUNCTION ----------
def get_file_icon(file_name):
    if any(ext in file_name.lower() for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']):
        return "🎬"
    elif any(ext in file_name.lower() for ext in ['.mp3', '.wav', '.flac', '.m4a']):
        return "🎵"
    elif any(ext in file_name.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
        return "🖼️"
    elif any(ext in file_name.lower() for ext in ['.pdf', '.doc', '.docx', '.txt']):
        return "📄"
    else:
        return "📁"

def get_status_emoji(percent):
    if percent < 25:
        return "⏳"
    elif percent < 50:
        return "📥"
    elif percent < 75:
        return "⚡"
    elif percent < 95:
        return "🚀"
    else:
        return "✅"

def create_download_stats(total, downloaded, elapsed):
    percent = (downloaded / total * 100) if total > 0 else 0
    
    speed_bps = downloaded / elapsed if elapsed > 0 else 0
    
    if speed_bps > 1024*1024:
        speed_text = f"{speed_bps/(1024*1024):.1f} MB/s"
    elif speed_bps > 1024:
        speed_text = f"{speed_bps/1024:.1f} KB/s"
    else:
        speed_text = f"{speed_bps:.0f} B/s"
    
    if speed_bps > 0 and total > downloaded:
        eta_seconds = (total - downloaded) / speed_bps
        eta_text = format_time(eta_seconds)
    else:
        eta_text = "Calculating..."
    
    bar_length = 15
    filled = int(bar_length * percent // 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    return f"""
{get_status_emoji(percent)} **DOWNLOAD PROGRESS**

{bar} {percent:.1f}%

📊 **Statistics:**
├ 📦 Size: {downloaded/1024/1024:.1f}MB / {total/1024/1024:.1f}MB
├ ⚡ Speed: {speed_text}
├ ⏱️ Elapsed: {format_time(elapsed)}
└ 🎯 ETA: {eta_text}
"""

async def enhanced_download_with_progress(url, message, context, file_name="Video"):
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        connector = aiohttp.TCPConnector(limit_per_host=5)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.terabox.com/',
        }
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    await message.edit_text(f"❌ Download failed: HTTP {response.status}")
                    return None
                
                total = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                last_update_time = start_time
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
                    temp_path = f.name
                
                file_icon = get_file_icon(file_name)
                
                await message.edit_text(
                    f"{file_icon} **STARTING DOWNLOAD**\n\n"
                    f"📁 {file_name}\n"
                    f"📦 Total Size: {format_size(total)}\n"
                    f"⏳ Preparing...\n\n"
                    f"{CREDIT}"
                )
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    chunk_size = 1024 * 512
                    
                    async for chunk in response.content.iter_chunked(chunk_size):
                        if chunk:
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            current_time = time.time()
                            elapsed = current_time - start_time
                            
                            if current_time - last_update_time >= 2 or (downloaded/total*100) - (downloaded-len(chunk))/total*100 >= 5:
                                last_update_time = current_time
                                
                                stats = create_download_stats(total, downloaded, elapsed)
                                
                                try:
                                    await message.edit_text(
                                        f"{stats}\n"
                                        f"🔗 Source: Terabox\n"
                                        f"👤 User: {message.chat.title or 'Group'}\n\n"
                                        f"{CREDIT}"
                                    )
                                except:
                                    pass
                
                total_time = time.time() - start_time
                avg_speed = total / total_time if total_time > 0 else 0
                
                if avg_speed > 1024*1024:
                    final_speed = f"{avg_speed/(1024*1024):.1f} MB/s"
                else:
                    final_speed = f"{avg_speed/1024:.1f} KB/s"
                
                await message.edit_text(
                    f"✅ **DOWNLOAD COMPLETE**\n\n"
                    f"🎬 File: {file_name}\n"
                    f"📦 Size: {format_size(total)}\n"
                    f"⏱️ Time: {format_time(total_time)}\n"
                    f"⚡ Avg Speed: {final_speed}\n"
                    f"📤 Status: Ready for Telegram Upload\n\n"
                    f"{CREDIT}"
                )
                
                return temp_path
                
    except Exception as e:
        await message.edit_text(f"❌ Download error: {str(e)[:100]}")
        return None

# ---------- SIMPLE UPLOAD FUNCTION ----------
async def simple_upload_to_telegram(file_path, title, message, context, user_info=None):
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
                       f"👤 User: {user_info.get('first_name', 'User') if user_info else 'User'}\n"
                       f"⚡ Via Terabox Downloader Bot\n\n{CREDIT}",
                supports_streaming=True,
                read_timeout=600,
                write_timeout=600,
                connect_timeout=600,
                filename=title[:64] + ".mp4"
            )
        
        upload_time = time.time() - start_time
        
        if upload_time > 0:
            upload_speed = size_bytes / upload_time
            if upload_speed > 1024 * 1024:
                speed_text = f"{upload_speed/(1024*1024):.1f} MB/s"
            else:
                speed_text = f"{upload_speed/1024:.1f} KB/s"
        else:
            speed_text = "Very Fast"
        
        return True, upload_time, speed_text, sent_message
        
    except Exception as e:
        return False, 0, str(e), None

# ---------- HANDLE TEXT MESSAGES (FOR DM) ----------
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    terabox_domains = ['terabox.com', 'terabox.app', 'teraboxapp.com', 'teraboxurl.com', '1024tera.com', '1024tera.co', '1024terabox.com', '1024-terabox.com', 'mirrobox.com', 'nephobox.com', 'freeterabox.com', '4funbox.com', '4funbox.co', 'momerybox.com', 'tibibox.com', 'terabox.fun', 'terabox.link', 'teraboxshare.com', 'teraboxsharefile.com', 'teraboxlink.com', 'terasharelink.com', 'terasharefile.com', 'terashareus.com', 'gibibox.com', 'pebibox.com', 'fancybox.in', 'bestclouddrive.com', '4funbox.in', 'teraboxfree.com', 'terabox.club', 'terabox.click']
    is_terabox_link = any(domain in message_text.lower() for domain in terabox_domains)
    
    if is_terabox_link:
        await process_terabox_link(update, context, message_text, is_private=True)

# ---------- COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.message.chat.id
    
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

async def genny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # FIRST CHECK SUBSCRIPTION - ALWAYS
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

# ---------- CALLBACK HANDLER ----------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # ✅ FIRST CHECK FILE SIZE BEFORE DOWNLOADING
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(direct_link) as resp:
                content_length = resp.headers.get('Content-Length')
                if content_length:
                    size_bytes = int(content_length)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Check if file is larger than 100MB
                    if size_mb > 300:
                        await q.edit_message_text(
                            f"❌ **File Too Large**\n\n"
                            f"📁 Title: {title}\n"
                            f"📦 Size: {format_size(size_bytes)}\n\n"
                            f"⚠️ Telegram limits: Max 300MB\n"
                            f"📥 Use Direct Download link instead.\n\n"
                            f"{CREDIT}"
                        )
                        return
    except:
        pass  # If we can't check size, continue with download
    
    await q.edit_message_text(f"🎬 **STARTING DOWNLOAD**\n\n📁 {title}\n📦 {file_size}")
    
    file_path = await enhanced_download_with_progress(direct_link, q.message, context, title)
    
    if not file_path:
        return
    
    # Check file size after download
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    
    # ✅ REDUCED TO 300MB LIMIT
    if size_mb > 300:
        await q.edit_message_text(
            f"❌ **File Too Large for Telegram**\n\n"
            f"📁 Title: {title}\n"
            f"📦 Size: {format_size(size_bytes)}\n\n"
            f"⚠️ Telegram limit: 300MB\n"
            f"📥 Use Direct Download link:\n{direct_link}\n\n"
            f"{CREDIT}"
        )
        os.remove(file_path)
        return
    
    try:
        success, upload_time, speed_text, sent_message = await simple_upload_to_telegram(
            file_path, title, q.message, context, user_info
        )
        
        if success and sent_message:
            # ✅ FORWARD VIDEO AND BOTH LINKS TO SAVE GROUP
            await forward_video_to_save_group(
                context, sent_message, user_info, title, 
                format_size(size_bytes), direct_link, original_link
            )
            
            await asyncio.sleep(2)
            await q.message.delete()
            
        else:
            await q.edit_message_text(f"❌ Upload failed: {speed_text}")
            
    except Exception as e:
        error_msg = str(e)
        if "File too large" in error_msg:
            await q.edit_message_text("❌ File too large for Telegram (300MB limit)\nUse Direct Download")
        elif "timed out" in error_msg:
            await q.edit_message_text("❌ Upload timeout! Slow internet connection.\nTry Direct Download")
        else:
            await q.edit_message_text(f"❌ Upload failed: {error_msg[:100]}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ---------- ADDITIONAL COMMANDS ----------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await check_and_require_subscription(update, context)
    if not is_subscribed:
        return
    
    help_text = (
        "🤖 **Terabox Downloader Bot Help**\n\n"
        "📌 **Available Commands:**\n"
        "/start - Start the bot\n"
        "/genny <link> - Download terabox link (in groups)\n"
        "/help - Show this help message\n"
        "/info - Show your information\n\n"
        "📌 **How to use:**\n"
        "**In Private Chat:** Simply send Terabox links directly\n"
        "**In Groups:** Use /genny <terabox-link>\n\n"
        "📌 **Example Links:**\n"
        "• https://terabox.com/s/...\n"
        "• https://www.terabox.com/s/...\n"
        "• https://teraboxapp.com/s/...\n\n"
        f"{CREDIT}"
    )
    await update.message.reply_text(help_text)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ---------- ADMIN COMMANDS ----------
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    ADMIN_IDS = [7804119193]
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return
    
    stats_text = (
        f"📊 **BOT STATISTICS**\n\n"
        f"👥 Total Users: {len(user_data)}\n"
        f"🔄 Active Sessions: {len(sessions)}\n"
        f"⏰ Cooldown Users: {len(user_last)}\n"
        f"💾 Save Group: {SAVE_GROUP_ID}\n\n"
        f"📢 Channel: {CHANNEL_USERNAME}\n"
        f"👥 Group: {GROUP_USERNAME}\n\n"
        f"✅ **Allowed Groups:**\n"
    )
    
    for group_id, group_name in ALLOWED_GROUPS.items():
        stats_text += f"• {group_name} ({group_id})\n"
    
    await update.message.reply_text(stats_text)

async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to manually send links to save group"""
    user = update.effective_user
    
    ADMIN_IDS = [7804119193]
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /links <original_link> <direct_link> [title]")
        return
    
    original_link = context.args[0]
    direct_link = context.args[1]
    title = context.args[2] if len(context.args) > 2 else "Unknown"
    
    user_info = {
        'user_id': user.id,
        'username': user.username or 'Admin',
        'first_name': user.first_name,
        'last_name': user.last_name or '',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        await send_links_to_save_group(context, user_info, original_link, direct_link, title, "Unknown")
        await update.message.reply_text("✅ Links sent to save group!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ---------- MAIN FUNCTION ----------
def main():
    load_user_data()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("genny", genny))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("links", links_command))
    
    # Add message handler for text messages in private chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    app.add_handler(CallbackQueryHandler(buttons))
    
    print("=" * 60)
    print("🤖 TERABOX DOWNLOADER BOT STARTED")
    print("=" * 60)
    print(f"📢 Channel: {CHANNEL_USERNAME}")
    print(f"👥 Group: {GROUP_USERNAME}")
    print(f"💾 Save Group ID: {SAVE_GROUP_ID}")
    print("=" * 60)
    print("✅ **NEW FEATURE:** Direct DM Support")
    print("📱 Private Chat: Send links directly")
    print("👥 Groups: Use /genny command")
    print("=" * 60)
    print("✅ **ALL LINKS WILL BE SENT TO SAVE GROUP:**")
    print("1. ✅ User sends Terabox link → Both links saved")
    print("2. ✅ Direct download link → Saved separately")
    print("3. ✅ Original Terabox link → Saved separately")
    print("4. ✅ Video download via Telegram → Video + Both links saved")
    print("=" * 60)
    print(f"✅ Users MUST join channel & group to use bot")
    print(f"✅ Allowed Groups: {len(ALLOWED_GROUPS)}")
    print(f"👤 Loaded Users: {len(user_data)}")
    print("=" * 60)
    print("✅ Bot is ready to use!")
    print("=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()