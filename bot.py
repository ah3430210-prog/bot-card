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

TOKEN = os.environ["BOT_TOKEN"]

ADMIN_ID = 8502501681
RATE = 125
PORT = int(os.environ.get("PORT", "10000"))

BKASH = "01326630510"
NAGAD = "01326630510"
BYBIT_UID = "531771545"
BINANCE_UID = "780473636"

SUPPORT = "https://t.me/abirhasan6738"


# ================= DATABASE =================

def db():
    return sqlite3.connect("botcard.db")


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
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_id TEXT NOT NULL,
            screenshot_file_id TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register_user(user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users(user_id, balance) VALUES (?, 0)",
        (user_id,)
    )

    con.commit()
    con.close()


# ================= WEB SERVER =================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BOT CARD IS LIVE")

    def log_message(self, *args):
        pass


def start_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# ================= MAIN MENU =================

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


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    register_user(update.effective_user.id)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "✨ Welcome to BOT CARD!\n\n"
        "━━━━━━━━━━━━━━\n"
        f"💱 Rate: 1 USD = {RATE} BDT\n"
        "━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option:",
        reply_markup=main_menu(update.effective_user.id)
    )


# ================= ADMIN =================

async def admin_command(update, context):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔐 Open Admin Panel",
                callback_data="admin"
            )]
        ])
    )


async def show_admin(query):

    if query.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Product", callback_data="admin_add")],
        [InlineKeyboardButton("🗑️ Remove Product", callback_data="admin_remove")],
        [InlineKeyboardButton("📦 Product List", callback_data="admin_products")],
        [InlineKeyboardButton("💵 Deposit Requests", callback_data="admin_deposits")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")],
    ]

    await query.edit_message_text(
        "🔐 ADMIN PANEL\n\n"
        "━━━━━━━━━━━━━━\n"
        "⚙️ Control Center\n"
        "━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= ADD PRODUCT =================

async def start_add_product(query, context):

    if query.from_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["product_step"] = "name"

    await query.edit_message_text(
        "➕ ADD PRODUCT\n\n"
        "Step 1/4\n\n"
        "📦 Send Product Name:"
    )


async def receive_admin_text(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    step = context.user_data.get("product_step")

    if not step:
        return

    text = update.message.text.strip()

    if step == "name":

        context.user_data["product_name"] = text
        context.user_data["product_step"] = "details"

        await update.message.reply_text(
            "📝 Step 2/4\n\n"
            "Send Product Details:"
        )

    elif step == "details":

        context.user_data["product_details"] = text
        context.user_data["product_step"] = "price"

        await update.message.reply_text(
            "💵 Step 3/4\n\n"
            "Send Price in USD:\n\n"
            "Example: 5"
        )

    elif step == "price":

        try:
            price = float(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid price.")
            return

        if price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0.")
            return

        context.user_data["product_price"] = price
        context.user_data["product_step"] = "stock"

        await update.message.reply_text(
            "📊 Step 4/4\n\n"
            "Send Stock:\n\n"
            "Example: 10"
        )

    elif step == "stock":

        try:
            stock = int(text)
        except ValueError:
            await update.message.reply_text("❌ Stock must be a whole number.")
            return

        if stock < 0:
            await update.message.reply_text("❌ Invalid stock.")
            return

        name = context.user_data["product_name"]
        details = context.user_data["product_details"]
        price = context.user_data["product_price"]

        con = db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO products(name, details, price, stock)
            VALUES (?, ?, ?, ?)
        """, (name, details, price, stock))

        product_id = cur.lastrowid

        con.commit()
        con.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ PRODUCT ADDED\n\n"
            f"🆔 ID: #{product_id}\n"
            f"📦 {name}\n"
            f"📝 {details}\n"
            f"💵 ${price:.2f}\n"
            f"🇧🇩 ৳{price * RATE:.2f}\n"
            f"📊 Stock: {stock}"
        )


# ================= PRODUCT LIST =================

async def product_list(query):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name, price, stock
        FROM products
        WHERE stock > 0
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "📦 PRODUCTS\n\n❌ No products available."
        )
        return

    keyboard = []

    for pid, name, price, stock in rows:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {name} — ${price:.2f}",
                callback_data=f"product_{pid}"
            )
        ])

    await query.edit_message_text(
        "💳 AVAILABLE PRODUCTS\n\n"
        "👇 Select a product:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def product_details(query, pid):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT name, details, price, stock
        FROM products
        WHERE id = ?
    """, (pid,))

    row = cur.fetchone()
    con.close()

    if not row:
        await query.edit_message_text("❌ Product not found.")
        return

    name, details, price, stock = row

    await query.edit_message_text(
        f"📦 {name}\n\n"
        f"📝 Details:\n{details}\n\n"
        f"💵 Price: ${price:.2f}\n"
        f"🇧🇩 ৳{price * RATE:.2f}\n"
        f"📊 Stock: {stock}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🛒 Buy",
                callback_data=f"buy_{pid}"
            )],
            [InlineKeyboardButton(
                "🔙 Products",
                callback_data="buy"
            )]
        ])
    )


# ================= BUY =================

async def buy_product(query, pid):

    user_id = query.from_user.id
    register_user(user_id)

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT name, price, stock
        FROM products
        WHERE id = ?
    """, (pid,))

    row = cur.fetchone()

    if not row:
        con.close()
        await query.edit_message_text("❌ Product not found.")
        return

    name, price, stock = row

    if stock <= 0:
        con.close()
        await query.edit_message_text("❌ Out of stock.")
        return

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )

    balance = cur.fetchone()[0]

    if balance < price:
        con.close()
        await query.edit_message_text(
            "❌ INSUFFICIENT BALANCE\n\n"
            f"💵 Price: ${price:.2f}\n"
            f"💰 Balance: ${balance:.2f}"
        )
        return

    cur.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (price, user_id)
    )

    cur.execute(
        "UPDATE products SET stock = stock - 1 WHERE id = ?",
        (pid,)
    )

    cur.execute("""
        INSERT INTO orders(user_id, product_id, price, status)
        VALUES (?, ?, ?, 'Pending')
    """, (user_id, pid, price))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    await query.edit_message_text(
        "📦 ORDER CREATED\n\n"
        f"🆔 #{order_id}\n"
        f"📦 {name}\n"
        f"💵 ${price:.2f}\n\n"
        "⏳ Waiting for admin approval."
    )


# ================= DEPOSIT =================

async def deposit_menu(query):

    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="dep_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="dep_nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="dep_bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="dep_binance")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")],
    ]

    await query.edit_message_text(
        "💵 DEPOSIT\n\n"
        "Choose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def select_deposit_method(query, context, method):

    context.user_data.clear()
    context.user_data["deposit_method"] = method
    context.user_data["deposit_step"] = "amount"

    if method == "bKash":
        payment = f"📱 bKash: {BKASH}"
    elif method == "Nagad":
        payment = f"📱 Nagad: {NAGAD}"
    elif method == "Bybit":
        payment = f"💳 Bybit UID: {BYBIT_UID}"
    else:
        payment = f"🪙 Binance UID: {BINANCE_UID}"

    await query.edit_message_text(
        f"💵 DEPOSIT — {method}\n\n"
        f"{payment}\n\n"
        "━━━━━━━━━━━━━━\n"
        "💰 Send the amount in USD.\n\n"
        "Example: 10"
    )


async def receive_deposit(update, context):

    step = context.user_data.get("deposit_step")

    if not step:
        return

    text = update.message.text.strip()

    if step == "amount":

        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text(
                "❌ Enter a valid USD amount."
            )
            return

        if amount <= 0:
            await update.message.reply_text(
                "❌ Amount must be greater than 0."
            )
            return

        context.user_data["amount"] = amount
        context.user_data["deposit_step"] = "transaction"

        await update.message.reply_text(
            "🧾 TRANSACTION ID\n\n"
            "Send your transaction ID:"
        )

    elif step == "transaction":

        if len(text) < 3:
            await update.message.reply_text(
                "❌ Invalid transaction ID."
            )
            return

        context.user_data["transaction_id"] = text
        context.user_data["deposit_step"] = "screenshot"

        await update.message.reply_text(
            "📸 SCREENSHOT\n\n"
            "Now send your payment screenshot."
        )


async def receive_screenshot(update, context):

    if context.user_data.get("deposit_step") != "screenshot":
        return

    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send a payment screenshot."
        )
        return

    user_id = update.effective_user.id
    method = context.user_data["deposit_method"]
    amount = context.user_data["amount"]
    transaction_id = context.user_data["transaction_id"]
    file_id = update.message.photo[-1].file_id

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO deposits(
            user_id,
            method,
            amount,
            transaction_id,
            screenshot_file_id
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        method,
        amount,
        transaction_id,
        file_id
    ))

    deposit_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ DEPOSIT REQUEST SENT\n\n"
        f"🆔 Request: #{deposit_id}\n"
        f"💰 Amount: ${amount:.2f}\n"
        f"📱 Method: {method}\n\n"
        "⏳ Waiting for admin approval."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"depapprove_{deposit_id}"
            ),
            InlineKeyboardButton(
                "❌ Decline",
                callback_data=f"depdecline_{deposit_id}"
            )
        ]
    ])

    await context.bot.send_photo(
        ADMIN_ID,
        file_id,
        caption=(
            "💵 NEW DEPOSIT REQUEST\n\n"
            f"🆔 #{deposit_id}\n"
            f"👤 User: {user_id}\n"
            f"📱 Method: {method}\n"
            f"💰 Amount: ${amount:.2f}\n"
            f"🧾 Transaction ID: {transaction_id}"
        ),
        reply_markup=keyboard
    )


# ================= DEPOSIT APPROVE =================

async def approve_deposit(query, deposit_id):

    if query.from_user.id != ADMIN_ID:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, status
        FROM deposits
        WHERE id = ?
    """, (deposit_id,))

    row = cur.fetchone()

    if not row:
        con.close()
        return

    user_id, amount, status = row

    if status != "Pending":
        con.close()
        await query.answer(
            f"Already {status}",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE deposits
        SET status = 'Approved'
        WHERE id = ?
    """, (deposit_id,))

    cur.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
    """, (amount, user_id))

    con.commit()
    con.close()

    await query.edit_message_caption(
        caption=(
            "✅ DEPOSIT APPROVED\n\n"
            f"🆔 #{deposit_id}\n"
            f"💰 Added: ${amount:.2f}\n"
            f"👤 User: {user_id}"
        )
    )

    await query.bot.send_message(
        user_id,
        "✅ DEPOSIT APPROVED\n\n"
        f"💰 Added: ${amount:.2f}\n"
        "Your balance has been updated."
    )


# ================= DEPOSIT DECLINE =================

async def decline_deposit(query, deposit_id):

    if query.from_user.id != ADMIN_ID:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, status
        FROM deposits
        WHERE id = ?
    """, (deposit_id,))

    row = cur.fetchone()

    if not row:
        con.close()
        return

    user_id, status = row

    if status != "Pending":
        con.close()
        await query.answer(
            f"Already {status}",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE deposits
        SET status = 'Declined'
        WHERE id = ?
    """, (deposit_id,))

    con.commit()
    con.close()

    await query.edit_message_caption(
        caption=f"❌ DEPOSIT DECLINED\n\nRequest #{deposit_id}"
    )

    await query.bot.send_message(
        user_id,
        "❌ DEPOSIT DECLINED\n\n"
        "Your deposit request was declined."
    )


# ================= ORDERS =================

async def my_orders(query):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT orders.id,
               products.name,
               orders.price,
               orders.status
        FROM orders
        JOIN products
        ON products.id = orders.product_id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
    """, (query.from_user.id,))

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "🧾 MY ORDERS\n\nNo orders found."
        )
        return

    text = "🧾 MY ORDERS\n\n"

    for oid, name, price, status in rows:
        text += (
            f"🆔 #{oid}\n"
            f"📦 {name}\n"
            f"💵 ${price:.2f}\n"
            f"📌 {status}\n\n"
        )

    await query.edit_message_text(text)


# ================= BUTTONS =================

async def buttons(update, context):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "admin":
        await show_admin(query)

    elif data == "admin_add":
        await start_add_product(query, context)

    elif data == "admin_products":
        await admin_product_list(query)

    elif data == "admin_remove":
        await remove_product_menu(query)

    elif data == "buy":
        await product_list(query)

    elif data.startswith("product_"):
        await product_details(query, int(data.split("_")[1]))

    elif data.startswith("buy_"):
        await buy_product(query, int(data.split("_")[1]))

    elif data == "deposit":
        await deposit_menu(query)

    elif data == "dep_bkash":
        await select_deposit_method(query, context, "bKash")

    elif data == "dep_nagad":
        await select_deposit_method(query, context, "Nagad")

    elif data == "dep_bybit":
        await select_deposit_method(query, context, "Bybit")

    elif data == "dep_binance":
        await select_deposit_method(query, context, "Binance")

    elif data.startswith("depapprove_"):
        await approve_deposit(query, int(data.split("_")[1]))

    elif data.startswith("depdecline_"):
        await decline_deposit(query, int(data.split("_")[1]))

    elif data == "balance":

        register_user(query.from_user.id)

        con = db()
        cur = con.cursor()

        cur.execute(
      
