import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.environ["BOT_TOKEN"]

ADMIN_ID = 8502501681
RATE = 125

PORT = int(os.environ.get("PORT", "10000"))

BKASH = "01326630510"
NAGAD = "01326630510"
BYBIT_UID = "531771545"
BINANCE_UID = "780473636"

SUPPORT = "https://t.me/abirhasan6738"


# =========================================================
# DATABASE
# =========================================================

DB_NAME = "botcard.db"


def get_db():
    return sqlite3.connect(DB_NAME)


def setup_database():
    con = get_db()
    cur = con.cursor()

    # Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0
        )
    """)

    # Products
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            details TEXT DEFAULT '',
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)

    # Orders
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Deposits
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_id TEXT NOT NULL,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register_user(user_id):
    con = get_db()
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)",
        (user_id,)
    )

    con.commit()
    con.close()


# =========================================================
# WEB SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"BOT CARD IS LIVE")

    def log_message(self, format, *args):
        pass


def start_web_server():
    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(f"Web server running on port {PORT}")

    server.serve_forever()


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(user_id):

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Buy Product",
                callback_data="buy"
            )
        ],
        [
            InlineKeyboardButton(
                "💵 Deposit",
                callback_data="deposit"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 My Balance",
                callback_data="balance"
            )
        ],
        [
            InlineKeyboardButton(
                "🧾 My Orders",
                callback_data="orders"
            )
        ],
        [
            InlineKeyboardButton(
                "💸 Withdraw",
                callback_data="withdraw"
            )
        ],
        [
            InlineKeyboardButton(
                "↩️ Refund",
                callback_data="refund"
            )
        ],
        [
            InlineKeyboardButton(
                "📞 Support",
                callback_data="support"
            )
        ],
        [
            InlineKeyboardButton(
                "👤 Profile",
                callback_data="profile"
            )
        ],
    ]

    # Admin button only for admin
    if user_id == ADMIN_ID:
        keyboard.append([
            InlineKeyboardButton(
                "🔐 Admin Panel",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    register_user(user_id)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "✨ Welcome to BOT CARD!\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💱 Rate: 1 USD = {RATE} BDT\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👇 Select an option:",
        reply_markup=main_menu(user_id)
    )


# =========================================================
# /ADMIN
# =========================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Access denied."
        )
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Welcome Admin 👋\n\n"
        "👇 Select an option:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔐 Open Admin Panel",
                    callback_data="admin"
                )
            ]
        ])
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def show_admin_panel(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add Product",
                callback_data="admin_add"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 Product List",
                callback_data="admin_products"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Remove Product",
                callback_data="admin_remove"
            )
        ],
        [
            InlineKeyboardButton(
                "💵 Deposit Requests",
                callback_data="admin_deposits"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Users",
                callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back"
            )
        ],
    ]

    await query.edit_message_text(
        "🔐 ADMIN PANEL\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "⚙️ Control Center\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# BASIC USER PAGES
# =========================================================

async def show_balance(query):

    user_id = query.from_user.id

    register_user(user_id)

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cur.fetchone()

    con.close()

    balance = row[0] if row else 0

    await query.edit_message_text(
        "💰 MY BALANCE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💵 USD: ${balance:.2f}\n"
        f"🇧🇩 BDT: ৳{balance * RATE:.2f}\n"
        "━━━━━━━━━━━━━━━━"
    )


async def show_profile(query):

    user = query.from_user

    await query.edit_message_text(
        "👤 PROFILE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 User ID: {user.id}\n"
        f"👤 Username: @{user.username or 'N/A'}\n"
        "━━━━━━━━━━━━━━━━"
    )


async def show_withdraw(query):

    await query.edit_message_text(
        "💸 WITHDRAW\n\n"
        "Available methods:\n\n"
        "📱 bKash\n"
        "📱 Nagad\n"
        "💳 Bybit\n"
        "🪙 Binance\n\n"
        "⏳ Withdraw requests require admin approval."
    )


async def show_refund(query):

    await query.edit_message_text(
        "↩️ REFUND\n\n"
        "Select an order from My Orders to request a refund."
    )


async def show_support(query):

    await query.edit_message_text(
        "📞 SUPPORT\n\n"
        "Need help?\n"
        "Contact our support:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💬 Telegram Support",
                    url=SUPPORT
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data="back"
                )
            ]
        ])
    )


# =========================================================
# MAIN BUTTON ROUTER
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # ---------------- ADMIN ----------------

    if data == "admin":
        await show_admin_panel(query)
        return

    # ---------------- BASIC USER ----------------

    if data == "balance":
        await show_balance(query)
        return

    if data == "profile":
        await show_profile(query)
        return

    if data == "withdraw":
        await show_withdraw(query)
        return

    if data == "refund":
        await show_refund(query)
        return

    if data == "support":
        await show_support(query)
        return

    # ---------------- BACK ----------------

    if data == "back":

        await query.edit_message_text(
            "💳 BOT CARD\n\n"
            "👇 Select an option:",
            reply_markup=main_menu(
                query.from_user.id
            )
        )

        return

    # =====================================================
    # PART 2 + PART 3 WILL ADD THEIR BUTTONS HERE
    # =====================================================

    if data in (
        "buy",
        "deposit",
        "admin_add",
        "admin_products",
        "admin_remove",
        "admin_deposits",
        "admin_users",
    ):

        await query.edit_message_text(
            "⏳ Loading..."
        )

        return

    await query.edit_message_text(
        "❌ Unknown option."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("Starting BOT CARD...")

    setup_database()

    # Render health server
    Thread(
        target=start_web_server,
        daemon=True
    ).start()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    # Buttons
    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    print("BOT CARD is running...")

    app.run_polling()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
