<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6366F1,100:22D3EE&height=220&section=header&text=ContentPro%20Bot&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Your%20Telegram%20content%20%26%20growth%20engine&descAlignY=55&descSize=20" width="100%"/>

<a href="https://t.me/philemon4u">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=2500&pause=800&color=22D3EE&center=true&vCenter=true&multiline=true&width=700&height=90&lines=35%2B+content+generators+in+one+bot;Live+football+scores+%E2%9A%BD+%2B+trending+news+%F0%9F%94%A5;Auto-posts+to+YOUR+channel+every+hour;Deploy+in+minutes+%E2%80%94+resell+as+your+own+product" alt="Typing SVG" />
</a>

<br/>

<img src="https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/python--telegram--bot-21.6-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" />
<img src="https://img.shields.io/badge/deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" />
<img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" />
<img src="https://img.shields.io/badge/status-active-brightgreen?style=for-the-badge" />

<br/><br/>

<a href="https://render.com/deploy">
  <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="40"/>
</a>
&nbsp;
<a href="https://bookmei.vercel.app/">
  <img src="https://img.shields.io/badge/📅_Book_a_site%2Fservice-6366F1?style=for-the-badge" height="40"/>
</a>
&nbsp;
<a href="https://t.me/philemon4u">
  <img src="https://img.shields.io/badge/💬_Chat_with_creator-26A5E4?style=for-the-badge" height="40"/>
</a>

</div>

<br/>

> Replace the Render deploy link above with `https://render.com/deploy?repo=<your-github-repo-url>` once this is pushed to GitHub, so the button deploys **your** copy directly.

---

## 📖 Table of Contents

- [✨ What's Inside](#-whats-inside)
- [💬 Conversational Flows](#-conversational-flows)
- [🤖 Auto-Post to Your Channel](#-auto-post-to-your-channel-grow-views-on-autopilot)
- [🛠 Local Setup](#-local-setup)
- [☁️ Deploy to Render](#️-deploy-to-render-recommended-free-tier-works)
- [🎨 White-Labeling / Reselling](#-white-labeling--reselling-this-bot)
- [📦 Data](#-data)
- [🔑 API Keys](#-notes-on-api-keys)

---

## ✨ What's Inside

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:1e1b4b,100:0f172a&height=3&section=header" width="100%"/>

| Category | Commands |
|---|---|
| 🧩 Core content | `/sports` `/bible` `/game` `/design` `/motivation` `/influencer` `/shop` `/tech` `/others` |
| ⚡ Enhanced content | `/weather` `/youtube` `/tweet` `/hashtags` `/business` `/crypto` `/ai` `/music` `/podcast` `/news` `/joke` `/fact` |
| 💎 Premium | `/roast` `/story` `/recipe` `/fitness` `/travel` `/mindset` `/horoscope` `/dictionary` `/quiz` `/country` `/challenge` `/image` `/meme` |
| 🆕 New tools | `/football` · `/trending` · `/qr` · `/translate` · `/currency` · `/poll` · `/namecard` |
| 🤖 Automation | `/autopost` · `/autoposts` |
| ⚙️ Utilities | `/subscribe` `/reminder` `/setcity` `/settings` `/stats` `/links` `/start` `/help` |

<br/>

<div align="center">
<img src="https://raw.githubusercontent.com/Anmol-Baranwal/Cool-GIFs-For-Github/main/pinkflag.gif" width="35%" alt="animated divider"/>
</div>

## 💬 Conversational Flows

The bot **asks follow-up questions** instead of guessing what you want:

```
🌤  Tap "Weather"      → "Which region?"      → "Which city?"           → forecast
#️⃣  Tap "Hashtags"     → "Which platform?"    → "What's your niche?"    → hashtag sets
⚽  Tap "Football"     → "Which league?"                                → live scores
🔥  Tap "Trending"     → "Which category?"                              → news + photo
```

After any flow finishes, the bot **does not** re-show the whole menu — only a
small **🏠 Menu** button appears, so results stay clean and the full category
list only pops up when you actually ask for it.

---

## 🤖 Auto-Post to Your Channel (grow views on autopilot)

<div align="center">

```mermaid
sequenceDiagram
    participant You
    participant Bot
    participant Channel as Your Channel
    You->>Bot: /autopost
    Bot->>You: Forward a message or send @channel
    You->>Bot: @mychannel
    Bot->>Channel: Verify admin status
    Bot->>You: ✅ Connected — pick a niche
    You->>Bot: Technology
    Bot->>You: Pick a frequency
    You->>Bot: Every hour
    loop Every minute (background)
        Bot->>Bot: Check due channels
        Bot->>Channel: 🔥 Post trending headline + photo
    end
```

</div>

1. Add the bot as an **admin** of your Telegram channel (with "Post Messages" permission).
2. Run `/autopost` in a private chat with the bot.
3. Forward any message from your channel (or type its `@username`).
4. Pick a niche: general, technology, business, entertainment, health, science, or sports.
5. Pick a posting frequency: 15 min, 30 min, 1h, 3h, 6h, 12h, or daily.
6. Done — a background job checks every minute and posts trending headlines
   (with a picture, when available) to your channel exactly on schedule.
   Manage everything with `/autoposts` (pause / resume / remove).

This runs **independently per user** — everyone who talks to the bot can
connect their own channel(s), niche, and schedule without affecting anyone
else's setup.

---

## 🛠 Local Setup

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
2. In Render, choose **New → Blueprint**, point it at your repo (it reads `render.yaml`).
3. Set the `TELEGRAM_TOKEN` environment variable when prompted (kept out of git on purpose).
4. Deploy — Render runs `pip install -r requirements.txt` then `python bot.py`.

**Option B — Manual Web Service**
1. New → Web Service → connect your repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `python bot.py`
4. Add `TELEGRAM_TOKEN` (and optionally `WEBSITE_URL`, `CREATOR_USERNAME`, `BOOKING_URL` to rebrand).
5. Deploy.

> **Why "Web Service" and not "Background Worker"?** Render's free tier only
> supports Web Services, which require binding to `$PORT`. The bot talks to
> Telegram via long-polling (no inbound webhook needed), so `bot.py` starts a
> tiny built-in health-check HTTP server on `$PORT` automatically — nothing to
> configure. Free services sleep after inactivity; ping the service URL with
> [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org)
> every 5–10 minutes to keep it awake, or upgrade to a paid instance.

> **Python version:** pinned to `3.12.7` via `runtime.txt` / `PYTHON_VERSION`
> — this avoids a crash on Python 3.14 where `python-telegram-bot` 21.6 and
> APScheduler rely on event-loop behavior that 3.14 removed. If you ever bump
> dependencies, keep an eye on this.

Railway, Fly.io, and a plain VPS work the same way — install
`requirements.txt` and run `python bot.py` with `TELEGRAM_TOKEN` set. A
`Procfile` is included for Heroku-style platforms too.

---

## 🎨 White-Labeling / Reselling This Bot

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
retaining user preferences (`bot_data_backup.db` is included as an example).

---

## 🔑 Notes on API Keys

Everything works out of the box using free, keyless public endpoints
(Open-Meteo for weather, CoinGecko for crypto, ESPN for sports/football, a
NewsAPI mirror for news/trending, MyMemory for translation, Frankfurter for
currency, etc). `COINGECKO_API_KEY` and `NEWSAPI_KEY` are optional — add them
only if you hit rate limits and have paid keys for those services.

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:22D3EE,100:6366F1&height=150&section=footer"/>

Made with ❤️ by **Drenchack** · [Website](https://dtc-official.vercel.app) · [Contact](https://t.me/philemon4u) · [Book a service](https://bookmei.vercel.app/)

</div>
