#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          CONTENT CREATOR PRO BOT  v3.0                                      ║
║          Made with ❤️  by Drenchack                                         ║
║          Telegram: @drenchack                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

A professional Telegram bot for content creators with 30+ content categories.
All features use FREE APIs - no paid subscriptions required.

Features:
  Core:       /sports /bible /game /design /motivation /influencer
              /shop /tech /others
  Enhanced:   /weather /youtube /tweet /hashtags /business /crypto
              /ai /music /podcast /image /news /joke /fact
  Premium:    /roast /story /recipe /fitness /travel /mindset
              /affirmation /horoscope /dictionary /translate
              /qr /poll /quiz /meme /challenge /namecard
  Utilities:  /subscribe /reminder /settings /setcity /help /stats
"""

from dotenv import load_dotenv
load_dotenv()
import os
import sys
import json
import random
import hashlib
import html as html_mod
import threading
import time
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
import urllib.parse

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

try:
    import sqlite3
    HAS_DB = True
except ImportError:
    HAS_DB = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TELEGRAM_TOKEN      = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
COINGECKO_API_KEY   = os.environ.get("COINGECKO_API_KEY", None)
NEWSAPI_KEY         = os.environ.get("NEWSAPI_KEY", None)
BOT_VERSION         = "3.0.0"
BOT_AUTHOR          = "Drenchack"
BOT_AUTHOR_LINK     = "https://t.me/drenchack"

# ─── API Endpoints ─────────────────────────────────────────────────────────────
ESPN_BASE        = "http://site.api.espn.com/apis/site/v2/sports"
BIBLE_API_URL    = "https://bible-api.com"
FREETOGAME_API   = "https://www.freetogame.com/api"
NEWS_MIRROR      = "https://saurav.tech/NewsAPI"
DESIGN_QUOTES    = "https://dummyjson.com/quotes"
FAKESTORE        = "https://fakestoreapi.com"
WEATHER_API      = "https://api.open-meteo.com/v1/forecast"
GEO_API          = "https://geocoding-api.open-meteo.com/v1/search"
POLLINATIONS_IMG = "https://pollinations.ai/p"
COINGECKO_API    = "https://api.coingecko.com/api/v3"
AUDIO_DB         = "https://www.theaudiodb.com/api/v1/json/2"
JOKE_API         = "https://v2.jokeapi.dev/joke"
FACT_API         = "https://uselessfacts.jsph.pl/random.json"
TRIVIA_API       = "https://opentdb.com/api.php"
DICTIONARY_API   = "https://api.dictionaryapi.dev/api/v2/entries/en"
COUNTRY_API      = "https://restcountries.com/v3.1"
QR_API           = "https://api.qrserver.com/v1/create-qr-code"
MEME_API         = "https://meme-api.com/gimme"
ADVICE_API       = "https://api.adviceslip.com/advice"
AFFIRMATION_API  = "https://www.affirmations.dev"
COCKTAIL_API     = "https://www.thecocktaildb.com/api/json/v1/1"
MEAL_API         = "https://www.themealdb.com/api/json/v1/1"
DOG_API          = "https://dog.ceo/api/breeds/image/random"
CAT_FACT_API     = "https://catfact.ninja/fact"
NUMBER_API       = "http://numbersapi.com"

# ─── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_LAT  = 40.7128
DEFAULT_LON  = -74.0060
DEFAULT_CITY = "New York"
DB_PATH      = os.environ.get("DB_PATH", "bot_data.db")

# ─── In-memory state (fallback when DB unavailable) ───────────────────────────
_mem_subscriptions: Dict[int, List[str]] = {}   # chat_id → [categories]
_mem_settings: Dict[int, dict] = {}             # user_id → settings
_bot_stats = {"total_requests": 0, "commands_used": defaultdict(int)}


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def init_db():
    if not HAS_DB:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER, chat_id INTEGER, category TEXT,
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, chat_id, category))""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        city TEXT DEFAULT 'New York',
        lat REAL DEFAULT 40.7128,
        lon REAL DEFAULT -74.0060,
        reminder_time TEXT DEFAULT '09:00',
        language TEXT DEFAULT 'en',
        weekly_theme_idx INTEGER DEFAULT 0,
        timezone TEXT DEFAULT 'UTC')""")
    c.execute("""CREATE TABLE IF NOT EXISTS bot_stats (
        date TEXT, command TEXT, count INTEGER,
        PRIMARY KEY (date, command))""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_commands INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()


def db_upsert_user(user_id: int, username: str):
    if not HAS_DB:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO user_profiles (user_id, username) VALUES (?,?)
        ON CONFLICT(user_id) DO UPDATE SET username=?, last_seen=CURRENT_TIMESTAMP,
        total_commands=total_commands+1""", (user_id, username, username))
    conn.commit()
    conn.close()


def db_add_subscription(user_id: int, chat_id: int, category: str):
    if not HAS_DB:
        _mem_subscriptions.setdefault(chat_id, [])
        if category not in _mem_subscriptions[chat_id]:
            _mem_subscriptions[chat_id].append(category)
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO subscriptions (user_id,chat_id,category) VALUES (?,?,?)",
              (user_id, chat_id, category))
    conn.commit()
    conn.close()


def db_remove_subscription(user_id: int, chat_id: int, category: str):
    if not HAS_DB:
        if chat_id in _mem_subscriptions:
            _mem_subscriptions[chat_id] = [c for c in _mem_subscriptions[chat_id] if c != category]
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subscriptions WHERE user_id=? AND chat_id=? AND category=?",
              (user_id, chat_id, category))
    conn.commit()
    conn.close()


def db_get_subscriptions(chat_id: int) -> List[str]:
    if not HAS_DB:
        return _mem_subscriptions.get(chat_id, [])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM subscriptions WHERE chat_id=?", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def db_get_all_subscriptions() -> List[tuple]:
    if not HAS_DB:
        result = []
        for chat_id, cats in _mem_subscriptions.items():
            for cat in cats:
                result.append((chat_id, cat))
        return result
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT chat_id, category FROM subscriptions")
    rows = c.fetchall()
    conn.close()
    return rows


def db_set_user_setting(user_id: int, **kwargs):
    if not HAS_DB:
        _mem_settings.setdefault(user_id, _default_settings())
        _mem_settings[user_id].update(kwargs)
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM user_settings WHERE user_id=?", (user_id,))
    existing = c.fetchone()
    if existing:
        fields = ", ".join([f"{k}=?" for k in kwargs])
        values = list(kwargs.values()) + [user_id]
        c.execute(f"UPDATE user_settings SET {fields} WHERE user_id=?", values)
    else:
        all_keys = list(kwargs.keys()) + ["user_id"]
        placeholders = ",".join(["?"] * len(all_keys))
        values = list(kwargs.values()) + [user_id]
        c.execute(f"INSERT INTO user_settings ({','.join(all_keys)}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()


def _default_settings():
    return {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON,
            "reminder_time": "09:00", "language": "en", "weekly_theme_idx": 0, "timezone": "UTC"}


def db_get_user_setting(user_id: int) -> dict:
    default = _default_settings()
    if not HAS_DB:
        return _mem_settings.get(user_id, default)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["user_id", "city", "lat", "lon", "reminder_time", "language", "weekly_theme_idx", "timezone"]
        d = {k: v for k, v in zip(keys, row)}
        d.pop("user_id", None)
        return d
    return default


def db_get_total_users() -> int:
    if not HAS_DB:
        return len(_mem_settings)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_profiles")
    count = c.fetchone()[0]
    conn.close()
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_seed(category: str) -> int:
    today = date.today().isoformat()
    seed_str = f"{category}-{today}"
    return int(hashlib.md5(seed_str.encode()).hexdigest(), 16)


def fetch_json(url: str, params: dict = None, headers: dict = None, timeout: int = 15) -> Any:
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def sanitize(text: str) -> str:
    return html_mod.escape(str(text))


def truncate(text: str, max_len: int = 100) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def track_command(cmd: str):
    _bot_stats["total_requests"] += 1
    _bot_stats["commands_used"][cmd] += 1


def progress_bar(value: float, max_val: float = 100, width: int = 10) -> str:
    filled = int((value / max_val) * width)
    return "█" * filled + "░" * (width - filled)


# ═══════════════════════════════════════════════════════════════════════════════
# BRANDING & KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════════════

BRAND_FOOTER = f"\n\n<i>🤖 Powered by <b>ContentPro Bot</b> | Made by <a href='{BOT_AUTHOR_LINK}'>{BOT_AUTHOR}</a></i>"

WELCOME_ART = """
╔═══════════════════════════════════╗
║   🚀  CONTENT CREATOR PRO BOT    ║
║       Made by  D R E N C H A C K  ║
╚═══════════════════════════════════╝"""


def make_keyboard(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


MAIN_KB = make_keyboard([
    [InlineKeyboardButton("⚽ Sports",     callback_data="cmd_sports"),
     InlineKeyboardButton("📖 Bible",      callback_data="cmd_bible"),
     InlineKeyboardButton("🎮 Game",       callback_data="cmd_game")],
    [InlineKeyboardButton("🎨 Design",     callback_data="cmd_design"),
     InlineKeyboardButton("💪 Motivation", callback_data="cmd_motivation"),
     InlineKeyboardButton("📱 Influencer", callback_data="cmd_influencer")],
    [InlineKeyboardButton("🛒 Shop",       callback_data="cmd_shop"),
     InlineKeyboardButton("💻 Tech",       callback_data="cmd_tech"),
     InlineKeyboardButton("🔥 Others",     callback_data="cmd_others")],
    [InlineKeyboardButton("🌤 Weather",    callback_data="cmd_weather"),
     InlineKeyboardButton("▶️ YouTube",    callback_data="cmd_youtube"),
     InlineKeyboardButton("🐦 Tweet",      callback_data="cmd_tweet")],
    [InlineKeyboardButton("# Hashtags",    callback_data="cmd_hashtags"),
     InlineKeyboardButton("💼 Business",   callback_data="cmd_business"),
     InlineKeyboardButton("₿ Crypto",      callback_data="cmd_crypto")],
    [InlineKeyboardButton("🤖 AI Tools",   callback_data="cmd_ai"),
     InlineKeyboardButton("🎵 Music",      callback_data="cmd_music"),
     InlineKeyboardButton("🎙 Podcast",    callback_data="cmd_podcast")],
    [InlineKeyboardButton("📰 News",       callback_data="cmd_news"),
     InlineKeyboardButton("😂 Joke",       callback_data="cmd_joke"),
     InlineKeyboardButton("🧠 Fun Fact",   callback_data="cmd_fact")],
    [InlineKeyboardButton("🔥 Roast Me",   callback_data="cmd_roast"),
     InlineKeyboardButton("📖 Story",      callback_data="cmd_story"),
     InlineKeyboardButton("🍽 Recipe",     callback_data="cmd_recipe")],
    [InlineKeyboardButton("💪 Fitness",    callback_data="cmd_fitness"),
     InlineKeyboardButton("✈️ Travel",     callback_data="cmd_travel"),
     InlineKeyboardButton("🧘 Mindset",    callback_data="cmd_mindset")],
    [InlineKeyboardButton("⭐ Horoscope",  callback_data="cmd_horoscope"),
     InlineKeyboardButton("📚 Dictionary", callback_data="cmd_dictionary"),
     InlineKeyboardButton("🎯 Quiz",       callback_data="cmd_quiz")],
    [InlineKeyboardButton("🌍 Country",    callback_data="cmd_country"),
     InlineKeyboardButton("🎉 Challenge",  callback_data="cmd_challenge"),
     InlineKeyboardButton("🖼 Image",      callback_data="cmd_image")],
    [InlineKeyboardButton("🔔 Subscribe",  callback_data="cmd_show_subscribe"),
     InlineKeyboardButton("⏰ Reminder",   callback_data="cmd_show_reminder"),
     InlineKeyboardButton("📊 My Stats",   callback_data="cmd_mystats")],
])


# ═══════════════════════════════════════════════════════════════════════════════
# CORE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_upsert_user(user.id, user.username or user.first_name)
    total_users = db_get_total_users()

    text = (
        f"<pre>{WELCOME_ART}</pre>\n\n"
        f"👋 Welcome, <b>{sanitize(user.first_name)}</b>!\n\n"
        f"<b>ContentPro Bot</b> generates unique content across <b>30+ categories</b> "
        f"for your social media, blogs &amp; creative work.\n\n"
        f"✅ <b>100% Free APIs</b> - No subscriptions needed\n"
        f"📅 <b>Fresh content daily</b> - Changes every 24 hours\n"
        f"🔔 <b>Auto-delivery</b> - Subscribe &amp; receive daily content\n"
        f"🌍 <b>Global</b> - Weather, news &amp; trends worldwide\n\n"
        f"<b>👥 Community:</b> {total_users:,} creators using this bot\n\n"
        f"🎯 <b>Tap any button below to get started!</b>\n\n"
        f"<i>Type /help for the full command list</i>"
    )
    await update.message.reply_html(text, reply_markup=MAIN_KB)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"<b>📖 ContentPro Bot - Complete Command List</b>\n\n"
        f"<b>━━ CORE CONTENT ━━</b>\n"
        f"/sports - Live scores &amp; news\n"
        f"/bible - Daily verse + prayer\n"
        f"/game - Trending games &amp; tips\n"
        f"/design - Design tips &amp; challenges\n"
        f"/motivation - Quotes &amp; affirmations\n"
        f"/influencer - Growth strategies\n"
        f"/shop - Trending products\n"
        f"/tech - Tech news &amp; tips\n"
        f"/others - Viral content ideas\n\n"
        f"<b>━━ ENHANCED CONTENT ━━</b>\n"
        f"/weather - Local weather insights\n"
        f"/youtube - YouTube trends &amp; tips\n"
        f"/tweet - Viral thread templates\n"
        f"/hashtags - Optimized hashtag sets\n"
        f"/business - Business &amp; startup news\n"
        f"/crypto - Live crypto prices\n"
        f"/ai - AI tools &amp; news\n"
        f"/music - Music trends &amp; ideas\n"
        f"/podcast - Podcast ideas &amp; tips\n"
        f"/news - Breaking global news\n"
        f"/joke - Random jokes\n"
        f"/fact - Mind-blowing facts\n\n"
        f"<b>━━ PREMIUM FEATURES ━━</b>\n"
        f"/roast - Savage roast generator\n"
        f"/story - AI story starter\n"
        f"/recipe - Random recipe idea\n"
        f"/fitness - Workout &amp; fitness tips\n"
        f"/travel - Travel destination ideas\n"
        f"/mindset - Deep mindset content\n"
        f"/horoscope - Daily horoscope\n"
        f"/dictionary [word] - Word definition\n"
        f"/quiz - Random trivia quiz\n"
        f"/country - Random country facts\n"
        f"/challenge - 30-day challenge ideas\n"
        f"/image [prompt] - AI image generation\n"
        f"/meme - Random meme\n\n"
        f"<b>━━ UTILITIES ━━</b>\n"
        f"/subscribe - Daily auto-content\n"
        f"/reminder - Schedule reminders\n"
        f"/setcity [city] - Set location\n"
        f"/settings - Your preferences\n"
        f"/stats - Bot statistics\n"
        f"/start - Main menu\n\n"
        f"{BRAND_FOOTER}"
    )
    await update.message.reply_html(text, reply_markup=MAIN_KB)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cmd = query.data.replace("cmd_", "")

    if cmd == "show_subscribe":
        await show_subscribe_menu(update, context, is_callback=True)
        return
    elif cmd == "show_reminder":
        await show_reminder_menu(update, context, is_callback=True)
        return
    elif cmd == "mystats":
        await cmd_mystats(update, context, is_callback=True)
        return
    elif cmd == "back_main":
        await query.edit_message_text("🏠 Main Menu", reply_markup=MAIN_KB, parse_mode=ParseMode.HTML)
        return
    elif cmd.startswith("sub_"):
        category = cmd.replace("sub_", "")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db_add_subscription(user_id, chat_id, category)
        await query.answer(f"✅ Subscribed to {category}!", show_alert=True)
        await show_subscribe_menu(update, context, is_callback=True)
        return
    elif cmd.startswith("unsub_"):
        category = cmd.replace("unsub_", "")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db_remove_subscription(user_id, chat_id, category)
        await query.answer(f"❌ Unsubscribed from {category}", show_alert=True)
        await show_subscribe_menu(update, context, is_callback=True)
        return

    handlers = {
        "sports": cmd_sports, "bible": cmd_bible, "game": cmd_game,
        "design": cmd_design, "motivation": cmd_motivation,
        "influencer": cmd_influencer, "shop": cmd_shop,
        "tech": cmd_tech, "others": cmd_others,
        "weather": cmd_weather, "youtube": cmd_youtube,
        "tweet": cmd_tweet, "hashtags": cmd_hashtags,
        "business": cmd_business, "crypto": cmd_crypto,
        "ai": cmd_ai, "music": cmd_music, "podcast": cmd_podcast,
        "news": cmd_news, "joke": cmd_joke, "fact": cmd_fact,
        "roast": cmd_roast, "story": cmd_story, "recipe": cmd_recipe,
        "fitness": cmd_fitness, "travel": cmd_travel,
        "mindset": cmd_mindset, "horoscope": cmd_horoscope,
        "dictionary": cmd_dictionary, "quiz": cmd_quiz,
        "country": cmd_country, "challenge": cmd_challenge,
        "image": cmd_image, "meme": cmd_meme,
    }

    handler = handlers.get(cmd)
    if handler:
        track_command(cmd)
        try:
            await query.edit_message_text(f"⏳ Generating <b>{cmd}</b> content...", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await handler(update, context, is_callback=True)
    else:
        await query.edit_message_text("❓ Unknown command.", parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════════════════════
# SUBSCRIBE & REMINDER
# ═══════════════════════════════════════════════════════════════════════════════

async def show_subscribe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    chat_id = update.effective_chat.id
    subscribed = db_get_subscriptions(chat_id)

    categories = [
        ("sports","⚽"), ("bible","📖"), ("game","🎮"), ("design","🎨"),
        ("motivation","💪"), ("influencer","📱"), ("shop","🛒"), ("tech","💻"),
        ("others","🔥"), ("weather","🌤"), ("youtube","▶️"), ("business","💼"),
        ("crypto","₿"), ("ai","🤖"), ("music","🎵"), ("podcast","🎙"),
        ("news","📰"), ("fitness","🏋"), ("travel","✈️"), ("mindset","🧘"),
    ]

    text = (
        "<b>🔔 Daily Content Subscriptions</b>\n\n"
        "Tap to toggle ON/OFF. Active categories will be delivered daily.\n\n"
        f"<b>Active:</b> {len(subscribed)} categories\n"
    )

    keyboard = []
    row = []
    for i, (cat, emoji) in enumerate(categories):
        is_on = cat in subscribed
        label = f"{'✅' if is_on else '⬜'} {emoji} {cat}"
        prefix = "unsub" if is_on else "sub"
        row.append(InlineKeyboardButton(label, callback_data=f"cmd_{prefix}_{cat}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="cmd_back_main")])

    markup = InlineKeyboardMarkup(keyboard)
    if is_callback:
        try:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception:
            await update.callback_query.message.reply_html(text, reply_markup=markup)
    else:
        await update.message.reply_html(text, reply_markup=markup)


async def show_reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    text = (
        "<b>⏰ Daily Reminder Setup</b>\n\n"
        "Schedule automatic content delivery to this chat.\n\n"
        "<b>Commands:</b>\n"
        "▫️ /setreminder 09:00 — Set delivery time\n"
        "▫️ /setcategories sports,tech,bible — Choose categories\n"
        "▫️ /reminderstatus — View current settings\n"
        "▫️ /cancelreminder — Stop all reminders\n\n"
        "<b>Example setup:</b>\n"
        "<code>/setreminder 08:30</code>\n"
        "<code>/setcategories motivation,tech,bible,crypto</code>\n\n"
        "📅 Content refreshes daily at midnight.\n"
        "🌍 Set your timezone with /setcity for accurate timing."
    )
    markup = make_keyboard([[InlineKeyboardButton("🏠 Back", callback_data="cmd_back_main")]])
    if is_callback:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await update.message.reply_html(text)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_sports(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("sports")
    sports_list = [
        ("NFL 🏈", "football/nfl"),
        ("NBA 🏀", "basketball/nba"),
        ("MLB ⚾", "baseball/mlb"),
        ("NHL 🏒", "hockey/nhl"),
        ("EPL ⚽", "soccer/eng.1"),
    ]
    seed = generate_daily_seed("sports")
    lines = ["<b>⚽ SPORTS | Live Scores &amp; News</b>\n"]

    for league_name, league_path in sports_list:
        url = f"{ESPN_BASE}/{league_path}/scoreboard"
        data = fetch_json(url)
        if "error" in data:
            continue
        events = data.get("events", [])[:2]
        for event in events:
            comps = event.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            state = comps.get("status", {}).get("type", {}).get("description", "")
            team_info = []
            for c in competitors:
                abbrev = c.get("team", {}).get("abbreviation", "?")
                score = c.get("score", "0")
                team_info.append(f"{abbrev} {score}")
            if team_info:
                lines.append(f"  <b>{league_name}:</b> {' vs '.join(team_info)} | {state}")

    # Sports news
    try:
        news = fetch_json(f"{ESPN_BASE}/football/nfl/news")
        for a in news.get("articles", [])[:4]:
            t = a.get("headline", "")
            if t:
                lines.append(f"  📰 {sanitize(t)}")
    except Exception:
        pass

    ideas = [
        "🎬 Post match highlights with your commentary",
        "📊 Create a player stats comparison infographic",
        "🏆 Make a bracket prediction post this week",
        "📸 Behind-the-scenes stadium content",
        "🎯 Fantasy sports tips & lineup suggestions",
        "📅 Historic throwback moments this date",
    ]
    lines.append(f"\n<b>💡 Content Idea:</b>\n{ideas[seed % len(ideas)]}")

    content_tips = [
        "Post within 30 mins of game end for max reach",
        "Use team hashtags for organic discovery",
        "Polls ('Who wins tonight?') drive engagement",
        "Reaction videos to big plays get high views",
    ]
    lines.append(f"\n<b>📈 Creator Tip:</b>\n{content_tips[seed % len(content_tips)]}")

    response = "\n".join(lines) + BRAND_FOOTER
    if len(lines) < 4:
        response = "<b>⚽ SPORTS</b>\nNo live games right now. Check back during active game times!" + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_bible(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("bible")
    seed = generate_daily_seed("bible")
    random.seed(seed)
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id)
    theme_idx = settings.get("weekly_theme_idx", 0)

    data = fetch_json("https://bible-api.com/data/web/random")
    if "error" in data:
        data = fetch_json("https://bible-api.com/john+3:16")

    verse_ref  = data.get("reference", "John 3:16")
    verse_text = data.get("text", "For God so loved the world...").strip()
    translation= data.get("translation_name", "WEB")
    book       = verse_ref.split()[0] if " " in verse_ref else verse_ref

    topic_map = {
        "John":"Faith & Salvation","Psalm":"Praise & Worship","Proverbs":"Wisdom",
        "Matthew":"Discipleship","Romans":"Grace","Genesis":"Beginnings",
        "Isaiah":"Hope","Philippians":"Contentment","Ephesians":"Growth",
        "Psalms":"Worship","Luke":"Compassion","Hebrews":"Perseverance",
        "Revelation":"Eternal Hope","Corinthians":"Love","Timothy":"Leadership",
    }
    topic = topic_map.get(book, "God's Word")

    week_num = date.today().isocalendar()[1]
    weekly_themes = [
        "Walking in Faith","The Power of Prayer","Love & Compassion","Strength in Trials",
        "Gratitude & Thanksgiving","Wisdom & Understanding","Hope & Renewal",
        "Grace & Forgiveness","Courage & Boldness","Peace & Rest","Serve & Give",
        "Perseverance","Trust in God","Humility","Joy of the Lord","Faithfulness",
        "God's Promises","New Beginnings","Unity in Christ","Overcoming Fear",
        "Patience","Kindness","Self-Control","Worship & Praise","Renewing the Mind",
        "God's Love","Purpose & Calling","Spiritual Warfare","Abiding in Christ",
        "Light of the World","Salt of the Earth","The Narrow Path","Redeemed",
        "Living by the Spirit","Heavenly Treasure","The Good Shepherd","Bearing Fruit",
        "Armor of God","The Great Commission","Christ's Return","Divine Protection",
        "God's Provision","Honoring God","Faith Without Works","The Vine & Branches",
        "Living Stones","Chosen Generation","More Than Conquerors","Anchored in Hope",
        "Rooted in Love","The Blessed Life","Shining Bright","The Lord's Prayer",
    ]
    weekly_theme = weekly_themes[(week_num + theme_idx - 1) % len(weekly_themes)]
    week_day = date.today().strftime("%A")

    explanations = [
        f"This verse reveals the depth of <b>{topic.lower()}</b> in our walk with God. Let it anchor your spirit today.",
        f"Here we see God's timeless truth about <b>{topic.lower()}</b>. His Word never returns void — receive it fully.",
        f"The message centres on <b>{topic.lower()}</b> — a cornerstone of Christian life. Meditate on these words.",
        f"Divine wisdom about <b>{topic.lower()}</b> flows through this scripture. Allow it to reshape your perspective.",
    ]
    prayers = [
        f"Heavenly Father, thank You for Your Word. Help me grow in <b>{topic.lower()}</b> today. Guide my steps. In Jesus' name, Amen.",
        f"Lord, open my eyes to the depth of <b>{topic.lower()}</b> in my life. Let Your Word be a lamp to my feet. Amen.",
        f"Father, let the truth of <b>{topic.lower()}</b> produce fruit in my life. Fill me with Your Spirit. Amen.",
    ]
    declarations = [
        f"🗣 I declare that I walk in {topic.lower()} today.",
        f"🗣 I receive the gift of {topic.lower()} into my heart.",
        f"🗣 I am strengthened in {topic.lower()} through His grace.",
    ]
    action_steps = [
        "📝 Journal your response to this verse today",
        "🤝 Share this verse with someone who needs it",
        "🙏 Set a 5-minute prayer timer right now",
        "📖 Read the full chapter this verse comes from",
    ]

    response = (
        f"<b>📖 BIBLE | Daily Devotion</b>\n\n"
        f"📅 <b>{week_day}, {date.today().strftime('%B %d, %Y')}</b>\n"
        f"🎯 <b>Weekly Theme:</b> <i>{weekly_theme}</i>\n"
        f"💎 <b>Topic:</b> {topic}\n\n"
        f"<b>📜 {sanitize(verse_ref)}</b> ({translation})\n"
        f"<i>«{sanitize(verse_text)}»</i>\n\n"
        f"<b>✨ Reflection:</b>\n{explanations[seed % len(explanations)]}\n\n"
        f"<b>🙏 Prayer:</b>\n{prayers[seed % len(prayers)]}\n\n"
        f"<b>{declarations[seed % len(declarations)]}</b>\n\n"
        f"<b>✅ Action Step:</b>\n{action_steps[seed % len(action_steps)]}"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_game(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("game")
    seed = generate_daily_seed("game")
    data = fetch_json(f"{FREETOGAME_API}/games?sort-by=popularity")
    lines = ["<b>🎮 GAME | Trending Games &amp; Content</b>\n"]

    if "error" not in data and isinstance(data, list):
        lines.append("<b>🔥 Hot Free Games:</b>")
        for game in data[:6]:
            title  = sanitize(game.get("title","Unknown"))
            genre  = sanitize(game.get("genre","General"))
            platform = sanitize(game.get("platform","PC"))
            lines.append(f"  🎯 <b>{title}</b> | {genre} | {platform}")
    else:
        for g in ["Fortnite (Battle Royale)","Valorant (Tactical)","Apex Legends (BR)",
                  "GTA V (Action)","Minecraft (Sandbox)","Roblox (Platform)"]:
            lines.append(f"  🎯 {g}")

    hashtags = [
        "#GamingCommunity #GameOn #ViralGame #StreamHighlights #NewRelease #Gaming",
        "#GamerLife #EpicGaming #TwitchStreamer #GameTips #ContentCreator #GamingNews",
        "#IndieGame #Esports #Multiplayer #Speedrun #GameReview #TopGames",
    ]
    lines.append(f"\n<b># Trending Hashtags:</b>\n{hashtags[seed % len(hashtags)]}")

    ideas = [
        "🎬 Walkthrough guide for hottest new release",
        "🏆 Top 10 moments compilation from recent streams",
        "👀 First Impressions video - 10 mins max",
        "⚡ Speed run attempt with live commentary",
        "🆚 Game comparison: which is better?",
        "😂 Reacting to gaming fails compilation",
        "🏗 Epic build challenge in sandbox games",
        "💡 Beginner tips series (3 episodes)",
    ]
    lines.append(f"\n<b>💡 Today's Content Ideas:</b>")
    for i in range(3):
        lines.append(f"  {ideas[(seed + i * 2) % len(ideas)]}")

    thumb_tips = [
        "🖼 Use orange + blue contrast (proven CTR booster)",
        "😱 Add expressive reaction face for click-through",
        "📝 Max 4 bold words on thumbnail",
        "👁 Use arrows/circles to direct the eye",
        "✨ Add glow effects for a premium look",
    ]
    lines.append(f"\n<b>🖼 Thumbnail Tip:</b>\n{thumb_tips[seed % len(thumb_tips)]}")

    streaming = [
        "🎤 Read chat messages out loud — viewers love it",
        "📅 Set a consistent streaming schedule (2-3x/week)",
        "🤝 Raid another creator after your stream ends",
        "🎁 Set channel point rewards for engagement",
        "⏱ 2-4 hour streams outperform marathon sessions",
    ]
    lines.append(f"\n<b>📡 Stream Tip:</b>\n{streaming[seed % len(streaming)]}")
    response = "\n".join(lines) + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_design(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("design")
    seed = generate_daily_seed("design")
    random.seed(seed)

    quotes_data = fetch_json(f"{DESIGN_QUOTES}/random")
    quote_block = ""
    if "error" not in quotes_data:
        q = quotes_data.get("quote", "")
        a = quotes_data.get("author", "")
        if q:
            quote_block = f"\n<i>«{sanitize(q)}»</i> — <b>{sanitize(a)}</b>\n"

    tips = [
        "🎨 60-30-10 rule: 60% dominant, 30% secondary, 10% accent color",
        "📐 White space is design — let content breathe",
        "🔤 Limit to 2-3 fonts per project max",
        "📏 Use 8px grid systems for perfect alignment",
        "👁 Visual hierarchy: size → color → placement",
        "♿ Accessibility: 4.5:1 minimum contrast ratio for text",
        "💡 Micro-animations make interfaces feel alive",
        "📱 Design mobile-first, then scale up",
        "📊 F-pattern layout for text-heavy web pages",
        "↔️ Consistent spacing = professional look",
    ]
    challenges = [
        "Design a minimalist poster using ONLY typography",
        "Create a color palette from a photo you took today",
        "Redesign a famous logo with a modern twist",
        "Design a splash screen for a meditation app",
        "Create a 5-slide carousel post for Instagram",
        "Design a hero section in black and white only",
        "Create a magazine cover for a fictional brand",
        "Design 6 custom stickers based on emotions",
    ]
    tools = [
        "🖥 Figma — Collaborative UI design (free tier)",
        "🎨 Canva — Quick social graphics (free tier)",
        "🤖 Adobe Firefly — AI image generation",
        "🌈 Coolors.co — Instant color palettes",
        "📷 Unsplash — Free high-quality stock photos",
        "🔤 Fontjoy — Smart font pairing tool",
        "✂️ Remove.bg — Background removal",
        "🎭 Dribbble / Behance — Design inspiration",
    ]
    trends = [
        "AI-assisted design & prompt-based creation",
        "Bento grid layouts for social media",
        "Kinetic typography in short-form video",
        "Dark mode with vibrant neon accents",
        "Glassmorphism with frosted blur effects",
        "Minimal brutalist design revival",
        "3D elements integrated in flat design",
        "Accessible design as a selling point",
    ]
    palettes = [
        "🌅 Sunset: #FF6B6B + #FFA07A + #FFD700",
        "🌊 Ocean: #006994 + #40E0D0 + #F0F8FF",
        "🌿 Nature: #2D5A27 + #8FBC8F + #F5F5DC",
        "🌙 Midnight: #1A1A2E + #16213E + #E94560",
        "☀️ Minimal: #FAFAFA + #212121 + #FF4500",
        "🎆 Neon: #0D0D0D + #FF00FF + #00FFFF",
    ]

    response = (
        f"<b>🎨 DESIGN | Daily Creative Inspiration</b>\n"
        f"{quote_block}\n"
        f"<b>💡 Tip of the Day:</b>\n{tips[seed % len(tips)]}\n\n"
        f"<b>🏋 Design Challenge:</b>\n{challenges[seed % len(challenges)]}\n\n"
        f"<b>🔧 Tool Spotlight:</b>\n{tools[seed % len(tools)]}\n\n"
        f"<b>📈 Trending Style:</b>\n{trends[seed % len(trends)]}\n\n"
        f"<b>🎨 Today's Palette:</b>\n{palettes[seed % len(palettes)]}\n\n"
        f"<b>🔗 Resources:</b>\n"
        f"  coolors.co | fonts.google.com | behance.net | icons8.com"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("motivation")
    seed = generate_daily_seed("motivation")
    random.seed(seed)

    quote_text = "The only way to do great work is to love what you do."
    author = "Steve Jobs"

    q_data = fetch_json(f"https://qapi.vercel.app/api/random")
    if "error" not in q_data:
        quote_text = q_data.get("quote", quote_text)
        author = q_data.get("author", author)

    affirmations = [
        "I am capable of achieving greatness through consistent effort.",
        "Today holds opportunities I haven't yet imagined.",
        "I choose progress over perfection — always.",
        "My potential grows with every challenge I face.",
        "I am the architect of my life and I build with purpose.",
        "I deserve success and I am prepared to work for it.",
        "My mindset shapes my reality — I choose abundance.",
        "I am grateful for all I have and all I'm becoming.",
        "Every step forward counts, no matter how small.",
        "I attract greatness because I am greatness in progress.",
    ]
    actions = [
        "📝 Write down 3 things you're grateful for RIGHT NOW",
        "⏱ Set a 25-minute Pomodoro timer on ONE key task",
        "📞 Send an encouraging message to someone today",
        "📋 Review your goals and update your plan for this week",
        "🏃 Get up and exercise for just 15 minutes",
        "📚 Read for 20 minutes on a topic that grows you",
        "🚫 Eliminate ONE distraction from your space today",
        "🤝 Connect with one person in your industry",
    ]
    week_focus_list = [
        "Mindset","Discipline","Creativity","Connection","Growth","Service",
        "Balance","Resilience","Gratitude","Focus","Courage","Patience",
        "Health","Learning","Purpose","Abundance","Confidence","Integrity",
        "Leadership","Empathy","Innovation","Persistence","Optimism","Adaptability",
    ]
    weekly_focus = week_focus_list[(date.today().isocalendar()[1] - 1) % len(week_focus_list)]

    energy_levels = ["🔴 Low", "🟡 Medium", "🟢 High", "⚡ Maximum"]
    today_energy = energy_levels[seed % len(energy_levels)]

    daily_challenge = [
        "Do one thing today that scares you slightly",
        "Go one hour without your phone",
        "Talk to a stranger and learn their story",
        "Write your 5-year vision in 5 minutes",
        "Do 10 push-ups every hour today",
        "Write a handwritten note to someone you appreciate",
    ]

    response = (
        f"<b>💪 MOTIVATION | Daily Fuel</b>\n\n"
        f"<i>«{sanitize(quote_text)}»</i>\n"
        f"<b>— {sanitize(author)}</b>\n\n"
        f"<b>🌟 Affirmation:</b>\n{affirmations[seed % len(affirmations)]}\n\n"
        f"<b>✅ Action Step:</b>\n{actions[seed % len(actions)]}\n\n"
        f"<b>🎯 Weekly Focus:</b> <b>{weekly_focus}</b>\n"
        f"<b>⚡ Energy Level:</b> {today_energy}\n\n"
        f"<b>🏆 Daily Challenge:</b>\n{daily_challenge[seed % len(daily_challenge)]}\n\n"
        f"<i>«Consistency today creates the life you want tomorrow.»</i>"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_influencer(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("influencer")
    seed = generate_daily_seed("influencer")
    random.seed(seed)

    platform_insights = [
        "📱 <b>TikTok:</b> Hook in 1.5 sec. Trending sounds = 30% more reach. Post 1-4x/day.",
        "📸 <b>Instagram:</b> Reels get 3x reach. Carousels drive saves. Stories daily = retention.",
        "▶️ <b>YouTube:</b> 8-12 min videos maximise ad revenue. Shorts for top-of-funnel reach.",
        "💼 <b>LinkedIn:</b> Personal story + professional insight = viral. Post Tue-Thu 8-10am.",
        "🐦 <b>Twitter/X:</b> Thread + hot take = viral. Post 3-5x/day for algorithmic boost.",
        "📌 <b>Pinterest:</b> SEO-rich descriptions. Infographics get 200% more saves.",
        "🎙 <b>Podcasts:</b> Consistency > quality early on. Weekly drops build loyal audience.",
    ]
    strategies = [
        "Behind-the-scenes content builds 40% more authentic trust",
        "UGC campaigns boost engagement 4x vs brand content",
        "Collab with creators ±20% your size for best growth",
        "Educational content positions you as the go-to authority",
        "Emotional storytelling creates the most loyal audiences",
        "Content series create anticipation and return viewers",
        "Polls + Q&As = algorithm signals + audience research",
    ]
    monetization = [
        "💰 Brand deals: Pitch 5 brands in your niche this week",
        "📦 Digital products: Template, guide, or preset = passive income",
        "🔗 Affiliate: Share 3 tools you actually use with honest reviews",
        "⭐ Membership: Exclusive content via Patreon = recurring revenue",
        "🧑‍🏫 Coaching: 1:1 sessions at premium rates using your expertise",
        "👕 Merch: Start with print-on-demand (zero upfront cost)",
        "📚 Course: Package your knowledge into an online course",
    ]
    hot_niches = [
        "🤖 AI tools & automation for everyday people",
        "💚 Sustainable living & eco-friendly lifestyle",
        "💸 Personal finance & wealth building for beginners",
        "🧬 Health optimisation & biohacking",
        "🌍 Digital nomad & remote work lifestyle",
        "🧠 Mental health, therapy & emotional intelligence",
        "💼 Side hustles that scale to full-time income",
        "📚 BookTok & reading community content",
    ]
    growth_tips = [
        "Post consistently 3-5x/week minimum",
        "Engage within first 60 mins of posting (signals algorithm)",
        "Cross-post to all platforms from ONE piece of content",
        "Study your best-performing post and recreate the formula",
        "Spend 30 mins/day engaging with others in your niche",
    ]
    collab_tips = [
        "DM 3 creators in your niche for a collab this week",
        "Guest post on a larger creator's platform",
        "Do a live session with a complementary creator",
        "Create a shared resource with another creator",
    ]

    response = (
        f"<b>📱 INFLUENCER | Growth &amp; Strategy</b>\n\n"
        f"<b>📊 Platform Insight:</b>\n{platform_insights[seed % len(platform_insights)]}\n\n"
        f"<b>🎯 Content Strategy:</b>\n{strategies[seed % len(strategies)]}\n\n"
        f"<b>💰 Monetization Tip:</b>\n{monetization[seed % len(monetization)]}\n\n"
        f"<b>🔥 Hot Niche:</b>\n{hot_niches[seed % len(hot_niches)]}\n\n"
        f"<b>📈 Growth Tip:</b>\n{growth_tips[seed % len(growth_tips)]}\n\n"
        f"<b>🤝 Collab Idea:</b>\n{collab_tips[seed % len(collab_tips)]}\n\n"
        f"<b>📅 Content Calendar:</b>\n"
        f"  Mon/Wed/Fri → Value (tips, tutorials, how-tos)\n"
        f"  Tue/Thu → Engagement (polls, questions, debates)\n"
        f"  Sat/Sun → Personal (BTS, stories, lifestyle)"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("shop")
    seed = generate_daily_seed("shop")
    random.seed(seed)
    products = fetch_json(f"{FAKESTORE}/products?limit=8")
    lines = ["<b>🛒 SHOP | Trending Products &amp; E-Commerce</b>\n"]

    if "error" not in products and isinstance(products, list):
        lines.append("<b>Featured Products:</b>")
        for i, p in enumerate(products[:5], 1):
            title    = sanitize(p.get("title","Product"))
            price    = p.get("price","N/A")
            category = sanitize(p.get("category","General")).title()
            rating   = p.get("rating",{}).get("rate","N/A")
            count    = p.get("rating",{}).get("count","N/A")
            lines.append(f"  {i}. <b>{truncate(title, 50)}</b>")
            lines.append(f"     💲{price} | {category} | ⭐{rating} ({count} reviews)")
    else:
        for cat in ["Electronics & Gadgets","Fashion & Apparel","Home & Kitchen",
                    "Beauty & Personal Care","Sports & Outdoors","Books & Media"]:
            lines.append(f"  🛍 {cat}")

    trends = [
        "♻️ Sustainable/eco products growing 40%+ year-over-year",
        "📦 Subscription boxes thriving in beauty, food, fitness",
        "📲 TikTok Shop & Instagram Checkout driving impulse buys",
        "🎁 Personalised/custom products command 25%+ premium",
        "🏠 DTC brands outperforming traditional retail channels",
        "🎥 Live shopping events seeing 10x conversion vs static",
        "💳 Buy Now Pay Later (BNPL) increasing cart value 30%",
    ]
    lines.append(f"\n<b>📈 Market Trend:</b>\n{trends[seed % len(trends)]}")

    review_ideas = [
        "📹 A vs B comparison video for similar products",
        "📦 Unboxing with honest first impressions",
        "💰 '5 Products Under $50 That Changed My Life'",
        "🎄 Seasonal gift guide post (high search traffic)",
        "📊 'Products I bought on Amazon this month' series",
        "⭐ 'Overrated vs Underrated' product debate",
    ]
    lines.append(f"\n<b>💡 Content Idea:</b>\n{review_ideas[seed % len(review_ideas)]}")

    ecom_tips = [
        "📸 Consistent white background product photos = trust",
        "⏰ Flash sales & countdown timers boost urgency",
        "📧 Abandoned cart emails recover 15-20% of lost sales",
        "💬 Display reviews prominently (social proof = sales)",
        "📱 Mobile checkout must be 3 clicks or less",
        "🔁 Upsell: 'Customers also bought...' section",
    ]
    lines.append(f"\n<b>🛍 E-Commerce Tip:</b>\n{ecom_tips[seed % len(ecom_tips)]}")
    response = "\n".join(lines) + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_tech(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("tech")
    seed = generate_daily_seed("tech")
    news_data = fetch_json(f"{NEWS_MIRROR}/top-headlines/category/technology/us.json")
    lines = ["<b>💻 TECH | News, Trends &amp; Tips</b>\n"]

    articles = news_data.get("articles", []) if "error" not in news_data else []
    if articles:
        lines.append("<b>📰 Top Tech Headlines:</b>")
        for a in articles[:6]:
            title  = a.get("title","")
            source = a.get("source",{}).get("name","")
            if title and title != "[Removed]":
                lines.append(f"  📌 {sanitize(truncate(title, 80))}")
                if source:
                    lines[-1] += f" <i>({sanitize(source)})</i>"
    else:
        lines.append("<b>📰 Tech Highlights:</b>")
        for h in ["AI is getting faster, cheaper, and more capable",
                  "Quantum computing breaking new performance records",
                  "Cybersecurity threats evolving with AI assistance",
                  "AR glasses making serious consumer comeback",
                  "Open-source AI models challenging proprietary ones"]:
            lines.append(f"  📌 {h}")

    content_angles = [
        "🤖 'How AI is changing [your industry]' explainer",
        "🔐 Cybersecurity tips every person should know",
        "📱 Upcoming gadget reviews and what to expect",
        "💾 Open-source tools that replace expensive software",
        "☁️ Cloud computing explained for non-techies",
        "🌱 Green tech — sustainable computing is the future",
        "🧱 Blockchain use cases beyond cryptocurrency",
        "⚡ Speed test: which phone/laptop is fastest in 2025",
    ]
    lines.append(f"\n<b>💡 Content Angle:</b>\n{content_angles[seed % len(content_angles)]}")

    quick_tips = [
        "🔐 Enable 2FA on EVERY account starting today",
        "🛡 Use a password manager — stop reusing passwords",
        "🔄 Keep all software updated for security patches",
        "💾 Backup with 3-2-1: 3 copies, 2 media types, 1 offsite",
        "🕵️ Use privacy-focused browsers (Brave/Firefox)",
        "📡 VPN on public Wi-Fi — non-negotiable",
        "🚫 Ad-blocker = faster browsing + privacy",
    ]
    lines.append(f"\n<b>⚡ Quick Tech Tip:</b>\n{quick_tips[seed % len(quick_tips)]}")

    quotes = [
        "\"The best way to predict the future is to invent it.\" — Alan Kay",
        "\"Technology is best when it brings people together.\" — Matt Mullenweg",
        "\"Move fast and break things — then fix them.\" — Tech Mantra",
        "\"Software is eating the world.\" — Marc Andreessen",
    ]
    lines.append(f"\n<i>{quotes[seed % len(quotes)]}</i>")
    response = "\n".join(lines) + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_others(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("others")
    seed = generate_daily_seed("others")
    random.seed(seed)

    viral_formats = [
        "📋 '10 Things Nobody Tells You About [Topic]' listicle",
        "🗣 Controversial opinion post with discussion hooks",
        "⏱ 'Day in the Life' with timestamps & chapters",
        "✨ Before/After transformation content",
        "🎯 Unique challenge with a twist on a trend",
        "📺 React to your old content (nostalgia wins)",
        "📬 Q&A answering DMs and comments",
        "🎭 POV skits tied to your niche",
        "🧵 Thread breaking down complex topic simply",
        "📖 Storytime with a lesson at the end",
    ]
    angles = [
        "Share a personal failure as a teachable lesson",
        "Mashup two unrelated niches for fresh perspective",
        "Create a roadmap: step-by-step how to achieve X",
        "Interview someone with opposing views",
        "Document a 30-day challenge with daily updates",
        "Give your hot take on something in your niche",
        "Explain something complex using simple analogies",
    ]
    hooks = [
        "\"Stop scrolling. This will change how you see [topic].\"",
        "\"I spent 5 years learning this. You get it in 5 mins.\"",
        "\"Everyone talks about X. Nobody talks about Y.\"",
        "\"This one insight doubled my results. Here it is.\"",
        "\"Most creators get this completely wrong.\"",
        "\"Save this. You'll thank me later.\"",
    ]
    algo_tips = [
        "⏰ Post when your audience is most active",
        "🎵 Use trending audio on TikTok/Reels for discovery",
        "💾 'Save this for later' CTA = algorithm signal",
        "⚡ First 3 seconds MUST hook — no slow intros",
        "📝 Always use captions for silent viewers",
        "🔁 Repurpose one video across 4+ platforms",
    ]
    categories = ["Fitness","Travel","Food","Finance","Relationships",
                  "Education","Music","Photography","Fashion","Home DIY",
                  "Pets","Parenting","Comedy","Health","Spirituality"]
    cat1 = categories[seed % len(categories)]
    cat2 = categories[(seed + 5) % len(categories)]

    response = (
        f"<b>🔥 OTHERS | Viral Content Engine</b>\n\n"
        f"<b>📹 Trending Format:</b>\n{viral_formats[seed % len(viral_formats)]}\n\n"
        f"<b>🎯 Content Angle:</b>\n{angles[seed % len(angles)]}\n\n"
        f"<b>🪝 Engagement Hook:</b>\n{hooks[seed % len(hooks)]}\n\n"
        f"<b>🧬 Niche Mashup Idea:</b>\n"
        f"Combine <b>{cat1}</b> + <b>{cat2}</b> for a unique angle\n\n"
        f"<b>📊 Algorithm Tip:</b>\n{algo_tips[seed % len(algo_tips)]}\n\n"
        f"<b>🏗 Post Structure:</b>\n"
        f"  1️⃣ Hook (first 3 sec/lines)\n"
        f"  2️⃣ Value (middle — deliver the promise)\n"
        f"  3️⃣ CTA (comment/share/save/follow)\n\n"
        f"<i>🔥 Done is better than perfect. Post something today!</i>"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("weather")
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id)
    lat  = settings.get("lat",  DEFAULT_LAT)
    lon  = settings.get("lon",  DEFAULT_LON)
    city = settings.get("city", DEFAULT_CITY)

    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,uv_index",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,sunrise,sunset,wind_speed_10m_max",
        "timezone": "auto", "forecast_days": 3,
    }
    data = fetch_json(WEATHER_API, params=params)
    wmo = {
        0:"☀️ Clear sky",1:"🌤 Mainly clear",2:"⛅ Partly cloudy",3:"☁️ Overcast",
        45:"🌫 Foggy",51:"🌦 Light drizzle",61:"🌧 Slight rain",63:"🌧 Moderate rain",
        65:"⛈ Heavy rain",71:"❄️ Slight snow",73:"❄️ Moderate snow",75:"❄️ Heavy snow",
        80:"🌦 Rain showers",95:"⛈ Thunderstorm",
    }
    if "error" in data:
        await _send(update, "<b>🌤 WEATHER</b>\n⚠️ Could not fetch weather. Use /setcity to set location.", is_callback)
        return

    cur = data.get("current", {})
    daily = data.get("daily", {})
    wcode    = cur.get("weather_code", 0)
    wdesc    = wmo.get(wcode, "🌡 Unknown")
    temp     = cur.get("temperature_2m","N/A")
    feels    = cur.get("apparent_temperature","N/A")
    humidity = cur.get("relative_humidity_2m","N/A")
    wind     = cur.get("wind_speed_10m","N/A")
    uv       = cur.get("uv_index","N/A")

    highs = daily.get("temperature_2m_max",[])
    lows  = daily.get("temperature_2m_min",[])
    sunrises = daily.get("sunrise",["","",""])
    sunsets  = daily.get("sunset",["","",""])
    days_labels = ["Today","Tomorrow","Day 3"]

    forecast_lines = []
    for i in range(min(3, len(highs))):
        h = highs[i] if i < len(highs) else "N/A"
        l = lows[i]  if i < len(lows)  else "N/A"
        wc = (daily.get("weather_code") or [wcode]*3)[i]
        wd = wmo.get(wc, "🌡")
        forecast_lines.append(f"  {days_labels[i]}: {wd} {h}°/{l}°C")

    content_map = {
        0:"☀️ Perfect golden hour lighting — shoot now!",
        1:"📸 Soft natural light — great for portraits",
        2:"🎨 Moody overcast = perfect diffused photography",
        3:"🏠 Indoor cozy content day — candles & coffee",
        45:"🌫 Fog creates atmospheric, cinematic shots",
        61:"🌧 Rainy window aesthetic is trending — shoot it",
        71:"❄️ Snow day = Winter wonderland content",
        95:"⛈ Storm B-roll is dramatic &amp; engaging",
    }
    content_tip = content_map.get(wcode, "🎬 Adapt your shoot to current conditions")

    uv_advice = "🟢 Safe" if float(str(uv) or 0) < 3 else ("🟡 Moderate" if float(str(uv) or 0) < 6 else "🔴 High — use SPF!")

    response = (
        f"<b>🌤 WEATHER | {sanitize(city)}</b>\n\n"
        f"<b>Now:</b> {wdesc}\n"
        f"🌡 {temp}°C (feels {feels}°C)\n"
        f"💧 Humidity: {humidity}% | 💨 Wind: {wind} km/h | ☀️ UV: {uv} {uv_advice}\n\n"
        f"<b>📅 3-Day Forecast:</b>\n" + "\n".join(forecast_lines) + "\n\n"
        f"🌅 Sunrise: {sunrises[0][-5:] if sunrises else 'N/A'} | "
        f"🌇 Sunset: {sunsets[0][-5:] if sunsets else 'N/A'}\n\n"
        f"<b>📸 Creator Tip:</b>\n{content_tip}\n\n"
        f"<i>📍 Change location: /setcity YourCity</i>"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("youtube")
    seed = generate_daily_seed("youtube")
    random.seed(seed)

    video_ideas = [
        "🎓 Ultimate beginner's guide to [topic in your niche]",
        "📦 Unboxing + honest 30-day review",
        "📅 'Day in the Life' with cinematic B-roll",
        "🆚 Product comparison: which is actually worth it?",
        "💡 '[Number] Things I Wish I Knew Before...'",
        "🏆 Year in review / Best of [topic] compilation",
        "❓ Answering your most asked DM questions",
        "🧪 Experiment: I tried [thing] for 30 days — here's what happened",
        "📊 Data deep-dive: the truth about [popular claim]",
        "🤝 Collab with a creator in adjacent niche",
    ]
    seo_tips = [
        "📝 Title format: '[Number] [Adjective] [Topic] | [Year]'",
        "⏰ Upload within peak hours (Tue-Fri, 2-4pm your timezone)",
        "🖼 Custom thumbnails = 30% higher CTR vs auto-generated",
        "📍 Use chapters — videos with chapters rank higher",
        "🔚 End screen: 2 videos + 1 subscribe button",
        "🔑 First 2 lines of description = most important for SEO",
        "📅 Weekly uploads compound — don't skip",
        "🤝 Collab with similar-sized channels for mutual growth",
    ]
    thumb_tips = [
        "🎨 Orange + teal contrast (proven highest CTR combo)",
        "😮 Close-up face showing genuine emotion",
        "📝 Max 4 words, bold, high contrast text",
        "🔍 Add visual curiosity — arrow, circle, question mark",
        "🏷 Maintain consistent branding / colour scheme",
        "⚡ High contrast on mobile — most views are mobile",
    ]
    lengths = [
        "📱 Shorts (< 60s) — Top of funnel, new audiences",
        "⚡ 5-8 min — Tutorials, quick tips, high engagement",
        "💰 8-15 min — Sweet spot for mid-roll ad revenue",
        "🎓 15-30 min — Deep dives, documentaries, loyal fans",
        "🎥 30-60 min — Live replays, podcasts, interview content",
    ]
    channel_growth = [
        "🎯 Niche down — be the go-to channel for ONE topic",
        "📊 Study your top 3 videos and make more like them",
        "💬 Reply to every comment in the first 24 hours",
        "📣 Create a community post weekly for algorithm boost",
        "🔁 Create a Shorts version of every long video",
    ]

    response = (
        f"<b>▶️ YOUTUBE | Growth &amp; Content Strategy</b>\n\n"
        f"<b>💡 Video Idea:</b>\n{video_ideas[seed % len(video_ideas)]}\n\n"
        f"<b>🔍 SEO Tip:</b>\n{seo_tips[seed % len(seo_tips)]}\n\n"
        f"<b>🖼 Thumbnail Tip:</b>\n{thumb_tips[seed % len(thumb_tips)]}\n\n"
        f"<b>⏱ Optimal Length:</b>\n{lengths[seed % len(lengths)]}\n\n"
        f"<b>📈 Channel Growth:</b>\n{channel_growth[seed % len(channel_growth)]}\n\n"
        f"<b>📊 Upload Schedule:</b>\n"
        f"  Consistent > frequent. Weekly = sustainable growth.\n"
        f"  Best days: Tuesday, Wednesday, Thursday\n"
        f"  Best time: 2–4 PM local time"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_tweet(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("tweet")
    seed = generate_daily_seed("tweet")
    random.seed(seed)

    topics = [
        "Productivity hacks nobody in [industry] shares",
        "Lessons from failing at [thing] publicly",
        "The uncomfortable truth about [common belief]",
        "What I wish I knew before starting [thing]",
        "Unpopular opinion: [hot take]",
        "The real reason most [people] fail at [goal]",
        "How I went from [X] to [Y] in [timeframe]",
        "Thread: [topic] explained for beginners",
    ]
    hooks = [
        "Stop scrolling.\n\nThis thread will change how you see [topic]:",
        "I spent 3 years learning this.\n\nYou can learn it in 3 minutes:\n\n🧵",
        "Everyone talks about X.\n\nNobody talks about Y.\n\nHere's the truth:",
        "This one idea doubled my results.\n\nStoling it and posting it anyway:\n\n🧵",
        "Most [people] get this wrong.\n\nLet me show you what actually works:",
        "I wish someone told me this earlier.\n\nSo I'm telling you:",
    ]
    thread = [
        "1/ The common belief is wrong. Here's what the data actually shows...",
        "2/ Most people start at the wrong point. The real starting place is...",
        "3/ Here's the framework that changed everything for me...",
        "4/ A real example in action: [specific case study]...",
        "5/ The counterintuitive truth that top performers know...",
        "6/ Action steps you can take RIGHT NOW:\n  → Step 1\n  → Step 2\n  → Step 3",
        "7/ The mistake 90% of people make at this stage...",
        "Fin/ Save this thread. Share it with someone who needs it.\n\nFollow for more.",
    ]
    posting_tips = [
        "Post between 7-9am or 6-9pm (EST) for max reach",
        "Reply to viral tweets in your niche within first hour",
        "Build in public — your journey > your expertise",
        "Controversial but defensible takes spread fastest",
    ]

    response = (
        f"<b>🐦 TWEET | Viral Thread Generator</b>\n\n"
        f"<b>💡 Topic Idea:</b>\n{topics[seed % len(topics)]}\n\n"
        f"<b>🪝 Opening Hook:</b>\n<code>{hooks[seed % len(hooks)]}</code>\n\n"
        f"<b>📝 Thread Blueprint:</b>\n"
        + "\n".join([f"  {t}" for t in thread]) + "\n\n"
        f"<b>⏰ Posting Tip:</b>\n{posting_tips[seed % len(posting_tips)]}\n\n"
        f"<b># Hashtags:</b>\n#ContentCreator #Thread #GrowthMindset #BuildInPublic"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("hashtags")
    seed = generate_daily_seed("hashtags")
    random.seed(seed)

    pools = {
        "general":  ["#ContentCreator #Viral #Trending #Explore #MustWatch #GoViral",
                     "#Creator #Content #NewPost #DailyContent #ViralContent #CreatorLife"],
        "tech":     ["#TechNews #AI #Innovation #Technology #Future #ArtificialIntelligence",
                     "#Programming #Coding #Developer #Software #TechLife #MachineLearning"],
        "lifestyle":["#Lifestyle #Motivation #Mindset #SelfCare #GrowthMindset #Wellness",
                     "#MorningRoutine #Productivity #SelfImprovement #Focus #Goals"],
        "business": ["#Business #Entrepreneur #Startup #Marketing #Branding #Growth",
                     "#DigitalMarketing #SideHustle #Ecommerce #BusinessTips #StartupLife"],
        "creative": ["#Creative #Design #Art #Photography #GraphicDesign #Artist",
                     "#DigitalArt #Creativity #DesignInspo #CreativeProcess #VisualArt"],
        "fitness":  ["#Fitness #Workout #GymLife #FitFam #HealthyLiving #Training",
                     "#Nutrition #Gains #FitnessMotivation #ExerciseDaily #StayFit"],
        "food":     ["#FoodPhotography #Foodie #Recipe #Cooking #Delicious #FoodBlogger",
                     "#HomeCooking #MealPrep #FoodContent #Yummy #FoodPorn"],
    }
    platform_advice = {
        "Instagram":"Use 25-30 hashtags. Mix sizes: 30% mega (500k+), 40% medium, 30% small niche.",
        "TikTok":   "Use 3-5 relevant hashtags. Trending > niche on TikTok. Keep in caption.",
        "Twitter/X":"1-3 hashtags max. More looks spammy. #Thread for threads.",
        "LinkedIn": "3-5 professional hashtags. Industry-specific ones get most traction.",
        "YouTube":  "15 tags in video settings. Include title keywords + variations.",
        "Pinterest":"5-10 keyword-rich hashtags. Descriptive > trendy on Pinterest.",
    }
    strategies = [
        "🏋 Mix: 20% mega (1M+), 30% large (200k-1M), 30% medium (20k-200k), 20% micro",
        "🔄 Rotate hashtag sets every 2 weeks to avoid shadowban",
        "🎯 Create a branded hashtag unique to your content",
        "🔬 Test 3 different hashtag sets and compare analytics",
        "📊 Check which hashtags drive the most profile visits",
    ]

    cats = list(pools.keys())
    cat1 = cats[seed % len(cats)]
    cat2 = cats[(seed + 2) % len(cats)]
    platforms = list(platform_advice.keys())
    platform  = platforms[seed % len(platforms)]

    response = (
        f"<b># HASHTAGS | Optimized Sets</b>\n\n"
        f"<b>📱 {platform} Strategy:</b>\n{platform_advice[platform]}\n\n"
        f"<b>Set 1 — {cat1.title()}:</b>\n{pools[cat1][seed % len(pools[cat1])]}\n\n"
        f"<b>Set 2 — {cat2.title()}:</b>\n{pools[cat2][(seed+1) % len(pools[cat2])]}\n\n"
        f"<b>Set 3 — Mixed:</b>\n{pools['general'][seed % len(pools['general'])]} "
        f"{pools[cat1][(seed+2) % len(pools[cat1])]}\n\n"
        f"<b>🧠 Hashtag Strategy:</b>\n{strategies[seed % len(strategies)]}"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_business(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("business")
    seed = generate_daily_seed("business")
    random.seed(seed)

    topics = [
        "AI-powered startups are disrupting every traditional industry",
        "Remote work permanently reshaping commercial real estate",
        "The subscription economy now drives $1.5T in global revenue",
        "Sustainable business practices becoming competitive advantage",
        "Creator economy: influencers becoming legitimate business owners",
        "Fintech innovations changing how small businesses access capital",
        "Digital transformation still accelerating in traditional sectors",
        "Gen Z entrepreneurs rewriting the rules of business building",
    ]
    founder_tips = [
        "📞 Validate idea with 10 customer conversations before building",
        "🎯 Focus on ONE problem — solve it exceptionally well",
        "📢 Build in public — your transparency attracts early adopters",
        "💰 Revenue first, funding second — prove the model works",
        "👥 Hire for attitude in early stages, train for skill",
        "🤝 Network is net worth — attend 2 industry events/month",
        "📊 Read competitors' 1-star reviews to find your market gaps",
        "📱 Start with distribution, then build the product",
    ]
    books = [
        "📚 Zero to One — Peter Thiel",
        "📚 The Lean Startup — Eric Ries",
        "📚 Good to Great — Jim Collins",
        "📚 Start With Why — Simon Sinek",
        "📚 The E-Myth Revisited — Michael Gerber",
        "📚 Built to Sell — John Warrillow",
        "📚 Traction — Gabriel Weinberg",
        "📚 $100M Offers — Alex Hormozi",
    ]
    metrics = [
        "📊 MRR (Monthly Recurring Revenue) — lifeblood of subscription business",
        "📊 CAC (Customer Acquisition Cost) — what you spend to get a customer",
        "📊 LTV (Lifetime Value) — total revenue from one customer",
        "📊 Churn Rate — % of customers who leave monthly",
        "📊 Gross Margin — revenue minus direct costs",
        "📊 NPS (Net Promoter Score) — how likely customers are to refer",
    ]
    daily_actions = [
        "Reach out to one potential customer or partner today",
        "Review your top 3 KPIs and identify what's blocking growth",
        "Spend 90 minutes on ONE high-leverage task (no interruptions)",
        "Send one thank you note to a customer or team member",
        "Review one competitor's marketing and extract 3 ideas",
    ]

    response = (
        f"<b>💼 BUSINESS | Trends &amp; Entrepreneurship</b>\n\n"
        f"<b>📈 Market Trend:</b>\n{topics[seed % len(topics)]}\n\n"
        f"<b>🚀 Founder Tip:</b>\n{founder_tips[seed % len(founder_tips)]}\n\n"
        f"<b>📚 Must Read:</b>\n{books[seed % len(books)]}\n\n"
        f"<b>📊 Key Metric:</b>\n{metrics[seed % len(metrics)]}\n\n"
        f"<b>✅ Daily Action:</b>\n{daily_actions[seed % len(daily_actions)]}\n\n"
        f"<b>⚡ Quick Business Wins:</b>\n"
        f"  1️⃣ Review KPIs\n"
        f"  2️⃣ One customer touchpoint\n"
        f"  3️⃣ One high-leverage task\n"
        f"  4️⃣ One learning (podcast/book/article)"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("crypto")
    seed = generate_daily_seed("crypto")
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}

    data = fetch_json(f"{COINGECKO_API}/simple/price",
        params={"ids":"bitcoin,ethereum,solana,cardano,ripple,polkadot,dogecoin,avalanche-2,chainlink,matic-network",
                "vs_currencies":"usd","include_24hr_change":"true","include_market_cap":"true"},
        headers=headers)

    lines = ["<b>₿ CRYPTO | Market Update</b>\n"]
    name_map = {"bitcoin":"Bitcoin BTC","ethereum":"Ethereum ETH","solana":"Solana SOL",
                "cardano":"Cardano ADA","ripple":"XRP","polkadot":"Polkadot DOT",
                "dogecoin":"Dogecoin DOGE","avalanche-2":"Avalanche AVAX",
                "chainlink":"Chainlink LINK","matic-network":"Polygon MATIC"}

    if "error" not in data and data:
        lines.append("<b>💹 Live Prices:</b>")
        for cid, info in data.items():
            name   = name_map.get(cid, cid.title())
            price  = info.get("usd", 0)
            change = info.get("usd_24h_change", 0) or 0
            cap    = info.get("usd_market_cap", 0)
            sign   = "+" if change >= 0 else ""
            emoji  = "📈" if change >= 0 else "📉"
            bar    = progress_bar(abs(change), 10)
            mcap   = f"${cap/1e9:.1f}B" if cap > 1e9 else f"${cap/1e6:.0f}M"
            lines.append(f"  {emoji} <b>{name}:</b> ${price:,.4f} ({sign}{change:.2f}%) | MCap: {mcap}")
    else:
        fallback = [("Bitcoin BTC",67890,2.3),("Ethereum ETH",3420,1.8),
                    ("Solana SOL",148,5.2),("Cardano ADA",0.45,-1.2),("XRP",0.62,0.8)]
        lines.append("<b>💹 Prices (Cached):</b>")
        for name, price, change in fallback:
            sign = "+" if change >= 0 else ""
            emoji = "📈" if change >= 0 else "📉"
            lines.append(f"  {emoji} <b>{name}:</b> ${price:,.2f} ({sign}{change:.1f}%)")

    content_ideas = [
        "🎓 'Crypto for Absolute Beginners' 5-part series",
        "🔐 'How to Secure Your Crypto' — wallets explained",
        "⚡ DeFi explained simply with real-world analogies",
        "📊 Compare top 5 cryptos: strengths & weaknesses",
        "🌱 Staking vs Yield Farming — risk comparison guide",
        "📉 'What to do when crypto crashes' — mindset piece",
    ]
    safety_tips = [
        "🔐 NEVER share your private keys or seed phrase with anyone",
        "💾 Hardware wallet (Ledger/Trezor) for long-term storage",
        "✅ Always verify contract addresses before transacting",
        "🔗 Bookmark official URLs — beware phishing clones",
        "💡 Start with BTC/ETH before exploring altcoins",
    ]
    market_insights = [
        "Bitcoin halving events historically precede bull runs",
        "Institutional adoption continues to grow in 2025",
        "Layer 2 solutions are solving Ethereum's gas fee problem",
        "Regulatory clarity is improving in most major economies",
    ]

    lines.append(f"\n<b>💡 Content Idea:</b>\n{content_ideas[seed % len(content_ideas)]}")
    lines.append(f"\n<b>🔐 Safety Tip:</b>\n{safety_tips[seed % len(safety_tips)]}")
    lines.append(f"\n<b>📊 Market Insight:</b>\n{market_insights[seed % len(market_insights)]}")
    response = "\n".join(lines) + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("ai")
    seed = generate_daily_seed("ai")
    random.seed(seed)

    tools = [
        "🧠 Claude 3.5 Sonnet — Best for coding, analysis & long context",
        "🤖 GPT-4o — Multimodal reasoning, vision & creative tasks",
        "🎨 Midjourney V6 — Highest quality AI image generation",
        "🖼 Stable Diffusion XL — Open-source, run locally or free",
        "💻 Cursor — AI-native code editor (replaces VS Code for many)",
        "🔍 Perplexity AI — Research with citations (replaces basic search)",
        "🎬 RunwayML — AI video generation, editing & VFX",
        "🗣 ElevenLabs — Voice cloning and professional text-to-speech",
        "🎵 Suno AI — Full AI music generation from text prompts",
        "✍️ Notion AI — Writing assistant embedded in your workspace",
        "🤖 n8n + AI — No-code AI workflow automation",
        "📊 Julius AI — Chat with your data, charts & CSV files",
    ]
    trends = [
        "Small Language Models (SLMs) running on-device gaining traction",
        "AI agents autonomously completing multi-step workflows",
        "Open-source models closing the gap with proprietary ones",
        "AI video generation reaching near-broadcast quality",
        "Multimodal AI (text + vision + voice) becoming standard",
        "RAG (Retrieval-Augmented Generation) solving hallucinations",
        "AI in healthcare diagnostics showing breakthrough results",
        "Personal AI assistants becoming 'second brain' tools",
    ]
    prompts = [
        "\"Act as a [role] and write a [format] about [topic] for [audience]\"",
        "\"Generate 10 viral [platform] post ideas about [topic]\"",
        "\"Create a detailed [content type] outline with [N] sections\"",
        "\"Write a compelling email sequence for [product/service] launch\"",
        "\"Analyse the top 5 strengths of [competitor] and suggest how I can compete\"",
        "\"Explain [complex topic] using the analogy of [simple thing]\"",
    ]
    free_tools = [
        "ChatGPT — chat.openai.com (GPT-3.5 free)",
        "Claude — claude.ai (Claude 3 Haiku free)",
        "Gemini — gemini.google.com (free tier)",
        "Copilot — copilot.microsoft.com (free, GPT-4)",
        "Perplexity — perplexity.ai (free tier)",
        "DALL-E 3 — in ChatGPT free (limited)",
        "Canva AI — canva.com (free magic tools)",
        "Hugging Face — huggingface.co (open source)",
    ]
    ai_workflow = [
        "Research → Perplexity | Write → Claude | Images → DALL-E | Video → RunwayML",
        "Plan → Notion AI | Code → Cursor | Design → Midjourney | Publish → Buffer AI",
        "Outline → ChatGPT | Draft → Claude | Edit → Grammarly | Thumbnail → Canva AI",
    ]

    response = (
        f"<b>🤖 AI TOOLS | What's Trending in AI</b>\n\n"
        f"<b>🔦 Tool Spotlight:</b>\n{tools[seed % len(tools)]}\n\n"
        f"<b>📈 Trend:</b>\n{trends[seed % len(trends)]}\n\n"
        f"<b>✍️ Prompt Template:</b>\n<code>{prompts[seed % len(prompts)]}</code>\n\n"
        f"<b>🆓 Free AI Stack ({date.today().year}):</b>\n"
        + "\n".join([f"  • {t}" for t in free_tools[:5]]) + "\n\n"
        f"<b>⚡ AI Workflow Idea:</b>\n{ai_workflow[seed % len(ai_workflow)]}\n\n"
        f"<b>💡 Pro Tip:</b>\nSpecific prompts = better results.\n"
        f"Include: Role + Task + Format + Audience + Constraints."
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_music(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("music")
    seed = generate_daily_seed("music")
    random.seed(seed)
    lines = ["<b>🎵 MUSIC | Trends &amp; Content Ideas</b>\n"]

    trending = fetch_json(f"{AUDIO_DB}/trending.php?country=us&type=itunes&format=singles")
    if "error" not in trending and trending.get("trending"):
        lines.append("<b>🔥 Trending Tracks (US):</b>")
        for i, t in enumerate(trending["trending"][:7], 1):
            name   = sanitize(t.get("strTrack","Unknown"))
            artist = sanitize(t.get("strArtist","Unknown"))
            lines.append(f"  {i}. {name} — {artist}")
    else:
        popular = [
            "Espresso — Sabrina Carpenter","Too Sweet — Hozier",
            "Lose Control — Teddy Swims","Beautiful Things — Benson Boone",
            "A Bar Song — Shaboozey","Gata Only — FloyyMenor ft. Cris MJ",
            "Die With A Smile — Lady Gaga & Bruno Mars",
        ]
        lines.append("<b>🔥 Popular Tracks:</b>")
        for t in popular:
            lines.append(f"  🎶 {t}")

    genres = [
        "🎸 Afrobeats (global dominance continues)",
        "🎵 K-Pop (BTS/BLACKPINK influence expanding)",
        "🎷 Latin Pop / Reggaeton (fastest growing genre)",
        "🎧 Lo-fi Hip Hop (study/focus niche is massive)",
        "⚡ Hyperpop (Gen Z's signature sound)",
        "🎹 Indie Folk (emotional storytelling trending)",
        "🎺 Afrohouse (African electronic going global)",
    ]
    lines.append(f"\n<b>📈 Hot Genre:</b>\n{genres[seed % len(genres)]}")

    content_ideas = [
        "🎵 'My Top 10 Songs This Month' playlist video",
        "🎤 React to new album release in real time",
        "🎸 Break down songwriting techniques in a hit song",
        "🎹 Create music using FREE tools (GarageBand/BandLab)",
        "📜 History of a genre from origins to today",
        "🆚 Compare original vs iconic cover versions",
        "🏝 'Desert island' top 10 tracks challenge",
        "🎧 'Songs for every mood' playlist curation",
    ]
    lines.append(f"\n<b>💡 Content Idea:</b>\n{content_ideas[seed % len(content_ideas)]}")

    creation_tips = [
        "📱 BandLab (free) — produce full tracks on your phone",
        "🎤 USB microphone ($30) = decent vocal recording quality",
        "🎧 Study song structures: Intro→Verse→Chorus→Bridge→Outro",
        "🆓 Use royalty-free samples from FreeSound.org",
        "🔊 Master with LANDR (free tier) for professional sound",
        "📲 Post 60-second music clips on TikTok for discovery",
    ]
    lines.append(f"\n<b>🎛 Creation Tip:</b>\n{creation_tips[seed % len(creation_tips)]}")
    response = "\n".join(lines) + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_podcast(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("podcast")
    seed = generate_daily_seed("podcast")
    random.seed(seed)

    formats = [
        "🎙 Solo deep dive with personal stories + data",
        "🤝 Interview format with an expert in your niche",
        "🗣 Co-hosted debate on a controversial topic",
        "📖 Narrative storytelling with sound design",
        "🎭 Roundtable: 3-4 guests, themed discussion",
        "📬 Q&A answering listener questions only",
        "📊 Case study: deep dive on one success or failure",
        "📰 Weekly news commentary for your niche",
    ]
    episodes = [
        "How I [achieved result] in [timeframe] — the unfiltered story",
        "The one skill that changed everything in [niche]",
        "Interview: [Guest type] on overcoming [common challenge]",
        "Top 5 mistakes beginners make in [topic]",
        "Lessons from [book/event/person] applied to [niche]",
        "Behind the scenes: what nobody tells you about [industry]",
        "[Niche] predictions for the next 3 years",
        "The [uncomfortable truth] about [popular belief in niche]",
    ]
    production = [
        "🎙 Shure SM7B or Rode NT-USB for clean vocals",
        "🏠 Record in a walk-in closet (natural acoustic treatment)",
        "✂️ Descript (free) = transcript-based editing",
        "⏱ 30-45 minutes = sweet spot for commuter listening",
        "🎵 Consistent intro/outro music = brand recognition",
        "📅 Weekly drops beat daily or monthly — consistency wins",
    ]
    platforms = [
        "🟢 Spotify for Podcasters — free, simple, global reach",
        "🍎 Apple Podcasts — essential for iOS loyal audience",
        "📺 YouTube — video podcast trend is exploding in 2025",
        "🟠 Amazon Music — growing fast, less competition",
        "🔵 Pocket Casts — engaged, high-retention listeners",
    ]
    growth = [
        "✂️ Clip best 60-sec moments for TikTok/Reels/Shorts",
        "📝 Transcribe episodes for SEO blog posts",
        "🤝 Ask guests to share episodes with their audiences",
        "⭐ Actively ask listeners for Apple Podcast reviews",
        "📊 Feature interesting guests — they bring their audience",
    ]

    response = (
        f"<b>🎙 PODCAST | Ideas &amp; Production</b>\n\n"
        f"<b>🎬 Format Idea:</b>\n{formats[seed % len(formats)]}\n\n"
        f"<b>💡 Episode Topic:</b>\n{episodes[seed % len(episodes)]}\n\n"
        f"<b>🎛 Production Tip:</b>\n{production[seed % len(production)]}\n\n"
        f"<b>📡 Best Platform:</b>\n{platforms[seed % len(platforms)]}\n\n"
        f"<b>📈 Growth Strategy:</b>\n{growth[seed % len(growth)]}\n\n"
        f"<b>📊 Podcast Funnel:</b>\n"
        f"  🎙 Record → ✂️ Edit → 📤 Publish → 📱 Clip for Social → 📝 Blog Post"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("news")
    categories_list = ["general","technology","business","entertainment","health","science","sports"]
    seed = generate_daily_seed("news")
    cat = categories_list[seed % len(categories_list)]

    data = fetch_json(f"{NEWS_MIRROR}/top-headlines/category/{cat}/us.json")
    lines = [f"<b>📰 NEWS | Top Headlines — {cat.title()}</b>\n"]

    articles = data.get("articles",[]) if "error" not in data else []
    if articles:
        for i, a in enumerate(articles[:8], 1):
            title  = a.get("title","")
            source = a.get("source",{}).get("name","")
            desc   = a.get("description","") or ""
            if title and title != "[Removed]":
                lines.append(f"  {i}. <b>{sanitize(truncate(title, 90))}</b>")
                if desc and desc != "[Removed]":
                    lines.append(f"     <i>{sanitize(truncate(desc, 80))}</i>")
                if source:
                    lines.append(f"     — {sanitize(source)}")
                lines.append("")
    else:
        lines.append("⚠️ Could not fetch live news. Try again shortly.")

    lines.append(f"<b>💡 Content Angle:</b>\nReact to the biggest headline above with your unique take!")
    response = "\n".join(lines) + BRAND_FOOTER
    await _send(update, response, is_callback)


async def cmd_joke(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("joke")
    data = fetch_json(f"{JOKE_API}/Any?blacklistFlags=nsfw,racist,sexist,explicit")
    if "error" in data:
        jokes = [
            ("Why don't scientists trust atoms?", "Because they make up everything!"),
            ("I told my wife she should embrace her mistakes.", "She gave me a hug."),
            ("Why do programmers prefer dark mode?", "Because light attracts bugs!"),
            ("I asked my dog what 2 minus 2 is.", "He said nothing."),
        ]
        seed = generate_daily_seed("joke")
        q, a = jokes[seed % len(jokes)]
        text = f"<b>😂 JOKE OF THE DAY</b>\n\n🤔 {sanitize(q)}\n\n😂 {sanitize(a)}"
    elif data.get("type") == "single":
        text = f"<b>😂 JOKE OF THE DAY</b>\n\n{sanitize(data.get('joke',''))}"
    else:
        setup    = data.get("setup","")
        delivery = data.get("delivery","")
        text = f"<b>😂 JOKE OF THE DAY</b>\n\n🤔 {sanitize(setup)}\n\n😂 {sanitize(delivery)}"

    text += "\n\n<i>Share this joke to brighten someone's day! 😄</i>" + BRAND_FOOTER
    await _send(update, text, is_callback)


async def cmd_fact(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("fact")
    data = fetch_json(f"{FACT_API}?language=en")
    fact_text = ""
    if "error" not in data:
        fact_text = data.get("text","")

    if not fact_text:
        seed = generate_daily_seed("fact")
        facts = [
            "Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs that was still edible.",
            "A group of flamingos is called a 'flamboyance'.",
            "The human brain generates about 70,000 thoughts per day.",
            "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
            "Sharks are older than trees. Sharks have been around for ~450 million years, trees only ~350 million.",
            "There are more possible iterations of a chess game than atoms in the observable universe.",
            "The Eiffel Tower can grow over 15cm taller in summer due to thermal expansion.",
            "A day on Venus is longer than a year on Venus.",
        ]
        fact_text = facts[seed % len(facts)]

    # Get a number fact too
    day_num = date.today().timetuple().tm_yday
    num_data = fetch_json(f"{NUMBER_API}/{day_num}/date?json")
    num_fact = num_data.get("text","") if "error" not in num_data else ""

    text = (
        f"<b>🧠 MIND-BLOWING FACT</b>\n\n"
        f"💡 {sanitize(fact_text)}\n"
    )
    if num_fact:
        text += f"\n<b>📅 On This Day (#{day_num}):</b>\n{sanitize(num_fact)}\n"
    text += "\n<i>Save and share this to educate your audience! 🤯</i>" + BRAND_FOOTER
    await _send(update, text, is_callback)


async def cmd_roast(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("roast")
    seed = generate_daily_seed("roast")
    random.seed(seed)
    user = update.effective_user
    name = sanitize(user.first_name)

    roasts = [
        f"Hey {name}, your bio says 'content creator' but the only thing you've created is an excuse for why you haven't posted yet. 😂",
        f"Relax {name}, the algorithm didn't shadow ban you. Your content just went viral... in the wrong direction. 🤣",
        f"{name}, your posting schedule is so inconsistent, even your phone forgot you had a social media account. 💀",
        f"Bro {name}, you've been 'about to post something big' for 3 months. At this point, even your drafts are questioning your commitment. 😭",
        f"{name} walks into a room full of content creators and says 'I'll start posting next Monday.' Classic. 😂",
        f"Your engagement rate is so low, {name}, even your mum double-taps out of pity. 💔",
        f"{name}, you have a 'content strategy' document with 47 pages and zero posts to show for it. The Google Doc is eating better than your audience. 🤣",
        f"Don't worry {name}, 'going viral' is just sleeping on the sofa while your content gets zero views. You're basically famous. 😭",
    ]
    comebacks = [
        "But real talk — that's what separates creators who make it from those who don't: posting anyway. 💪",
        "But seriously, the creators laughing are the ones who were also afraid to start. Post the thing. 🚀",
        "That said, every viral creator started from zero. Your comeback arc is going to be legendary. 📈",
        "Jokes aside, one post today beats 100 planned posts that never happen. Go create something. 🎬",
    ]
    content_ideas_post_roast = [
        "📹 Post a 'Watch me create content for 24 hours straight' challenge",
        "😂 Post a self-roast — audiences LOVE creator vulnerability",
        "🎯 Go live right now. No prep, just authenticity.",
        "📝 Document your 'starting from zero' journey — that's the content!",
    ]

    response = (
        f"<b>🔥 ROAST GENERATOR</b>\n\n"
        f"{roasts[seed % len(roasts)]}\n\n"
        f"<b>💪 Real Talk:</b>\n{comebacks[seed % len(comebacks)]}\n\n"
        f"<b>🎯 Turn This Into Content:</b>\n{content_ideas_post_roast[seed % len(content_ideas_post_roast)]}"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_story(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("story")
    seed = generate_daily_seed("story")
    random.seed(seed)

    settings = [
        "a neon-lit cyberpunk city in 2089","a remote island with no internet",
        "a reality where dreams can be sold as NFTs","a medieval kingdom run by algorithms",
        "a space colony that's run out of coffee","a post-AI world where creativity is the only currency",
        "a village where everyone can read minds","a time-loop where every Monday repeats",
    ]
    characters = [
        "a burned-out content creator who discovers a hidden talent",
        "an AI that develops emotions and starts a secret blog",
        "a time traveller who keeps arriving 5 minutes too late",
        "a social media manager for a medieval dragon",
        "the last person on Earth without a smartphone",
        "a motivational speaker who has secretly given up",
        "an entrepreneur who can only sell things they personally hate",
    ]
    conflicts = [
        "who finds a USB drive containing the future","who has 24 hours to change one major decision",
        "who accidentally goes viral for the wrong reason",
        "who must prove their worth without using technology",
        "who discovers their biggest competitor is their future self",
        "who wakes up with someone else's memories",
        "who has to teach an AI what it means to be human",
    ]
    first_lines = [
        "The notification came at 3am, and it changed everything.",
        "She deleted her social media at noon. By midnight, she was famous.",
        "The algorithm had been learning. Nobody expected what it learned.",
        "He had 10 seconds left on the live stream when the phone rang.",
        "The last thing anyone expected was an apology.",
        "She opened the app and saw 47 million followers. Yesterday it was 47.",
        "The deal was simple: create one piece of content that changes the world. He had 7 days.",
    ]
    genres = ["Sci-Fi Thriller", "Dark Comedy", "Inspirational Drama",
              "Tech Noir", "Slice of Life", "Mystery", "Adventure"]
    writing_tips = [
        "📝 Use the 3-act structure: Setup → Confrontation → Resolution",
        "✍️ Write the ending first, then work backwards",
        "🎭 Every character needs a want AND a need (often different)",
        "📖 Show don't tell: actions reveal character better than descriptions",
        "⚡ Open in medias res — drop the reader mid-action",
    ]

    response = (
        f"<b>📖 STORY STARTER | Creative Writing Spark</b>\n\n"
        f"<b>🎭 Genre:</b> {genres[seed % len(genres)]}\n\n"
        f"<b>🌍 Setting:</b>\n{settings[seed % len(settings)]}\n\n"
        f"<b>👤 Character:</b>\n{characters[seed % len(characters)]}\n\n"
        f"<b>⚡ Conflict:</b>\n{conflicts[seed % len(conflicts)]}\n\n"
        f"<b>✍️ Opening Line:</b>\n<i>{first_lines[seed % len(first_lines)]}</i>\n\n"
        f"<b>💡 Writing Tip:</b>\n{writing_tips[seed % len(writing_tips)]}\n\n"
        f"<i>Use this as content! Write the next 3 paragraphs and post as a thread.</i>"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("recipe")
    data = fetch_json(f"{MEAL_API}/random.php")
    seed = generate_daily_seed("recipe")

    if "error" not in data and data.get("meals"):
        meal   = data["meals"][0]
        name   = sanitize(meal.get("strMeal","Recipe"))
        cat    = sanitize(meal.get("strCategory","General"))
        area   = sanitize(meal.get("strArea","International"))
        instructions = sanitize(meal.get("strInstructions","See below")[:500])
        tags   = sanitize(meal.get("strTags","") or "cooking,food")
        yt     = meal.get("strYoutube","")

        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}","")
            meas= meal.get(f"strMeasure{i}","")
            if ing and ing.strip():
                ingredients.append(f"{meas.strip()} {ing.strip()}".strip())

        text = (
            f"<b>🍽 RECIPE | {name}</b>\n\n"
            f"🌍 Origin: {area} | 🏷 Category: {cat}\n"
            f"🏷 Tags: #{tags.replace(',', ' #')}\n\n"
            f"<b>🧂 Ingredients:</b>\n"
            + "\n".join([f"  • {ing}" for ing in ingredients[:12]]) + "\n\n"
            f"<b>📋 Instructions (Summary):</b>\n{instructions}...\n\n"
        )
        if yt:
            text += f"<b>▶️ Full Recipe Video:</b> {yt}\n\n"
    else:
        recipes = [
            ("Jollof Rice 🇬🇭", "West African","Rice, tomatoes, onions, peppers, spices, oil",
             "Blend tomatoes, peppers & onions. Fry paste in oil. Add rice and stock. Cook covered on low heat for 30 mins."),
            ("Avocado Toast 🥑","American","Bread, avocado, lemon, salt, pepper, optional toppings",
             "Toast bread. Mash avocado with lemon juice, salt, pepper. Spread on toast. Add toppings of choice."),
            ("Pasta Aglio e Olio 🍝","Italian","Spaghetti, garlic, olive oil, red pepper, parsley, parmesan",
             "Cook pasta. Fry sliced garlic in olive oil. Add red pepper flakes. Toss with pasta and pasta water. Top with parsley."),
        ]
        r = recipes[seed % len(recipes)]
        text = (
            f"<b>🍽 RECIPE | {r[0]}</b>\n\n"
            f"🌍 Origin: {r[1]}\n\n"
            f"<b>🧂 Key Ingredients:</b>\n{r[2]}\n\n"
            f"<b>📋 Method:</b>\n{r[3]}\n\n"
        )

    content_ideas = [
        "🎬 'I tried this recipe for the first time' reaction video",
        "📱 Post a 60-second reel with the cooking process",
        "🤳 Poll: 'Would you try this?' — great for engagement",
        "📸 Flat lay of ingredients before cooking",
    ]
    text += f"<b>💡 Content Idea:</b>\n{content_ideas[seed % len(content_ideas)]}" + BRAND_FOOTER
    await _send(update, text, is_callback)


async def cmd_fitness(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("fitness")
    seed = generate_daily_seed("fitness")
    random.seed(seed)

    workouts = [
        ("💪 Upper Body Strength", [
            "4×10 Push-ups (or bench press)","3×12 Dumbbell rows","3×12 Shoulder press",
            "3×15 Bicep curls","3×15 Tricep dips","2×15 Lateral raises",
        ]),
        ("🦵 Lower Body Power", [
            "4×10 Squats (bodyweight or weighted)","3×12 Romanian deadlifts",
            "3×12 Lunges (each leg)","3×15 Glute bridges","3×15 Calf raises",
            "2×60s Wall sit",
        ]),
        ("🔥 HIIT Cardio Blast", [
            "40s Burpees → 20s rest","40s Jump squats → 20s rest",
            "40s Mountain climbers → 20s rest","40s High knees → 20s rest",
            "40s Push-ups → 20s rest","Repeat 3-4 rounds",
        ]),
        ("🧘 Core & Flexibility", [
            "3×60s Plank","3×15 Crunches","3×15 Leg raises",
            "3×30s Side planks","10 mins yoga stretching","5 mins deep breathing",
        ]),
        ("🏃 Active Recovery", [
            "30 min easy walk","10 min light jogging","Full body stretch routine",
            "Foam rolling (10 mins)","Cold shower for recovery","Hydrate: 2-3L water",
        ]),
    ]
    workout = workouts[seed % len(workouts)]

    nutrition_tips = [
        "🥗 Eat 0.8-1g protein per lb bodyweight for muscle building",
        "💧 Drink 500ml water 30 mins before every meal",
        "⏰ Eat within 30 mins post-workout for optimal recovery",
        "🚫 Cut ultra-processed foods — replace with 1 whole food swap/week",
        "🌙 Avoid food 2-3 hours before sleep for better fat burning",
        "🍎 '80/20 rule': eat clean 80% — don't restrict 100%",
    ]
    recovery_tips = [
        "😴 7-9 hours sleep = your most powerful performance tool",
        "🧊 Cold exposure (2-3 mins cold shower) reduces inflammation",
        "💪 Active recovery > complete rest on off days",
        "🧘 10 mins meditation reduces cortisol and speeds recovery",
        "📊 Track your workouts — progress = motivation",
    ]
    content_ideas = [
        "📹 '30-day transformation challenge' daily vlog",
        "🤳 'Workout with me' real-time session video",
        "📊 Progress photo update (monthly)",
        "🍱 'What I eat in a day' for muscle gain/fat loss",
        "❌ 'Gym mistakes I made for 2 years' educational content",
        "💡 'Beginner gym guide' for complete newcomers",
    ]

    response = (
        f"<b>💪 FITNESS | Daily Workout &amp; Tips</b>\n\n"
        f"<b>🏋 Today's Workout: {workout[0]}</b>\n"
        + "\n".join([f"  ▫️ {ex}" for ex in workout[1]]) + "\n\n"
        f"<b>🥗 Nutrition Tip:</b>\n{nutrition_tips[seed % len(nutrition_tips)]}\n\n"
        f"<b>🔄 Recovery Tip:</b>\n{recovery_tips[seed % len(recovery_tips)]}\n\n"
        f"<b>💡 Fitness Content Idea:</b>\n{content_ideas[seed % len(content_ideas)]}\n\n"
        f"<b>📊 Fitness Tracking:</b>\n"
        f"  Track: Weight | Reps | Sets | Rest time | Energy level"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_travel(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("travel")
    seed = generate_daily_seed("travel")
    random.seed(seed)

    destinations = [
        {"name":"🇯🇵 Kyoto, Japan","vibe":"Ancient temples meets modern Japan","budget":"$$","best_time":"Mar-May, Oct-Nov","content":"Cherry blossom shots, temple walks, street food"},
        {"name":"🇮🇹 Amalfi Coast, Italy","vibe":"Cliffside villages over turquoise sea","budget":"$$$","best_time":"Apr-Jun, Sep-Oct","content":"Drone footage, boat tours, pasta-making"},
        {"name":"🇬🇭 Accra, Ghana","vibe":"Vibrant culture, beaches, incredible food","budget":"$","best_time":"Nov-Mar","content":"Chop bars, markets, music scenes, Labadi Beach"},
        {"name":"🇨🇴 Cartagena, Colombia","vibe":"Colourful colonial streets and the Caribbean","budget":"$","best_time":"Dec-Mar","content":"Street art, old city walk, boat trips"},
        {"name":"🇳🇿 Queenstown, NZ","vibe":"Adventure capital of the world","budget":"$$$","best_time":"Dec-Feb (summer)","content":"Extreme sports, fjords, bungee jumping"},
        {"name":"🇹🇭 Chiang Mai, Thailand","vibe":"Digital nomad paradise with rich culture","budget":"$","best_time":"Nov-Feb","content":"Night markets, temples, elephant sanctuaries"},
        {"name":"🇵🇹 Lisbon, Portugal","vibe":"Europe's most underrated city","budget":"$$","best_time":"Mar-May, Sep-Oct","content":"Trams, tiles, fado music, pastel de nata"},
        {"name":"🇸🇳 Dakar, Senegal","vibe":"West African music, art, and coastline","budget":"$","best_time":"Nov-Feb","content":"Pink Lake, Gorée Island, local cuisine"},
    ]
    dest = destinations[seed % len(destinations)]

    travel_content_ideas = [
        "📹 '24 hours in [city]' immersive vlog",
        "💰 '[City] on a budget' money-saving guide",
        "🍽 'Best local food in [city]' taste test video",
        "🗺 'First timer's guide to [destination]' blog + reel",
        "🤳 'Things nobody tells you about [place]' honest review",
        "📸 'Most Instagrammable spots in [destination]' photo guide",
        "🎒 'Packing for [trip type]: my complete list'",
    ]
    packing_tips = [
        "🎒 Roll clothes instead of folding — saves 30% space",
        "📱 Download maps.me offline BEFORE you arrive",
        "💊 Pack 2x more medication than you think you need",
        "💳 Notify your bank of travel dates to avoid card blocks",
        "🔌 Universal adapter + power bank are non-negotiables",
        "📸 Pack a neutral outfit for photos that works anywhere",
    ]
    travel_hacks = [
        "🛫 Book Tuesday/Wednesday flights for best prices",
        "🏨 Check hotel vs Airbnb vs hostel for your travel style",
        "💱 Use Wise or Revolut for zero-fee currency exchange",
        "📶 Buy local SIM at airport for cheap data",
        "🌐 Google Translate offline mode before you land",
    ]

    response = (
        f"<b>✈️ TRAVEL | Destination of the Day</b>\n\n"
        f"<b>📍 Destination:</b> {dest['name']}\n"
        f"✨ <b>Vibe:</b> {dest['vibe']}\n"
        f"💰 <b>Budget:</b> {dest['budget']} | 📅 <b>Best Time:</b> {dest['best_time']}\n"
        f"📸 <b>Content Gold:</b> {dest['content']}\n\n"
        f"<b>💡 Travel Content Idea:</b>\n{travel_content_ideas[seed % len(travel_content_ideas)]}\n\n"
        f"<b>🎒 Packing Tip:</b>\n{packing_tips[seed % len(packing_tips)]}\n\n"
        f"<b>💡 Travel Hack:</b>\n{travel_hacks[seed % len(travel_hacks)]}\n\n"
        f"<b>📊 Travel Content Formats That Perform:</b>\n"
        f"  🎬 Vlogs > Photos on YouTube\n"
        f"  📱 Reels > Static posts on Instagram\n"
        f"  🗺 'Guide' videos get evergreen search traffic"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_mindset(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("mindset")
    seed = generate_daily_seed("mindset")
    random.seed(seed)

    # Try advice API
    advice_data = fetch_json(f"{ADVICE_API}")
    advice_text = ""
    if "error" not in advice_data:
        advice_text = advice_data.get("slip",{}).get("advice","")

    deep_insights = [
        "The quality of your questions determines the quality of your life.",
        "You don't rise to the level of your goals. You fall to the level of your systems.",
        "Identity change is the north star of habit change — act as who you want to become.",
        "Most people overestimate what they can do in 1 year and underestimate 10 years.",
        "The gap between who you are and who you want to be is filled by action, not planning.",
        "Your environment is stronger than your willpower. Design your space for success.",
        "Comfort and growth cannot coexist. Choose your discomfort.",
        "The version of you that succeeds is built in the moments no one is watching.",
    ]
    reframes = [
        "❌ 'I have to...' → ✅ 'I get to...'",
        "❌ 'I failed...' → ✅ 'I learned that...'",
        "❌ 'I'm not good at this...' → ✅ 'I'm not good at this YET.'",
        "❌ 'This is too hard...' → ✅ 'This is worth doing because it's hard.'",
        "❌ 'I don't have time...' → ✅ 'This is not my priority right now.'",
        "❌ 'What if I fail?' → ✅ 'What if I succeed?'",
    ]
    mental_models = [
        "🧠 <b>First Principles:</b> Break everything down to fundamental truths",
        "🔄 <b>Inversion:</b> Think about what you want to avoid, not just achieve",
        "📊 <b>Pareto (80/20):</b> 20% of actions produce 80% of results",
        "🌊 <b>Compounding:</b> Small consistent actions compound to massive results",
        "🪞 <b>Second-Order Thinking:</b> Ask 'and then what?' for every decision",
        "🎯 <b>Regret Minimisation:</b> Choose what 80-year-old you would respect",
    ]
    journaling_prompts = [
        "What would today look like if I was operating at my best?",
        "What am I tolerating in my life that I should eliminate?",
        "What would I do if I knew I couldn't fail?",
        "Who do I need to become to achieve what I want?",
        "What belief is holding me back most right now?",
        "If I had only 6 months left, what would I stop doing?",
    ]

    response = (
        f"<b>🧘 MINDSET | Deep Thinking &amp; Growth</b>\n\n"
        f"<b>💡 Insight:</b>\n<i>{deep_insights[seed % len(deep_insights)]}</i>\n\n"
    )
    if advice_text:
        response += f"<b>🌟 Advice:</b>\n{sanitize(advice_text)}\n\n"

    response += (
        f"<b>🔄 Cognitive Reframe:</b>\n{reframes[seed % len(reframes)]}\n\n"
        f"<b>🧠 Mental Model:</b>\n{mental_models[seed % len(mental_models)]}\n\n"
        f"<b>📓 Journaling Prompt:</b>\n<i>{journaling_prompts[seed % len(journaling_prompts)]}</i>\n\n"
        f"<b>⚡ 5-Minute Mindset Reset:</b>\n"
        f"  1️⃣ 5 deep breaths\n"
        f"  2️⃣ Write 3 things you're grateful for\n"
        f"  3️⃣ Write today's single most important task\n"
        f"  4️⃣ Read your core values statement"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_horoscope(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("horoscope")
    seed = generate_daily_seed("horoscope")
    random.seed(seed)

    signs = [
        ("♈ Aries","Mar 21–Apr 19","Mars","Fire"),("♉ Taurus","Apr 20–May 20","Venus","Earth"),
        ("♊ Gemini","May 21–Jun 20","Mercury","Air"),("♋ Cancer","Jun 21–Jul 22","Moon","Water"),
        ("♌ Leo","Jul 23–Aug 22","Sun","Fire"),("♍ Virgo","Aug 23–Sep 22","Mercury","Earth"),
        ("♎ Libra","Sep 23–Oct 22","Venus","Air"),("♏ Scorpio","Oct 23–Nov 21","Pluto","Water"),
        ("♐ Sagittarius","Nov 22–Dec 21","Jupiter","Fire"),("♑ Capricorn","Dec 22–Jan 19","Saturn","Earth"),
        ("♒ Aquarius","Jan 20–Feb 18","Uranus","Air"),("♓ Pisces","Feb 19–Mar 20","Neptune","Water"),
    ]
    today_sign = signs[seed % len(signs)]

    themes = [
        "creativity and self-expression","relationships and connections","career and ambition",
        "finances and abundance","health and wellness","communication and clarity",
        "inner growth and reflection","adventure and new beginnings","leadership and courage",
    ]
    energies = ["🔥 High Energy","✨ Creative","🌊 Emotional","💨 Mental","🌍 Grounded","⚡ Electric"]
    lucky_numbers = [random.randint(1,99) for _ in range(3)]
    lucky_colors  = ["Golden Yellow","Deep Blue","Emerald Green","Ruby Red","Pearl White","Midnight Purple","Coral Orange","Silver Grey"]
    focus_areas   = ["Career","Love","Health","Wealth","Creativity","Relationships","Personal Growth","Spirituality"]

    daily_messages = [
        f"The universe aligns for {today_sign[0].split()[1]}. Trust the process unfolding before you.",
        f"Powerful energy flows in your direction. Take bold action today.",
        f"Today calls for introspection. Your deepest answers come from within.",
        f"An unexpected connection or opportunity arrives. Stay open and receptive.",
        f"Clarity replaces confusion today. Trust what you instinctively know.",
        f"Your authentic voice carries more power today than you realise. Speak up.",
        f"Focus on what you can control. Release what you cannot.",
    ]

    response = (
        f"<b>⭐ HOROSCOPE | Daily Cosmic Guidance</b>\n\n"
        f"<b>Today's Sign:</b> {today_sign[0]}\n"
        f"📅 {today_sign[1]} | 🌍 Element: {today_sign[3]} | ☿ Ruler: {today_sign[2]}\n\n"
        f"<b>📜 Daily Message:</b>\n<i>{daily_messages[seed % len(daily_messages)]}</i>\n\n"
        f"<b>🎯 Today's Theme:</b> {themes[seed % len(themes)].title()}\n"
        f"<b>⚡ Energy:</b> {energies[seed % len(energies)]}\n"
        f"<b>🎨 Lucky Color:</b> {lucky_colors[seed % len(lucky_colors)]}\n"
        f"<b>🔢 Lucky Numbers:</b> {', '.join(map(str, lucky_numbers[:3]))}\n"
        f"<b>🎯 Focus Area:</b> {focus_areas[seed % len(focus_areas)]}\n\n"
        f"<b>💡 Content Idea:</b>\nPost your daily horoscope reading for your audience!\n"
        f"Add your unique interpretation for a personal touch."
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_dictionary(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("dictionary")
    args = context.args if hasattr(context, 'args') and context.args else []

    power_words = [
        "serendipity","ephemeral","resilience","perspicacious","sonder",
        "hiraeth","sanguine","petrichor","vellichor","meraki","chrysalism",
    ]
    seed  = generate_daily_seed("dictionary")
    word  = " ".join(args) if args else power_words[seed % len(power_words)]
    data  = fetch_json(f"{DICTIONARY_API}/{urllib.parse.quote(word)}")

    if "error" not in data and isinstance(data, list) and data:
        entry = data[0]
        word_found = sanitize(entry.get("word", word))
        phonetic   = sanitize(entry.get("phonetic","") or "")
        meanings   = entry.get("meanings",[])

        text = f"<b>📚 DICTIONARY | Word of the Day</b>\n\n<b>{word_found}</b>"
        if phonetic:
            text += f" <i>{phonetic}</i>"
        text += "\n\n"

        for meaning in meanings[:3]:
            pos   = meaning.get("partOfSpeech","")
            defs  = meaning.get("definitions",[])
            examples = meaning.get("definitions",[])
            if defs:
                text += f"<b>{pos.title()}:</b>\n"
                for d in defs[:2]:
                    text += f"  📖 {sanitize(d.get('definition',''))}\n"
                    example = d.get('example','')
                    if example:
                        text += f"  <i>e.g. «{sanitize(example)}»</i>\n"
                text += "\n"
    else:
        fallback_words = {
            "serendipity": ("noun","Finding something good without looking for it","A serendipitous meeting changed her career."),
            "resilience":  ("noun","The capacity to recover from difficulties","Her resilience inspired the whole team."),
            "ephemeral":   ("adjective","Lasting for a very short time","The ephemeral beauty of cherry blossoms."),
            "meraki":      ("noun (Greek)","Doing something with soul, creativity, and love","She cooked with meraki — every dish told a story."),
        }
        fw  = fallback_words.get(word.lower(), ("noun","A fascinating word","Use it in a sentence today!"))
        text = (
            f"<b>📚 DICTIONARY | Word of the Day</b>\n\n"
            f"<b>{word.title()}</b>\n\n"
            f"<b>{fw[0].title()}:</b>\n  📖 {fw[1]}\n  <i>e.g. «{fw[2]}»</i>\n\n"
        )

    text += (
        f"<b>💡 Creator Tip:</b>\nUse a 'Word of the Day' post series!\n"
        f"Define → Example sentence → Ask followers to use it.\n"
        f"High save rate = algorithm boost.\n\n"
        f"<i>Try: /dictionary [any word]</i>"
        + BRAND_FOOTER
    )
    await _send(update, text, is_callback)


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("quiz")
    data = fetch_json(f"{TRIVIA_API}?amount=1&type=multiple")
    seed = generate_daily_seed("quiz")

    if "error" not in data and data.get("results"):
        result  = data["results"][0]
        question = html_mod.unescape(result.get("question",""))
        correct  = html_mod.unescape(result.get("correct_answer",""))
        incorrect= [html_mod.unescape(a) for a in result.get("incorrect_answers",[])]
        category = html_mod.unescape(result.get("category","General"))
        difficulty = result.get("difficulty","medium")
        all_answers = incorrect + [correct]
        random.shuffle(all_answers)
        answer_labels = ["A","B","C","D"]
        correct_label = answer_labels[all_answers.index(correct)]

        text = (
            f"<b>🎯 QUIZ TIME!</b>\n\n"
            f"📚 Category: {sanitize(category)}\n"
            f"🎯 Difficulty: {difficulty.title()}\n\n"
            f"<b>❓ {sanitize(question)}</b>\n\n"
        )
        for label, answer in zip(answer_labels, all_answers):
            text += f"  {label}) {sanitize(answer)}\n"
        text += f"\n<tg-spoiler>✅ Answer: {correct_label}) {sanitize(correct)}</tg-spoiler>"
    else:
        questions = [
            ("What is the most used programming language in 2024?","Python","JavaScript","Rust","Go","A"),
            ("Which platform has the highest engagement rate in 2024?","TikTok","Instagram","YouTube","Twitter","A"),
            ("What does 'SEO' stand for?","Search Engine Optimisation","Social Engagement Online","Site Exposure Output","Search Experience Optimisation","A"),
            ("In what year was the first iPhone released?","2005","2006","2007","2008","C"),
        ]
        q = questions[seed % len(questions)]
        text = (
            f"<b>🎯 QUIZ TIME!</b>\n\n"
            f"<b>❓ {q[0]}</b>\n\n"
            f"  A) {q[1]}\n  B) {q[2]}\n  C) {q[3]}\n  D) {q[4]}\n\n"
            f"<tg-spoiler>✅ Answer: {q[5]})</tg-spoiler>"
        )

    text += (
        "\n\n<b>💡 Creator Tip:</b>\nQuiz posts get 3x more engagement!\n"
        "Post a daily quiz in your niche with 'Answer in comments' CTA."
        + BRAND_FOOTER
    )
    await _send(update, text, is_callback)


async def cmd_country(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("country")
    seed = generate_daily_seed("country")
    # Get random country
    data = fetch_json(f"{COUNTRY_API}/all?fields=name,capital,population,region,languages,currencies,flag,flags,area,timezones")

    if "error" not in data and isinstance(data, list) and data:
        random.seed(seed)
        country = random.choice(data)
        name       = country.get("name",{}).get("common","Unknown")
        capital    = (country.get("capital") or ["Unknown"])[0]
        population = country.get("population",0)
        region     = country.get("region","Unknown")
        flag       = country.get("flag","🏳")
        area       = country.get("area",0)
        languages  = ", ".join(list((country.get("languages") or {}).values())[:3])
        currencies = ", ".join([v.get("name","") for v in (country.get("currencies") or {}).values()][:2])
        timezones  = (country.get("timezones") or ["UTC"])[0]

        pop_formatted = f"{population:,}"
        area_formatted = f"{area:,.0f} km²" if area else "N/A"

        text = (
            f"<b>🌍 COUNTRY OF THE DAY</b>\n\n"
            f"{flag} <b>{sanitize(name)}</b>\n\n"
            f"🏙 Capital: {sanitize(capital)}\n"
            f"🌎 Region: {sanitize(region)}\n"
            f"👥 Population: {pop_formatted}\n"
            f"📐 Area: {area_formatted}\n"
            f"🗣 Languages: {sanitize(languages)}\n"
            f"💰 Currency: {sanitize(currencies)}\n"
            f"🕐 Timezone: {sanitize(timezones)}\n\n"
        )
    else:
        countries = [
            ("🇬🇭 Ghana","Accra","West Africa","33M","Twi, English","Cedi (GHS)"),
            ("🇳🇬 Nigeria","Abuja","West Africa","220M","Yoruba, Hausa, Igbo, English","Naira (NGN)"),
            ("🇿🇦 South Africa","Pretoria","Southern Africa","60M","11 official languages","Rand (ZAR)"),
            ("🇧🇷 Brazil","Brasília","South America","215M","Portuguese","Real (BRL)"),
        ]
        c = countries[seed % len(countries)]
        text = (
            f"<b>🌍 COUNTRY OF THE DAY</b>\n\n"
            f"<b>{c[0]}</b>\n\n"
            f"🏙 Capital: {c[1]}\n🌎 Region: {c[2]}\n👥 Population: {c[3]}\n"
            f"🗣 Languages: {c[4]}\n💰 Currency: {c[5]}\n\n"
        )

    text += (
        "<b>💡 Content Ideas:</b>\n"
        "  📸 'Did you know about [country]?' post\n"
        "  🌍 Country trivia quiz for your audience\n"
        "  📊 Compare 2 countries in same region\n"
        "  ✈️ 'Why you should visit [country]' reel"
        + BRAND_FOOTER
    )
    await _send(update, text, is_callback)


async def cmd_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("challenge")
    seed = generate_daily_seed("challenge")
    random.seed(seed)

    challenges = [
        {"name":"📸 30-Day Photo Challenge","days":30,"category":"Photography",
         "description":"Post one photo every day for 30 days with different themes",
         "days_list":["Day 1: Self-portrait","Day 2: Something yellow","Day 3: Texture close-up",
                      "Day 4: Reflection","Day 5: Golden hour","Day 6: Something old",
                      "Day 7: Food flat lay","Day 8: Motion blur","Day 9: Shadow play","Day 10: Architecture"]},
        {"name":"💪 30-Day Fitness Challenge","days":30,"category":"Fitness",
         "description":"Progressive daily workout that builds strength over 30 days",
         "days_list":["Day 1: 10 pushups","Day 2: 15 squats","Day 3: 30s plank",
                      "Day 4: 10 burpees","Day 5: Rest + stretch","Day 6: 20 pushups",
                      "Day 7: 20 squats","Day 8: 1 min plank","Day 9: 15 burpees","Day 10: 2km walk"]},
        {"name":"📚 30-Day Reading Challenge","days":30,"category":"Learning",
         "description":"Read 30 minutes per day and share one insight publicly",
         "days_list":["Day 1: Autobiography","Day 2: Business book","Day 3: Science",
                      "Day 4: Biography","Day 5: Self-help","Day 6: History",
                      "Day 7: Psychology","Day 8: Fiction (classic)","Day 9: Investing","Day 10: Philosophy"]},
        {"name":"🎬 30-Day Content Challenge","days":30,"category":"Content Creation",
         "description":"Post one piece of content daily and document your growth",
         "days_list":["Day 1: Introduce yourself","Day 2: Share a tip","Day 3: Tell your story",
                      "Day 4: Teach something","Day 5: Share a fail","Day 6: Post a poll",
                      "Day 7: Collaboration post","Day 8: Tutorial video","Day 9: Product review","Day 10: Q&A post"]},
        {"name":"🧘 21-Day Mindset Challenge","days":21,"category":"Mental Health",
         "description":"Daily mental exercises to rewire your thinking patterns",
         "days_list":["Day 1: Gratitude list (10 items)","Day 2: Identify a limiting belief",
                      "Day 3: 10-min meditation","Day 4: Write your vision statement",
                      "Day 5: Cold shower (2 mins)","Day 6: Digital detox for 4 hours",
                      "Day 7: Acts of kindness (3 today)","Day 8: Journaling session","Day 9: Read for 30 mins","Day 10: Nature walk"]},
    ]
    challenge = challenges[seed % len(challenges)]

    accountability_tips = [
        "📢 Announce publicly — social accountability is powerful",
        "👥 Find a challenge partner for mutual accountability",
        "📊 Track daily with a simple checklist app",
        "📱 Share daily progress as Stories for engagement",
        "🏆 Set a reward for completing the full challenge",
    ]

    response = (
        f"<b>🎉 CHALLENGE | {challenge['name']}</b>\n\n"
        f"⏱ Duration: <b>{challenge['days']} days</b> | Category: <b>{challenge['category']}</b>\n\n"
        f"<b>📋 Description:</b>\n{challenge['description']}\n\n"
        f"<b>📅 First 10 Days Preview:</b>\n"
        + "\n".join([f"  ✅ {d}" for d in challenge['days_list']]) + "\n\n"
        f"<b>💡 Accountability Tip:</b>\n{accountability_tips[seed % len(accountability_tips)]}\n\n"
        f"<b>🎬 Content Strategy:</b>\n"
        f"  📱 Day 1: Announcement video\n"
        f"  📸 Daily: Progress story/update\n"
        f"  📹 Day 30: Final results video\n"
        f"  🔄 Compile into a transformation reel"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_meme(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("meme")
    data = fetch_json(f"{MEME_API}")
    seed = generate_daily_seed("meme")

    if "error" not in data:
        title   = sanitize(data.get("title","Meme"))
        url     = data.get("url","")
        subreddit = sanitize(data.get("subreddit","memes"))
        ups     = data.get("ups", 0)

        text = (
            f"<b>😂 MEME OF THE DAY</b>\n\n"
            f"<b>{title}</b>\n"
            f"📌 r/{subreddit} | 👍 {ups:,} upvotes\n\n"
            f"🔗 {url}\n\n"
            f"<b>💡 Meme Content Tips:</b>\n"
            f"  🔥 Relatable > Funny for engagement\n"
            f"  📌 Niche memes = more saves & shares\n"
            f"  ✏️ Create custom memes in your niche\n"
            f"  ⚡ Trending meme format + your niche topic = viral"
        )
    else:
        meme_ideas = [
            "The 'Distracted Boyfriend' applied to [your niche]",
            "Drake pointing meme: [old way] vs [your method]",
            "Expanding brain meme about levels of [skill]",
            "Two buttons meme: [hard choice in your niche]",
            "Gru's plan meme: your content strategy",
        ]
        text = (
            f"<b>😂 MEME IDEAS</b>\n\n"
            f"Could not load meme. Here are custom meme ideas:\n\n"
            + "\n".join([f"  😂 {m}" for m in meme_ideas]) +
            f"\n\n<b>💡 Tools:</b> imgflip.com or Canva for custom memes"
        )

    text += BRAND_FOOTER
    await _send(update, text, is_callback)


async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    track_command("image")
    seed = generate_daily_seed("image")
    random.seed(seed)

    # Check if custom prompt provided
    args = context.args if hasattr(context, 'args') and context.args else []
    if args:
        prompt = " ".join(args)
    else:
        prompts = [
            "a professional content creator workspace, MacBook, ring light, cozy aesthetic, morning light, photorealistic, 4k",
            "abstract social media growth concept, ascending rocket, neon colors, dark background, digital art, 4k",
            "flat lay photography, phone, notebook, coffee, aesthetic desk setup, warm tones, overhead shot",
            "futuristic AI neural network visualization, glowing nodes, blue purple neon, dark background, 8k render",
            "cozy podcast studio, vintage microphone, warm lamp light, books in background, cinematic, 4k",
            "vibrant gaming battlestation, RGB lighting, multiple monitors, dark room, cyberpunk aesthetic",
            "minimal scandinavian office, white walls, plants, natural wood desk, morning sunlight, 4k photo",
            "luxury brand flat lay, gold accents, marble surface, premium lifestyle photography",
            "motivational quote background, sunrise mountains, golden hour, breathtaking landscape, 4k",
            "creative agency aesthetic, brainstorm board, sticky notes, modern office, editorial style photo",
        ]
        prompt = prompts[seed % len(prompts)]

    # Multiple image variations
    width, height = 1024, 1024
    seed_val = seed % 9999

    encoded_prompt = urllib.parse.quote(prompt)
    img_url_1 = f"{POLLINATIONS_IMG}/{encoded_prompt}?width={width}&height={height}&seed={seed_val}&model=flux"
    img_url_2 = f"{POLLINATIONS_IMG}/{encoded_prompt}?width={width}&height={height}&seed={seed_val+1}&model=flux"

    response = (
        f"<b>🖼 AI IMAGE GENERATOR</b>\n\n"
        f"<b>🎨 Prompt:</b>\n<i>{sanitize(prompt)}</i>\n\n"
        f"<b>🔗 Generated Images:</b>\n"
        f"1️⃣ {img_url_1}\n\n"
        f"2️⃣ {img_url_2}\n\n"
        f"<b>💡 How to Use:</b>\n"
        f"  1. Tap a link to open the image\n"
        f"  2. Long-press → Save to Camera Roll\n"
        f"  3. Use in your content or as inspiration\n\n"
        f"<b>⚡ Custom Image:</b>\n"
        f"<code>/image a sunset over Lagos skyline, golden hour, aerial view</code>\n\n"
        f"<b>🔧 Pro Prompting Tips:</b>\n"
        f"  • Add 'photorealistic, 4k, 8k' for quality\n"
        f"  • Specify lighting: golden hour, neon, soft light\n"
        f"  • Add style: 'cinematic, editorial, aesthetic'\n"
        f"  • Include mood: 'cozy, dramatic, minimal, luxury'"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user = update.effective_user
    chat_id = update.effective_chat.id
    subscribed = db_get_subscriptions(chat_id)
    settings = db_get_user_setting(user.id)
    total_users = db_get_total_users()

    top_commands = sorted(_bot_stats["commands_used"].items(), key=lambda x: x[1], reverse=True)[:5]
    top_str = "\n".join([f"  /{cmd}: {count}x" for cmd, count in top_commands]) or "  No data yet"

    response = (
        f"<b>📊 BOT STATISTICS</b>\n\n"
        f"<b>🌍 Global Stats:</b>\n"
        f"  👥 Total users: {total_users:,}\n"
        f"  📊 Total requests: {_bot_stats['total_requests']:,}\n\n"
        f"<b>⚙️ Your Settings:</b>\n"
        f"  📍 Location: {settings.get('city', DEFAULT_CITY)}\n"
        f"  ⏰ Reminder: {settings.get('reminder_time', '09:00')}\n"
        f"  🔔 Subscriptions: {len(subscribed)} categories\n"
        + (f"  📋 Active: {', '.join(subscribed[:5])}\n" if subscribed else "") + "\n"
        f"<b>🏆 Top Commands (Session):</b>\n{top_str}\n\n"
        f"<b>📅 Server Date:</b> {date.today().strftime('%B %d, %Y')}\n"
        f"<b>🤖 Bot Version:</b> v{BOT_VERSION}"
        + BRAND_FOOTER
    )
    await _send(update, response, is_callback)


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_subscribe_menu(update, context, is_callback=False)

async def cmd_reminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_reminder_menu(update, context, is_callback=False)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_mystats(update, context, is_callback=False)

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id)
    subscribed = db_get_subscriptions(update.effective_chat.id)
    text = (
        f"<b>⚙️ YOUR SETTINGS</b>\n\n"
        f"📍 <b>Location:</b> {settings.get('city', DEFAULT_CITY)}\n"
        f"⏰ <b>Reminder Time:</b> {settings.get('reminder_time', '09:00')}\n"
        f"🌐 <b>Language:</b> {settings.get('language', 'en').upper()}\n"
        f"🔔 <b>Subscriptions:</b> {', '.join(subscribed) or 'None'}\n\n"
        f"<b>🔧 Commands to Update:</b>\n"
        f"  /setcity London — update weather location\n"
        f"  /setreminder 08:00 — set reminder time\n"
        f"  /setcategories motivation,tech — set categories\n"
        f"  /subscribe — manage all subscriptions\n"
        f"  /settheme 5 — change Bible weekly theme\n\n"
        f"<b>📊 Quick Stats:</b>\n"
        f"  /stats — full bot statistics"
    )
    await update.message.reply_html(text)


async def cmd_setcity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_html(
            "📍 Usage: <code>/setcity CityName</code>\n"
            "Example: <code>/setcity Accra</code>\n"
            "Example: <code>/setcity London</code>"
        )
        return
    city_name = " ".join(context.args).title()
    geo = fetch_json(GEO_API, {"name": city_name, "count": 1, "language": "en", "format": "json"})
    if "error" not in geo and geo.get("results"):
        r = geo["results"][0]
        lat = r.get("latitude", DEFAULT_LAT)
        lon = r.get("longitude", DEFAULT_LON)
        full_name = f"{r.get('name',city_name)}, {r.get('country','')}"
    else:
        lat, lon, full_name = DEFAULT_LAT, DEFAULT_LON, city_name
    db_set_user_setting(update.effective_user.id, city=full_name, lat=lat, lon=lon)
    await update.message.reply_html(f"✅ Location set to <b>{sanitize(full_name)}</b>!\nUse /weather to check conditions.")


async def cmd_setreminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_html("Usage: <code>/setreminder HH:MM</code>")
        return
    try:
        datetime.strptime(context.args[0], "%H:%M")
    except ValueError:
        await update.message.reply_html("❌ Invalid time. Use HH:MM format. Example: <code>/setreminder 09:00</code>")
        return
    db_set_user_setting(update.effective_user.id, reminder_time=context.args[0])
    await update.message.reply_html(f"⏰ Reminder set for <b>{context.args[0]}</b> daily!")


async def cmd_setcategories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_html("Usage: <code>/setcategories cat1,cat2,cat3</code>")
        return
    all_cats = ["sports","bible","game","design","motivation","influencer","shop","tech",
                "others","weather","youtube","business","crypto","ai","music","podcast",
                "news","fitness","travel","mindset"]
    chat_id  = update.effective_chat.id
    user_id  = update.effective_user.id
    cats     = [c.strip().lower() for c in " ".join(context.args).split(",")]
    for c in all_cats:
        db_remove_subscription(user_id, chat_id, c)
    added = [c for c in cats if c in all_cats]
    for c in added:
        db_add_subscription(user_id, chat_id, c)
    if added:
        await update.message.reply_html(f"✅ Daily categories: <b>{', '.join(added)}</b>")
    else:
        await update.message.reply_html("❌ No valid categories. Check /help for the list.")


async def cmd_reminderstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = update.effective_user.id
    chat_id  = update.effective_chat.id
    settings = db_get_user_setting(user_id)
    subs     = db_get_subscriptions(chat_id)
    text = (
        f"<b>⏰ Reminder Status</b>\n\n"
        f"🕐 Time: <b>{settings.get('reminder_time','09:00')}</b> daily\n"
        f"📍 Location: {settings.get('city', DEFAULT_CITY)}\n"
        f"📋 Categories: {', '.join(subs) or 'None set'}\n\n"
        f"Use /subscribe to change categories\n"
        f"Use /setreminder HH:MM to change time"
    )
    await update.message.reply_html(text)


async def cmd_cancelreminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    all_cats = ["sports","bible","game","design","motivation","influencer","shop","tech",
                "others","weather","youtube","business","crypto","ai","music","podcast",
                "news","fitness","travel","mindset"]
    for c in all_cats:
        db_remove_subscription(user_id, chat_id, c)
    await update.message.reply_html("✅ All reminders cancelled. Use /subscribe to set up new ones.")


async def cmd_settheme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_html("Usage: <code>/settheme 1-52</code>")
        return
    try:
        idx = int(context.args[0]) - 1
        if idx < 0 or idx > 51:
            raise ValueError
    except ValueError:
        await update.message.reply_html("❌ Enter a number between 1 and 52.")
        return
    db_set_user_setting(update.effective_user.id, weekly_theme_idx=idx)
    await update.message.reply_html(f"✅ Weekly Bible theme index set to <b>{idx+1}</b>!")


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE HANDLER (Natural Language)
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").lower().strip()
    user = update.effective_user
    db_upsert_user(user.id, user.username or user.first_name)

    keyword_map = {
        ("bible","verse","devotion","prayer","scripture"): cmd_bible,
        ("sports","score","game","football","basketball","nba","nfl"): cmd_sports,
        ("motivation","motivate","inspire","quote","affirmation"): cmd_motivation,
        ("crypto","bitcoin","ethereum","coin","blockchain"): cmd_crypto,
        ("weather","rain","temperature","forecast","sunny","cloud"): cmd_weather,
        ("joke","funny","laugh","humor","lol","haha"): cmd_joke,
        ("fact","facts","learn","interesting","trivia"): cmd_fact,
        ("recipe","food","cook","meal","eat","cooking"): cmd_recipe,
        ("fitness","workout","exercise","gym","health"): cmd_fitness,
        ("travel","trip","vacation","destination","places"): cmd_travel,
        ("music","song","artist","playlist","genre"): cmd_music,
        ("ai","artificial intelligence","chatgpt","claude","gpt"): cmd_ai,
        ("design","logo","art","graphic","colour","color"): cmd_design,
        ("business","startup","entrepreneur","money","income"): cmd_business,
        ("news","headline","breaking","current","latest"): cmd_news,
    }

    for keywords, handler in keyword_map.items():
        if any(kw in text for kw in keywords):
            await handler(update, context)
            return

    # Default response
    responses = [
        f"Hey {user.first_name}! 👋 Tap the menu buttons or type a command like /sports, /motivation, or /bible.",
        f"Hi {user.first_name}! 🚀 Type /help to see all 30+ content categories.",
        f"What's up {user.first_name}! 🎯 Try /start to see the full menu of content options.",
    ]
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    await update.message.reply_html(responses[seed % len(responses)], reply_markup=MAIN_KB)


# ═══════════════════════════════════════════════════════════════════════════════
# SEND HELPER
# ═══════════════════════════════════════════════════════════════════════════════

async def _send(update: Update, text: str, is_callback: bool):
    # Telegram message limit is 4096 chars
    MAX = 4000
    if len(text) > MAX:
        text = text[:MAX] + "..."

    if is_callback:
        try:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except Exception:
            try:
                await update.callback_query.message.reply_html(text, disable_web_page_preview=True)
            except Exception:
                pass
        # Show main keyboard after response
        try:
            await update.callback_query.message.reply_html(
                f"🎯 Choose your next content category:",
                reply_markup=MAIN_KB,
                disable_web_page_preview=True,
            )
        except Exception:
            pass
    else:
        try:
            await update.message.reply_html(text, disable_web_page_preview=True)
        except Exception:
            await update.message.reply_html(text[:MAX], disable_web_page_preview=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

async def send_scheduled_content(bot):
    """Send daily content to subscribed chats."""
    all_subs = db_get_all_subscriptions()
    chat_categories: Dict[int, List[str]] = defaultdict(list)
    for chat_id, category in all_subs:
        chat_categories[chat_id].append(category)

    current_time = datetime.now().strftime("%H:%M")

    for chat_id, categories in chat_categories.items():
        try:
            # Check user's preferred time
            if HAS_DB:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT user_id FROM subscriptions WHERE chat_id=? LIMIT 1", (chat_id,))
                row = c.fetchone()
                conn.close()
                if row:
                    settings = db_get_user_setting(row[0])
                    if settings.get("reminder_time","09:00") != current_time:
                        continue

            # Pick a random subscribed category
            cat = random.choice(categories)
            seed = generate_daily_seed(cat)
            content_previews = {
                "motivation": "💪 Your daily motivation is ready!",
                "bible": "📖 Your daily verse awaits!",
                "crypto": "₿ Fresh crypto prices & insights!",
                "tech": "💻 Today's tech news is in!",
                "sports": "⚽ Latest scores & sports content!",
                "ai": "🤖 AI tools & trends update!",
                "fitness": "💪 Today's workout is ready!",
                "news": "📰 Breaking news update!",
            }
            preview = content_previews.get(cat, f"🎯 Your daily {cat} content is ready!")
            await bot.send_message(
                chat_id=chat_id,
                text=f"{preview}\n\nTap /{cat} to get it now!\n\n<i>💡 Manage: /subscribe | /cancelreminder</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if TELEGRAM_TOKEN in ("YOUR_BOT_TOKEN_HERE", ""):
        print("ERROR: Set TELEGRAM_TOKEN environment variable.")
        print("Get a token from @BotFather on Telegram.")
        sys.exit(1)

    init_db()
    print(f"✅ Database ready: {DB_PATH}" if HAS_DB else "⚠️  Running without DB (subscriptions in-memory only)")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ─── Command Handlers ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",             start))
    app.add_handler(CommandHandler("help",              help_command))

    # Core content
    app.add_handler(CommandHandler("sports",            cmd_sports))
    app.add_handler(CommandHandler("bible",             cmd_bible))
    app.add_handler(CommandHandler("game",              cmd_game))
    app.add_handler(CommandHandler("design",            cmd_design))
    app.add_handler(CommandHandler("motivation",        cmd_motivation))
    app.add_handler(CommandHandler("influencer",        cmd_influencer))
    app.add_handler(CommandHandler("shop",              cmd_shop))
    app.add_handler(CommandHandler("tech",              cmd_tech))
    app.add_handler(CommandHandler("others",            cmd_others))

    # Enhanced
    app.add_handler(CommandHandler("weather",           cmd_weather))
    app.add_handler(CommandHandler("youtube",           cmd_youtube))
    app.add_handler(CommandHandler("tweet",             cmd_tweet))
    app.add_handler(CommandHandler("hashtags",          cmd_hashtags))
    app.add_handler(CommandHandler("business",          cmd_business))
    app.add_handler(CommandHandler("crypto",            cmd_crypto))
    app.add_handler(CommandHandler("ai",                cmd_ai))
    app.add_handler(CommandHandler("music",             cmd_music))
    app.add_handler(CommandHandler("podcast",           cmd_podcast))
    app.add_handler(CommandHandler("news",              cmd_news))
    app.add_handler(CommandHandler("joke",              cmd_joke))
    app.add_handler(CommandHandler("fact",              cmd_fact))

    # Premium
    app.add_handler(CommandHandler("roast",             cmd_roast))
    app.add_handler(CommandHandler("story",             cmd_story))
    app.add_handler(CommandHandler("recipe",            cmd_recipe))
    app.add_handler(CommandHandler("fitness",           cmd_fitness))
    app.add_handler(CommandHandler("travel",            cmd_travel))
    app.add_handler(CommandHandler("mindset",           cmd_mindset))
    app.add_handler(CommandHandler("horoscope",         cmd_horoscope))
    app.add_handler(CommandHandler("dictionary",        cmd_dictionary))
    app.add_handler(CommandHandler("quiz",              cmd_quiz))
    app.add_handler(CommandHandler("country",           cmd_country))
    app.add_handler(CommandHandler("challenge",         cmd_challenge))
    app.add_handler(CommandHandler("meme",              cmd_meme))
    app.add_handler(CommandHandler("image",             cmd_image))

    # Utilities
    app.add_handler(CommandHandler("subscribe",         cmd_subscribe))
    app.add_handler(CommandHandler("reminder",          cmd_reminder_cmd))
    app.add_handler(CommandHandler("setreminder",       cmd_setreminder))
    app.add_handler(CommandHandler("setcategories",     cmd_setcategories))
    app.add_handler(CommandHandler("reminderstatus",    cmd_reminderstatus))
    app.add_handler(CommandHandler("cancelreminder",    cmd_cancelreminder))
    app.add_handler(CommandHandler("settings",          cmd_settings))
    app.add_handler(CommandHandler("setcity",           cmd_setcity))
    app.add_handler(CommandHandler("settheme",          cmd_settheme))
    app.add_handler(CommandHandler("stats",             cmd_stats))

    # ─── Callback & Message Handlers ─────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^cmd_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ─── Scheduler ────────────────────────────────────────────────────────────
    if HAS_SCHEDULER:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            send_scheduled_content,
            trigger="cron",
            minute="*",
            args=[app.bot],
            misfire_grace_time=30,
        )
        scheduler.start()
        print("✅ Scheduler started")

    # ─── Launch ───────────────────────────────────────────────────────────────
    print("\n" + "═" * 55)
    print("  🚀 ContentPro Bot v3.0 — ONLINE")
    print(f"  Made with ❤️  by {BOT_AUTHOR}")
    print("═" * 55)
    print("  Core:    /sports /bible /game /design /motivation")
    print("  Enhanced:/weather /crypto /ai /music /news /quiz")
    print("  Premium: /roast /story /recipe /fitness /travel")
    print("═" * 55)
    print("  Press Ctrl+C to stop.\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
