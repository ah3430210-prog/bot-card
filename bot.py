import os
import time
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]

ADMIN_ID = 8502501681

RATE = 125

BKASH = "01326630510"
NAGAD = "01326630510"
BYBIT_UID = "531771545"
BINANCE_UID = "780473636"

SUPPORT_URL = "https://t.me/abirhasan6738"

DB_FILE = "botcard.db"

PORT = int(os.environ.get("PORT", "10000"))


def connect_db():
    return sqlite3.connect(DB_FILE)


def setup_database():
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            description TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            details TEXT DEFAULT '',
            expires_at REAL DEFAULT 0,
            refunded INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register_user(user):
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO users(user_id, username)
        VALUES (?, ?)
        """,
        (user.id, user.username or "")
    )

    con.commit()
    con.close()


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Buy Card", callback_data="products")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🧾 My Orders", callback_data="orders")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("↩️ Refund", callback_data="refund")],
        [InlineKeyboardButton("📞 Support", callback_data="support")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "Welcome to BOT CARD!\n"
        "👤 BY ABIR\n\n"
        f"💱 Rate: 1 USD = {RATE} BDT",
        reply_markup=main_menu()
    )


async def products(query):
    con = connect_db()
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
            "💳 BUY CARD\n\nNo products available."
        )
        return

    buttons = []

    for product_id, name, price, stock in rows:
        buttons.append([
            InlineKeyboardButton(
                f"💳 {name} - ${price:.2f}",
                callback_data=f"product_{product_id}"
            )
        ])

    await query.edit_message_text(
        "💳 AVAILABLE PRODUCTS\n\n"
        f"💱 1 USD = {RATE} BDT",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def product_details(query, product_id):
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT name, price, stock, description
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    row = cur.fetchone()
    con.close()

    if not row:
        await query.edit_message_text("❌ Product not found.")
        return

    name, price, stock, description = row

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 Order",
                callback_data=f"buy_{product_id}"
            )
        ]
    ])

    await query.edit_message_text(
        f"💳 {name}\n\n"
        f"💵 Price: ${price:.2f}\n"
        f"🇧🇩 Price: ৳{price * RATE:.2f}\n"
        f"📦 Stock: {stock}\n\n"
        f"{description}",
        reply_markup=keyboard
    )


async def create_order(query, product_id):
    con = connect_db()
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
        await query.edit_message_text("❌ Product not found.")
        return

    name, price, stock = product

    if stock <= 0:
        con.close()
        await query.edit_message_text("❌ Out of stock.")
        return

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (query.from_user.id,)
    )

    user = cur.fetchone()

    if not user:
        con.close()
        await query.edit_message_text("❌ User not found.")
        return

    balance = user[0]

    if balance < price:
        con.close()

        await query.edit_message_text(
            f"❌ Insufficient balance.\n\n"
            f"Price: ${price:.2f}\n"
            f"Balance: ${balance:.2f}"
        )
        return

    cur.execute(
        """
        UPDATE users
        SET balance = balance - ?
        WHERE user_id = ?
        """,
        (price, query.from_user.id)
    )

    cur.execute(
        """
        INSERT INTO orders(user_id, product_id, price)
        VALUES (?, ?, ?)
        """,
        (query.from_user.id, product_id, price)
    )

    order_id = cur.lastrowid

    con.commit()
    con.close()

    await query.edit_message_text(
        "📦 ORDER CREATED\n\n"
        f"Order ID: #{order_id}\n"
        f"Product: {name}\n"
        f"Price: ${price:.2f}\n\n"
        "⏳ Waiting for admin approval."
    )

    await query.bot.send_message(
        ADMIN_ID,
        "📦 NEW ORDER\n\n"
        f"Order ID: #{order_id}\n"
        f"User ID: {query.from_user.id}\n"
        f"Product: {name}\n"
        f"Price: ${price:.2f}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Approve",
                    callback_data=f"approve_{order_id}"
                ),
                InlineKeyboardButton(
                    "❌ Decline",
                    callback_data=f"decline_{order_id}"
                )
            ]
        ])
    )


async def deposit_menu(query):
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="dep_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="dep_nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="dep_bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="dep_binance")],
    ]

    await query.edit_message_text(
        "💵 DEPOSIT\n\nChoose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def deposit_method(query, method):
    if method == "bkash":
        text = (
            "📱 bKash\n\n"
            "Send Money to:\n"
            f"{BKASH}\n\n"
            "After payment, send your amount and transaction ID to admin."
        )

    elif method == "nagad":
        text = (
            "📱 Nagad\n\n"
            "Send Money to:\n"
            f"{NAGAD}\n\n"
            "After payment, send your amount and transaction ID to admin."
        )

    elif method == "bybit":
        text = (
            "💳 Bybit\n\n"
            "UID:\n"
            f"{BYBIT_UID}\n\n"
            "After payment, send your amount and transaction ID to admin."
        )

    else:
        text = (
            "🪙 Binance\n\n"
            "UID:\n"
            f"{BINANCE_UID}\n\n"
            "After payment, send your amount and transaction ID to admin."
        )

    await query.edit_message_text(text)


async def withdraw_menu(query):
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="wd_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="wd_nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="wd_bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="wd_binance")],
    ]

    await query.edit_message_text(
        "💸 WITHDRAW\n\nChoose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def withdraw_method(query, method):
    names = {
        "bkash": "bKash Number",
        "nagad": "Nagad Number",
        "bybit": "Bybit UID",
        "binance": "Binance UID"
    }

    await query.edit_message_text(
        f"💸 {method.title()} Withdraw\n\n"
        f"Send your {names[method]} and amount.\n\n"
        "⏳ Admin will review your request."
    )


async def show_balance(query):
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (query.from_user.id,)
    )

    row = cur.fetchone()
    con.close()

    balance = row[0] if row else 0

    await query.edit_message_text(
        "💰 MY BALANCE\n\n"
        f"USD: ${balance:.2f}\n"
        f"BDT: ৳{balance * RATE:.2f}"
    )


async def show_orders(query):
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT orders.id, products.name, orders.price,
               orders.status, orders.expires_at
        FROM orders
        JOIN products ON products.id = orders.product_id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
        """,
        (query.from_user.id,)
    )

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "🧾 MY ORDERS\n\nNo orders found."
        )
        return

    text = "🧾 MY ORDERS\n\n"

    for order_id, name, price, status, expires_at in rows:

        if status == "Approved":
            remaining = int(expires_at - time.time())

            if remaining <= 0:
                status = "Expired"
            else:
                minutes = remaining // 60
                seconds = remaining % 60
                status = f"Active {minutes:02d}:{seconds:02d}"

        text += (
            f"#{order_id} - {name}\n"
            f"Price: ${price:.2f}\n"
            f"Status: {status}\n\n"
        )

    await query.edit_message_text(text)


async def refund_menu(query):
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT id, price, status
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (query.from_user.id,)
    )

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "↩️ REFUND\n\nNo orders found."
        )
        return

    buttons = []

    for order_id, price, status in rows:
        buttons.append([
            InlineKeyboardButton(
                f"Order #{order_id} - ${price:.2f}",
                callback_data=f"refund_{order_id}"
            )
        ])

    await query.edit_message_text(
        "↩️ SELECT ORDER FOR REFUND:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def request_refund(query, order_id):
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        SELECT price, refunded
        FROM orders
        WHERE id = ? AND user_id = ?
        """,
        (order_id, query.from_user.id)
    )

    row = cur.fetchone()

    if not row:
        con.close()
        await query.edit_message_text("❌ Order not found.")
        return

    amount, refunded = row

    if refunded:
        con.close()
        await query.edit_message_text(
            "❌ This order was already refunded."
        )
        return

    cur.execute(
        """
        SELECT id
        FROM refunds
        WHERE order_id = ? AND status = 'Pending'
        """,
        (order_id,)
    )

    if cur.fetchone():
        con.close()
        await query.edit_message_text(
            "⏳ Refund request already pending."
        )
        return

    cur.execute(
        """
        INSERT INTO refunds(order_id, user_id, amount)
        VALUES (?, ?, ?)
        """,
        (order_id, query.from_user.id, amount)
    )

    con.commit()
    con.close()

    await query.edit_message_text(
        "↩️ REFUND REQUEST SENT\n\n"
        f"Order ID: #{order_id}\n"
        f"Amount: ${amount:.2f}\n\n"
        "⏳ Waiting for admin."
    )

    await query.bot.send_message(
        ADMIN_ID,
        "↩️ REFUND REQUEST\n\n"
        f"Order ID: #{order_id}\n"
        f"User ID: {query.from_user.id}\n"
        f"Amount: ${amount:.2f}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Accept",
                    callback_data=f"raccept_{order_id}"
                ),
                InlineKeyboardButton(
                    "❌ Decline",
                    callback_data=f"rdecline_{order_id}"
                )
            ]
        ])
    )


async def approve_order(query, context, order_id):
    if query.from_user.id != ADMIN_ID:
        return

    context.user_data["approve_order"] = order_id

    await query.edit_message_text(
        f"✅ Order #{order_id}\n\n"
        "Send the product details/custom text now."
    )


async def admin_message(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if "approve_order" not in context.user_data:
        return

    order_id = context.user_data.pop("approve_order")
    details = update.message.text

    expires_at = time.time() + 900

    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        UPDATE orders
        SET status = 'Approved',
            details = ?,
            expires_at = ?
        WHERE id = ?
        """,
        (details, expires_at, order_id)
    )

    cur.execute(
        "SELECT user_id FROM orders WHERE id = ?",
        (order_id,)
    )

    row = cur.fetchone()

    con.commit()
    con.close()

    if row:
        user_id = row[0]

        await update.bot.send_message(
            user_id,
            "✅ ORDER APPROVED\n\n"
            f"Order ID: #{order_id}\n\n"
            "📦 PRODUCT DETAILS\n"
            f"{details}\n\n"
            "⏱️ TIME: 15 MINUTES"
        )

    await update.message.reply_text(
        f"✅ Order #{order_id} approved.\n"
        "⏱️ 15-minute timer started."
    )


async def admin_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "/addproduct Name | Price | Stock | Description\n"
        "/removeproduct ID"
    )


async def add_product(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    data = update.message.text.replace(
        "/addproduct",
        "",
        1
    ).strip()

    parts = [x.strip() for x in data.split("|")]

    if len(parts) != 4:
        await update.message.reply_text(
            "Format:\n"
            "/addproduct Name | Price | Stock | Description"
        )
        return

    name = parts[0]

    try:
        price = float(parts[1])
        stock = int(parts[2])
    except ValueError:
        await update.message.reply_text(
            "❌ Price or stock is invalid."
        )
        return

    description = parts[3]

    con = connect_db()
    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO products(name, price, stock, description)
        VALUES (?, ?, ?, ?)
        """,
        (name, price, stock, description)
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        "✅ PRODUCT ADDED\n\n"
        f"Name: {name}\n"
        f"Price: ${price:.2f}\n"
        f"BDT: ৳{price * RATE:.2f}\n"
        f"Stock: {stock}"
    )


async def remove_product(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    data = update.message.text.replace(
        "/removeproduct",
        "",
        1
    ).strip()

    try:
        product_id = int(data)
    except ValueError:
        await update.message.reply_text(
            "Use: /removeproduct ID"
        )
        return

    con = connect_db()
    cur = con.cursor()

    cur.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    deleted = cur.rowcount

    con.commit()
    con.close()

    if deleted:
        await update.message.reply_text(
            "✅ Product removed."
        )
    else:
        await update.message.reply_text(
            "❌ Product not found."
        )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    register_user(query.from_user)

    if data == "products":
        await products(query)

    elif data.startswith("product_"):
        await product_details(
            query,
            int(data.split("_")[1])
        )

    elif data.startswith("buy_"):
        await create_order(
            query,
            int(data.split("_")[1])
        )

    elif data == "balance":
        await show_balance(query)

    elif data == "orders":
        await show_orders(query)

    elif data == "deposit":
        await deposit_menu(query)

    elif data.startswith("dep_"):
        await deposit_method(
            query,
            data.split("_")[1]
        )

    elif data == "withdraw":
        await withdraw_menu(query)

    elif data.startswith("wd_"):
        await withdraw_method(
            query,
            data.split("_")[1]
        )

    elif data == "refund":
        await refund_menu(query)

    elif data.startswith("refund_"):
        await request_refund(
            query,
            int(data.split("_")[1])
        )

    elif data == "support":
        await query.edit_message_text(
            "📞 SUPPORT",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💬 Telegram Support",
                        url=SUPPORT_URL
                    )
                ]
            ])
        )

    elif data == "profile":
        await query.edit_message_text(
            "👤 PROFILE\n\n"
            f"User ID: {query.from_user.id}\n"
            f"Username: @{query.from_user.username or 'N/A'}"
        )

    elif data.startswith("approve_"):
        await approve_order(
            query,
            context,
            int(data.split("_")[1])
        )

    elif data.startswith("decline_"):
        if query.from_user.id != ADMIN_ID:
            return

        order_id = int(data.split("_")[1])

        con = connect_db()
        cur = con.cursor()

        cur.execute(
            """
            UPDATE orders
            SET status = 'Declined'
            WHERE id = ?
            """,
            (order_id,)
        )

        con.commit()
        con.close()

        await query.edit_message_text(
            f"❌ Order #{order_id} declined."
        )

    elif data.startswith("raccept_"):
        await accept_refund(
            query,
            int(data.split("_")[1])
        )

    elif data.startswith("rdecline_"):
        await decline_refund(
            query,
            int(data.split("_")[1])
        )


async def accept_refund(query, order_id):
    if query.from_user.id !
