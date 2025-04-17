import logging
import os

from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence

from .commands import help_command, log_handler
from .utils import parse_interval, seconds_to_next_boundry
from apis.binanceApi.fetcher import fetch_data
from tradingComponents.strategies import ShadowsTrendingTouch

logger = logging.getLogger("oracle.link")
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

stt = ShadowsTrendingTouch(
    sma_period=7,
    shadow_to_body_ratio=1.25,
    shadow_padding_pips=2,
    opposite_shadow_to_body_ratio=0.25
)

class OracleLinkBot:
    def __init__(self, token):
        persistence = PicklePersistence(filepath=f'{parent_dir}/data/userData/oracle_link_bot.pkl')
        self.app = ApplicationBuilder().token(token).persistence(persistence).build()

    def run(self):
        print("🚀 Bot is running...")
        self.init_bot()
        self.app.run_polling()

    def init_bot(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("stop", self.stop_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        self.app.add_handler(CommandHandler("help", help_command))
        self.app.add_handler(CommandHandler("add", self.add_symbol))
        self.app.add_handler(CommandHandler("rmv", self.remove_symbol))
        self.app.add_handler(CommandHandler("list", self.list_watchlist))
        # Doesn't work if the command exists
        self.app.add_handler(MessageHandler(filters.COMMAND, log_handler, block=False))

    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        watchlist = context.user_data.setdefault('watchlist', [])
        if (symbol, timeframe) in watchlist:
            await update.message.reply_text(
                f"⚠️ {symbol} already exists with timeframe {timeframe}"
            )
            return

        watchlist.append((symbol, timeframe))
        await update.message.reply_text(f"✅ Added {symbol} ({timeframe}) to watchlist")

    async def list_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command, showing sorted watchlist"""

        watchlist = context.user_data.get('watchlist', [])
        if not watchlist:
            await update.message.reply_text("Watchlist is empty")
            return

        sorted_watchlist = sorted(
            watchlist,
            key=lambda x: (x[0].lower(), x[1])
        )

        message = "<b>🔍 Watchlist</b>\n\n"
        message += "<code>"  # Start monospace formatting
        message += "Symbol    Timeframe\n"
        message += "─" * 20 + "\n"  # Separator line

        for symbol, tf in sorted_watchlist:
            message += f"{symbol:<9} {tf}\n"

        message += "</code>"  # End monospace formatting

        await update.message.reply_text(message, parse_mode="HTML")

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rmv command"""
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /rmv <ticker> <timeframe>")
            return

        symbol = args[0].upper()
        timeframe = args[1].lower()

        watchlist = context.user_data.get('watchlist', [])
        if (symbol, timeframe) not in watchlist:
            await update.message.reply_text(f"❌ {symbol} with timeframe {timeframe} not found in watchlist")
            return

        watchlist.remove((symbol, timeframe))
        await update.message.reply_text(f"✅ Removed {symbol} ({timeframe}) from watchlist")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = "🚀 Crypto Trading Bot At Your Service!"
        watchlist = context.user_data.get('watchlist', [])
        if not watchlist:
            msg += "\nWatchlist is empty （；´д｀）ゞ\n"
            await update.message.reply_text(msg)
            return

        chat_id = update.message.chat_id
        for key, interval_str in watchlist:
            interval_sec = parse_interval(interval_str)
            delay = seconds_to_next_boundry(interval_sec)
            context.job_queue.run_repeating(
                self.scheduled_job,
                interval=interval_sec,
                first=delay,
                data={'chat_id': chat_id, 'symbol': key, 'interval': interval_str}
            )

        msg += "\nStarted watching... (▀̿Ĺ̯▀̿ ̿)\n"
        await update.message.reply_text(msg)

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.job_queue.stop()
        await update.message.reply_text("Link stopped watching... (_　_)。゜zｚＺ.")

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['watchlist'] = []
        await update.message.reply_text("Watchlist cleared. ╰(￣ω￣ｏ)")

    async def scheduled_job(self, context: ContextTypes.DEFAULT_TYPE):
        # Kian HERE u CODE
        job_data = context.job.data
        chat_id = job_data["chat_id"]
        interval = job_data["interval"]
        symbol = job_data["symbol"]

        num_of_candles = 120
        df = fetch_data(symbol=symbol, timeframe=interval, lookback_minutes=parse_interval(interval) * num_of_candles)

        confidence = stt.evaluate(df)

        await context.bot.send_message(chat_id=chat_id, text=f"STT: {confidence}")


