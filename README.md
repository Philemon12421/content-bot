# 🚀 ContentPro Bot

An all-in-one Telegram content bot: 35+ generators (motivation, crypto, sports,
weather, hashtags, recipes, etc.), **live football scores**, **trending news
with pictures**, a **QR/translate/currency/poll toolkit**, and an **automated
channel-posting engine** that keeps your Telegram channel fed with fresh,
niche-targeted trending content every hour (or every 15 minutes — you choose).

Built to be deployed in minutes and resold/white-labeled as your own product.

---

## ✨ What's inside

| Category | Commands |
|---|---|
| Core content | `/sports` `/bible` `/game` `/design` `/motivation` `/influencer` `/shop` `/tech` `/others` |
| Enhanced content | `/weather` `/youtube` `/tweet` `/hashtags` `/business` `/crypto` `/ai` `/music` `/podcast` `/news` `/joke` `/fact` |
| Premium | `/roast` `/story` `/recipe` `/fitness` `/travel` `/mindset` `/horoscope` `/dictionary` `/quiz` `/country` `/challenge` `/image` `/meme` |
| **New tools** | `/football` (live scores, asks which league) · `/trending` (news + photos, asks category) · `/qr` · `/translate` · `/currency` · `/poll` · `/namecard` |
| **Automation** | `/autopost` — connect your channel and auto-post trending news for a niche every 15 min / 30 min / 1h / 3h / 6h / 12h / 24h. `/autoposts` — pause, resume, or remove channels. |
| Utilities | `/subscribe` `/reminder` `/setcity` `/settings` `/stats` `/links` `/start` `/help` |

### Conversational flows
The bot now **asks follow-up questions** instead of guessing:
- Tap **Weather** → it asks which region, then which city.
- Tap **Hashtags** → it asks your platform, then your niche.
- Tap **Football** → it asks which league.
- Tap **Trending** → it asks which category.
- `/autopost` walks you through connecting a channel → picking a niche → picking a posting frequency.

After a flow finishes, the bot does **not** re-show the whole menu — it only
gives you a small "🏠 Menu" button, so results stay clean and the next menu
only appears if you actually ask for it.

### Auto-post to your channel (grow views on autopilot)
1. Add the bot as an **admin** of your Telegram channel (with "Post Messages" permission).
2. Run `/autopost` in a private chat with the bot.
3. Forward any message from your channel (or type its `@username`).
4. Pick a niche: general, technology, business, entertainment, health, science, or sports.
5. Pick a posting frequency.
6. Done — the bot checks every minute in the background and posts trending
   headlines (with a picture, when one is available) to your channel exactly
   on schedule. Manage your channels any time with `/autoposts`.

This works independently for every user — each person who talks to the bot
can connect their own channel(s), pick their own niche, and set their own
schedule; nobody's setup affects anyone else's.

---

## 🛠 Local setup

```bash
git clone <your-repo-url>
cd contentpro-bot
cp .env.example .env       # then fill in TELEGRAM_TOKEN
pip install -r requirements.txt
python bot.py
```

Get `TELEGRAM_TOKEN` from [@BotFather](https://t.me/BotFather) on Telegram.

---

## ☁️ Deploy to Render (recommended, free tier works)

**Option A — One-click via Blueprint**
1. Push this repo to GitHub.
2. In Render, choose **New → Blueprint**, point it at your repo (it will read `render.yaml`).
3. Set the `TELEGRAM_TOKEN` environment variable when prompted (it's marked `sync: false` so Render will ask for it — never commit your real token).
4. Deploy. Render will run `pip install -r requirements.txt` then `python bot.py`.

**Option B — Manual Web Service**
1. New → Web Service → connect your repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `python bot.py`
4. Add environment variable `TELEGRAM_TOKEN` (and optionally `WEBSITE_URL`, `CREATOR_USERNAME`, `BOOKING_URL` to rebrand — see below).
5. Deploy.

> **Why "Web Service" and not "Background Worker"?** Render's free tier only
> supports Web Services, which require binding to `$PORT`. The bot itself
> talks to Telegram via long-polling (no inbound webhook needed), so `bot.py`
> starts a tiny built-in health-check HTTP server on `$PORT` just to satisfy
> Render — you don't need to configure anything for this, it's automatic.
> Free Render services sleep after inactivity; ping the service URL with
> [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org)
> every 5–10 minutes if you need it always-on on the free tier, or upgrade to
> a paid instance.

**Other platforms:** Railway, Fly.io, and a plain VPS all work the same way —
install `requirements.txt` and run `python bot.py` with `TELEGRAM_TOKEN` set.
A `Procfile` is included for Heroku-style platforms too.

---

## 🎨 White-labeling / reselling this bot

Every bit of branding is an environment variable, so you can resell this same
codebase to multiple clients without touching the code:

| Variable | What it controls |
|---|---|
| `TELEGRAM_TOKEN` | Which bot account it runs as (each client needs their own bot from @BotFather) |
| `WEBSITE_URL` | The "🌐 Website" link shown in `/links`, `/start`, and every response footer |
| `CREATOR_USERNAME` | The Telegram handle shown as "💬 Chat with the creator" |
| `BOOKING_URL` | The "🗓 Book a site/service" link |
| `DB_PATH` | Where the SQLite database lives (give each client their own file/deploy) |

To sell to a new client: spin up a new Render service from the same repo,
give them a fresh `TELEGRAM_TOKEN`, and set their own `WEBSITE_URL` /
`CREATOR_USERNAME` / `BOOKING_URL` — that's the whole process.

---

## 📦 Data

`bot_data.db` is a SQLite database storing user settings, subscriptions,
command stats, and auto-post configuration. It's created automatically on
first run if it doesn't exist. Back it up periodically if you care about
retaining user preferences (a `bot_data_backup.db` pattern is included as an
example).

---

## 🔑 Notes on API keys

Everything works out of the box using free, keyless public endpoints
(Open-Meteo for weather, CoinGecko for crypto, ESPN for sports/football, a
NewsAPI mirror for news/trending, MyMemory for translation, Frankfurter for
currency, etc). `COINGECKO_API_KEY` and `NEWSAPI_KEY` are optional — add them
only if you hit rate limits and have paid keys for those services.
