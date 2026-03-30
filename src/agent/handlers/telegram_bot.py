"""Telegram bot handler — command router for Legion.

Receives commands from your Telegram app and dispatches to the
appropriate handler. Extensible: add new command handlers as you
add more capabilities (trading, lead gen, etc.).

Auth: whitelisted users only (OWNER_TELEGRAM_ID in .env).
"""

import logging
import os
import asyncio
from dataclasses import dataclass
from typing import Callable, Awaitable

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from src.storage.database import Database

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_ID = os.getenv("OWNER_TELEGRAM_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

if not OWNER_ID:
    raise RuntimeError("OWNER_TELEGRAM_ID not set in .env — "
                       "Message @userinfobot on Telegram to get your ID")

OWNER_ID = int(OWNER_ID)

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ── Auth ─────────────────────────────────────────────────────────────────────

async def auth_check(update: Update) -> bool:
    """Return True only if message is from the whitelisted owner."""
    return update.effective_user.id == OWNER_ID


async def auth_fail(update: Update):
    """Send 'access denied' reply."""
    await update.message.reply_text("Access denied — you are not authorized.")


# ── Dataclass: Command Handler ───────────────────────────────────────────────

@dataclass
class CommandHandler_:
    name: str
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
    description: str


# ── Handler Registry ──────────────────────────────────────────────────────────

def build_handlers(db: Database) -> list[CommandHandler_]:
    """Return all registered command handlers. Add new commands here."""

    async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await auth_check(update):
            return await auth_fail(update)
        await update.message.reply_text(
            "Legion Bot is online.\n\n"
            "Available commands:\n"
            "/start — show this message\n"
            "/help — show help\n"
            "/research <topic> — run research on a topic\n"
            "/status — check bot status\n"
            "/history — show recent research sessions"
        )

    async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await auth_check(update):
            return await auth_fail(update)
        await update.message.reply_text(
            "Legion Bot — available commands:\n\n"
            "/start — welcome message\n"
            "/help — show this message\n"
            "/research <topic> — run web research on <topic>\n"
            "/status — check system status\n"
            "/history — show recent research sessions\n\n"
            "Just send a message to chat with Legion."
        )

    async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await auth_check(update):
            return await auth_fail(update)
        await update.message.reply_text(
            "Legion Bot is running.\n"
            f"Database: {db.db_path}\n"
            "All systems operational."
        )

    async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await auth_check(update):
            return await auth_fail(update)
        await update.message.reply_text("Fetching research history...")
        from src.agent.handlers.research_handler import handle_research_history
        history = await handle_research_history(db, limit=5)
        await update.message.reply_text(history or "No research sessions yet.")

    async def cmd_research(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await auth_check(update):
            return await auth_fail(update)
        query = " ".join(ctx.args)
        if not query:
            await update.message.reply_text(
                "Usage: /research <topic>\n"
                "Example: /research trading bot strategies"
            )
            return
        await update.message.reply_text(f"Researching: {query}...")
        from src.agent.handlers.research_handler import handle_research_request
        try:
            result = await handle_research_request(
                user_message=f"research more on {query}",
                db=db,
            )
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(f"Research failed: {e}")
            await update.message.reply_text(f"Research failed: {e}")

    return [
        CommandHandler_("start", cmd_start, "welcome message"),
        CommandHandler_("help", cmd_help, "show help"),
        CommandHandler_("status", cmd_status, "check status"),
        CommandHandler_("history", cmd_history, "show research history"),
        CommandHandler_("research", cmd_research, "run web research"),
    ]


async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update):
        return await auth_fail(update)
    await update.message.reply_text(
        "Unknown command. Send /help to see available commands."
    )


async def echo_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Default handler for non-command text messages."""
    if not await auth_check(update):
        return await auth_fail(update)
    await update.message.reply_text(
        "Got your message. For commands, use /help to see what's available."
    )


# ── Main ─────────────────────────────────────────────────────────────────────

async def post_init(application: Application):
    """Run after application is initialized."""
    await application.bot.send_message(
        chat_id=OWNER_ID,
        text="Legion Bot is now online.",
    )


def run_bot():
    """Entry point — start the Telegram bot."""
    db = Database(db_path=os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "legion.db"))

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register command handlers
    handlers = asyncio.run(build_handlers(db))
    for h in handlers:
        app.add_handler(CommandHandler(h.name, h.func))
        logger.info(f"Registered command: /{h.name}")

    # Fallback handlers
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))

    logger.info("Legion Telegram bot starting...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
