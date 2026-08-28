import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 8502501681
RATE = 125

BKASH = "01326630510"
NAGAD = "01326630510"
BYBIT_UID = "531771545"
BINANCE_UID = "780473636"

SUPPORT = "https://t.me/abirhasan6738"

PORT = int(os.environ.get("PORT", "10000"))


# ---------- WEB SERVER ----------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BOT CARD is live")

    def log_message(self, *args):
        pass


def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# ---------- DATABASE ----------

def setup_database():
    con = sqlite3.connect("botcard.db")
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0
        )
    """)

    con.commit()
    con.close()


def register_user(user_id):
    con = sqlite3.connect("botcard.db")
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users(user_id) VALUES(?)",
        (user_id,)
    )

    con.commit()
    con.close()


# ---------- MENU ----------

def main_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Buy Card", callback_data="buy")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🧾 My Orders", callback_data="orders")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("↩️ Refund", callback_data="refund")],
        [InlineKeyboardButton("📞 Support", callback_data="support")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
    ]

    return InlineKeyboardMarkup(keyboard)


# ---------- START ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "Welcome to BOT CARD! 👋\n\n"
        f"💱 Rate: 1 USD = {RATE} BDT",
        reply_markup=main_menu()
    )


# ---------- BUTTONS ----------

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "buy":

        await query.edit_message_text(
            "💳 BUY CARD\n\n"
            "Available products will appear here."
        )

    elif query.data == "deposit":

        keyboard = [
            [InlineKeyboardButton("📱 bKash", callback_data="bkash")],
            [InlineKeyboardButton("📱 Nagad", callback_data="nagad")],
            [InlineKeyboardButton("💳 Bybit", callback_data="bybit")],
            [InlineKeyboardButton("🪙 Binance", callback_data="binance")],
        ]

        await query.edit_message_text(
            "💵 DEPOSIT\n\n"
            "Choose payment method:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "bkash":

        await query.edit_message_text(
            "📱 bKash Deposit\n\n"
            "Send Money:\n"
            f"{BKASH}\n\n"
            "After payment, send your transaction details to admin."
        )

    elif query.data == "nagad":

        await query.edit_message_text(
            "📱 Nagad Deposit\n\n"
            "Send Money:\n"
            f"{NAGAD}\n\n"
            "After payment, send your transaction details to admin."
        )

    elif query.data == "bybit":

        await query.edit_message_text(
            "💳 Bybit Deposit\n\n"
            "UID:\n"
            f"{BYBIT_UID}\n\n"
            "After payment, send your transaction details to admin."
        )

    elif query.data == "binance":

        await query.edit_message_text(
            "🪙 Binance Deposit\n\n"
            "UID:\n"
            f"{BINANCE_UID}\n\n"
            "After payment, send your transaction details to admin."
        )

    elif query.data == "balance":

        con = sqlite3.connect("botcard.db")
        cur = con.cursor()

        cur.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,)
        )

        row = cur.fetchone()
        con.close()

        balance = row[0] if row else 0

        await query.edit_message_text(
            "💰 MY BALANCE\n\n"
            f"USD: ${balance:.2f}\n"
            f"BDT: ৳{balance * RATE:.2f}"
        )

    elif query.data == "orders":

        await query.edit_message_text(
            "🧾 MY ORDERS\n\n"
            "No orders yet."
        )

    elif query.data == "withdraw":

        await query.edit_message_text(
            "💸 WITHDRAW\n\n"
            "Available methods:\n\n"
            "📱 bKash\n"
            "📱 Nagad\n"
            "💳 Bybit\n"
            "🪙 Binance\n\n"
            "Withdraw requests require admin approval."
        )

    elif query.data == "refund":

        await query.edit_message_text(
            "↩️ REFUND\n\n"
            "Select an order from My Orders to request a refund."
        )

    elif query.data == "support":

        await query.edit_message_text(
            "📞 SUPPORT\n\n"
            "Contact support:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💬 Telegram Support",
                        url=SUPPORT
                    )
                ]
            ])
        )

    elif query.data == "profile":

        await query.edit_message_text(
            "👤 PROFILE\n\n"
            f"User ID: {user_id}\n"
            f"Username: @{query.from_user.username or 'N/A'}"
        )


# ---------- ADMIN ----------

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Admin ID verified.\n\n"
        "Next step: product management."
    )


# ---------- MAIN ----------

def main():

    setup_database()

    Thread(
        target=start_web_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", admin)
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    print("BOT CARD is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
