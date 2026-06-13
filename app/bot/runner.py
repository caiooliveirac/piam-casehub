"""Telegram bot runner — long-polling process.

Runs as its own container/service (`bot`). Shares the same image and DB as the
web service. Exits early with a clear message if no token is configured.
"""

from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot import handlers
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("piam.bot")


def build_application() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler("novo", handlers.cmd_novo))
    app.add_handler(CommandHandler("casos", handlers.cmd_casos))
    app.add_handler(CommandHandler("fechar", handlers.cmd_fechar))
    app.add_handler(CommandHandler("resumo", handlers.cmd_resumo))

    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handlers.on_file))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text)
    )
    return app


def main() -> None:
    if not settings.telegram_bot_token:
        logger.error(
            "TELEGRAM_BOT_TOKEN ausente — o bot não será iniciado. "
            "Defina o token no .env."
        )
        raise SystemExit(1)
    logger.info("Iniciando bot PIAM CaseHub (long polling)…")
    app = build_application()
    app.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
