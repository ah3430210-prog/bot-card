import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


TOKEN = os.environ["BOT_TOKEN"]

ADMIN_ID = 8502501681

PORT = int(os.environ.get("PORT", "10000"))


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BOT CARD IS LIVE")

    def log_message(self, format, *args):
        pass


def start_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


def main_menu(user_id):

    buttons = [
        [InlineKeyboardButton("💳 Buy Product", callback_data="buy")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🧾 My Orders", callback_data="orders")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("↩️ Refund", callback_data="refund")],
        [InlineKeyboardButton("📞 Support", callback_data="support")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
    ]

    if user_id == ADMIN_ID:
        buttons.append([
            InlineKeyboardButton(
                "🔐 Admin Panel",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "✨ Welcome to BOT CARD!\n\n"
        "━━━━━━━━━━━━━━\n"
        "💱 Rate: 1 USD = 125 BDT\n"
        "━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option:",
        reply_markup=main_menu(user_id)
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "admin":

        if user_id != ADMIN_ID:
            await query.answer(
                "❌ Access denied!",
                show_alert=True
            )
            return

        keyboard = [
            [InlineKeyboardButton(
                "➕ Add Product",
                callback_data="admin_add"
            )],
            [InlineKeyboardButton(
                "🗑️ Remove Product",
                callback_data="admin_remove"
            )],
            [InlineKeyboardButton(
                "📦 Product List",
                callback_data="admin_products"
            )],
            [InlineKeyboardButton(
                "👥 Users",
                callback_data="admin_users"
            )],
            [InlineKeyboardButton(
                "💰 Manage Balance",
                callback_data="admin_balance"
            )],
            [InlineKeyboardButton(
                "🔙 Back",
                callback_data="back"
            )],
        ]

        await query.edit_message_text(
            "🔐 ADMIN PANEL\n\n"
            "━━━━━━━━━━━━━━\n"
            "⚙️ Control Center\n"
            "━━━━━━━━━━━━━━\n\n"
            "👇 Choose an option:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "back":

        await query.edit_message_text(
            "💳 BOT CARD\n\n"
            "👇 Choose an option:",
            reply_markup=main_menu(user_id)
        )

    else:

        await query.edit_message_text(
            f"🔹 {data.upper()}\n\n"
            "⏳ This feature will be added in the next update."
        )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Use the button below:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔐 Open Admin Panel",
                    callback_data="admin"
                )
            ]
        ])
    )


def main():

    Thread(
        target=start_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", admin_command)
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    print("BOT CARD IS RUNNING")

    app.run_polling()


if __name__ == "__main__":
    main()
