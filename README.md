# Telegram Movie / TV Series Filter Bot

Pyrogram + MongoDB Telegram bot with:
- group auto search by plain text
- admin private panel with buttons
- movies and TV series split in results
- TMDb + OMDb poster fallback
- quality + codec selection
- private inbox delivery for downloads
- source channel auto-ingest into MongoDB
- owner-locked buttons so only the searching user can click them

## User flow

1. Add the bot to your allowed group.
2. A user types a movie or TV series name in the group.
3. Bot replies with poster + caption + **Movies / TV Series** buttons.
4. Only the original searching user can use those buttons.
5. Another user clicking them gets: `Not working for you`.
6. After quality / codec / episode selection, the bot sends the file to that user's private inbox.
7. The bot also sends a help message in private explaining how to download the file.

## Admin flow

1. Open the bot in private chat.
2. Send `/admin`.
3. Use buttons to:
   - find movie titles
   - find series titles
   - sync movie posts
   - sync series posts
4. Edit by buttons + text reply:
   - poster URL
   - movie / series name
   - file quality
   - file codec
5. Use `/syncseries` to upload a forwarded series post into MongoDB.

## Easy environment values

Copy `.env.example` to `.env` for local use.

For Render, use `render.env.template` as your guide.

### Required
- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `MONGO_URI`

### Common optional values
- `ADMINS`
- `USER_GROUP_IDS`
- `MOVIE_SOURCE_CHANNELS`
- `SERIES_SOURCE_CHANNELS`
- `SERIES_INFO_CHANNEL_ID`
- `LOG_CHAT_ID`
- `TMDB_API_KEY`
- `OMDB_API_KEY`

## Local run

```bash
pip install -r requirements.txt
python main.py
```

## Render deploy

This project is prepared for **Render Background Worker** deployment.

### Quick start

1. Push this project to GitHub.
2. In Render, create a **Background Worker** or a **Blueprint**.
3. Use:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Add the environment variables from `render.env.template`.
5. Deploy.

There is also a ready `render.yaml` file in the project root.

More detailed steps are in `RENDER.md`.

## Other included files

- `render.yaml` -> Render Blueprint config
- `runtime.txt` -> Python version hint
- `Dockerfile` -> optional container build
- `railway.json` -> Railway config
- `KOYEB.md` -> older Koyeb notes

## Channel caption format

```text
Type: movie
Title: Interstellar
Year: 2014
Quality: 1080p
Codec: x264
Language: English
Size: 2.3GB
```

For series:

```text
Type: series
Title: The Last of Us
Year: 2023
Season: 1
Episode: 1
Quality: 1080p
Codec: HEVC
```

## Notes

- Group results show **Movies** and **TV Series** as separate buttons.
- Preview results include poster + clean caption.
- File delivery goes to the bot private inbox.
- Only the original user can click the result buttons.
- Admin edits work through buttons + text replies.
