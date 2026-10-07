# Universal Media Downloader Bot

A production-ready, highly resilient Telegram bot for downloading media from YouTube, Instagram, X/Twitter, Reddit, and more. Optimized for Render's 512MB RAM free tier.

## Features

- **Multi-platform support**: YouTube, Instagram, X/Twitter, Reddit, Facebook
- **Memory efficient**: Optimized for Render's 512MB RAM limit
- **Auto cleanup**: Ephemeral file management with `atexit` handlers
- **Sleep prevention**: Built-in heartbeat to keep Render container alive
- **Docker ready**: Complete Docker Compose setup
- **Health monitoring**: Built-in health check endpoint

## Quick Start (Local)

```bash
# Clone and setup
git clone <your-repo>
cd Universal-Media-Downloader-Telegram-Bot

# Copy and edit config
cp .env.example .env
# Edit .env with your BOT_TOKEN and settings

# Install dependencies
pip install -r requirements.txt

# Run with Docker Compose (includes Redis)
docker-compose up -d

# Or run directly
python -m bot.main
```

## Deploy to Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/Universal-Media-Downloader-Telegram-Bot.git
git push -u origin main
```

### 2. Create Render Services

#### Option A — Blueprint (recommended)
Push this repo (it contains `.render.yaml`), then in Render: **New → Blueprint** → pick the repo.
The blueprint creates the worker. Then add the secrets (next step).

#### Option B — Manual
Go to [Render Dashboard](https://dashboard.render.com):

##### A. Redis Database (Free)
1. Click **New** → **Redis**
2. Name: `ubd-redis`
3. Plan: **Free** (25MB)
4. Region: Choose closest
5. Copy the **Internal Redis URL** (format: `redis://...:6379`)

##### B. Worker Service
1. Click **New** → **Background Worker**
2. Connect your GitHub repository
3. Settings:
   - **Name**: `universal-media-downloader`
   - **Environment**: `Docker`
   - **Plan**: **Free** (512MB RAM)
   - **Branch**: `main`
   - **Dockerfile Path**: `./Dockerfile`
4. **Environment Variables** (Dashboard → Environment tab):
   ```
   BOT_TOKEN=<your token from @BotFather — never commit it>
   REDIS_URL=<your-internal-redis-url-from-step-A>
   RENDER=true
   MAX_FILE_SIZE_MB=49
   KEEP_ALIVE_ENABLED=true
   KEEP_ALIVE_INTERVAL=300
   LOG_LEVEL=INFO
   ```
   Set `BOT_TOKEN` as a **Secret** so it is never displayed in logs.
5. Click **Create Worker**

> `MAX_FILE_SIZE_MB=49` — the standard Telegram Bot API rejects uploads over 50MB.
> Raise it only if you run a local Bot API server.

### 3. Important Notes

- **BOT_TOKEN**: Never commit to Git! Set it in Render's Environment Variables
- **Redis**: Use the **Internal URL** from your Render Redis instance (free tier allows 25MB)
- **Sleep Prevention**: The bot runs a heartbeat every 5 minutes to prevent Render from sleeping the free tier
- **File Storage**: Files are stored in `/tmp` which is ephemeral on Render (cleared on restart)
- **Concurrency**: Limited to 1 concurrent download to stay within 512MB RAM

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot Token from @BotFather | **Required** |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | `512` |
| `VIDEO_QUALITY` | Video quality (1080p, 720p, 480p, 360p, audio_only) | `720p` |
| `KEEP_ALIVE_ENABLED` | Enable heartbeat to prevent sleep | `true` |
| `KEEP_ALIVE_INTERVAL` | Heartbeat interval in seconds | `300` |
| `COOKIES_DIR` | Path to yt-dlp cookies | `~/.yt-dlp/cookies` |
| `RENDER` | Set to "true" on Render | `false` |

## Bot Commands

- `/start` - Show help message
- `/help` - Show help message
- `/download <URL>` - Download media from URL
- Send any supported URL directly to the bot

## Supported Platforms

| Platform | Formats |
|----------|---------|
| YouTube | Videos, Shorts, Playlists |
| Instagram | Posts, Reels, Stories |
| X/Twitter | Videos, GIFs, Carousels |
| Reddit | Native videos, galleries |
| Facebook | Video posts |

## Architecture

```
┌─────────────────────────────────────┐
│           Render (512MB)            │
├─────────────────────────────────────┤
│  ┌──────────┐    ┌──────────────┐   │
│  │  Bot     │◄───│   Redis      │   │
│  │  Worker  │    │   (25MB)     │   │
│  └──────────┘    └──────────────┘   │
│       │                                │
│       ▼                                │
│  ┌──────────────┐                      │
│  │  yt-dlp      │                      │
│  │  Extractor   │                      │
│  └──────────────┘                      │
│       │                                │
│       ▼                                │
│  ┌──────────────┐                      │
│  │  FFmpeg      │                      │
│  │  Processor   │                      │
│  └──────────────┘                      │
│       │                                │
│       ▼                                │
│  ┌──────────────┐                      │
│  │  Telegram    │                      │
│  │  Uploader    │                      │
│  └──────────────┘                      │
└─────────────────────────────────────┘
```

## Memory Optimization

- **Single worker**: Only 1 concurrent download
- **Stream processing**: No intermediate file storage
- **Lazy imports**: Modules loaded on demand
- **Auto cleanup**: Files deleted immediately after upload
- **Minimal dependencies**: ~50MB base memory usage

## Cookie Setup (for private content)

Create Netscape-format cookie files in `~/.yt-dlp/cookies/`:
- `youtube_cookies.txt`
- `instagram_cookies.txt`
- `twitter_cookies.txt`
- `reddit_cookies.txt`

On Render, mount these as a **Secret File** or use a **Disk** (paid plan).

## License

MIT License - See LICENSE file for details