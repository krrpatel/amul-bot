"""Telegram bot for Amul product availability tracking."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from api_client import AmulAPIClient
from config import Config
from user_data_manager import UserDataManager  # New JSON-based manager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WAITING_FOR_PINCODE, SELECTING_PRODUCTS = range(2)


class AmulBot:
    def __init__(self):
        self.user_data = UserDataManager()  # Simple JSON storage
        self.product_cache: Dict[int, List[Dict[str, Any]]] = {}

    # -------------------- START --------------------

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "👋 *Welcome to Amul Product Tracker!*\n\n"
            "📍 Send your *6-digit pincode* to begin.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_PINCODE

    # -------------------- PINCODE --------------------

    async def receive_pincode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        pincode = update.message.text.strip()

        if not pincode.isdigit() or len(pincode) != 6:
            await update.message.reply_text("❌ Please enter a valid 6-digit pincode.")
            return WAITING_FOR_PINCODE

        self.user_data.set_pincode(user_id, pincode)
        await update.message.reply_text("🔍 Fetching products...")

        try:
            client = AmulAPIClient()
            client.set_store_preferences(pincode)
            products = client.get_products()

            if not products:
                await update.message.reply_text("❌ No products found.")
                return ConversationHandler.END

            self.product_cache[user_id] = products
            await self.show_product_selection(update, user_id, products, page=0)
            return SELECTING_PRODUCTS

        except Exception as e:
            logger.exception("Product fetch failed")
            await update.message.reply_text("❌ Failed to fetch products.")
            return ConversationHandler.END

    # -------------------- PRODUCT UI --------------------

    async def show_product_selection(self, update, user_id, products, page=0):
        PER_PAGE = 5
        selected = self.user_data.get_selected_products(user_id)

        total_pages = (len(products) + PER_PAGE - 1) // PER_PAGE
        start = page * PER_PAGE
        end = start + PER_PAGE
        page_products = products[start:end]

        text = (
            f"📦 *Amul Protein Products* ({page+1}/{total_pages})\n"
            f"✅ Selected: {len(selected)}\n\n"
        )

        keyboard = []

        for idx, product in enumerate(page_products):
            global_index = start + idx
            alias = product["alias"]
            name = product["name"]
            price = product["price"]
            available = product["available"] > 0

            checked = "☑️" if alias in selected else "⬜"
            status = "✅" if available else "❌"

            keyboard.append([
                InlineKeyboardButton(
                    f"{checked} {name} ₹{price} {status}",
                    callback_data=f"toggle:{page}:{global_index}"
                )
            ])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page+1}"))

        if nav:
            keyboard.append(nav)

        keyboard.append([
            InlineKeyboardButton("✅ Done", callback_data="done"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"page:{page}")
        ])

        markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

    # -------------------- CALLBACKS --------------------

    async def handle_product_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data
        products = self.product_cache.get(user_id, [])
        selected = self.user_data.get_selected_products(user_id)

        if data.startswith("toggle:"):
            _, page, index = data.split(":")
            page, index = int(page), int(index)

            alias = products[index]["alias"]
            if alias in selected:
                selected.remove(alias)
            else:
                selected.add(alias)

            self.user_data.set_selected_products(user_id, selected)
            await self.show_product_selection(update, user_id, products, page)
            return SELECTING_PRODUCTS

        if data.startswith("page:"):
            page = int(data.split(":")[1])
            await self.show_product_selection(update, user_id, products, page)
            return SELECTING_PRODUCTS

        if data == "done":
            await query.edit_message_text(
                "✅ Tracking started!\n\n"
                "/myproducts – View tracked\n"
                "/check – Check now\n"
		"/change - change product\n"
                "/stop – Stop tracking"
            )
            return ConversationHandler.END

        return SELECTING_PRODUCTS

    # -------------------- COMMANDS --------------------

    async def my_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        selected = self.user_data.get_selected_products(user_id)
        products = self.product_cache.get(user_id, [])

        if not selected:
            await update.message.reply_text("📭 No tracked products.")
            return

        msg = "📦 *Your Tracked Products*\n\n"
        for p in products:
            if p["alias"] in selected:
                msg += f"• {p['name']} ₹{p['price']}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    async def stop_tracking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user_data.clear_user(update.effective_user.id)
        await update.message.reply_text("🛑 Tracking stopped.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/start – Setup\n"
            "/check – Check availability\n"
            "/myproducts – View tracked\n"
            "/change – Change products\n"
            "/stop – Stop tracking"
        )
    
    async def change_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Allow user to change their tracked products."""
        user_id = update.effective_user.id
        pincode = self.user_data.get_pincode(user_id)
        
        if not pincode:
            await update.message.reply_text(
                "❌ You haven't set up tracking yet.\nUse /start first."
            )
            return ConversationHandler.END
        
        await update.message.reply_text("🔍 Fetching products...")
        
        try:
            client = AmulAPIClient()
            client.set_store_preferences(pincode)
            products = client.get_products()
            
            if not products:
                await update.message.reply_text("❌ No products found.")
                return ConversationHandler.END
            
            self.product_cache[user_id] = products
            await self.show_product_selection(update, user_id, products, page=0)
            return SELECTING_PRODUCTS
            
        except Exception as e:
            logger.exception("Product fetch failed")
            await update.message.reply_text("❌ Failed to fetch products.")
            return ConversationHandler.END

    async def check_availability(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check availability of tracked products right now."""
        user_id = update.effective_user.id

        selected = self.user_data.get_selected_products(user_id)
        pincode = self.user_data.get_pincode(user_id)

        if not pincode or not selected:
            await update.message.reply_text(
                "❌ You haven't set up tracking yet.\nUse /start first."
            )
            return

        await update.message.reply_text("🔍 Checking availability...")

        try:
            client = AmulAPIClient()
            client.set_store_preferences(pincode)
            products = client.get_products()

            if not products:
                await update.message.reply_text("❌ No products found right now.")
                return

            message = "📊 *Availability Status*\n\n"

            for product in products:
                if product["alias"] in selected:
                    status = "✅ Available" if product["available"] > 0 else "❌ Out of stock"
                    message += f"• {product['name']} – {status}\n"

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception:
            logger.exception("Check availability failed")
            await update.message.reply_text("❌ Failed to check availability.")

    # -------------------- RUN --------------------

    def run(self):
        app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

        conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                WAITING_FOR_PINCODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_pincode)],
                SELECTING_PRODUCTS: [CallbackQueryHandler(self.handle_product_selection)],
            },
            fallbacks=[],
        )
        
        # Separate conversation handler for /change command
        change_conv = ConversationHandler(
            entry_points=[CommandHandler("change", self.change_products)],
            states={
                SELECTING_PRODUCTS: [CallbackQueryHandler(self.handle_product_selection)],
            },
            fallbacks=[],
        )

        app.add_handler(conv)
        app.add_handler(change_conv)
        app.add_handler(CommandHandler("myproducts", self.my_products))
        app.add_handler(CommandHandler("stop", self.stop_tracking))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("check", self.check_availability))

        logger.info("🤖 Bot running...")
        app.run_polling()


if __name__ == "__main__":
    AmulBot().run()
