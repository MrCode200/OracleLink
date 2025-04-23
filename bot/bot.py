import logging
import os
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence, \
    CallbackQueryHandler

from tradingComponents.patterns.breackout import breakout
from tradingComponents.Dow import detect_dow_trend, plot_candle_chart
from .commands import log_handler
from apis.binanceApi.fetcher import fetch_klines
from tradingComponents.strategies import ShadowsTrendingTouch
from .utils import parse_interval, seconds_to_next_boundry

logger = logging.getLogger("oracle.link")
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

stt = ShadowsTrendingTouch(
    sma_period=7,
    shadow_to_body_ratio=1.25,
    shadow_padding_price=0,
    opposite_shadow_to_body_ratio=0.25
)

class OracleLinkBot:
    def __init__(self, token):
        persistence = PicklePersistence(filepath=f'{parent_dir}/data/userData/oracle_link_bot.pkl')
        self.app = ApplicationBuilder().token(token).persistence(persistence).build()
        self.startup_time = datetime.now()

    def run(self):
        print("🚀 Bot is running...")
        self.init_bot()
        self.app.run_polling()

    def init_bot(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("stop", self.stop_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("add", self.add_symbol))
        self.app.add_handler(CommandHandler("rmv", self.remove_symbol))
        self.app.add_handler(CommandHandler("list", self.list_watchlist))

        self.app.add_handler(CallbackQueryHandler(self.inline_button_handler))
        # Doesn't work if the command exists
        self.app.add_handler(MessageHandler(filters.COMMAND, log_handler, block=False))

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        running = user_data.get('running', False)
        job_count = len(context.job_queue.jobs())
        await update.message.reply_text(f"🕑 Last startup: {self.startup_time}\n"
                                        f"🏃 Running {job_count} jobs: {running}")

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
        user_data = context.user_data
        watchlist = user_data.get('watchlist', [])

        if not watchlist:
            await update.message.reply_text("Your watchlist is empty! Nothing to manage. 📭")
            return

        page = 0
        keyboard = self.create_watchlist_keyboard(watchlist, page)

        await update.message.reply_text(
            "Select items to remove from your watchlist:\n"
            f"Page {page + 1}/{(len(watchlist) - 1) // 5 + 1}",
            reply_markup=keyboard
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        if user_data.get('running'):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Stop", callback_data='stop')]
            ])
            await update.message.reply_text(
                "🤖 Your bot is already running! Jobs will continue to fire until you stop them. (ง •̀_•́)ง",
                reply_markup=keyboard
            )
            return

        watchlist = user_data.get('watchlist', [])
        if not watchlist:
            await update.message.reply_text("Your watchlist is empty. Use /add first. (￣﹃￣)...")
            return

        chat_id = update.effective_chat.id
        user_data['running'] = True

        # Stop any existing jobs first
        if context.job_queue:
            context.job_queue.stop()

        for symbol, interval_str in watchlist:
            interval_sec: int = parse_interval(interval_str)
            delay: float = seconds_to_next_boundry(interval_sec)
            logger.debug(f"Starting job for {symbol} with interval {interval_sec} seconds")
            context.job_queue.run_repeating(
                self.scheduled_job,
                interval=interval_sec,
                first=delay,
                data={'chat_id': chat_id, 'symbol': symbol, 'interval': interval_str}
            )

        await update.message.reply_text(
            "✅ Started watching your symbols! (▀̿Ĺ̯▀̿ ̿)\n"
            "ℹ️ Note: Changes you make (add / rmv) won't take effect until you /stop and then /start again."
        )

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        if not user_data.get('running'):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start", callback_data='start')]
            ])
            await update.message.reply_text(
                "🚫 The bot is already stopped for you. (┬┬﹏┬┬)",
                reply_markup=keyboard
            )
            return

        user_data['running'] = False

        # Stop all jobs
        if context.job_queue:
            context.job_queue.stop()

        await update.message.reply_text(
            "🛑 Stopped watching your symbols. (_　_)。゜zｚＺ\n"
            "ℹ️ To start again, simply use /start."
        )

    def create_watchlist_keyboard(self, watchlist, page=0, items_per_page=5):
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_items = watchlist[start_idx:end_idx]

        keyboard = []
        # Add watchlist item buttons
        for symbol, interval in current_items:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {symbol} ({interval})",
                    callback_data=f"remove_{symbol}_{interval}"
                )
            ])

        # Add navigation buttons if needed
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
        if end_idx < len(watchlist):
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        return InlineKeyboardMarkup(keyboard)

    async def inline_button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_data = context.user_data

        if query.data.startswith('page_'):
            # Handle page navigation
            page = int(query.data.split('_')[1])
            watchlist = user_data.get('watchlist', [])
            keyboard = self.create_watchlist_keyboard(watchlist, page)

            await query.message.edit_text(
                "Select items to remove from your watchlist:\n"
                f"Page {page + 1}/{(len(watchlist) - 1) // 5 + 1}",
                reply_markup=keyboard
            )
            await query.answer()

        elif query.data.startswith('remove_'):
            # Handle item removal
            _, symbol, interval = query.data.split('_')
            watchlist = user_data.get('watchlist', [])
            item = (symbol, interval)

            if item in watchlist:
                watchlist.remove(item)
                user_data['watchlist'] = watchlist

                # Update the watchlist view
                if watchlist:
                    keyboard = self.create_watchlist_keyboard(watchlist, 0)
                    await query.message.edit_text(
                        "Select items to remove from your watchlist:\n"
                        f"Page 1/{(len(watchlist) - 1) // 5 + 1}",
                        reply_markup=keyboard
                    )
                else:
                    await query.message.edit_text("Your watchlist is now empty! Nothing to manage. 📭")
                
                await query.answer(f"Removed {symbol} ({interval}) ✅")

        elif query.data == 'start':
            if context.user_data.get('running'):
                await query.answer("Bot is already running! 🤖")
                return
            await query.answer("Starting bot... ✅")
            await self.start_command(update, context)
        elif query.data == 'stop':
            if not context.user_data.get('running'):
                await query.answer("Bot is already stopped! 🛑")
                return
            await query.answer("Stopping bot... 🔄")
            await self.stop_command(update, context)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['watchlist'] = []
        await update.message.reply_text("Watchlist cleared. ╰(￣ω￣ｏ)")

    async def scheduled_job(self, context: ContextTypes.DEFAULT_TYPE):
        job_data = context.job.data
        chat_id = job_data["chat_id"]
        interval = job_data["interval"]
        symbol = job_data["symbol"]

        # Fetching data
        df = fetch_klines(symbol=symbol, interval=interval, limit=75)

        # STT
        stt_conf = stt.evaluate(df)

        # Breakout
        breakout_info: dict[str, float | str] = breakout(df)

        if stt_conf == 0 or breakout_info["direction"] is None:
            return

        # Dow
        result, peaks, valleys = detect_dow_trend(df)
        buf = plot_candle_chart(df, peaks, valleys, result, breakout_info=breakout_info, sma=stt.sma_period, symbol=symbol,
                                return_img_buffer=True, show_candles=15)

        caption: str = (f"STT: {stt_conf}\n"
                        f"Breakout: \n")
        for key, value in breakout_info.items():
            caption += f"{key}: {value}\n"
        await context.bot.send_photo(chat_id=chat_id, photo=buf, caption=caption)
