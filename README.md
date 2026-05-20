# Content Creator Bot v2.0

A premium **Telegram bot** that generates **unique, daily content** across **17+ categories** using completely **free APIs**. Built for content creators, social media managers, bloggers, podcasters, YouTubers, and anyone who needs fresh content ideas daily.

## Features Overview

### Core Features (9 commands)

| Command | Description |
|---------|-------------|
| `/sports` | Live scores, standings & trending headlines (ESPN, no API key) |
| `/bible` | Daily Bible verse + explanation + prayer (unique each day, weekly theme) |
| `/game` | Trending free-to-play games, hashtags, content ideas & thumbnail tips |
| `/design` | Design tips, daily challenges, tool spotlights & trending styles |
| `/motivation` | Unique daily quotes, affirmations, action steps & weekly focus |
| `/influencer` | Platform insights, content strategies, monetization tips & trending niches |
| `/shop` | Trending products, shopping trends, product review content ideas |
| `/tech` | Latest tech headlines, content angles, and quick security/privacy tips |
| `/others` | Viral format ideas, cross-niche mashups, engagement hooks & strategies |

### Enhanced Features (8 more commands)

| Command | Description |
|---------|-------------|
| `/weather` | Local weather conditions with content creation tips for outdoor shoots |
| `/youtube` | Trending video ideas, SEO tips, thumbnail strategies & channel growth |
| `/tweet` | Viral tweet thread generator with hooks, structure & posting times |
| `/hashtags` | Optimized hashtag sets for Instagram, TikTok, Twitter, LinkedIn & YouTube |
| `/business` | Business news, entrepreneurship tips, book recommendations & KPIs |
| `/crypto` | Live cryptocurrency prices (CoinGecko), market data & content ideas |
| `/ai` | Latest AI tools, models, trends & prompt engineering tips |
| `/music` | Trending tracks, genres, music content ideas & production tips |
| `/podcast` | Podcast format ideas, episode topics, production tips & distribution |
| `/image` | AI-generated images from text prompts (Pollinations, free, no key) |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/subscribe` | Subscribe to daily content auto-delivery |
| `/reminder` | Set up daily reminders for content inspiration |
| `/setreminder HH:MM` | Set specific delivery time (e.g., `/setreminder 09:00`) |
| `/setcategories cat1,cat2` | Choose which categories to receive daily |
| `/setcity CityName` | Set your location for weather content |
| `/settheme NUMBER` | Choose weekly Bible theme (1-52) |
| `/settings` | View and manage all your preferences |
| `/reminderstatus` | Check current reminder settings |
| `/cancelreminder` | Stop all daily reminders |

### Why This Bot?

- **Zero API keys needed** for most features — uses free, open endpoints
- **Unique content daily** — deterministic seeding ensures fresh content every day
- **Interactive buttons** — easy navigation between all categories
- **Subscription system** — auto-deliver content at your preferred time
- **Multi-language ready** — can be extended for different languages
- **Zero cost to operate** — designed for free hosting platforms

---

## How It Works

Each command fetches real-time or curated data from free public APIs:

| Feature | API Endpoint | Auth Required |
|---------|-------------|---------------|
| Sports | [ESPN Hidden API](https://github.com/pseudo-r/Public-ESPN-API) | None |
| Bible | [bible-api.com](https://bible-api.com) | None |
| Game | [FreeToGame API](https://www.freetogame.com/api-doc) | None |
| Design | [DummyJSON Quotes](https://dummyjson.com/docs/quotes) | None |
| Motivation | [Quotes API](https://github.com/theriturajps/Quotes-API) + [Real Inspire](https://api.realinspire.live) | None |
| Shop | [FakeStoreAPI](https://fakestoreapi.com) | None |
| Tech | [NewsAPI Mirror](https://github.com/SauravKanchan/NewsAPI) | None |
| Weather | [Open-Meteo](https://open-meteo.com) | None |
| Crypto | [CoinGecko API](https://www.coingecko.com/en/api) | Optional key |
| AI Image | [Pollinations AI](https://pollinations.ai) | None |
| Music | [TheAudioDB](https://www.theaudiodb.com) | None |

The bot generates **unique content daily** using a **date-based seed**, so `/bible`, `/motivation`, `/design`, and many others produce different results every single day.

---

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- pip (Python package manager)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/content-creator-bot.git
cd content-creator-bot

# Install dependencies
pip install -r requirements.txt


3. Configuration
Set your Telegram bot token as an environment variable:

bash



# Linux/macOS
export TELEGRAM_TOKEN="your_bot_token_here"

# Windows (Command Prompt)
set TELEGRAM_TOKEN=your_bot_token_here

# Windows (PowerShell)
$env:TELEGRAM_TOKEN="your_bot_token_here"

Optional environment variables:

bash



export COINGECKO_API_KEY="your_coingecko_key"  # For higher rate limits
export DB_PATH="/data/bot_data.db"              # Custom DB path
4. Run the Bot
bash



python bot.py
The bot will start polling and respond to commands on Telegram.

5. Test It
Open Telegram, find your bot, and send:

/start — Welcome message with buttons
/sports — Live sports scores
/bible — Today's devotional
/motivation — Daily inspiration
Free Hosting Options
Option 1: Render (Recommended — easiest)
Push code to GitHub repository
Go to render.com → Sign up with GitHub
Click New + → Web Service
Connect your repository
Configure:
Name: content-creator-bot
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: python bot.py
Add Environment Variable:
TELEGRAM_TOKEN = your bot token
Select Free plan
Click Create Web Service
Keep Render awake: Free tier sleeps after inactivity. Use UptimeRobot (free) to ping your bot URL every 14 minutes.

Option 2: Railway (Free $5 credit, no sleep)
Push to GitHub
Go to railway.app → New Project
Deploy from GitHub repo
Add environment variable: TELEGRAM_TOKEN
Auto-detects Python — no extra config
Deploy
Option 3: Koyeb (Always-on free tier)
Push to GitHub
Go to koyeb.com → Create App
Connect GitHub repo
Build Command: pip install -r requirements.txt
Run Command: python bot.py
Add TELEGRAM_TOKEN environment variable
Deploy
Option 4: PythonAnywhere (Free tier — best for testing)
Upload files via web interface or clone from GitHub
Open a bash console:
bash



pip install --user python-telegram-bot requests apscheduler
Run: python bot.py
Use a screen session to keep it running:
bash



screen -S bot
python bot.py
# Ctrl+A, D to detach
Option 5: Replit (Easiest for quick testing)
Create a new Python Repl
Paste code and requirements.txt
Add TELEGRAM_TOKEN as a Secret
Run button ▶️
Use UptimeRobot to ping the Repl URL every 5 minutes
Keeping Free Hosting Alive
Most free hosts put apps to sleep. Add a simple health endpoint using Flask:

python



# Add to bot.py before main()
from flask import Flask
import threading

health_app = Flask(__name__)

@health_app.route('/')
def health():
    return "Bot is running!"

def run_health():
    health_app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_health, daemon=True).start()
Then use UptimeRobot (free tier) to ping https://your-app-url.com/ every 10-15 minutes.

Customization Guide
Adding a New Feature
python



# 1. Add the handler function
async def cmd_newfeature(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    content = "<b>NEW FEATURE</b>\nYour content here"
    await _send(update, content, is_callback)

# 2. Register it
app.add_handler(CommandHandler("newfeature", cmd_newfeature))

# 3. Add to button handler dict
handlers["newfeature"] = cmd_newfeature

# 4. Add to keyboard
NEW_BUTTON = InlineKeyboardButton("New Feature", callback_data="cmd_newfeature")
Changing Weekly Bible Themes
Edit the weekly_themes list in cmd_bible():

python



weekly_themes = ["Your Theme 1", "Your Theme 2", ...]
Customizing Hashtag Pools
Edit the hashtag_pools dict in cmd_hashtags() to match your niche.

Changing Weather Default Location
Edit the defaults at the top of bot.py:

python



DEFAULT_LAT = 40.7128   # New York
DEFAULT_LON = -74.0060
DEFAULT_CITY = "New York"
Database
The bot uses SQLite (built into Python) for:

User subscriptions (daily delivery)
User settings (city, reminder time, theme)
Seen content tracking (avoids duplicates)
Database file: bot_data.db (in the bot directory, or DB_PATH env var)

No external database server needed — SQLite is file-based and perfect for small bots.

API Keys (Optional)
Most features work without any API keys. For enhanced features:



Service	Why Get It	How
CoinGecko	Higher rate limits (30 calls/min vs 10)	CoinGecko Dashboard
NewsAPI	More news sources (500 req/day free)	newsapi.org
Set them as environment variables:

bash



export COINGECKO_API_KEY="your_key"
export NEWSAPI_KEY="your_key"
Troubleshooting


Problem	Solution
Bot doesn't respond	Ensure TELEGRAM_TOKEN is set correctly
"No live games" for sports	ESPN works during active seasons only
Content seems similar	Date-based seed ensures daily uniqueness
Free host sleeps	Set up UptimeRobot to ping every 14 min
Rate limited by APIs	Most allow 100-1000 req/day free
/image not showing	Open the URL directly in browser
Weather wrong location	Use /setcity YourCityName
Complete Command List



Core Content:
  /sports       - Live sports scores & trending news
  /bible        - Daily Bible verse + explanation + prayer
  /game         - Trending games, hashtags & content ideas
  /design       - Design tips, challenges & inspiration
  /motivation   - Daily quotes, affirmations & action steps
  /influencer   - Platform strategies & monetization
  /shop         - Trending products & e-commerce insights
  /tech         - Latest tech news & innovations
  /others       - Viral content ideas & cross-niche mashups

Enhanced Content:
  /weather      - Local weather for content creators
  /youtube       - YouTube growth tips & video ideas
  /tweet         - Viral tweet thread generator
  /hashtags      - Optimized hashtag sets
  /business      - Business news & entrepreneurship
  /crypto        - Cryptocurrency prices & market data
  /ai            - AI tools, trends & prompt tips
  /music         - Music trends & content ideas
  /podcast       - Podcast ideas & production tips
  /image <prompt> - AI image generation

Utilities:
  /subscribe         - Subscribe to daily content
  /reminder          - Set up daily reminders
  /setreminder HH:MM - Set delivery time
  /setcategories     - Choose daily categories
  /settings          - View your preferences
  /setcity CityName  - Set your location
  /settheme NUMBER   - Set Bible theme
  /reminderstatus    - Check settings
  /cancelreminder    - Stop reminders

Architecture



bot.py
├── Configuration (APIs, tokens, defaults)
├── Database Layer (SQLite)
│   ├── Subscriptions
│   ├── User Settings
│   └── Seen Content
├── Helper Functions
│   ├── generate_daily_seed()
│   ├── fetch_json()
│   └── sanitize()
├── Command Handlers (19 total)
│   ├── Core: sports, bible, game, design, motivation, influencer, shop, tech, others
│   ├── Enhanced: weather, youtube, tweet, hashtags, business, crypto, ai, music, podcast
│   ├── Image: image (AI generation)
│   └── Utilities: subscribe, reminder, settings, setcity, settheme
├── Callback Handler (button routing)
├── Scheduler (auto-post reminders)
└── Main Entry Point
License
MIT — Use freely, modify, share. No attribution required but appreciated.

Support
Issues: Open a GitHub issue
Feature Requests: Suggest via issues or pull requests
Documentation: Check this README for all commands and setup
Version History


Version	Date	Changes
1.0.0	Initial	9 core commands with free APIs
2.0.0	Current	+8 enhanced features, subscriptions, scheduler, DB, settings, AI images
Built for content creators who need fresh ideas every day.





---

That's the complete package. Here's a summary of everything included:

**The bot now has 19 commands across 4 groups:**

**Core (9):** `/sports` `/bible` `/game` `/design` `/motivation` `/influencer` `/shop` `/tech` `/others`

**Enhanced (10):** `/weather` `/youtube` `/tweet` `/hashtags` `/business` `/crypto` `/ai` `/music` `/podcast` `/image`

**Utilities (8):** `/subscribe` `/reminder` `/setreminder` `/setcategories` `/settings` `/setcity` `/settheme` `/reminderstatus` `/cancelreminder`

**Key features added:**
- **Database** (SQLite) for persistent subscriptions and user settings
- **Scheduler** (APScheduler) for auto-posting daily content
- **AI Image Generation** via Pollinations (free, no key)
- **Weather** via Open-Meteo (free, no key)
- **Cryptocurrency** via CoinGecko
- **Music** via TheAudioDB
- **YouTube/Podcast/Business/Tweet/Hashtags** content generators
- **Customizable settings** per user (location, themes, timezone)
- **Full interactive keyboards** for easy navigation
- **Complete README** covering all commands, hosting, customization, and troubleshooting_
# content-bot
