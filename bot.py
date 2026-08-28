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


# =========================================================
# PART 2/3 — PRODUCT SYSTEM
# =========================================================

async def start_add_product(query, context):

    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Access denied!", show_alert=True)
        return

    context.user_data.clear()
    context.user_data["product_step"] = "name"

    await query.edit_message_text(
        "➕ ADD PRODUCT\n\n"
        "Step 1/4\n\n"
        "📦 Send Product Name:"
    )


async def receive_product_text(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    step = context.user_data.get("product_step")

    if not step:
        return

    text = update.message.text.strip()

    if step == "name":

        if not text:
            await update.message.reply_text(
                "❌ Product name cannot be empty."
            )
            return

        context.user_data["product_name"] = text
        context.user_data["product_step"] = "details"

        await update.message.reply_text(
            "📝 Step 2/4\n\n"
            "Send Product Details.\n\n"
            "Example:\n"
            "Premium Plan - 1 Year"
        )

    elif step == "details":

        context.user_data["product_details"] = text
        context.user_data["product_step"] = "price"

        await update.message.reply_text(
            "💵 Step 3/4\n\n"
            "Send Product Price in USD.\n\n"
            "Example:\n"
            "5"
        )

    elif step == "price":

        try:
            price = float(text)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid price.\n\n"
                "Example: 5"
            )
            return

        if price <= 0:
            await update.message.reply_text(
                "❌ Price must be greater than 0."
            )
            return

        context.user_data["product_price"] = price
        context.user_data["product_step"] = "stock"

        await update.message.reply_text(
            "📊 Step 4/4\n\n"
            "Send Product Stock.\n\n"
            "Example:\n"
            "10"
        )

    elif step == "stock":

        try:
            stock = int(text)
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

        name = context.user_data["product_name"]
        details = context.user_data["product_details"]
        price = context.user_data["product_price"]

        con = get_db()
        cur = con.cursor()

        cur.execute(
            """
            INSERT INTO products
            (name, details, price, stock)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                details,
                price,
                stock
            )
        )

        product_id = cur.lastrowid

        con.commit()
        con.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ PRODUCT ADDED SUCCESSFULLY\n\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 Product ID: #{product_id}\n"
            f"📦 Name: {name}\n"
            f"📝 Details: {details}\n"
            f"💵 Price: ${price:.2f}\n"
            f"🇧🇩 BDT: ৳{price * RATE:.2f}\n"
            f"📊 Stock: {stock}\n"
            "━━━━━━━━━━━━━━━━"
        )


# =========================================================
# PRODUCT LIST FOR USERS
# =========================================================

async def show_products(query):

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT id, name, price, stock
        FROM products
        WHERE stock > 0
        ORDER BY id DESC
        """
    )

    products = cur.fetchall()

    con.close()

    if not products:

        await query.edit_message_text(
            "💳 PRODUCTS\n\n"
            "❌ No products available right now.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="back"
                    )
                ]
            ])
        )

        return

    keyboard = []

    for product_id, name, price, stock in products:

        keyboard.append([
            InlineKeyboardButton(
                f"📦 {name} | ${price:.2f}",
                callback_data=f"product_{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back",
            callback_data="back"
        )
    ])

    await query.edit_message_text(
        "💳 AVAILABLE PRODUCTS\n\n"
        "👇 Select a product:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# PRODUCT DETAILS
# =========================================================

async def show_product_details(query, product_id):

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT name, details, price, stock
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    product = cur.fetchone()

    con.close()

    if not product:

        await query.edit_message_text(
            "❌ Product not found."
        )

        return

    name, details, price, stock = product

    await query.edit_message_text(
        "📦 PRODUCT DETAILS\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🏷️ Name: {name}\n\n"
        f"📝 Details:\n{details}\n\n"
        f"💵 Price: ${price:.2f}\n"
        f"🇧🇩 Price: ৳{price * RATE:.2f}\n"
        f"📊 Stock: {stock}\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🛒 Buy Now",
                    callback_data=f"buy_{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Products",
                    callback_data="buy"
                )
            ]
        ])
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

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT id, name, details, price, stock
        FROM products
        ORDER BY id DESC
        """
    )

    products = cur.fetchall()

    con.close()

    if not products:

        await query.edit_message_text(
            "📦 PRODUCT LIST\n\n"
            "❌ No products found.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

        return

    text = "📦 PRODUCT LIST\n\n"

    for product_id, name, details, price, stock in products:

        text += (
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: #{product_id}\n"
            f"📦 {name}\n"
            f"📝 {details}\n"
            f"💵 ${price:.2f}\n"
            f"📊 Stock: {stock}\n"
        )

    text += "━━━━━━━━━━━━━━━━"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Admin Panel",
                    callback_data="admin"
                )
            ]
        ])
    )


# =========================================================
# REMOVE PRODUCT MENU
# =========================================================

async def remove_product_menu(query):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT id, name
        FROM products
        ORDER BY id DESC
        """
    )

    products = cur.fetchall()

    con.close()

    if not products:

        await query.edit_message_text(
            "🗑️ REMOVE PRODUCT\n\n"
            "❌ No products found."
        )

        return

    keyboard = []

    for product_id, name in products:

        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {name}",
                callback_data=f"remove_{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Admin Panel",
            callback_data="admin"
        )
    ])

    await query.edit_message_text(
        "🗑️ REMOVE PRODUCT\n\n"
        "Select a product:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# REMOVE PRODUCT
# =========================================================

async def remove_product(query, product_id):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT name FROM products WHERE id = ?",
        (product_id,)
    )

    product = cur.fetchone()

    if not product:

        con.close()

        await query.edit_message_text(
            "❌ Product not found."
        )

        return

    name = product[0]

    cur.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    con.commit()
    con.close()

    await query.edit_message_text(
        "✅ PRODUCT REMOVED\n\n"
        f"📦 {name}\n"
        f"🆔 #{product_id}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Admin Panel",
                    callback_data="admin"
                )
            ]
        ])
    )


# =========================================================
# BUY PRODUCT
# =========================================================

async def buy_product(query, product_id):

    user_id = query.from_user.id

    register_user(user_id)

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT name, price, stock
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    product = cur.fetchone()

    if not product:

        con.close()

        await query.edit_message_text(
            "❌ Product not found."
        )

        return

    name, price, stock = product

    if stock <= 0:

        con.close()

        await query.edit_message_text(
            "❌ This product is out of stock."
        )

        return

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cur.fetchone()

    balance = row[0] if row else 0

    if balance < price:

        con.close()

        await query.edit_message_text(
            "❌ INSUFFICIENT BALANCE\n\n"
            f"📦 Product: {name}\n"
            f"💵 Price: ${price:.2f}\n"
            f"💰 Your Balance: ${balance:.2f}\n\n"
            "💵 Please deposit first.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💵 Deposit",
                        callback_data="deposit"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Products",
                        callback_data="buy"
                    )
                ]
            ])
        )

        return

    cur.execute(
        """
        UPDATE users
        SET balance = balance - ?
        WHERE user_id = ?
        """,
        (price, user_id)
    )

    cur.execute(
        """
        UPDATE products
        SET stock = stock - 1
        WHERE id = ?
        """,
        (product_id,)
    )

    cur.execute(
        """
        INSERT INTO orders
        (user_id, product_id, price, status)
        VALUES (?, ?, ?, 'Pending')
        """,
        (
            user_id,
            product_id,
            price
        )
    )

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
        "━━━━━━━━━━━━━━━━\n\n"
        "⏳ Waiting for admin approval."
    )


# =========================================================
# MY ORDERS
# =========================================================

async def show_orders(query):

    user_id = query.from_user.id

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT
            orders.id,
            products.name,
            orders.price,
            orders.status
        FROM orders
        JOIN products
        ON products.id = orders.product_id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
        """,
        (user_id,)
    )

    orders = cur.fetchall()

    con.close()

    if not orders:

        await query.edit_message_text(
            "🧾 MY ORDERS\n\n"
            "❌ No orders found.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="back"
                    )
                ]
            ])
        )

        return

    text = "🧾 MY ORDERS\n\n"

    for order_id, name, price, status in orders:

        text += (
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 Order: #{order_id}\n"
            f"📦 {name}\n"
            f"💵 ${price:.2f}\n"
            f"📌 Status: {status}\n"
        )

    await query.edit_message_text(text)


# =========================================================
# PART 2 BUTTON ROUTES
# =========================================================

async def product_button_router(query, context):

    data = query.data

    if data == "buy":
        await show_products(query)
        return True

    if data.startswith("product_"):

        product_id = int(
            data.split("_", 1)[1]
        )

        await show_product_details(
            query,
            product_id
        )

        return True

    if data.startswith("buy_"):

        product_id = int(
            data.split("_", 1)[1]
        )

        await buy_product(
            query,
            product_id
        )

        return True

    if data == "orders":

        await show_orders(query)
        return True

    if data == "admin_add":

        await start_add_product(
            query,
            context
        )

        return True

    if data == "admin_products":

        await admin_products(query)
        return True

    if data == "admin_remove":

        await remove_product_menu(query)
        return True

    if data.startswith("remove_"):

        product_id = int(
            data.split("_", 1)[1]
        )

        await remove_product(
            query,
            product_id
        )

        return True

    return False
