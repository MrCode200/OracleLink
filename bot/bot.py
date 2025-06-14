import logging
import os
import time
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, \
    CallbackQueryHandler, Application

from .additions import FilteredPersistence
from tradingComponents.patterns.breackout import breakout
from tradingComponents.Dow import detect_dow_trend, plot_candle_chart
from .commands import log_handler
from apis.binanceApi.fetcher import fetch_klines
from tradingComponents.strategies import ShadowsTrendingTouch
from utils import parse_interval, seconds_to_next_boundry

logger = logging.getLogger("oracle.link")
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

stt = ShadowsTrendingTouch(
    sma_period=7,
    shadow_to_body_ratio=1.25,
    shadow_multiplier=1,
    opposite_shadow_to_body_ratio_limit=5.5,
    ignore_sma_touch=True
)

class OracleLinkBot:
    def __init__(self, token: str):
        self.persistence = FilteredPersistence(blacklist_keys=['running'] ,filepath=f'{parent_dir}/data/userData/oracle_link_bot.pkl')
        self.app: Application = (ApplicationBuilder().
                                 token(token).
                                 persistence(self.persistence).
                                 post_init(self.post_init).
                                 post_stop(self.post_stop).
                                 build())
        self.startup_time = datetime.now()

    def run(self):
        print("🚀 Bot is running...")
        self.app.run_polling()

    async def post_init(self, application: Application):
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stop", self.stop_command))
        application.add_handler(CommandHandler("clear", self.clear_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("add", self.add_symbol_command))
        application.add_handler(CommandHandler("rmv", self.remove_symbol_command))
        application.add_handler(CommandHandler("list", self.list_watchlist_command))
        application.add_handler(CommandHandler("mydata", self.my_data_command)) # For debugging

        application.add_handler(CallbackQueryHandler(self.inline_button_handler))
        # Doesn't work if the command exists
        application.add_handler(MessageHandler(filters.COMMAND, log_handler, block=False))

        all_user_data: dict = await self.persistence.get_user_data()
        logger.info(f"Notifying {len(all_user_data)} users...")
        for user_id in all_user_data.keys():
            await application.bot.send_message(
                chat_id=user_id,
                text="🚀 Oracle Link Bot booted... ヾ(≧▽≦*)o"
            )

    async def my_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): # For debugging
        await update.message.reply_text("My data: {}".format(context.user_data))

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        running = user_data.get('running', False)

        total_job_count = len(context.job_queue.jobs())
        user_running_job_count = len(user_data.get('watchlist', []))

        # Calculate the time difference
        delta = datetime.now() - self.startup_time
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format the duration
        formatted_delta = f"{delta.days}d {hours:02}:{minutes:02}:{seconds:02}"

        await update.message.reply_text(f"🕑 Last startup: {formatted_delta}\n"
                                        f"🏃 Running {user_running_job_count}/{total_job_count} (user_jobs/total_jobs) jobs: {running}")

    async def add_symbol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) not in [2, 3]:
            await update.message.reply_text("Usage: /add <symbol> <timeframe> <send_always: optional>")
            return

        symbol = args[0].upper()
        timeframe = args[1].lower()
        send_always = bool(args[2].lower()) if len(args) == 3 else False

        # Validate timeframe (optional)
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if timeframe not in valid_timeframes:
            await update.message.reply_text(
                f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}"
            )
            return
        watchlist = context.user_data.setdefault('watchlist', [])
        if (symbol, timeframe, send_always) in watchlist:
            await update.message.reply_text(
                f"⚠️ {symbol} already exists with timeframe {timeframe}"
            )
            return

        watchlist.append((symbol, timeframe, send_always))
        await update.message.reply_text(f"✅ Added {symbol} ({timeframe}) to watchlist")

    async def list_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        for symbol, timeframe, send_always in sorted_watchlist:
            message += f"{symbol:<9} {timeframe}{" (send_always)" if send_always else ""}\n"

        message += "</code>"  # End monospace formatting

        await update.message.reply_text(message, parse_mode="HTML")

    async def remove_symbol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        for symbol, interval_str, send_always in watchlist:
            interval_sec: int = parse_interval(interval_str)
            delay: float = seconds_to_next_boundry(interval_sec)

            logger.debug(f"Starting job for {symbol} with interval {interval_sec} seconds; Send always: {send_always}")
            context.job_queue.run_repeating(
                self.scheduled_job,
                interval=interval_sec,
                first=delay,
                data={
                    'chat_id': chat_id,
                    'user_id': update.effective_user.id,
                    'symbol': symbol,
                    'interval': interval_str,
                    'send_always': send_always
                }
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
        for job in context.job_queue.jobs():
            if job.data['user_id'] == update.effective_user.id:
                job.schedule_removal()

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
        for symbol, interval, send_always in current_items:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {symbol} ({interval}){' Send always: on' if send_always else 'Send always: off'}",
                    callback_data=f"remove_{symbol}_{interval}_{send_always}"
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
            _, symbol, interval, send_always = query.data.split('_')
            watchlist = user_data.get('watchlist', [])
            item = (symbol, interval, send_always)

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
                
                await query.answer(f"Removed {symbol} ({interval}){' Send always: on' if send_always else ' Send always: off'} ✅")

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
        send_always = job_data["send_always"]

        # Fetching data
        # Due to random delays we delay for new candle and remove it
        try:
            time.sleep(2)
            df = fetch_klines(symbol=symbol, interval=interval, limit=75)
            df = df.iloc[:-1]

            # STT
            conf = stt.evaluate(df)

            # Breakout
            breakout_info: dict[str, float | str] = breakout(df)

            if not send_always and (conf == 0 or breakout_info["direction"] is None):
                return

            # Dow
            result, peaks, valleys = detect_dow_trend(df)
            buf = plot_candle_chart(df, peaks, valleys, result, breakout_info=breakout_info, sma=stt.sma_period, symbol=symbol,
                                    return_img_buffer=True, show_candles=25)

            caption: str = f"{symbol}-{interval}\n\n"
            caption += f"STT: {conf}\n"

            caption += "\nBreakout:\n"
            for key, value in breakout_info.items():
                caption += f"{key}: {value}\n"

            await context.bot.send_photo(chat_id=chat_id, photo=buf, caption=caption)

        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"Error: {e}")
            raise

    async def post_stop(self, application: Application):
        logger.info("Shutting down...")
        all_user_data: dict = await self.persistence.get_user_data()

        for user_id, user_data in all_user_data.items():
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text="🔄 Bot is shutting down for maintenance. Your settings will be preserved."
                )
            except Exception as e:
                logger.warning(f"Failed to send shutdown notification to user {user_id}: {e}")

        await application.persistence.flush()
        logger.info("Successfully shut down.")