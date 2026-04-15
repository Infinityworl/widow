# Deploy on Render

This bot should be deployed as a **Background Worker** on Render.

## Option 1: Render Dashboard

1. Upload this project to GitHub.
2. Open Render.
3. Click **New +** -> **Background Worker**.
4. Connect your GitHub repository.
5. For the service settings use:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
6. Open `render.env.template` and copy each value into Render **Environment Variables**.
7. Deploy.

## Option 2: render.yaml Blueprint

This repository already includes `render.yaml`.

1. Push the repo to GitHub.
2. In Render, create a new **Blueprint**.
3. Select the repository.
4. Render will read `render.yaml` and create a **worker** service.
5. Add the required environment variables before the first deploy.

## Important values

### Required
- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `MONGO_URI`

### Usually needed
- `ADMINS`
- `USER_GROUP_IDS`
- `MOVIE_SOURCE_CHANNELS`
- `SERIES_SOURCE_CHANNELS`
- `TMDB_API_KEY`
- `OMDB_API_KEY`

## Notes

- This project is a long-running Telegram bot, so it should be a **Background Worker**, not a web service.
- If the bot is already running somewhere else, stop that instance first so you do not run two copies at once.
- If MongoDB access is restricted by IP, allow Render to connect or use a connection string that supports cloud access.
