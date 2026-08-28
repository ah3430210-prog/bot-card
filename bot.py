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

DB = "botcard.db"


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB)


def setup_database():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            details TEXT DEFAULT '',
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            price REAL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            method TEXT,
            amount REAL,
            trx TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register_user(user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users(user_id,balance) VALUES(?,0)",
        (user_id,)
    )

    con.commit()
    con.close()


# =========================================================
# RENDER WEB SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"BOT CARD IS LIVE")

    def log_message(self, *args):
        pass


def web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# =========================================================
# MAIN MENU
# =========================================================

def menu(user_id):

    buttons = [
        [InlineKeyboardButton("💳 Products", callback_data="products")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🧾 My Orders", callback_data="orders")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("📞 Support", callback_data="support")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
    ]

    if user_id == ADMIN_ID:
        buttons.append([
            InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")
        ])

    return InlineKeyboardMarkup(buttons)


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    register_user(user_id)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "✨ Welcome!\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💱 Rate: 1 USD = {RATE} BDT\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option:",
        reply_markup=menu(user_id)
    )


# =========================================================
# HOME
# =========================================================

async def home(query):

    await query.edit_message_text(
        "💳 BOT CARD\n\n"
        "👇 Choose an option:",
        reply_markup=menu(query.from_user.id)
    )


# =========================================================
# PRODUCTS
# =========================================================

async def products(query):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id,name,price,stock
        FROM products
        WHERE stock > 0
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "📦 PRODUCTS\n\n"
            "❌ No products available.",
            reply_markup=back_button()
        )
        return

    buttons = []

    for pid, name, price, stock in rows:
        buttons.append([
            InlineKeyboardButton(
                f"📦 {name} — ${price:.2f}",
                callback_data=f"product:{pid}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔙 Back", callback_data="home")
    ])

    await query.edit_message_text(
        "📦 AVAILABLE PRODUCTS\n\n"
        "👇 Select a product:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def product_details(query, pid):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT name,details,price,stock
        FROM products
        WHERE id=?
    """, (pid,))

    row = cur.fetchone()
    con.close()

    if not row:
        await query.edit_message_text(
            "❌ Product not found.",
            reply_markup=back_button()
        )
        return

    name, details, price, stock = row

    keyboard = [
        [InlineKeyboardButton(
            "🛒 Buy Now",
            callback_data=f"buy:{pid}"
        )],
        [InlineKeyboardButton(
            "🔙 Products",
            callback_data="products"
        )]
    ]

    await query.edit_message_text(
        "📦 PRODUCT DETAILS\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🏷️ Name: {name}\n\n"
        f"📝 Details:\n{details}\n\n"
        f"💵 Price: ${price:.2f}\n"
        f"🇧🇩 BDT: ৳{price * RATE:.2f}\n"
        f"📊 Stock: {stock}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# BUY
# =========================================================

async def buy(query, pid):

    user_id = query.from_user.id
    register_user(user_id)

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT name,price,stock
        FROM products
        WHERE id=?
    """, (pid,))

    product = cur.fetchone()

    if not product:
        con.close()
        await query.edit_message_text("❌ Product not found.")
        return

    name, price, stock = product

    if stock <= 0:
        con.close()
        await query.edit_message_text(
            "❌ Product is out of stock.",
            reply_markup=back_button()
        )
        return

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    balance = cur.fetchone()[0]

    if balance < price:
        con.close()

        await query.edit_message_text(
            "❌ INSUFFICIENT BALANCE\n\n"
            f"📦 Product: {name}\n"
            f"💵 Price: ${price:.2f}\n"
            f"💰 Balance: ${balance:.2f}\n\n"
            "Please deposit first.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💵 Deposit",
                    callback_data="deposit"
                )],
                [InlineKeyboardButton(
                    "🔙 Products",
                    callback_data="products"
                )]
            ])
        )
        return

    cur.execute("""
        UPDATE users
        SET balance=balance-?
        WHERE user_id=?
    """, (price, user_id))

    cur.execute("""
        UPDATE products
        SET stock=stock-1
        WHERE id=?
    """, (pid,))

    cur.execute("""
        INSERT INTO orders(user_id,product_id,price,status)
        VALUES(?,?,?,'Pending')
    """, (user_id, pid, price))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    await query.edit_message_text(
        "✅ ORDER CREATED\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: #{order_id}\n"
        f"📦 Product: {name}\n"
        f"💵 Price: ${price:.2f}\n"
        "📌 Status: Pending\n"
        "━━━━━━━━━━━━━━━━"
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(query):

    user_id = query.from_user.id
    register_user(user_id)

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    amount = cur.fetchone()[0]

    con.close()

    await query.edit_message_text(
        "💰 MY BALANCE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💵 USD: ${amount:.2f}\n"
        f"🇧🇩 BDT: ৳{amount * RATE:.2f}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=back_button()
    )


# =========================================================
# ORDERS
# =========================================================

async def orders(query):

    user_id = query.from_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT orders.id,products.name,
               orders.price,orders.status
        FROM orders
        JOIN products
        ON products.id=orders.product_id
        WHERE orders.user_id=?
        ORDER BY orders.id DESC
    """, (user_id,))

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "🧾 MY ORDERS\n\n"
            "❌ No orders found.",
            reply_markup=back_button()
        )
        return

    text = "🧾 MY ORDERS\n\n"

    for oid, name, price, status in rows:
        text += (
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 #{oid}\n"
            f"📦 {name}\n"
            f"💵 ${price:.2f}\n"
            f"📌 {status}\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=back_button()
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit(query):

    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="pay:bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="pay:nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="pay:bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="pay:binance")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ]

    await query.edit_message_text(
        "💵 DEPOSIT\n\n"
        "Select payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def payment(query, method):

    if method == "bkash":
        text = (
            "📱 bKash DEPOSIT\n\n"
            f"Send Money: {BKASH}\n\n"
            "After payment, send the transaction ID to support."
        )

    elif method == "nagad":
        text = (
            "📱 Nagad DEPOSIT\n\n"
            f"Send Money: {NAGAD}\n\n"
            "After payment, send the transaction ID to support."
        )

    elif method == "bybit":
        text = (
            "💳 Bybit DEPOSIT\n\n"
            f"UID: {BYBIT_UID}\n\n"
            "After payment, send the transaction ID to support."
        )

    else:
        text = (
            "🪙 Binance DEPOSIT\n\n"
            f"UID: {BINANCE_UID}\n\n"
            "After payment, send the transaction ID to support."
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📞 Support",
                url=SUPPORT
            )],
            [InlineKeyboardButton(
                "🔙 Back",
                callback_data="deposit"
            )]
        ])
    )


# =========================================================
# PROFILE / WITHDRAW / SUPPORT
# =========================================================

async def profile(query):

    user = query.from_user

    await query.edit_message_text(
        "👤 PROFILE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {user.id}\n"
        f"👤 Username: @{user.username or 'N/A'}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=back_button()
    )


async def withdraw(query):

    await query.edit_message_text(
        "💸 WITHDRAW\n\n"
        "Available methods:\n\n"
        "📱 bKash\n"
        "📱 Nagad\n"
        "💳 Bybit\n"
        "🪙 Binance\n\n"
        "⏳ Contact support for withdrawal requests.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📞 Support",
                url=SUPPORT
            )],
            [InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )]
        ])
    )


async def support(query):

    await query.edit_message_text(
        "📞 SUPPORT\n\n"
        "Need help? Contact us below:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "💬 Telegram Support",
                url=SUPPORT
            )],
            [InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )]
        ])
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(query):

    if query.from_user.id != ADMIN_ID:
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
            "📦 Product List",
            callback_data="admin_products"
        )],
        [InlineKeyboardButton(
            "🗑️ Remove Product",
            callback_data="admin_remove"
        )],
        [InlineKeyboardButton(
            "💵 Deposit Requests",
            callback_data="admin_deposits"
        )],
        [InlineKeyboardButton(
            "👥 Users",
            callback_data="admin_users"
        )],
        [InlineKeyboardButton(
            "🔙 Back",
            callback_data="home"
        )],
    ]

    await query.edit_message_text(
        "🔐 ADMIN PANEL\n\n"
        "Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# ADMIN ADD PRODUCT
# =========================================================

async def admin_add(query, context):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    context.user_data.clear()
    context.user_data["add_step"] = "name"

    await query.edit_message_text(
        "➕ ADD PRODUCT\n\n"
        "Step 1/4\n\n"
        "Send product name:"
    )


async def receive_admin_text(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    step = context.user_data.get("add_step")

    if not step:
        return

    value = update.message.text.strip()

    if step == "name":

        context.user_data["name"] = value
        context.user_data["add_step"] = "details"

        await update.message.reply_text(
            "📝 Step 2/4\n\n"
            "Send product details:"
        )

    elif step == "details":

        context.user_data["details"] = value
        context.user_data["add_step"] = "price"

        await update.message.reply_text(
            "💵 Step 3/4\n\n"
            "Send price in USD:\n\n"
            "Example: 5"
        )

    elif step == "price":

        try:
            price = float(value)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid price. Example: 5"
            )
            return

        if price <= 0:
            await update.message.reply_text(
                "❌ Price must be greater than 0."
            )
            return

        context.user_data["price"] = price
        context.user_data["add_step"] = "stock"

        await update.message.reply_text(
            "📊 Step 4/4\n\n"
            "Send stock number:\n\n"
            "Example: 10"
        )

    elif step == "stock":

        try:
            stock = int(value)
        except ValueError:
            await update.message.reply_text(
                "❌ Stock must be a whole number."
            )
            return

        if stock < 0:
            await update.message.reply_text(
                "❌ Stock cannot be negative."
            )
            return

        name = context.user_data["name"]
        details = context.user_data["details"]
        price = context.user_data["price"]

        con = db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO products(name,details,price,stock)
            VALUES(?,?,?,?)
        """, (name, details, price, stock))

        pid = cur.lastrowid

        con.commit()
        con.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ PRODUCT ADDED\n\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: #{pid}\n"
            f"📦 {name}\n"
            f"📝 {details}\n"
            f"💵 ${price:.2f}\n"
            f"🇧🇩 ৳{price * RATE:.2f}\n"
            f"📊 Stock: {stock}\n"
            "━━━━━━━━━━━━━━━━"
        )


# =========================================================
# ADMIN PRODUCT LIST
# =========================================================

async def admin_products(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id,name,details,price,stock
        FROM products
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "📦 PRODUCT LIST\n\n"
            "❌ No products.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 Admin",
                    callback_data="admin"
                )]
            ])
        )
        return

    text = "📦 PRODUCT LIST\n\n"

    for pid, name, details, price, stock in rows:
        text += (
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 #{pid}\n"
            f"📦 {name}\n"
            f"📝 {details}\n"
            f"💵 ${price:.2f}\n"
            f"📊 Stock: {stock}\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔙 Admin",
                callback_data="admin"
            )]
        ])
    )


# =========================================================
# ADMIN REMOVE
# =========================================================

async def admin_remove(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT id,name FROM products ORDER BY id DESC"
    )

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "🗑️ No products found.",
            reply_markup=back_bu
