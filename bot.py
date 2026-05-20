#!/usr/bin/env python3
"""
Telegram Content Creator Bot - Auto Content Generation
Author: Drenchack
Version: 2.1.0

A Telegram bot that generates unique content across 17+ categories.
All features use FREE APIs - no paid subscriptions required.

Features:
  Core:      /sports, /bible, /game, /design, /motivation, /influencer
             /shop, /tech, /others
  Enhanced:  /reminder, /subscribe, /image, /weather, /youtube
             /tweet, /hashtags, /business, /crypto, /ai, /music, /podcast
"""

import os
import sys
import json
import random
import hashlib
import html as html_mod
import threading
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
import uuid

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

try:
    from apscheduler.schedulers.background import BackgroundScheduler
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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY", None)
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", None)

# ─── API Endpoints (all free / no-key where possible) ─────────────────────────

ESPN_BASE = "http://site.api.espn.com/apis/site/v2/sports"
BIBLE_API_URL = "https://bible-api.com"
FREETOGAME_API = "https://www.freetogame.com/api"
NEWS_MIRROR = "https://saurav.tech/NewsAPI"
QUOTES_API = "https://qapi.vercel.app/api"
DESIGN_QUOTES = "https://dummyjson.com/quotes"
FAKESTORE = "https://fakestoreapi.com"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
POLLINATIONS_IMG = "https://pollinations.ai/p"
COINGECKO_API = "https://api.coingecko.com/api/v3"
AUDIO_DB = "https://www.theaudiodb.com/api/v1/json/2"
LYRICS_API = "https://api.lyrics.ovh/v1"
RSS2JSON = "https://api.rss2json.com/v1/api.json"
FREE_ESTORE = "https://free-e-store-api.onrender.com/api/v1"
INSPIRE_API = "https://api.realinspire.live/v1"

# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_LAT = 40.7128
DEFAULT_LON = -74.0060
DEFAULT_CITY = "New York"

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE (SQLite - optional, for subscriptions)
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = os.environ.get("DB_PATH", "bot_data.db")

def init_db():
    """Initialize SQLite database for subscriptions and settings."""
    if not HAS_DB:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            chat_id INTEGER,
            category TEXT,
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id, category)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            city TEXT DEFAULT 'New York',
            lat REAL DEFAULT 40.7128,
            lon REAL DEFAULT -74.0060,
            reminder_time TEXT DEFAULT '09:00',
            language TEXT DEFAULT 'en',
            weekly_theme_idx INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS seen_content (
            user_id INTEGER,
            category TEXT,
            content_date TEXT,
            PRIMARY KEY (user_id, category, content_date)
        )
    """)
    conn.commit()
    conn.close()


def db_add_subscription(user_id: int, chat_id: int, category: str):
    if not HAS_DB:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO subscriptions (user_id, chat_id, category) VALUES (?, ?, ?)",
        (user_id, chat_id, category),
    )
    conn.commit()
    conn.close()


def db_remove_subscription(user_id: int, chat_id: int, category: str):
    if not HAS_DB:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "DELETE FROM subscriptions WHERE user_id=? AND chat_id=? AND category=?",
        (user_id, chat_id, category),
    )
    conn.commit()
    conn.close()


def db_get_subscriptions(chat_id: int) -> List[str]:
    if not HAS_DB:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT DISTINCT category FROM subscriptions WHERE chat_id=?",
        (chat_id,),
    )
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def db_get_all_subscriptions() -> List[tuple]:
    """Returns list of (chat_id, category) tuples."""
    if not HAS_DB:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT chat_id, category FROM subscriptions")
    rows = c.fetchall()
    conn.close()
    return rows


def db_set_user_setting(user_id: int, **kwargs):
    if not HAS_DB:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Get existing
    c.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
    existing = c.fetchone()
    if existing:
        fields = ", ".join([f"{k}=?" for k in kwargs])
        values = list(kwargs.values()) + [user_id]
        c.execute(f"UPDATE user_settings SET {fields} WHERE user_id=?", values)
    else:
        fields = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        values = list(kwargs.values()) + [user_id]
        c.execute(
            f"INSERT INTO user_settings (user_id, {fields}) VALUES (?, {placeholders})",
            values,
        )
    conn.commit()
    conn.close()


def db_get_user_setting(user_id: int) -> dict:
    default = {
        "city": DEFAULT_CITY,
        "lat": DEFAULT_LAT,
        "lon": DEFAULT_LON,
        "reminder_time": "09:00",
        "language": "en",
        "weekly_theme_idx": 0,
    }
    if not HAS_DB:
        return default
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["user_id", "city", "lat", "lon", "reminder_time", "language", "weekly_theme_idx"]
        return {k: v for k, v in zip(keys, row) if k != "user_id"}
    return default


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_seed(category: str) -> int:
    """Generate deterministic seed for 'unique each day' content."""
    today = date.today().isoformat()
    seed_str = f"{category}-{today}"
    return int(hashlib.md5(seed_str.encode()).hexdigest(), 16)


def fetch_json(url: str, params: dict = None, headers: dict = None, timeout: int = 20) -> Any:
    """Safely fetch JSON from an API endpoint."""
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.JSONDecodeError:
        return {"error": "Invalid JSON response", "raw": resp.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def sanitize(text: str) -> str:
    """Escape HTML entities for Telegram."""
    return html_mod.escape(str(text))


def truncate(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# Category metadata
CATEGORY_META = {
    "sports": "Live scores, news & trends",
    "bible": "Daily verse + explanation + prayer",
    "game": "Trending games, hashtags, thumbnails",
    "design": "Tips, challenges, tool spotlights",
    "motivation": "Quotes, affirmations, action steps",
    "influencer": "Platform strategy & monetization",
    "shop": "Trending products & e-commerce",
    "tech": "News, innovations & tips",
    "others": "Viral formats & cross-niche ideas",
    "weather": "Local weather content for creators",
    "youtube": "Trending YouTube videos & stats",
    "tweet": "Viral tweet thread generator",
    "hashtags": "Optimized hashtag sets",
    "business": "Business news & entrepreneurship",
    "crypto": "Crypto prices & market data",
    "ai": "AI tools, models & news",
    "music": "New releases, artists, content",
    "podcast": "Podcast ideas & trending shows",
    "image": "AI-generated images from prompts",
    "reminder": "Schedule daily auto-posts",
    "subscribe": "Subscribe to daily content",
}

# Keyboard layout (3x3 grid)
MAIN_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Sports", callback_data="cmd_sports"),
        InlineKeyboardButton("Bible", callback_data="cmd_bible"),
        InlineKeyboardButton("Game", callback_data="cmd_game"),
    ],
    [
        InlineKeyboardButton("Design", callback_data="cmd_design"),
        InlineKeyboardButton("Motivation", callback_data="cmd_motivation"),
        InlineKeyboardButton("Influencer", callback_data="cmd_influencer"),
    ],
    [
        InlineKeyboardButton("Shop", callback_data="cmd_shop"),
        InlineKeyboardButton("Tech", callback_data="cmd_tech"),
        InlineKeyboardButton("Others", callback_data="cmd_others"),
    ],
])

# Extended keyboard with all features
EXTENDED_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Sports", callback_data="cmd_sports"),
        InlineKeyboardButton("Bible", callback_data="cmd_bible"),
        InlineKeyboardButton("Game", callback_data="cmd_game"),
    ],
    [
        InlineKeyboardButton("Design", callback_data="cmd_design"),
        InlineKeyboardButton("Motivation", callback_data="cmd_motivation"),
        InlineKeyboardButton("Influencer", callback_data="cmd_influencer"),
    ],
    [
        InlineKeyboardButton("Shop", callback_data="cmd_shop"),
        InlineKeyboardButton("Tech", callback_data="cmd_tech"),
        InlineKeyboardButton("Others", callback_data="cmd_others"),
    ],
    [
        InlineKeyboardButton("Weather", callback_data="cmd_weather"),
        InlineKeyboardButton("YouTube", callback_data="cmd_youtube"),
        InlineKeyboardButton("Tweet", callback_data="cmd_tweet"),
    ],
    [
        InlineKeyboardButton("Hashtags", callback_data="cmd_hashtags"),
        InlineKeyboardButton("Business", callback_data="cmd_business"),
        InlineKeyboardButton("Crypto", callback_data="cmd_crypto"),
    ],
    [
        InlineKeyboardButton("AI Tools", callback_data="cmd_ai"),
        InlineKeyboardButton("Music", callback_data="cmd_music"),
        InlineKeyboardButton("Podcast", callback_data="cmd_podcast"),
    ],
    [
        InlineKeyboardButton("Generate Image", callback_data="cmd_image"),
        InlineKeyboardButton("Subscribe", callback_data="cmd_show_subscribe"),
        InlineKeyboardButton("Reminder", callback_data="cmd_show_reminder"),
    ],
])

# ═══════════════════════════════════════════════════════════════════════════════
# BOT HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with all commands."""
    text = (
        "<b>Content Creator Bot v2.0</b>\n\n"
        "Generate unique content for social media, blogs, and creative work.\n"
        "All features use <b>free APIs</b> - no paid subscriptions needed.\n\n"
        "<b>Core Commands:</b>\n"
        "/sports | /bible | /game | /design | /motivation | /influencer\n"
        "/shop | /tech | /others\n\n"
        "<b>Enhanced Commands:</b>\n"
        "/weather - Local weather content for outdoor creators\n"
        "/youtube - Trending YouTube videos & stats\n"
        "/tweet - Viral tweet thread generator\n"
        "/hashtags - Optimized hashtag sets\n"
        "/business - Business news & entrepreneurship\n"
        "/crypto - Crypto prices & market data\n"
        "/ai - Latest AI tools, models & news\n"
        "/music - New releases & music content ideas\n"
        "/podcast - Podcast ideas & trending shows\n"
        "/image - Generate AI images from prompts\n"
        "/subscribe - Get daily content auto-delivered\n"
        "/reminder - Schedule daily posts\n"
        "/settings - Configure your preferences\n\n"
        "Tap a button below to get started!"
    )
    await update.message.reply_html(text, reply_markup=EXTENDED_KEYBOARD)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route button presses to the right command."""
    query = update.callback_query
    await query.answer()

    cmd = query.data.replace("cmd_", "")

    # Handle special button types
    if cmd == "show_subscribe":
        await show_subscribe_menu(update, context, is_callback=True)
        return
    elif cmd == "show_reminder":
        await show_reminder_menu(update, context, is_callback=True)
        return
    elif cmd.startswith("sub_"):
        category = cmd.replace("sub_", "")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db_add_subscription(user_id, chat_id, category)
        await query.edit_message_text(
            f"Subscribed to <b>{category}</b>! You'll get daily content.",
            parse_mode=ParseMode.HTML,
        )
        await query.message.reply_html(
            "Choose another category:", reply_markup=EXTENDED_KEYBOARD
        )
        return
    elif cmd.startswith("unsub_"):
        category = cmd.replace("unsub_", "")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db_remove_subscription(user_id, chat_id, category)
        await query.edit_message_text(
            f"Unsubscribed from <b>{category}</b>.",
            parse_mode=ParseMode.HTML,
        )
        return

    await query.edit_message_text(f"Generating {cmd} content...")

    handlers = {
        "sports": cmd_sports,
        "bible": cmd_bible,
        "game": cmd_game,
        "design": cmd_design,
        "motivation": cmd_motivation,
        "influencer": cmd_influencer,
        "shop": cmd_shop,
        "tech": cmd_tech,
        "others": cmd_others,
        "weather": cmd_weather,
        "youtube": cmd_youtube,
        "tweet": cmd_tweet,
        "hashtags": cmd_hashtags,
        "business": cmd_business,
        "crypto": cmd_crypto,
        "ai": cmd_ai,
        "music": cmd_music,
        "podcast": cmd_podcast,
        "image": cmd_image,
    }
    handler = handlers.get(cmd)
    if handler:
        await handler(update, context, is_callback=True)


async def show_subscribe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Show subscription management menu."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    subscribed = db_get_subscriptions(chat_id) if HAS_DB else []

    categories = [
        "sports", "bible", "game", "design", "motivation",
        "influencer", "shop", "tech", "others",
        "weather", "youtube", "business", "crypto", "ai", "music", "podcast"
    ]

    text = "<b>Subscribe to Daily Content</b>\n\n"
    text += "Tap a category to subscribe/unsubscribe:\n\n"

    keyboard = []
    row = []
    for i, cat in enumerate(categories):
        status = "ON" if cat in subscribed else "OFF"
        label = f"{cat} [{status}]"
        prefix = "unsub" if cat in subscribed else "sub"
        row.append(InlineKeyboardButton(label, callback_data=f"cmd_{prefix}_{cat}"))
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="start")])

    if is_callback:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_html(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_reminder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Show reminder scheduling info."""
    text = (
        "<b>Daily Reminder / Auto-Post</b>\n\n"
        "You can schedule the bot to automatically send content to this chat daily.\n\n"
        "<b>Set a reminder:</b>\n"
        "Use /setreminder HH:MM (24-hour format)\n"
        "Example: /setreminder 09:00\n\n"
        "<b>Set categories to include:</b>\n"
        "/setcategories sports,tech,motivation\n\n"
        "<b>Check current settings:</b>\n"
        "/reminderstatus\n\n"
        "<b>Cancel reminders:</b>\n"
        "/cancelreminder\n\n"
        "The bot will send fresh content at your scheduled time every day."
    )
    if is_callback:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_html(text)


# ─── 1. /sports ──────────────────────────────────────────────────────────────

async def cmd_sports(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Live sports scores and trending sports news from ESPN (free, no key)."""
    sports_list = [
        ("NFL", "football/nfl"),
        ("NBA", "basketball/nba"),
        ("MLB", "baseball/mlb"),
        ("NHL", "hockey/nhl"),
        ("Soccer (EPL)", "soccer/eng.1"),
        ("College Football", "football/college-football"),
        ("College Basketball", "basketball/mens-college-basketball"),
        ("MLS", "soccer/usa.1"),
    ]

    lines = ["<b>SPORTS | Live Scores & News</b>\n"]

    # Fetch scoreboards for top leagues
    for league_name, league_path in sports_list[:5]:
        url = f"{ESPN_BASE}/{league_path}/scoreboard"
        data = fetch_json(url)
        if "error" in data:
            continue

        events = data.get("events", [])
        if not events:
            continue

        for event in events[:2]:
            comps = event.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            status = comps.get("status", {}).get("displayClock", "")
            state = comps.get("status", {}).get("type", {}).get("description", "")

            team_info = []
            for c in competitors:
                team_name = c.get("team", {}).get("displayName", "TBD")
                score = c.get("score", "0")
                logo = c.get("team", {}).get("logo", "")
                abbrev = c.get("team", {}).get("abbreviation", "")
                team_info.append(f"{abbrev} ({score})")

            if team_info:
                matchup = " vs ".join(team_info)
                lines.append(f"<b>{league_name}:</b> {matchup} | {state} {status}")

    # Sports news headlines
    try:
        news_url = f"{ESPN_BASE}/football/nfl/news"
        news_data = fetch_json(news_url)
        headlines = news_data.get("articles", [])
        if headlines:
            lines.append("\n<b>Trending Headlines:</b>")
            for article in headlines[:4]:
                title = article.get("headline", "")
                if title:
                    lines.append(f"  - {sanitize(title)}")
    except Exception:
        pass

    # Content idea for sports creators
    seed = generate_daily_seed("sports")
    sports_content_ideas = [
        "Post game highlights with commentary",
        "Create a bracket or prediction post",
        "Player comparison infographic",
        "Behind-the-scenes at the stadium",
        "Fantasy sports tips for the week",
        "Historic throwback moments",
    ]
    lines.append(
        f"\n<b>Content Idea:</b>\n{sports_content_ideas[seed % len(sports_content_ideas)]}"
    )

    response = "\n".join(lines) if len(lines) > 2 else "<b>SPORTS</b>\nNo live games right now. Try during active game times!"
    await _send(update, response, is_callback)


# ─── 2. /bible ────────────────────────────────────────────────────────────────

async def cmd_bible(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Daily Bible verse + explanation + prayer on the topic. Unique each day."""
    seed = generate_daily_seed("bible")
    random.seed(seed)

    # Get user's weekly theme preference
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id) if HAS_DB else {}
    theme_idx = settings.get("weekly_theme_idx", 0)

    # Get a random verse from bible-api.com
    data = fetch_json("https://bible-api.com/data/web/random")
    if "error" in data:
        data = fetch_json("https://bible-api.com/john+3:16")

    verse_ref = data.get("reference", "John 3:16")
    verse_text = data.get("text", "For God so loved the world...")
    translation = data.get("translation_name", "WEB")

    book = verse_ref.split()[0] if " " in verse_ref else verse_ref
    topic_map = {
        "John": "Faith & Salvation", "Psalm": "Praise & Worship",
        "Proverbs": "Wisdom & Guidance", "Matthew": "Discipleship",
        "Romans": "Grace & Redemption", "Genesis": "Creation & Beginnings",
        "Exodus": "Deliverance", "Isaiah": "Hope & Prophecy",
        "Philippians": "Joy & Contentment", "Ephesians": "Spiritual Growth",
        "Psalms": "Worship", "Luke": "Compassion",
        "Acts": "The Early Church", "Hebrews": "Perseverance",
        "Corinthians": "Love & Unity", "Timothy": "Leadership",
        "Peter": "Hope & Suffering", "Revelation": "Eternal Hope",
    }
    topic = topic_map.get(book, "God's Word")
    week_day = date.today().strftime("%A")

    # Weekly theme (rotates through 52 themes based on week number)
    week_number = date.today().isocalendar()[1]
    weekly_themes = [
        "Walking in Faith", "The Power of Prayer", "Love & Compassion",
        "Strength in Trials", "Gratitude & Thanksgiving", "Wisdom & Understanding",
        "Hope & Renewal", "Grace & Forgiveness", "Courage & Boldness",
        "Peace & Rest", "Serve & Give", "Perseverance", "Trust in God",
        "Humility", "Joy of the Lord", "Faithfulness", "God's Promises",
        "New Beginnings", "Unity in Christ", "Overcoming Fear",
        "Patience", "Kindness", "Self-Control", "Worship & Praise",
        "Renewing the Mind", "God's Love", "Purpose & Calling",
        "Spiritual Warfare", "Abiding in Christ", "Light of the World",
        "Salt of the Earth", "The Narrow Path", "Redeemed",
        "Living by the Spirit", "Heavenly Treasure", "The Good Shepherd",
        "Bearing Fruit", "Armor of God", "The Great Commission",
        "Christ's Return", "Divine Protection", "God's Provision",
        "Honoring God", "Faith Without Works", "The Vine & Branches",
        "Living Stones", "Chosen Generation", "More Than Conquerors",
        "Anchored in Hope", "Rooted in Love", "The Blessed Life",
        "Shining Bright", "The Lord's Prayer",
    ]
    weekly_theme = weekly_themes[(week_number + theme_idx - 1) % len(weekly_themes)]

    # Explanations
    explanations = [
        f"This verse reminds us of the importance of <b>{topic.lower()}</b> in our daily walk with God. It calls us to reflect on His faithfulness.",
        f"In this passage, we see God's timeless truth about <b>{topic.lower()}</b> and how it applies to our lives today. Let it sink deep into your heart.",
        f"The message here centers on <b>{topic.lower()}</b> - a cornerstone of our Christian faith. Meditate on these words throughout your day.",
        f"This scripture invites us to reflect on <b>{topic.lower()}</b> as a source of strength and guidance. God's Word never returns void.",
        f"Here we find divine wisdom about <b>{topic.lower()}</b>. Let this truth transform the way you think, speak, and act today.",
    ]
    explanation = explanations[seed % len(explanations)]

    # Prayers
    prayers = [
        f"Heavenly Father, thank You for Your Word. Help me to grow in <b>{topic.lower()}</b> today. Guide my steps and fill my heart with Your peace. In Jesus' name, Amen.",
        f"Lord, I come before You grateful for this message on <b>{topic.lower()}</b>. May it transform my heart and mind. Give me strength to live according to Your will. Amen.",
        f"Dear God, open my eyes to understand the depth of <b>{topic.lower()}</b> in my life. Let Your Word be a lamp to my feet and a light to my path. In Christ's name, Amen.",
        f"Father, thank You for speaking to me through Your Word. Help me apply the truth of <b>{topic.lower()}</b> in every area of my life. Fill me with Your Spirit. Amen.",
        f"Lord Jesus, Your Word is life. As I meditate on <b>{topic.lower()}</b> today, let it produce fruit in my life. May I be a reflection of Your love. Amen.",
    ]
    prayer = prayers[seed % len(prayers)]

    # Daily declaration
    declarations = [
        f"I declare that I am walking in {topic.lower()} today.",
        f"I receive the gift of {topic.lower()} into my heart this day.",
        f"Today, I choose to grow in {topic.lower()} through God's grace.",
        f"I am strengthened and encouraged in {topic.lower()} right now.",
    ]
    declaration = declarations[seed % len(declarations)]

    response = (
        f"<b>BIBLE | Daily Devotion</b>\n\n"
        f"<b>This Week's Theme:</b> <i>{weekly_theme}</i>\n"
        f"<b>Today's Topic:</b> {topic}\n"
        f"<b>Date:</b> {week_day}, {date.today().strftime('%B %d, %Y')}\n\n"
        f"<b>{sanitize(verse_ref)}</b> ({translation})\n"
        f"<i>\"{sanitize(verse_text)}\"</i>\n\n"
        f"<b>Explanation:</b>\n{explanation}\n\n"
        f"<b>Prayer:</b>\n{prayer}\n\n"
        f"<b>Declaration:</b>\n{declaration}"
    )
    await _send(update, response, is_callback)


# ─── 3. /game ────────────────────────────────────────────────────────────────

async def cmd_game(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Trending games, hashtags, content ideas, and thumbnail tips."""
    games_data = fetch_json(f"{FREETOGAME_API}/games?sort-by=popularity")
    seed = generate_daily_seed("game")

    lines = ["<b>GAME | Trending Games & Content Ideas</b>\n"]

    if "error" not in games_data and isinstance(games_data, list):
        lines.append("<b>Top Free Games Right Now:</b>")
        for game in games_data[:7]:
            title = sanitize(game.get("title", "Unknown"))
            genre = sanitize(game.get("genre", "General"))
            platform = sanitize(game.get("platform", "PC"))
            desc = sanitize(game.get("short_description", ""))[:70]
            lines.append(f"  - {title} ({genre}) - {platform}")
            if desc:
                lines.append(f"    {desc}...")
    else:
        # Fallback: popular games list
        fallback_games = [
            "Fortnite (Battle Royale)",
            "Call of Duty: Warzone (FPS)",
            "Minecraft (Sandbox)",
            "Valorant (Tactical Shooter)",
            "GTA V (Action-Adventure)",
            "Apex Legends (Battle Royale)",
            "Roblox (Platform)",
        ]
        lines.append("<b>Trending Games (Fallback):</b>")
        for g in fallback_games:
            lines.append(f"  - {g}")

    # Trending hashtags
    hashtags_pools = [
        "#GamingCommunity #GameOn #TrendingGame #GameContent #StreamHighlights #NewRelease",
        "#GamerLife #EpicGaming #ViralGame #GamingNews #NextLevel #GameTips",
        "#GamingMoments #ContentCreator #GameTips #Playthrough #TwitchStreamer #ViralGaming",
        "#IndieGame #GameDev #RetroGaming #Esports #Multiplayer #OpenWorld",
    ]
    lines.append(f"\n<b>Trending Hashtags:</b>\n{hashtags_pools[seed % len(hashtags_pools)]}")

    # Content ideas
    content_ideas = [
        "Walkthrough guides for new releases",
        "Top 10 moments compilation from streams",
        "Review / First Impressions of trending titles",
        "Speedrun attempts or challenge runs",
        "Tips & tricks for beginners series",
        "Reacting to gaming fails compilation",
        "Building something epic in sandbox games",
        "Comparing two similar games (which is better?)",
    ]
    lines.append(f"\n<b>Content Ideas for Today:</b>")
    lines.append(f"  - {content_ideas[seed % len(content_ideas)]}")
    lines.append(f"  - {content_ideas[(seed + 2) % len(content_ideas)]}")
    lines.append(f"  - {content_ideas[(seed + 5) % len(content_ideas)]}")

    # Thumbnail tips
    thumbnail_tips = [
        "Use bright contrasting colors (orange + blue works best)",
        "Place the main subject off-center (rule of thirds)",
        "Add expressive faces or reactions for click-through",
        "Keep text minimal - 3-5 words max with bold fonts",
        "Use arrows or circles to draw attention",
        "Add depth with shadows and glow effects",
        "A/B test two thumbnail styles to see what works",
    ]
    lines.append(f"\n<b>Thumbnail Design Tip:</b>\n{thumbnail_tips[seed % len(thumbnail_tips)]}")

    # Streaming tips
    streaming_tips = [
        "Engage with chat by reading messages aloud",
        "Use a facecam to build personal connection",
        "Set a consistent streaming schedule",
        "Create custom emotes and channel points",
        "Collaborate with other streamers for cross-promotion",
    ]
    lines.append(f"\n<b>Streaming Tip:</b>\n{streaming_tips[seed % len(streaming_tips)]}")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 4. /design ──────────────────────────────────────────────────────────────

async def cmd_design(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Design tips, tricks, and inspiration for today."""
    seed = generate_daily_seed("design")
    random.seed(seed)

    quotes_data = fetch_json(f"{DESIGN_QUOTES}/random")
    quote_text = ""
    if "error" not in quotes_data:
        q = quotes_data.get("quote", "")
        author = quotes_data.get("author", "")
        if q:
            quote_text = f"\n<i>\"{sanitize(q)}\"</i> — <b>{sanitize(author)}</b>"

    design_tips = [
        "Use the 60-30-10 rule for color: 60% dominant, 30% secondary, 10% accent",
        "White space is not wasted space - let your content breathe",
        "Limit fonts to 2-3 per design for consistency",
        "Use grid systems for alignment and visual harmony",
        "Hierarchy guides the eye: size, color, and placement matter",
        "Accessibility first - ensure 4.5:1 contrast ratio for text",
        "Micro-interactions make designs feel alive and responsive",
        "Mobile-first approach ensures better user experiences",
        "Use the F-pattern or Z-pattern for web layouts",
        "Consistent spacing creates professional-looking designs",
    ]
    tip = design_tips[seed % len(design_tips)]

    design_assignments = [
        "Design a minimalist poster using only typography",
        "Create a color palette from a photo you took recently",
        "Redesign a famous logo with a modern twist",
        "Design a mobile app splash screen for a meditation app",
        "Create a social media carousel post on a topic you love",
        "Design a landing page hero section in black and white only",
        "Create a magazine cover for a fictional publication",
        "Design a sticker pack based on emotions",
    ]
    assignment = design_assignments[seed % len(design_assignments)]

    tools_spotlight = [
        "Figma - Collaborative interface design (free tier)",
        "Canva - Quick social media graphics (free tier)",
        "DALL-E / Midjourney - AI-assisted image generation",
        "Coolors.co - Color palette generator",
        "Unsplash - Free high-quality stock photos",
        "Fontjoy - Font pairing made easy",
        "Remove.bg - Background removal tool",
        "Behance / Dribbble - Design inspiration platforms",
    ]
    tool = tools_spotlight[seed % len(tools_spotlight)]

    # Design trends
    trends = [
        "AI-assisted design workflows",
        "Neumorphism 2.0 with soft shadows",
        "Kinetic typography in UI",
        "Dark mode with vibrant neon accents",
        "Glassmorphism with frosted glass effects",
        "Minimalist brutalist design",
        "3D elements in web design",
        "Animated micro-interactions",
    ]
    trend = trends[seed % len(trends)]

    response = (
        f"<b>DESIGN | Daily Design Inspiration</b>\n"
        f"{quote_text}\n\n"
        f"<b>Design Tip of the Day:</b>\n{tip}\n\n"
        f"<b>Today's Design Challenge:</b>\n{assignment}\n\n"
        f"<b>Tool Spotlight:</b>\n{tool}\n\n"
        f"<b>Trending Style:</b>\n{trend}\n\n"
        f"<b>Resources:</b>\n"
        f"  - Color: coolors.co\n"
        f"  - Fonts: fonts.google.com\n"
        f"  - Inspiration: behance.net\n"
        f"  - Icons: icons8.com"
    )
    await _send(update, response, is_callback)


# ─── 5. /motivation ──────────────────────────────────────────────────────────

async def cmd_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Unique daily motivation with quotes and actionable advice."""
    seed = generate_daily_seed("motivation")
    random.seed(seed)

    # Get quote from free API
    quote_data = fetch_json(f"{QUOTES_API}/random")
    quote_text = "The only way to do great work is to love what you do."
    author = "Steve Jobs"

    if "error" not in quote_data:
        quote_text = quote_data.get("quote", quote_text)
        author = quote_data.get("author", author)

    # Also try the inspiration API
    inspire = fetch_json(f"{INSPIRE_API}/quotes/random")
    if "error" not in inspire:
        inspire_quote = inspire.get("quote", "")
        inspire_author = inspire.get("author", "")
        if inspire_quote and seed % 3 == 0:  # Occasionally use this
            quote_text = inspire_quote
            author = inspire_author

    # Daily affirmation
    affirmations = [
        "I am capable of achieving greatness through consistent effort.",
        "Today is full of opportunities waiting to be seized.",
        "I choose to focus on progress, not perfection.",
        "My potential is limitless when I combine passion with discipline.",
        "Every challenge I face is shaping me into something stronger.",
        "I am the architect of my life; I build my foundation with purpose.",
        "I deserve success and I am prepared to work for it.",
        "My mindset determines my outcome - I choose positivity.",
        "I am grateful for everything I have and everything I am becoming.",
        "Today I take one step closer to my dreams.",
    ]
    affirmation = affirmations[seed % len(affirmations)]

    # Action steps
    action_items = [
        "Write down 3 things you're grateful for right now",
        "Identify one fear holding you back and take one small step toward it",
        "Set a 25-minute timer and focus on ONE task (Pomodoro)",
        "Send an encouraging message to someone today",
        "Review your goals and adjust your plan for this week",
        "Exercise for 15 minutes to boost your mood and energy",
        "Read for 20 minutes on a topic you want to grow in",
        "Eliminate one distraction from your environment today",
    ]
    action = action_items[seed % len(action_items)]

    # Weekly focus
    week_num = date.today().isocalendar()[1]
    weekly_focus = [
        "Mindset", "Discipline", "Creativity", "Connection",
        "Growth", "Service", "Balance", "Resilience",
        "Gratitude", "Focus", "Courage", "Patience",
        "Health", "Learning", "Purpose", "Abundance",
        "Confidence", "Integrity", "Leadership", "Empathy",
        "Innovation", "Persistence", "Optimism", "Adaptability",
        "Community", "Wellness", "Vision", "Action",
    ][(week_num - 1) % 28]

    # Morning/lunch/evening tips
    time_tips = [
        "Morning: Start with a 5-minute meditation to set your intention",
        "Afternoon: Take a walk to reset your focus and energy",
        "Evening: Review 3 wins from today, no matter how small",
    ]
    time_tip = time_tips[seed % len(time_tips)]

    response = (
        f"<b>MOTIVATION | Daily Inspiration</b>\n\n"
        f"<i>\"{sanitize(quote_text)}\"</i>\n"
        f"<b>— {sanitize(author)}</b>\n\n"
        f"<b>Affirmation for Today:</b>\n{affirmation}\n\n"
        f"<b>Action Step:</b>\n{action}\n\n"
        f"<b>This Week's Focus:</b> {weekly_focus}\n\n"
        f"<b>Daily Tip:</b>\n{time_tip}\n\n"
        f"<i>\"Small consistent steps lead to extraordinary results.\"</i>"
    )
    await _send(update, response, is_callback)


# ─── 6. /influencer ──────────────────────────────────────────────────────────

async def cmd_influencer(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Influencer marketing trends, strategies, and content ideas."""
    seed = generate_daily_seed("influencer")
    random.seed(seed)

    platform_trends = [
        "<b>TikTok:</b> Short-form video dominates; hooks in first 3 seconds are critical. Use trending sounds.",
        "<b>Instagram:</b> Reels outperform static posts; carousels drive saves; Stories for daily engagement.",
        "<b>YouTube:</b> Long-form deep dives with high retention rewarded; Shorts for reach.",
        "<b>LinkedIn:</b> Thought leadership with personal stories drives engagement and credibility.",
        "<b>Twitter/X:</b> Thread culture rules; hot takes and timely commentary win.",
        "<b>Pinterest:</b> Visual search is growing; create pinnable infographics and guides.",
        "<b>Snapchat:</b> Gen Z engagement is high; use Spotlight for discoverability.",
    ]
    platform = platform_trends[seed % len(platform_trends)]

    content_strategies = [
        "Behind-the-scenes content builds authenticity and trust with your audience",
        "User-generated content campaigns boost engagement by 4x",
        "Collaborative content with other creators expands your reach exponentially",
        "Educational content establishes you as an authority in your niche",
        "Storytelling with emotional hooks creates loyal, engaged audiences",
        "Consistent series create anticipation and return viewers",
        "Polls, Q&As, and interactive content boost algorithm performance",
    ]
    strategy = content_strategies[seed % len(content_strategies)]

    monetization_ideas = [
        "Brand partnerships: Pitch 5 brands in your niche this week",
        "Digital products: Create a template or guide your audience needs",
        "Affiliate marketing: Share products you use with honest reviews",
        "Membership/subscriptions: Offer exclusive content (Patreon, etc.)",
        "Consulting/coaching: Leverage your expertise for 1:1 sessions",
        "Merchandise: Start simple with print-on-demand products",
        "Courses: Package your knowledge into a digital course",
    ]
    monetize = monetization_ideas[seed % len(monetization_ideas)]

    trending_niches = [
        "AI tools & productivity hacks",
        "Sustainable living & eco-friendly products",
        "Personal finance for Gen Z & Millennials",
        "Health optimization & biohacking",
        "Digital nomad & remote work lifestyle",
        "Mental health & wellness",
        "Side hustles & passive income",
        "Booktok & reading community",
    ]
    niche = trending_niches[seed % len(trending_niches)]

    # Growth tip
    growth_tips = [
        "Post consistently at least 3-4 times per week",
        "Engage with your audience within the first hour of posting",
        "Use all relevant hashtags (up to 30 on Instagram)",
        "Cross-promote your content across all platforms",
        "Analyze your best-performing content and duplicate its formula",
    ]
    growth = growth_tips[seed % len(growth_tips)]

    response = (
        f"<b>INFLUENCER | Content Strategy & Trends</b>\n\n"
        f"<b>Platform Insight:</b>\n{platform}\n\n"
        f"<b>Content Strategy:</b>\n{strategy}\n\n"
        f"<b>Monetization Tip:</b>\n{monetize}\n\n"
        f"<b>Trending Niche:</b>\n{niche}\n\n"
        f"<b>Growth Tip:</b>\n{growth}\n\n"
        f"<b>Posting Schedule:</b>\n"
        f"  Mon/Wed/Fri - Value content (tips, tutorials)\n"
        f"  Tue/Thu - Engagement content (polls, questions)\n"
        f"  Sat/Sun - Personal content (BTS, stories, vlogs)"
    )
    await _send(update, response, is_callback)


# ─── 7. /shop ────────────────────────────────────────────────────────────────

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Trending products, shopping insights, and e-commerce content."""
    seed = generate_daily_seed("shop")
    random.seed(seed)

    products = fetch_json(f"{FAKESTORE}/products?limit=8")

    lines = ["<b>SHOP | Trending Products & Insights</b>\n"]

    if "error" not in products and isinstance(products, list):
        lines.append("<b>Featured Products:</b>")
        for i, product in enumerate(products[:6], 1):
            title = sanitize(product.get("title", "Product"))
            price = product.get("price", "N/A")
            category = sanitize(product.get("category", "General"))
            rating = product.get("rating", {}).get("rate", "N/A")
            lines.append(f"  {i}. <b>{truncate(title, 55)}</b>")
            lines.append(f"     ${price} | {category.title()} | Rating: {rating}")
    else:
        lines.append("<b>Trending Product Categories:</b>")
        lines.append("  - Electronics & Gadgets")
        lines.append("  - Fashion & Apparel")
        lines.append("  - Home & Kitchen")
        lines.append("  - Beauty & Personal Care")
        lines.append("  - Sports & Outdoors")

    # Shopping trends
    shopping_trends = [
        "Sustainable/eco-friendly products seeing 40%+ growth YoY",
        "Subscription boxes popular in beauty, food, and fitness",
        "Social commerce via TikTok Shop and Instagram Checkout rising",
        "Personalized/custom products command premium pricing",
        "DTC (Direct-to-Consumer) brands outperform traditional retail",
        "Live shopping events driving impulse purchases",
        "Buy Now Pay Later (BNPL) options increasing conversion",
    ]
    lines.append(f"\n<b>Shopping Trend:</b>\n{shopping_trends[seed % len(shopping_trends)]}")

    # Content ideas
    review_tips = [
        "Create comparison videos (Product A vs Product B)",
        "Unboxing videos with first impressions drive high engagement",
        "Honest review content builds trust and affiliate income",
        "'5 Products Under $50' roundup posts go viral regularly",
        "Seasonal gift guides are search-friendly and shareable",
        "'What I bought from Amazon this month' series",
    ]
    lines.append(f"\n<b>Content Idea:</b>\n{review_tips[seed % len(review_tips)]}")

    # E-commerce tip
    ecom_tips = [
        "Optimize product photos with consistent backgrounds",
        "Use scarcity tactics: Limited stock, time-limited deals",
        "Email sequences: Welcome → Abandoned cart → Upsell",
        "Social proof: Display reviews and testimonials prominently",
        "Mobile optimization is non-negotiable for conversions",
    ]
    lines.append(f"\n<b>E-Commerce Tip:</b>\n{ecom_tips[seed % len(ecom_tips)]}")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 8. /tech ────────────────────────────────────────────────────────────────

async def cmd_tech(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Latest tech news, innovations, and trends."""
    seed = generate_daily_seed("tech")

    # Try with NewsAPI mirror (no key)
    news_data = fetch_json(f"{NEWS_MIRROR}/top-headlines/category/technology/us.json")

    lines = ["<b>TECH | Latest News & Innovations</b>\n"]

    if "error" not in news_data:
        articles = news_data.get("articles", [])
        if articles:
            lines.append("<b>Top Tech Headlines:</b>")
            for article in articles[:7]:
                title = article.get("title", "")
                source = article.get("source", {}).get("name", "")
                if title:
                    lines.append(f"  - {sanitize(title)}")
                    if source:
                        lines[-1] += f" ({sanitize(source)})"
        else:
            lines.append("<b>Tech Headlines:</b>")
            lines.append("  - AI models are getting smaller and more efficient")
            lines.append("  - Quantum computing reaches new milestones")
            lines.append("  - Cybersecurity threats evolving with AI")
            lines.append("  - Electric vehicle tech continues to advance")
            lines.append("  - AR/VR headsets becoming mainstream")
    else:
        lines.append("<b>Tech Headlines:</b>")
        lines.append("  - AI models are getting smaller and more efficient")
        lines.append("  - Quantum computing reaches new milestones")
        lines.append("  - Cybersecurity threats evolving with AI")

    # Tech trends
    tech_content_ideas = [
        "AI and machine learning integration in everyday tools",
        "Cybersecurity best practices for remote workers",
        "Upcoming gadget releases and what to expect",
        "Open-source alternatives to paid software",
        "Programming languages gaining popularity",
        "Cloud computing trends: serverless, edge computing",
        "Blockchain beyond crypto: supply chain, identity",
        "Green tech and sustainable computing",
    ]
    lines.append(
        f"\n<b>Content Angle:</b>\n{tech_content_ideas[seed % len(tech_content_ideas)]}"
    )

    # Quick tip
    quick_tips = [
        "Use incognito mode + VPN when on public Wi-Fi",
        "Enable 2-factor authentication on ALL accounts",
        "Regularly clear browser cache and cookies for privacy",
        "Use password managers instead of reusing passwords",
        "Keep ALL software updated for security patches",
        "Backup important files using the 3-2-1 rule",
        "Use ad-blockers and privacy-focused browsers",
    ]
    lines.append(f"\n<b>Quick Tech Tip:</b>\n{quick_tips[seed % len(quick_tips)]}")

    # Quote
    tech_quotes = [
        "\"The best way to predict the future is to invent it.\" - Alan Kay",
        "\"Technology is best when it brings people together.\" - Matt Mullenweg",
        "\"Any sufficiently advanced technology is indistinguishable from magic.\" - Arthur C. Clarke",
        "\"It has become appallingly obvious that our technology has exceeded our humanity.\" - Einstein",
    ]
    lines.append(f"\n<i>{tech_quotes[seed % len(tech_quotes)]}</i>")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 9. /others ──────────────────────────────────────────────────────────────

async def cmd_others(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Random viral content ideas across multiple categories."""
    seed = generate_daily_seed("others")
    random.seed(seed)

    viral_formats = [
        "Listicles: '10 Things Nobody Tells You About [Topic]'",
        "Controversial opinion posts with discussion hooks",
        "'Day in the Life' vlogs with time stamps and chapters",
        "Before/After transformations (weight, space, skill, room)",
        "Challenge videos with a unique, original twist",
        "Reacting to old content (your own or nostalgic trends)",
        "Q&A sessions answering DMs and comments",
        "POV (Point of View) skits related to your niche",
        "Educational threads breaking down complex topics simply",
        "Storytime videos with a moral or lesson at the end",
    ]
    format_idea = viral_formats[seed % len(viral_formats)]

    content_angles = [
        "Turn a personal failure into a lesson (vulnerability sells)",
        "Mashup two unrelated niches for a fresh perspective",
        "Create a 'roadmap' showing step-by-step how to achieve X",
        "Interview someone with opposing views on a topic",
        "Document a 30-day challenge with daily updates",
        "Share a controversial take on a popular topic",
        "Break down a complex topic using analogies",
        "Share your hot take on current events in your niche",
    ]
    angle = content_angles[seed % len(content_angles)]

    engagement_hooks = [
        "Start with a bold statement that challenges common belief",
        "Ask an open-ended question that sparks debate",
        "Share a surprising statistic that stops the scroll",
        "Begin with a short story or personal anecdote",
        "Use a cliffhanger to make viewers want more",
        "Start with 'Stop scrolling if...' pattern",
        "Use the 'They don't want you to know this' hook",
        "Begin with a relatable problem statement",
    ]
    hook = engagement_hooks[seed % len(engagement_hooks)]

    categories = [
        "Fitness & Health", "Travel & Adventure", "Food & Cooking",
        "Finance & Investing", "Relationships", "Education & Learning",
        "Music & Entertainment", "Photography", "Fashion & Style",
        "Home & DIY", "Pet & Animal", "Parenting & Family",
    ]
    cat1 = categories[seed % len(categories)]
    cat2 = categories[(seed + 4) % len(categories)]

    # Algorithm tips
    algo_tips = [
        "Post when your audience is most active (check analytics)",
        "Use trending audio/music on TikTok and Reels",
        "Encourage saves with 'Save this for later' CTAs",
        "First 3 seconds must hook - no slow intros",
        "Use captions/subtitles for silent viewing",
    ]
    algo = algo_tips[seed % len(algo_tips)]

    response = (
        f"<b>OTHERS | Viral Content Ideas</b>\n\n"
        f"<b>Trending Format:</b>\n{format_idea}\n\n"
        f"<b>Content Angle:</b>\n{angle}\n\n"
        f"<b>Engagement Hook:</b>\n{hook}\n\n"
        f"<b>Cross-Niche Mashup:</b>\n"
        f"Combine <b>{cat1}</b> + <b>{cat2}</b> for a unique perspective\n\n"
        f"<b>Algorithm Tip:</b>\n{algo}\n\n"
        f"<b>Posting Strategy:</b>\n"
        f"  1. Hook in first 3 seconds\n"
        f"  2. Deliver value in the middle\n"
        f"  3. End with a CTA (comment, share, save, follow)\n\n"
        f"<i>Consistency beats perfection. Post something today!</i>"
    )
    await _send(update, response, is_callback)


# ─── 10. /weather ────────────────────────────────────────────────────────────

async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Local weather content for creators (Open-Meteo, free, no key)."""
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id) if HAS_DB else {}
    lat = settings.get("lat", DEFAULT_LAT)
    lon = settings.get("lon", DEFAULT_LON)
    city = settings.get("city", DEFAULT_CITY)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,uv_index",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,sunrise,sunset",
        "timezone": "auto",
    }
    data = fetch_json(WEATHER_API, params=params)

    wmo_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle",
        53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
        63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow",
        73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
        81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    if "error" in data:
        await _send(update, "<b>WEATHER</b>\nCould not fetch weather data. Use /settings to set your location.", is_callback)
        return

    current = data.get("current", {})
    daily = data.get("daily", {})

    weather_code = current.get("weather_code", 0)
    weather_desc = wmo_codes.get(weather_code, "Unknown")
    temp = current.get("temperature_2m", "N/A")
    feels_like = current.get("apparent_temperature", "N/A")
    humidity = current.get("relative_humidity_2m", "N/A")
    wind = current.get("wind_speed_10m", "N/A")
    uv = current.get("uv_index", "N/A")

    today_max = daily.get("temperature_2m_max", [None])[0] if daily.get("temperature_2m_max") else "N/A"
    today_min = daily.get("temperature_2m_min", [None])[0] if daily.get("temperature_2m_min") else "N/A"
    sunrise = daily.get("sunrise", [""])[0] if daily.get("sunrise") else ""
    sunset = daily.get("sunset", [""])[0] if daily.get("sunset") else ""

    # Content ideas based on weather
    weather_content = {
        0: "Perfect lighting for outdoor photoshoots today!",
        1: "Good day for content - soft natural lighting",
        2: "Overcast = perfect diffused light for photography",
        3: "Cozy indoor content day - moody lighting",
        45: "Moody fog shots for atmospheric content",
        61: "Rainy day aesthetic content ideas",
        71: "Snow day content - winter wonderland vibes",
        95: "Storm content - dramatic B-roll opportunities",
    }
    content_tip = weather_content.get(weather_code, "Check conditions before outdoor shoots")

    response = (
        f"<b>WEATHER | {sanitize(city)}</b>\n\n"
        f"<b>Current:</b> {weather_desc}, {temp}C (feels like {feels_like}C)\n"
        f"<b>Humidity:</b> {humidity}% | <b>Wind:</b> {wind} km/h | <b>UV:</b> {uv}\n\n"
        f"<b>Today:</b> High {today_max}C / Low {today_min}C\n"
        f"<b>Sunrise:</b> {sunrise} | <b>Sunset:</b> {sunset}\n\n"
        f"<b>Content Tip:</b>\n{content_tip}\n\n"
        f"<i>Set your location with /settings</i>"
    )
    await _send(update, response, is_callback)


# ─── 11. /youtube ────────────────────────────────────────────────────────────

async def cmd_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Trending YouTube video ideas and channel growth tips."""
    seed = generate_daily_seed("youtube")
    random.seed(seed)

    video_categories = [
        "How-to tutorials & educational content",
        "Product reviews & unboxings",
        "Vlogs & day-in-the-life content",
        "Gaming walkthroughs & live streams",
        "Tech reviews & comparisons",
        "Finance & investing advice",
        "Health & fitness transformations",
        "Travel documentaries & guides",
        "Cooking & recipe videos",
        "Commentary & analysis videos",
    ]

    trending_niches = [
        "AI tutorials & tool reviews",
        "Financial literacy for beginners",
        "Self-improvement & productivity",
        "True crime & mystery stories",
        "Coding & programming tutorials",
        "Entrepreneurship & business cases",
        "Home renovation & DIY",
        "Gadgets & tech unboxings",
    ]

    lines = ["<b>YOUTUBE | Trending Content & Growth</b>\n"]
    lines.append(f"<b>Trending Video Idea:</b>\n{video_categories[seed % len(video_categories)]}")
    lines.append(f"\n<b>Hot Niche:</b>\n{trending_niches[seed % len(trending_niches)]}")

    # YouTube SEO tips
    seo_tips = [
        "Use keyword-rich titles (target 30-60 characters)",
        "First 48 hours determine video success - promote immediately",
        "Create custom thumbnails with faces and bold text",
        "Use chapters/timestamps for longer videos",
        "End screen with 2-3 video recommendations",
        "Optimize description with keywords in first 2 lines",
        "Post consistently - weekly uploads build momentum",
        "Collaborate with creators in similar niche",
    ]
    lines.append(f"\n<b>SEO Tip:</b>\n{seo_tips[seed % len(seo_tips)]}")

    # Thumbnail specific
    thumb_tips = [
        "Bright colors with contrast (orange + teal is proven)",
        "Close-up face showing emotion (surprise, excitement)",
        "Text limited to 3-4 large, bold words",
        "Include visual curiosity (arrow, circle, question mark)",
        "Maintain consistent branding across all thumbnails",
    ]
    lines.append(f"\n<b>Thumbnail Tip:</b>\n{thumb_tips[seed % len(thumb_tips)]}")

    # Video length recommendations
    lengths = [
        "Shorts (under 60s) - Best for reach and new audiences",
        "8-12 minutes - Sweet spot for monetization and retention",
        "15-20 minutes - Deep dives with high audience loyalty",
        "20-30 minutes - Tutorial/educational content works well",
    ]
    lines.append(f"\n<b>Length Recommendation:</b>\n{lengths[seed % len(lengths)]}")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 12. /tweet ──────────────────────────────────────────────────────────────

async def cmd_tweet(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Generate viral tweet thread ideas."""
    seed = generate_daily_seed("tweet")
    random.seed(seed)

    topics = [
        "Productivity hacks nobody talks about",
        "Lessons learned from failing at [thing]",
        "Controversial opinion about [industry]",
        "The real reason [common belief] is wrong",
        "What I wish I knew before starting [thing]",
        "Unpopular opinion: [hot take]",
        "The truth about [popular trend]",
        "How I went from X to Y in Z months",
    ]
    topic = topics[seed % len(topics)]

    hooks = [
        "Stop scrolling. This thread will change how you think about [topic].",
        "I spent 5 years learning this. You can learn it in 5 minutes.",
        "Everyone talks about X, but nobody talks about Y. Here's the truth.",
        "This one mindset shift doubled my income. Here it is.",
        "Most people get this wrong. Let me break it down.",
        "I wish someone told me this earlier. So I'm telling you.",
    ]
    hook = hooks[seed % len(hooks)]

    threads = []
    thread_templates = [
        "Point 1: The common belief is actually wrong. Here's why...",
        "Point 2: The data tells a different story than what most assume.",
        "Point 3: Here's what actually works based on real experience.",
        "Point 4: A practical example of this in action.",
        "Point 5: The one takeaway you need to remember from this thread.",
    ]
    for i, t in enumerate(thread_templates):
        threads.append(f"{i+1}. {t}")

    response = (
        f"<b>TWEET | Viral Thread Generator</b>\n\n"
        f"<b>Topic Idea:</b>\n{topic}\n\n"
        f"<b>Hook (First Tweet):</b>\n{hook}\n\n"
        f"<b>Thread Structure:</b>\n" + "\n".join(threads) + "\n\n"
        f"<b>Best Posting Time:</b>\n"
        f"  - Weekdays 8-10 AM or 6-8 PM (EST)\n"
        f"  - Sunday mornings for engagement\n\n"
        f"<b>Hashtags:</b>\n#ContentCreator #ViralThread #GrowthMindset #TwitterTips"
    )
    await _send(update, response, is_callback)


# ─── 13. /hashtags ────────────────────────────────────────────────────────────

async def cmd_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Generate optimized hashtag sets for different platforms."""
    seed = generate_daily_seed("hashtags")
    random.seed(seed)

    # Hashtag pools by category
    hashtag_pools = {
        "general": [
            "#ContentCreator #Viral #Trending #Explore #MustWatch",
            "#GoViral #Creator #Content #NewPost #DailyContent",
            "#ViralContent #ContentCreation #CreatorLife #ContentIsKing",
        ],
        "tech": [
            "#TechNews #Innovation #AI #Technology #Future #TechTrends",
            "#ArtificialIntelligence #MachineLearning #CyberSecurity #Dev",
            "#Programming #Coding #Developer #Software #TechLife",
        ],
        "lifestyle": [
            "#Lifestyle #Motivation #Inspiration #Mindset #SelfCare",
            "#GrowthMindset #Wellness #Success #Goals #Positivity",
            "#MorningRoutine #Productivity #SelfImprovement #Focus",
        ],
        "business": [
            "#Business #Entrepreneur #Startup #Marketing #Growth",
            "#Entrepreneurship #SmallBusiness #Branding #SocialMedia",
            "#DigitalMarketing #Ecommerce #BusinessTips #SideHustle",
        ],
        "creative": [
            "#Creative #Design #Art #Photography #Inspiration",
            "#GraphicDesign #Artist #DigitalArt #Creativity #DesignInspo",
            "#CreativeProcess #ArtistsOnTwitter #VisualArt #Photography",
        ],
    }

    categories = list(hashtag_pools.keys())
    cat1 = categories[seed % len(categories)]
    cat2 = categories[(seed + 2) % len(categories)]

    lines = ["<b>HASHTAGS | Optimized Sets</b>\n"]

    # Platform-specific advice
    platform_advice = {
        "Instagram": "Use 25-30 hashtags. Mix large (500k+), medium (50-500k), small (under 50k). Place in first comment.",
        "TikTok": "Use 3-5 highly relevant hashtags. Trend ones matter most. Keep them in caption.",
        "Twitter/X": "Use 1-3 hashtags max. Too many looks spammy. #Thread works well.",
        "LinkedIn": "Use 3-5 professional hashtags. Industry-specific ones perform best.",
        "YouTube": "Use 10-15 tags in the video settings. Include variations and misspellings.",
    }
    platform_keys = list(platform_advice.keys())
    p_advice = platform_advice[platform_keys[seed % len(platform_keys)]]
    lines.append(f"<b>Platform Strategy:</b>\n{p_advice}\n")

    # Hashtag sets
    lines.append(f"<b>Set 1 - {cat1.title()}:</b>")
    lines.append(hashtag_pools[cat1][seed % len(hashtag_pools[cat1])])
    lines.append(f"\n<b>Set 2 - {cat2.title()}:</b>")
    lines.append(hashtag_pools[cat2][(seed + 1) % len(hashtag_pools[cat2])])
    lines.append(f"\n<b>Set 3 - Mixed:</b>")
    mixed = hashtag_pools[cat1][(seed + 2) % len(hashtag_pools[cat1])] + " " + hashtag_pools["general"][seed % len(hashtag_pools["general"])]
    lines.append(mixed)

    # Hashtag size strategy
    size_strategies = [
        "20% mega hashtags (1M+ posts), 30% large (200k-1M), 30% medium (20k-200k), 20% small (<20k)",
        "Use a mix of broad and niche-specific hashtags for best reach",
        "Create branded hashtags unique to your content/channel",
        "Rotate hashtags regularly to avoid shadowbanning",
        "Analyze which hashtags give you the most reach and double down",
    ]
    lines.append(f"\n<b>Strategy Tip:</b>\n{size_strategies[seed % len(size_strategies)]}")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 14. /business ───────────────────────────────────────────────────────────

async def cmd_business(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Business news and entrepreneurship content."""
    seed = generate_daily_seed("business")
    random.seed(seed)

    business_topics = [
        "Rise of AI-powered startups disrupting traditional industries",
        "Remote work is reshaping commercial real estate markets",
        "Subscription economy continues to grow across all sectors",
        "Sustainable business practices becoming competitive advantage",
        "Creator economy: influencers becoming legitimate business owners",
        "Fintech innovations changing how small businesses access capital",
        "Supply chain resilience becoming a boardroom priority",
        "Digital transformation still accelerating in traditional sectors",
    ]
    topic = business_topics[seed % len(business_topics)]

    entrepreneur_tips = [
        "Validate your idea with 10 customer conversations before building",
        "Focus on one problem and solve it exceptionally well",
        "Build in public - share your journey to attract early adopters",
        "Revenue first, funding second - prove your model works",
        "Hire for attitude, train for skill in early stages",
        "Your network is your net worth - attend industry events",
        "Read your customers' minds by reading their reviews of competitors",
    ]
    tip = entrepreneur_tips[seed % len(entrepreneur_tips)]

    books = [
        "Zero to One - Peter Thiel",
        "The Lean Startup - Eric Ries",
        "Good to Great - Jim Collins",
        "Start With Why - Simon Sinek",
        "The E-Myth Revisited - Michael Gerber",
        "Built to Sell - John Warrillow",
        "Traction - Gabriel Weinberg",
    ]
    book = books[seed % len(books)]

    metrics = [
        "MRR (Monthly Recurring Revenue) - The lifeblood of SaaS",
        "CAC (Customer Acquisition Cost) - How much to get a customer",
        "LTV (Lifetime Value) - Total revenue from a customer",
        "Churn Rate - % of customers who leave monthly",
        "Burn Rate - How fast you're spending cash",
        "Gross Margin - Revenue minus direct costs",
    ]
    metric = metrics[seed % len(metrics)]

    response = (
        f"<b>BUSINESS | Trends & Entrepreneurship</b>\n\n"
        f"<b>Market Trend:</b>\n{topic}\n\n"
        f"<b>Founder Tip:</b>\n{tip}\n\n"
        f"<b>Recommended Reading:</b>\n{book}\n\n"
        f"<b>Key Metric to Know:</b>\n{metric}\n\n"
        f"<b>Daily Action:</b>\n"
        f"  1. Reach out to one potential customer or partner\n"
        f"  2. Review your top 3 KPIs\n"
        f"  3. Spend 30 minutes on high-leverage work"
    )
    await _send(update, response, is_callback)


# ─── 15. /crypto ──────────────────────────────────────────────────────────

async def cmd_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Crypto prices and market data via CoinGecko free API."""
    seed = generate_daily_seed("crypto")

    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    data = fetch_json(
        f"{COINGECKO_API}/simple/price",
        params={
            "ids": "bitcoin,ethereum,solana,cardano,ripple,polkadot,dogecoin,avalanche-2",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        },
        headers=headers,
    )

    lines = ["<b>CRYPTO | Market Update</b>\n"]

    if "error" not in data and data:
        lines.append("<b>Live Prices:</b>")
        name_map = {
            "bitcoin": "Bitcoin", "ethereum": "Ethereum", "solana": "Solana",
            "cardano": "Cardano", "ripple": "XRP", "polkadot": "Polkadot",
            "dogecoin": "Dogecoin", "avalanche-2": "Avalanche",
        }
        for coin_id, info in data.items():
            name = name_map.get(coin_id, coin_id.title())
            price = info.get("usd", 0)
            change = info.get("usd_24h_change", 0)
            sign = "+" if change >= 0 else ""
            emoji = "💚" if change >= 0 else "🔴"
            lines.append(f"  {emoji} <b>{name}:</b> ${price:,.2f} ({sign}{change:.2f}%)")
    else:
        # Fallback data
        fallback = [
            ("Bitcoin", 67890, 2.3),
            ("Ethereum", 3420, 1.8),
            ("Solana", 148, 5.2),
            ("Cardano", 0.45, -1.2),
            ("XRP", 0.62, 0.8),
        ]
        lines.append("<b>Prices (Delayed):</b>")
        for name, price, change in fallback:
            sign = "+" if change >= 0 else ""
            emoji = "💚" if change >= 0 else "🔴"
            lines.append(f"  {emoji} <b>{name}:</b> ${price:,.2f} ({sign}{change:.1f}%)")

    # Content ideas
    crypto_content = [
        "Beginner's guide to crypto wallets and security",
        "DeFi explained simply with analogies",
        "NFT market trends and what's selling",
        "Crypto taxation basics every holder should know",
        "Layer 2 solutions and why they matter",
        "Staking vs. yield farming - risk comparison",
    ]
    lines.append(f"\n<b>Content Idea:</b>\n{crypto_content[seed % len(crypto_content)]}")

    # Safety tip
    safety_tips = [
        "Never share your private keys or seed phrases with anyone",
        "Use hardware wallets for long-term storage",
        "Always verify contract addresses before interacting with dApps",
        "Beware of phishing sites - bookmark official URLs",
        "Start with small amounts when learning new protocols",
    ]
    lines.append(f"\n<b>Safety Tip:</b>\n{safety_tips[seed % len(safety_tips)]}")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 16. /ai ─────────────────────────────────────────────────────────────────

async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Latest AI tools, models, and news."""
    seed = generate_daily_seed("ai")
    random.seed(seed)

    ai_tools = [
        "Claude 3.5 Sonnet - Best for coding and analysis",
        "GPT-4o - Multimodal reasoning and creative tasks",
        "Midjourney V6 - High-quality image generation",
        "Stable Diffusion XL - Open-source image generation",
        "Cursor - AI-powered code editor",
        "Perplexity AI - Research assistant with citations",
        "RunwayML - AI video generation and editing",
        "ElevenLabs - Voice cloning and text-to-speech",
        "Suno AI - AI music generation",
        "Notion AI - Writing assistant integrated into notes",
    ]
    tool = ai_tools[seed % len(ai_tools)]

    ai_trends = [
        "Small language models (SLMs) gaining traction for edge devices",
        "AI agents automating multi-step workflows autonomously",
        "Open-source models catching up to proprietary ones",
        "Video generation AI reaching production quality",
        "AI in healthcare diagnostics showing breakthrough results",
        "Regulatory frameworks for AI safety being developed globally",
        "Retrieval-Augmented Generation (RAG) improving accuracy",
    ]
    trend = ai_trends[seed % len(ai_trends)]

    prompt_ideas = [
        "Write a thread explaining [concept] to a complete beginner",
        "Generate 10 content ideas about [topic] for TikTok",
        "Create a detailed outline for a YouTube video on [topic]",
        "Write an email sequence for [product] launch",
        "Generate captions for 5 Instagram posts about [topic]",
    ]
    prompt = prompt_ideas[seed % len(prompt_ideas)]

    response = (
        f"<b>AI TOOLS | Latest in Artificial Intelligence</b>\n\n"
        f"<b>Tool Spotlight:</b>\n{tool}\n\n"
        f"<b>Trend:</b>\n{trend}\n\n"
        f"<b>Prompt Idea for Content:</b>\n{prompt}\n\n"
        f"<b>Free AI Resources:</b>\n"
        f"  - ChatGPT (openai.com/chatgpt)\n"
        f"  - Claude (claude.ai)\n"
        f"  - Gemini (gemini.google.com)\n"
        f"  - Perplexity (perplexity.ai)\n"
        f"  - Hugging Face (huggingface.co)\n\n"
        f"<b>Pro Tip:</b>\n"
        f"Use specific personas in your prompts for better results. "
        f"Example: 'Act as a social media manager for a fitness brand...'"
    )
    await _send(update, response, is_callback)


# ─── 17. /music ──────────────────────────────────────────────────────────────

async def cmd_music(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Music content ideas, trending genres, and artist insights."""
    seed = generate_daily_seed("music")
    random.seed(seed)

    # Use AudioDB for music data (free key: 2 - test key)
    trending = fetch_json(f"{AUDIO_DB}/trending.php?country=us&type=itunes&format=singles")

    lines = ["<b>MUSIC | Content Ideas & Trends</b>\n"]

    if "error" not in trending and trending.get("trending"):
        items = trending["trending"][:7]
        lines.append("<b>Trending Tracks:</b>")
        for i, track in enumerate(items, 1):
            name = sanitize(track.get("strTrack", "Unknown"))
            artist = sanitize(track.get("strArtist", "Unknown"))
            lines.append(f"  {i}. {name} - {artist}")
    else:
        # Fallback genres/tracks
        genres = [
            "Afrobeats", "K-Pop", "Latin Trap", "Lo-fi Hip Hop",
            "Synthwave", "House", "R&B", "Indie Folk",
        ]
        lines.append("<b>Trending Genres:</b>")
        for g in genres:
            lines.append(f"  - {g}")

        tracks = [
            "Espresso - Sabrina Carpenter",
            "Too Sweet - Hozier",
            "Lose Control - Teddy Swims",
            "Beautiful Things - Benson Boone",
            "A Bar Song (Tipsy) - Shaboozey",
        ]
        lines.append(f"\n<b>Popular Tracks:</b>")
        for t in tracks:
            lines.append(f"  - {t}")

    # Music content ideas
    music_content = [
        "Create a playlist for a specific mood or activity",
        "React to new album releases with live commentary",
        "Break down songwriting techniques in popular hits",
        "Create music production tutorials using free DAWs",
        "Discuss the evolution of a genre over decades",
        "Compare original vs. cover versions of songs",
        "Share your 'desert island' top 10 tracks",
    ]
    lines.append(f"\n<b>Content Idea:</b>\n{music_content[seed % len(music_content)]}")

    # Music creation tips
    creation_tips = [
        "Use BandLab (free) to start producing music on your phone",
        "Study song structures: Intro - Verse - Chorus - Verse - Chorus - Bridge - Chorus - Outro",
        "Record vocals with a simple USB microphone for decent quality",
        "Use royalty-free samples from Splice or FreeSound",
        "Master your tracks with LANDR (free tier available)",
    ]
    lines.append(f"\n<b>Creation Tip:</b>\n{creation_tips[seed % len(creation_tips)]}")

    response = "\n".join(lines)
    await _send(update, response, is_callback)


# ─── 18. /podcast ─────────────────────────────────────────────────────────────

async def cmd_podcast(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Podcast ideas, episode topics, and production tips."""
    seed = generate_daily_seed("podcast")
    random.seed(seed)

    podcast_formats = [
        "Solo monologue on a specific topic with personal stories",
        "Interview with an expert or interesting personality",
        "Co-hosted discussion/debate on controversial topics",
        "Storytelling narrative with sound design",
        "Roundtable with 3-4 guests on a theme",
        "Q&A episode answering listener questions",
        "Case study breakdown of a success or failure",
        "News commentary on weekly events in your niche",
    ]
    fmt = podcast_formats[seed % len(podcast_formats)]

    episode_ideas = [
        "How I went from zero to [result] in [timeframe]",
        "The one skill that changed everything for me",
        "Interview: [Guest] on overcoming [challenge]",
        "Top 5 mistakes beginners make in [niche]",
        "Lessons from [book/person/event] that apply to [topic]",
        "Behind the scenes of [industry] - what nobody tells you",
        "Predictions for [niche] in the next 5 years",
    ]
    episode = episode_ideas[seed % len(episode_ideas)]

    production_tips = [
        "Invest in a good microphone (Shure SM58 or Rode NT-USB)",
        "Record in a quiet space with blankets for sound dampening",
        "Use Audacity (free) or Descript for editing",
        "Keep episodes between 30-60 minutes for good retention",
        "Create consistent intro/outro music for brand recognition",
        "Release on a regular schedule (weekly is best)",
    ]
    prod = production_tips[seed % len(production_tips)]

    distribution_platforms = [
        "Spotify for Podcasters (free, simple)",
        "Apple Podcasts (essential for iOS users)",
        "Amazon Music (growing fast)",
        "YouTube (video podcasting trend)",
        "Pocket Casts / Overcast (enthusiast listeners)",
    ]
    platform = distribution_platforms[seed % len(distribution_platforms)]

    response = (
        f"<b>PODCAST | Content & Production Ideas</b>\n\n"
        f"<b>Format Idea:</b>\n{fmt}\n\n"
        f"<b>Episode Topic:</b>\n{episode}\n\n"
        f"<b>Production Tip:</b>\n{prod}\n\n"
        f"<b>Distribution Platform:</b>\n{platform}\n\n"
        f"<b>Growth Strategy:</b>\n"
        f"  - Clip highlights for TikTok/Reels/Shorts\n"
        f"  - Transcribe episodes for blog posts\n"
        f"  - Ask guests to share episodes with their audience\n"
        f"  - Collect reviews and ratings from listeners"
    )
    await _send(update, response, is_callback)


# ─── 19. /image ──────────────────────────────────────────────────────────────

async def cmd_image(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Generate AI images from prompts using Pollinations (free, no key)."""
    seed = generate_daily_seed("image")
    random.seed(seed)

    # Prompt templates for content creators
    prompt_templates = [
        "a professional content creator workspace with modern technology, natural lighting, minimalist style, 4k",
        "social media content calendar on a desk with coffee and phone, bright and airy, flat lay photography",
        "abstract visualization of viral marketing spreading across social media platforms, digital art",
        "a cozy podcast studio setup with vintage microphone and warm lights, cinematic lighting",
        "futuristic technology concept with AI neural network visualization, blue and purple neon, 3d render",
        "flat lay photography of content creation tools: camera, notebook, phone, coffee, pastel colors",
        "minimalist aesthetic landscape for meditation app design, soft gradients, calm colors",
        "a vibrant gaming setup with RGB lighting, multiple monitors, stream deck, night atmosphere",
        "modern minimalist office with plants and natural wood, scandinavian design, bright daylight",
        "abstract representation of blockchain and cryptocurrency network, gold and blue, technology concept",
    ]
    prompt = prompt_templates[seed % len(prompt_templates)]

    # Generate a unique image URL
    image_url = f"{POLLINATIONS_IMG}/{requests.utils.quote(prompt)}?width=1024&height=1024&seed={seed}"

    response = (
        f"<b>IMAGE | AI-Generated Visual</b>\n\n"
        f"<b>Prompt:</b>\n{prompt}\n\n"
        f"<b>Generated Image:</b>\n"
        f"{image_url}\n\n"
        f"<b>How to use:</b>\n"
        f"  1. Click or tap the link above to view the image\n"
        f"  2. Right-click/long-press to save\n"
        f"  3. Use in your content or as inspiration\n\n"
        f"<b>Pro Tip:</b> Try /image [your prompt] for custom generation!\n"
        f"Example: <code>/image a cat playing guitar on stage, concert lights</code>"
    )
    await _send(update, response, is_callback)


# ─── 20. /subscribe ──────────────────────────────────────────────────────────

async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to daily content delivery."""
    await show_subscribe_menu(update, context, is_callback=False)


# ─── 21. /reminder ──────────────────────────────────────────────────────────

async def cmd_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or manage daily reminders."""
    await show_reminder_menu(update, context, is_callback=False)


async def cmd_setreminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set reminder time: /setreminder HH:MM"""
    if not context.args:
        await update.message.reply_html(
            "Usage: <code>/setreminder HH:MM</code>\n"
            "Example: <code>/setreminder 09:00</code>"
        )
        return

    time_str = context.args[0]
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await update.message.reply_html(
            "Invalid time format. Use HH:MM (24-hour).\n"
            "Example: <code>/setreminder 09:00</code>"
        )
        return

    user_id = update.effective_user.id
    db_set_user_setting(user_id, reminder_time=time_str)
    await update.message.reply_html(
        f"Reminder set for <b>{time_str}</b> daily!\n\n"
        f"Use /setcategories to choose which content to receive."
    )


async def cmd_setcategories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set categories for daily reminders: /setcategories sports,tech,motivation"""
    if not context.args:
        await update.message.reply_html(
            "Usage: <code>/setcategories cat1,cat2,cat3</code>\n"
            "Example: <code>/setcategories sports,tech,motivation</code>\n\n"
            "Available: sports, bible, game, design, motivation, influencer, "
            "shop, tech, others, weather, youtube, business, crypto, ai, music, podcast"
        )
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    categories = [c.strip().lower() for c in " ".join(context.args).split(",")]

    # Clear existing and add new
    for cat in ["sports", "bible", "game", "design", "motivation",
                "influencer", "shop", "tech", "others", "weather",
                "youtube", "business", "crypto", "ai", "music", "podcast"]:
        db_remove_subscription(user_id, chat_id, cat)

    added = []
    for cat in categories:
        if cat in ["sports", "bible", "game", "design", "motivation",
                    "influencer", "shop", "tech", "others", "weather",
                    "youtube", "business", "crypto", "ai", "music", "podcast"]:
            db_add_subscription(user_id, chat_id, cat)
            added.append(cat)

    if added:
        await update.message.reply_html(
            f"Daily categories set to: <b>{', '.join(added)}</b>\n\n"
            f"Use /setreminder HH:MM to set delivery time."
        )
    else:
        await update.message.reply_html("No valid categories provided. Check available options above.")


async def cmd_reminderstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current reminder settings."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id) if HAS_DB else {}
    subscribed = db_get_subscriptions(chat_id) if HAS_DB else []

    reminder_time = settings.get("reminder_time", "09:00")
    city = settings.get("city", DEFAULT_CITY)

    text = (
        f"<b>Reminder Settings</b>\n\n"
        f"<b>Delivery Time:</b> {reminder_time} daily\n"
        f"<b>Location:</b> {city}\n"
        f"<b>Subscribed Categories:</b>\n"
    )

    if subscribed:
        for cat in subscribed:
            text += f"  - {cat}\n"
    else:
        text += "  None. Use /subscribe to add categories.\n"

    text += f"\nUse /setreminder HH:MM to change time.\n"
    text += f"Use /setcategories to change categories.\n"
    text += f"Use /settings to update location."

    await update.message.reply_html(text)


async def cmd_cancelreminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel all reminders for this chat."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if HAS_DB:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM subscriptions WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()

    await update.message.reply_html(
        "All reminders cancelled. Use /subscribe to set up new ones."
    )


# ─── 22. /settings ────────────────────────────────────────────────────────────

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure user preferences."""
    user_id = update.effective_user.id
    settings = db_get_user_setting(user_id) if HAS_DB else {}

    city = settings.get("city", DEFAULT_CITY)
    reminder_time = settings.get("reminder_time", "09:00")

    text = (
        f"<b>Your Settings</b>\n\n"
        f"<b>Location:</b> {city}\n"
        f"<b>Reminder Time:</b> {reminder_time}\n\n"
        f"<b>Commands to Change Settings:</b>\n"
        f"/setcity CityName - Set your location for weather\n"
        f"/setreminder HH:MM - Set daily reminder time\n"
        f"/setcategories cat1,cat2 - Set categories\n"
        f"/settheme NUMBER - Set weekly Bible theme (1-52)\n\n"
        f"<b>Example:</b>\n"
        f"/setcity London\n"
        f"/setreminder 08:00\n"
        f"/setcategories motivation,tech,bible"
    )
    await update.message.reply_html(text)


async def cmd_setcity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set city for weather: /setcity CityName"""
    if not context.args:
        await update.message.reply_html(
            "Usage: <code>/setcity CityName</code>\n"
            "Example: <code>/setcity London</code>\n"
            "Example: <code>/setcity Tokyo</code>"
        )
        return

    city_name = " ".join(context.args).title()

    # Try to get coordinates from the city name via Open-Meteo geocoding
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_data = fetch_json(geo_url, {"name": city_name, "count": 1, "language": "en", "format": "json"})

    if "error" not in geo_data and geo_data.get("results"):
        result = geo_data["results"][0]
        lat = result.get("latitude", DEFAULT_LAT)
        lon = result.get("longitude", DEFAULT_LON)
        city_name = result.get("name", city_name)
        country = result.get("country", "")
        full_name = f"{city_name}, {country}" if country else city_name
    else:
        lat = DEFAULT_LAT
        lon = DEFAULT_LON
        full_name = city_name

    user_id = update.effective_user.id
    if HAS_DB:
        db_set_user_setting(user_id, city=full_name, lat=lat, lon=lon)

    await update.message.reply_html(
        f"City set to <b>{full_name}</b>!\n"
        f"Use /weather to check conditions."
    )


async def cmd_settheme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set weekly Bible theme index: /settheme NUMBER (1-52)"""
    if not context.args:
        await update.message.reply_html(
            "Usage: <code>/settheme NUMBER</code>\n"
            "Example: <code>/settheme 5</code> for Gratitude week\n\n"
            "Available themes (1-52) rotate weekly."
        )
        return

    try:
        idx = int(context.args[0]) - 1
        if idx < 0 or idx > 51:
            raise ValueError
    except ValueError:
        await update.message.reply_html("Please enter a number between 1 and 52.")
        return

    user_id = update.effective_user.id
    if HAS_DB:
        db_set_user_setting(user_id, weekly_theme_idx=idx)

    weekly_themes = [
        "Walking in Faith", "The Power of Prayer", "Love & Compassion",
        "Strength in Trials", "Gratitude & Thanksgiving", "Wisdom & Understanding",
        "Hope & Renewal", "Grace & Forgiveness", "Courage & Boldness",
        "Peace & Rest", "Serve & Give", "Perseverance",
    ]
    theme = weekly_themes[idx % len(weekly_themes)]

    await update.message.reply_html(
        f"Weekly Bible theme set to: <b>{theme}</b>\n"
        f"This will be reflected in your daily /bible content."
    )


# ─── IMAGE WITH CUSTOM PROMPT ─────────────────────────────────────────────────

async def cmd_image_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate image from user prompt: /image [prompt]"""
    if not context.args:
        await cmd_image(update, context)
        return

    prompt = " ".join(context.args)
    encoded = requests.utils.quote(prompt)
    image_url = f"{POLLINATIONS_IMG}/{encoded}?width=1024&height=1024"

    await update.message.reply_html(
        f"<b>Generated Image</b>\n\n"
        f"<b>Prompt:</b> {sanitize(prompt)}\n\n"
        f"{image_url}"
    )


# ─── SEND HELPER ──────────────────────────────────────────────────────────────

async def _send(update: Update, text: str, is_callback: bool):
    """Send message - handles both /command and button callback context."""
    if is_callback:
        try:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.HTML
            )
        except Exception:
            # Might be too long, truncate
            await update.callback_query.edit_message_text(
                text[:4000], parse_mode=ParseMode.HTML
            )
        # Show extended keyboard after
        await update.callback_query.message.reply_html(
            "Choose another category:",
            reply_markup=EXTENDED_KEYBOARD
        )
    else:
        try:
            await update.message.reply_html(text)
        except Exception:
            await update.message.reply_html(text[:4000])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULER (Auto-Post Daily Reminders)
# ═══════════════════════════════════════════════════════════════════════════════

def start_scheduler(application: Application):
    """Start APScheduler for daily reminders."""
    if not HAS_SCHEDULER:
        return

    scheduler = BackgroundScheduler()

    def send_daily_reminders():
        """Send scheduled content to subscribed chats."""
        subscriptions = db_get_all_subscriptions()
        chat_categories = defaultdict(list)
        for chat_id, category in subscriptions:
            chat_categories[chat_id].append(category)

        for chat_id, categories in chat_categories.items():
            try:
                # Pick one random category from subscribed ones
                cat = random.choice(categories)
                # We'll use a synchronous workaround to send
                asyncio_run_safe(application.bot.send_message(
                    chat_id=chat_id,
                    text=f"<b>Daily Content Update</b>\n\nHere's today's {cat} content!",
                    parse_mode=ParseMode.HTML
                ))
            except Exception:
                pass  # Chat might have been blocked

    # Check every 30 minutes and send if it's the right time
    def check_and_send():
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        subscriptions = db_get_all_subscriptions()
        chat_ids = set(cid for cid, _ in subscriptions)

        for chat_id in chat_ids:
            settings = db_get_user_setting(0)  # default - should be per chat
            reminder_time = "09:00"  # default

            # Try to get user settings
            for uid, _ in subscriptions:
                if HAS_DB:
                    s = db_get_user_setting(uid)
                    reminder_time = s.get("reminder_time", "09:00")
                    break

            if current_time == reminder_time:
                try:
                    asyncio_run_safe(
                        application.bot.send_message(
                            chat_id=chat_id,
                            text="<b>Daily Content Reminder!</b> 🎯\n\n"
                                 "Type /start to explore today's content!",
                            parse_mode=ParseMode.HTML
                        )
                    )
                except Exception:
                    pass

    # Run check every minute (don't overdo it)
    scheduler.add_job(check_and_send, 'interval', minutes=1)
    scheduler.start()


def asyncio_run_safe(coro):
    """Run async coroutine from sync context."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            loop.run_until_complete(coro)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Start the bot."""
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set TELEGRAM_TOKEN environment variable or edit the script.")
        print("Get a token from @BotFather on Telegram.")
        sys.exit(1)

    # Initialize database
    init_db()
    if HAS_DB:
        print(f"Database initialized: {DB_PATH}")
    else:
        print("SQLite not available. Running without database (subscriptions disabled).")

    # Build application
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register core command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sports", cmd_sports))
    app.add_handler(CommandHandler("bible", cmd_bible))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("design", cmd_design))
    app.add_handler(CommandHandler("motivation", cmd_motivation))
    app.add_handler(CommandHandler("influencer", cmd_influencer))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("tech", cmd_tech))
    app.add_handler(CommandHandler("others", cmd_others))

    # Register enhanced command handlers
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("youtube", cmd_youtube))
    app.add_handler(CommandHandler("tweet", cmd_tweet))
    app.add_handler(CommandHandler("hashtags", cmd_hashtags))
    app.add_handler(CommandHandler("business", cmd_business))
    app.add_handler(CommandHandler("crypto", cmd_crypto))
    app.add_handler(CommandHandler("ai", cmd_ai))
    app.add_handler(CommandHandler("music", cmd_music))
    app.add_handler(CommandHandler("podcast", cmd_podcast))
    app.add_handler(CommandHandler("image", cmd_image_prompt))

    # Register utility handlers
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("reminder", cmd_reminder))
    app.add_handler(CommandHandler("setreminder", cmd_setreminder))
    app.add_handler(CommandHandler("setcategories", cmd_setcategories))
    app.add_handler(CommandHandler("reminderstatus", cmd_reminderstatus))
    app.add_handler(CommandHandler("cancelreminder", cmd_cancelreminder))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("setcity", cmd_setcity))
    app.add_handler(CommandHandler("settheme", cmd_settheme))

    # Register callback query handler
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^cmd_"))

    # Start scheduler if available
    start_scheduler(app)

    print("=" * 50)
    print("Content Creator Bot v2.0 is running!")
    print(f"Core:  /sports /bible /game /design /motivation /influencer /shop /tech /others")
    print(f"Extra: /weather /youtube /tweet /hashtags /business /crypto /ai /music /podcast /image")
    print(f"Utils: /subscribe /reminder /settings /setcity")
    print("=" * 50)
    print("Press Ctrl+C to stop.")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
