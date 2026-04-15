from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pyrogram import idle

from app.bot import MovieBot
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


class HealthHandler(BaseHTTPRequestHandler):
    server_version = "MovieBotHealth/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            body = b"Telegram movie bot is running"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/health":
            payload = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        body = b"Not Found"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        logging.getLogger("health").debug("%s - %s", self.address_string(), format % args)


def start_health_server() -> ThreadingHTTPServer:
    port = int(os.getenv("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health-server", daemon=True)
    thread.start()
    logging.info("Health server started on 0.0.0.0:%s", port)
    return server


async def main() -> None:
    health_server = start_health_server()
    bot: MovieBot | None = None

    try:
        settings = get_settings()
        bot = MovieBot(settings)
        await bot.start()
        await bot.db_service.ensure_indexes()

        me = await bot.get_me()
        logging.info("Bot started as @%s", me.username)

        if not bot.settings.bot_username and me.username:
            bot.settings.bot_username = me.username

        await idle()
    finally:
        if bot is not None:
            try:
                await bot.stop()
            except Exception as exc:
                logging.warning("Bot stop skipped: %s", exc)
        health_server.shutdown()
        health_server.server_close()


if __name__ == "__main__":
    asyncio.run(main())

