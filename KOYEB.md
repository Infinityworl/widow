# Koyeb deployment guide for this Telegram bot

This bot is a **worker**, not a normal website. In Koyeb, choose **Worker service**. Koyeb documents worker services as the correct type for background jobs, and GitHub deployments can build from a Dockerfile. citeturn129585search0turn285640search4turn129585search2

## What to upload
Push this full project to GitHub first.

## Koyeb dashboard steps
1. Open Koyeb dashboard
2. Click **Create App**
3. Choose **Worker**
4. Choose **GitHub**
5. Select your repo
6. Build method: **Dockerfile**
7. Dockerfile path: `Dockerfile`
8. Workdir: leave default if project root is the repo root
9. Deploy

## Start command
If Koyeb asks for a run command, use:

```bash
python main.py
```

## Required environment variables
Copy these from `.env.example` into Koyeb Environment Variables:

- API_ID
- API_HASH
- BOT_TOKEN
- MONGO_URI
- DATABASE_NAME
- ADMINS
- USER_GROUP_IDS
- MOVIE_SOURCE_CHANNELS
- SERIES_SOURCE_CHANNELS
- SERIES_INFO_CHANNEL_ID
- LOG_CHAT_ID
- BOT_USERNAME
- TMDB_API_KEY
- TMDB_BEARER_TOKEN
- OMDB_API_KEY
- MAX_SEARCH_RESULTS
- RESULT_PAGE_SIZE

## Quick check before deploy
- Bot added to the target group
- Bot started once in private chat
- Bot made admin in source channels if channel auto-read is needed
- MongoDB network access allows Koyeb

## Optional CLI deployment
Koyeb CLI supports GitHub deployment, Dockerfile builds, and worker service type. citeturn293641search1turn293641search2

```bash
koyeb app init telegram-movie-bot \
  --git github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME \
  --git-branch main \
  --git-builder docker \
  --type worker
```
