import os
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
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

DB = "botcard.db"


# =========================================================
# DATABASE
# =========================================================

def db():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def setup_database():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL UNIQUE,
            amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            amount REAL NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    con.commit()
    con.close()


def register_user(user_id):
    con = db()
    con.execute(
        "INSERT OR IGNORE INTO users(user_id, balance) VALUES(?, 0)",
        (user_id,),
    )
    con.commit()
    con.close()


def get_balance(user_id):
    register_user(user_id)

    con = db()
    row = con.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    con.close()

    return float(row["balance"])


# =========================================================
# HTTP HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"BOT CARD IS LIVE")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

    def log_message(self, *args):
        pass


def web_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# =========================================================
# KEYBOARDS
# =========================================================

def home_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton("💳 Buy Card", callback_data="products")],
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
            InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")
        ])

    return InlineKeyboardMarkup(buttons)


def back_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Product", callback_data="admin_add")],
        [InlineKeyboardButton("📦 Product List", callback_data="admin_products")],
        [InlineKeyboardButton("🗑️ Remove Product", callback_data="admin_remove")],
        [InlineKeyboardButton("💵 Deposit Requests", callback_data="admin_deposits")],
        [InlineKeyboardButton("🧾 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])


def cancel_keyboard(callback="home"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=callback)]
    ])


# =========================================================
# COMMON TEXT
# =========================================================

def home_text():
    return (
        "💳 BOT CARD\n\n"
        "✨ Welcome to BOT CARD!\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💱 Rate: 1 USD = {RATE} BDT\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option:"
    )


# =========================================================
# START / COMMANDS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id)
    context.user_data.clear()

    await update.message.reply_text(
        home_text(),
        reply_markup=home_keyboard(user_id),
    )


async def command_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_balance_message(update.effective_user.id, update.message)


async def command_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_orders(update.effective_user.id, update.message)


async def command_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_deposit_message(update.message)


async def command_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_withdraw_message(update.message)


async def command_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_profile_message(update.effective_user, update.message)


async def command_refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_refund_message(update.effective_user.id, update.message)


async def command_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    context.user_data.clear()

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Choose an option:",
        reply_markup=admin_keyboard(),
    )


# =========================================================
# HOME
# =========================================================

async def show_home_query(query):
    await query.edit_message_text(
        home_text(),
        reply_markup=home_keyboard(query.from_user.id),
    )


# =========================================================
# BALANCE
# =========================================================

async def show_balance_message(user_id, message):
    balance = get_balance(user_id)

    await message.reply_text(
        "💰 MY BALANCE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💵 USD: ${balance:.2f}\n"
        f"🇧🇩 BDT: ৳{balance * RATE:.2f}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=back_home(),
    )


async def balance_query(query):
    balance = get_balance(query.from_user.id)

    await query.edit_message_text(
        "💰 MY BALANCE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💵 USD: ${balance:.2f}\n"
        f"🇧🇩 BDT: ৳{balance * RATE:.2f}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=back_home(),
    )


# =========================================================
# PRODUCTS
# =========================================================

async def products_query(query):
    con = db()

    rows = con.execute("""
        SELECT id, name, price, stock
        FROM products
        WHERE stock > 0
        ORDER BY id DESC
    """).fetchall()

    con.close()

    if not rows:
        await query.edit_message_text(
            "📦 AVAILABLE PRODUCTS\n\n"
            "❌ No products available.",
            reply_markup=back_home(),
        )
        return

    buttons = []

    for row in rows:
        buttons.append([
            InlineKeyboardButton(
                f"📦 {row['name']} — ${row['price']:.2f}",
                callback_data=f"product:{row['id']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔙 Back", callback_data="home")
    ])

    await query.edit_message_text(
        "📦 AVAILABLE PRODUCTS\n\n"
        "👇 Select a product:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def product_details_query(query, product_id):
    try:
        product_id = int(product_id)
    except ValueError:
        await query.edit_message_text(
            "❌ Invalid product.",
            reply_markup=back_home(),
        )
        return

    con = db()

    row = con.execute("""
        SELECT id, name, details, price, stock
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    con.close()

    if row is None:
        await query.edit_message_text(
            "❌ Product not found.",
            reply_markup=back_home(),
        )
        return

    keyboard = [
        [InlineKeyboardButton(
            "🛒 Buy Now",
            callback_data=f"buy:{row['id']}",
        )],
        [InlineKeyboardButton(
            "🔙 Products",
            callback_data="products",
        )],
    ]

    await query.edit_message_text(
        "📦 PRODUCT DETAILS\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🏷️ Name: {row['name']}\n\n"
        f"📝 Details:\n{row['details']}\n\n"
        f"💵 Price: ${row['price']:.2f}\n"
        f"🇧🇩 Price: ৳{row['price'] * RATE:.2f}\n"
        f"📊 Stock: {row['stock']}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================================================
# BUY
# =========================================================

async def buy_product_query(query, product_id):
    try:
        product_id = int(product_id)
    except ValueError:
        await query.edit_message_text(
            "❌ Invalid product.",
            reply_markup=back_home(),
        )
        return

    user_id = query.from_user.id
    register_user(user_id)

    con = db()

    try:
        con.execute("BEGIN IMMEDIATE")

        product = con.execute("""
            SELECT id, name, price, stock
            FROM products
            WHERE id = ?
        """, (product_id,)).fetchone()

        if product is None:
            con.rollback()
            await query.edit_message_text(
                "❌ Product not found.",
                reply_markup=back_home(),
            )
            return

        if product["stock"] <= 0:
            con.rollback()
            await query.edit_message_text(
                "❌ Product is out of stock.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 Products",
                        callback_data="products",
                    )],
                    [InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="home",
                    )],
                ]),
            )
            return

        user = con.execute("""
            SELECT balance
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        balance = float(user["balance"])

        if balance < float(product["price"]):
            con.rollback()

            await query.edit_message_text(
                "❌ INSUFFICIENT BALANCE\n\n"
                "━━━━━━━━━━━━━━━━\n"
                f"📦 Product: {product['name']}\n"
                f"💵 Required: ${product['price']:.2f}\n"
                f"💰 Balance: ${balance:.2f}\n"
                "━━━━━━━━━━━━━━━━\n\n"
                "Please deposit first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "💵 Deposit",
                        callback_data="deposit",
                    )],
                    [InlineKeyboardButton(
                        "🔙 Products",
                        callback_data="products",
                    )],
                ]),
            )
            return

        con.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
        """, (float(product["price"]), user_id))

        con.execute("""
            UPDATE products
            SET stock = stock - 1
            WHERE id = ? AND stock > 0
        """, (product_id,))

        cur = con.execute("""
            INSERT INTO orders(
                user_id,
                product_id,
                price,
                status,
                created_at
            )
            VALUES(?, ?, ?, 'Pending', ?)
        """, (
            user_id,
            product_id,
            float(product["price"]),
            now(),
        ))

        order_id = cur.lastrowid

        con.commit()

    except Exception:
        con.rollback()

        await query.edit_message_text(
            "❌ Purchase failed. Please try again.",
            reply_markup=back_home(),
        )
        return

    finally:
        con.close()

    await query.edit_message_text(
        "✅ ORDER CREATED\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: #{order_id}\n"
        f"📦 Product: {product['name']}\n"
        f"💵 Price: ${product['price']:.2f}\n"
        "📌 Status: Pending\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=back_home(),
    )


# =========================================================
# ORDERS
# =========================================================

async def show_orders(user_id, message):
    con = db()

    rows = con.execute("""
        SELECT
            orders.id,
            products.name,
            orders.price,
            orders.status
        FROM orders
        JOIN products ON products.id = orders.product_id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
    """, (user_id,)).fetchall()

    con.close()

    if not rows:
        await message.reply_text(
            "🧾 MY ORDERS\n\n"
            "❌ No orders found.",
            reply_markup=back_home(),
        )
        return

    text = "🧾 MY ORDERS\n\n"

    for row in rows:
        text += (
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 #{row['id']}\n"
            f"📦 {row['name']}\n"
            f"💵 ${row['price']:.2f}\n"
            f"📌 {row['status']}\n"
        )

    await message.reply_text(
        text,
        reply_markup=back_home(),
    )


async def orders_query(query):
    user_id = query.from_user.id

    con = db()

    rows = con.execute("""
        SELECT
            orders.id,
            products.name,
            orders.price,
            orders.status
        FROM orders
        JOIN products ON products.id = orders.product_id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
    """, (user_id,)).fetchall()

    con.close()

    if not rows:
        await query.edit_message_text(
            "🧾 MY ORDERS\n\n"
            "❌ No orders found.",
            reply_markup=back_home(),
        )
        return

    text = "🧾 MY ORDERS\n\n"

    for row in rows:
        text += (
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 #{row['id']}\n"
            f"📦 {row['name']}\n"
            f"💵 ${row['price']:.2f}\n"
            f"📌 {row['status']}\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=back_home(),
    )


# =========================================================
# DEPOSIT
# =========================================================

def deposit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 bKash", callback_data="pay:bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="pay:nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="pay:bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="pay:binance")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])


async def show_deposit_message(message):
    await message.reply_text(
        "💵 DEPOSIT\n\n"
        "Select payment method:",
        reply_markup=deposit_keyboard(),
    )


async def deposit_query(query):
    await query.edit_message_text(
        "💵 DEPOSIT\n\n"
        "Select payment method:",
        reply_markup=deposit_keyboard(),
    )


async def payment_query(query, method):
    method = method.lower()

    if method == "bkash":
        title = "📱 bKash DEPOSIT"
        info = f"Send Money: {BKASH}"

    elif method == "nagad":
        title = "📱 Nagad DEPOSIT"
        info = f"Send Money: {NAGAD}"

    elif method == "bybit":
        title = "💳 Bybit DEPOSIT"
        info = f"UID: {BYBIT_UID}"

    elif method == "binance":
        title = "🪙 Binance DEPOSIT"
        info = f"UID: {BINANCE_UID}"

    else:
        await query.edit_message_text(
            "❌ Invalid payment method.",
            reply_markup=back_home(),
        )
        return

    query_text = (
        f"{title}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{info}\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "After sending payment, submit your amount and transaction ID."
    )

    keyboard = [
        [InlineKeyboardButton(
            "📝 Submit Deposit",
            callback_data=f"deposit_submit:{method}",
        )],
        [InlineKeyboardButton(
            "🔙 Deposit Methods",
            callback_data="deposit",
        )],
    ]

    await query.edit_message_text(
        query_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def start_deposit_submission(query, context, method):
    context.user_data.clear()
    context.user_data["deposit_method"] = method
    context.user_data["flow"] = "deposit_amount"

    await query.edit_message_text(
        "💵 DEPOSIT REQUEST\n\n"
        "Step 1/2\n\n"
        "💵 Enter amount in USD.\n\n"
        "Example: 10",
        reply_markup=cancel_keyboard("deposit"),
    )


# =========================================================
# WITHDRAW
# =========================================================

def withdraw_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButt
