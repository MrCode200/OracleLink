import logging
import asyncio
import ccxt
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("oracle.link")


class Bot:
    def __init__(self):
        self.token = "7749426469:AAEDOfpbgsgdK2_6HMbeQLaX_t1V53YT6lw"  # Replace with actual token
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.watchlist: list[tuple[str, str]] = []
        self.enable_shadow_scanning = True
        self.app = None

    async def run(self):
        await self.initialize()  # build & add handlers
        await self.app.initialize()  # prepares the app
        await self.app.start()  # starts internal tasks
        await self.app.updater.start_polling()  # begins polling
        # Keep the loop alive until you want to stop:
        await self.app.updater.idle()  # waits for stop signal
        # Then cleanly tear everything down:
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def initialize(self):
        """Initialize the Telegram bot application with proper handler binding"""
        self.app = ApplicationBuilder().token(self.token).build()

        # Use lambda wrappers to preserve instance context
        handlers = [
            CommandHandler("start", lambda u, c: self.start(u, c)),
            CommandHandler("add", lambda u, c: self.add_symbol(u, c)),
            CommandHandler("rmv", lambda u, c: self.remove_symbol(u, c)),
            CommandHandler("list", lambda u, c: self.list_watchlist(u, c)),
        ]

        for handler in handlers:
            self.app.add_handler(handler)

        # Add message handler with proper binding
        self.app.add_handler(MessageHandler(
            filters.ALL,
            lambda u, c: self.log_incoming_message(u, c)
        ))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🚀 Crypto Trading Bot To Your Service!\n\n"
            "<b>Available Commands:</b>\n"
            "/add <ticker> <timeframe> - Add to watchlist\n"
            "/rmv <ticker> <timeframe> - Remove from watchlist\n"
            "/list - Show current watchlist\n",
            parse_mode="HTML"
        )

    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command"""
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /add <symbol> <timeframe>")
            return

        symbol = args[0].upper()
        timeframe = args[1].lower()

        # Validate timeframe (optional)
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if timeframe not in valid_timeframes:
            await update.message.reply_text(
                f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}"
            )
            return

        if (symbol, timeframe) in self.watchlist:
            await update.message.reply_text(
                f"⚠️ {symbol} already exists with timeframe {timeframe}"
            )
            return

        self.watchlist.append((symbol, timeframe))
        await update.message.reply_text(f"✅ Added {symbol} ({timeframe}) to watchlist")

    async def list_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command, showing sorted watchlist in a table"""
        if not self.watchlist:
            await update.message.reply_text("Watchlist is empty")
            return

        sorted_watchlist = sorted(
            self.watchlist,
            key=lambda x: (x[0].lower(), x[1])
        )

        table = "<b>🔍 Watchlist</b>\n\n"
        table += "<table border='1'><tr><th>Ticker</th><th>Timeframe</th></tr>"

        for symbol, tf in sorted_watchlist:  # Now safely unpacking tuples
            table += f"<tr><td>{symbol}</td><td>{tf}</td></tr>"

        table += "</table>"

        await update.message.reply_text(table, parse_mode="HTML")

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rmv command"""
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /rmv <ticker> <timeframe>")
            return

        symbol = args[0].upper()
        timeframe = args[1].lower()

        if (symbol, timeframe) not in self.watchlist:
            await update.message.reply_text(f"❌ {symbol} with timeframe {timeframe} not found in watchlist")
            return

        self.watchlist.remove((symbol, timeframe))
        await update.message.reply_text(f"✅ Removed {symbol} ({timeframe}) from watchlist")

    async def log_incoming_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log incoming messages"""
        if update.message:
            user = update.effective_user.username if update.effective_user else "unknown"
            text = update.message.text or "<no text>"
            logger.info(f"Message from {user}: {text}")

async def main():
    """Main entry point with proper cleanup"""
    bot = Bot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(Bot().run())