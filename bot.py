import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
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
PORT = int(os.environ.get("PORT", 10000))

BKASH = "01326630510"
NAGAD = "01326630510"
BYBIT_UID = "531771545"
BINANCE_UID = "780473636"

SUPPORT = "https://t.me/abirhasan6738"

DB = "botcard.db"


# =========================
# DATABASE
# =========================

def db():
    return sqlite3.connect(DB)


def setup():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            stock INTEGER,
            description TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            price REAL,
            status TEXT DEFAULT 'Pending',
            details TEXT DEFAULT '',
            approved_at REAL DEFAULT 0,
            expires_at REAL DEFAULT 0,
            refunded INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            trx TEXT,
            screenshot TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            account TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS refunds(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register(user):
    con = db()
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users(user_id,username) VALUES(?,?)",
        (user.id, user.username or "")
    )

    cur.execute(
        "UPDATE users SET username=? WHERE user_id=?",
        (user.username or "", user.id)
    )

    con.commit()
    con.close()


# =========================
# RENDER WEB SERVER
# =========================

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BOT CARD is live")

    def log_message(self, *args):
        pass


def web_server():
    HTTPServer(
        ("0.0.0.0", PORT),
        Handler
    ).serve_forever()


# =========================
# MAIN MENU
# =========================

def menu():

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


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    register(update.effective_user)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "Welcome to BOT CARD!\n"
        "👤 BY ABIR\n\n"
        f"💱 Rate: 1 USD = {RATE} BDT",
        reply_markup=menu()
    )


# =========================
# PRODUCTS
# =========================

async def show_products(query):

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
            "💳 BUY CARD\n\nNo products available."
        )
        return

    keyboard = []

    for pid, name, price, stock in rows:

        keyboard.append([
            InlineKeyboardButton(
                f"💳 {name} — ${price:.2f}",
                callback_data=f"view_{pid}"
            )
        ])

    await query.edit_message_text(
        f"💳 AVAILABLE PRODUCTS\n\n"
        f"💱 1 USD = {RATE} BDT",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ORDER
# =========================

async def create_order(query, product_id):

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT name,price,stock FROM products WHERE id=?",
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
        """
        SELECT balance FROM users WHERE user_id=?
        """,
        (query.from_user.id,)
    )

    balance = cur.fetchone()[0]

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
        SET balance=balance-?
        WHERE user_id=?
        """,
        (price, query.from_user.id)
    )

    cur.execute(
        """
        INSERT INTO orders(user_id,product_id,price)
        VALUES(?,?,?)
        """,
        (query.from_user.id, product_id, price)
    )

    order_id = cur.lastrowid

    con.commit()
    con.close()

    await query.edit_message_text(
        "✅ ORDER CREATED\n\n"
        f"Order ID: #{order_id}\n"
        f"Product: {name}\n"
        f"Price: ${price:.2f}\n\n"
        "⏳ Waiting for admin approval."
    )

    try:
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
    except Exception:
        pass


# =========================
# DEPOSIT
# =========================

async def deposit_menu(query):

    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="dep_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="dep_nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="dep_bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="dep_binance")],
    ]

    await query.edit_message_text(
        "💵 DEPOSIT\n\n"
        "Choose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def deposit_method(query, method):

    if method == "bkash":
        text = (
            "📱 bKash Deposit\n\n"
            "Send Money to:\n"
            f"`{BKASH}`\n\n"
            "তারপর /deposit_request command ব্যবহার করো।"
        )

    elif method == "nagad":
        text = (
            "📱 Nagad Deposit\n\n"
            "Send Money to:\n"
            f"`{NAGAD}`\n\n"
            "তারপর /deposit_request command ব্যবহার করো।"
        )

    elif method == "bybit":
        text = (
            "💳 Bybit Deposit\n\n"
            "UID:\n"
            f"`{BYBIT_UID}`\n\n"
            "তারপর /deposit_request command ব্যবহার করো।"
        )

    else:
        text = (
            "🪙 Binance Deposit\n\n"
            "UID:\n"
            f"`{BINANCE_UID}`\n\n"
            "তারপর /deposit_request command ব্যবহার করো।"
        )

    await query.edit_message_text(text)


# =========================
# WITHDRAW
# =========================

async def withdraw_menu(query):

    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="wd_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="wd_nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="wd_bybit")],
        [InlineKeyboardButton("🪙 Binance", callback_data="wd_binance")],
    ]

    await query.edit_message_text(
        "💸 WITHDRAW\n\n"
        "Choose payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def withdraw_method(query, method):

    labels = {
        "bkash": "bKash Number",
        "nagad": "Nagad Number",
        "bybit": "Bybit UID",
        "binance": "Binance UID"
    }

    await query.edit_message_text(
        f"💸 Withdraw via {method.title()}\n\n"
        f"Send your {labels[method]} and amount to admin.\n\n"
        "Admin will review the request manually."
    )


# =========================
# BUTTON HANDLER
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    register(query.from_user)

    # USER MENU

    if data == "products":
        await show_products(query)

    elif data.startswith("view_"):

        pid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute(
            "SELECT name,price,stock,description FROM products WHERE id=?",
            (pid,)
        )

        row = cur.fetchone()
        con.close()

        if not row:
            await query.edit_message_text("❌ Product not found.")
            return

        name, price, stock, description = row

        await query.edit_message_text(
            f"💳 {name}\n\n"
            f"💵 ${price:.2f}\n"
            f"🇧🇩 ৳{price * RATE:.2f}\n"
            f"📦 Stock: {stock}\n\n"
            f"{description}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛒 Order",
                        callback_data=f"buy_{pid}"
                    )
                ]
            ])
        )

    elif data.startswith("buy_"):

        pid = int(data.split("_")[1])

        await create_order(query, pid)

    elif data == "balance":

        con = db()
        cur = con.cursor()

        cur.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (query.from_user.id,)
        )

        balance = cur.fetchone()[0]

        con.close()

        await query.edit_message_text(
            "💰 MY BALANCE\n\n"
            f"USD: ${balance:.2f}\n"
            f"BDT: ৳{balance * RATE:.2f}"
        )

    elif data == "orders":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT orders.id,
                   products.name,
                   orders.price,
                   orders.status,
                   orders.expires_at
            FROM orders
            JOIN products
            ON products.id=orders.product_id
            WHERE orders.user_id=?
            ORDER BY orders.id DESC
        """, (query.from_user.id,))

        rows = cur.fetchall()
        con.close()

        if not rows:
            await query.edit_message_text(
                "🧾 MY ORDERS\n\nNo orders found."
            )
            return

        import time

        text = "🧾 MY ORDERS\n\n"

        for oid, name, price, status, expires in rows:

            if status == "Approved" and expires:

                remaining = int(expires - time.time())

                if remaining <= 0:
                    status = "Expired"

                else:
                    minutes = remaining // 60
                    seconds = remaining % 60

                    status = (
                        f"Active — "
                        f"{minutes:02d}:{seconds:02d}"
                    )

            text += (
                f"Order #{oid}\n"
                f"Product: {name}\n"
                f"Price: ${price:.2f}\n"
                f"Status: {status}\n\n"
            )

        await query.edit_message_text(text)

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

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT id,price,status
            FROM orders
            WHERE user_id=?
            ORDER BY id DESC
        """, (query.from_user.id,))

        rows = cur.fetchall()
        con.close()

        if not rows:
            await query.edit_message_text(
                "↩️ REFUND\n\nNo orders found."
            )
            return

        keyboard = []

        for oid, price, status in rows:

            keyboard.append([
                InlineKeyboardButton(
                    f"Order #{oid} — ${price:.2f}",
                    callback_data=f"refund_{oid}"
                )
            ])

        await query.edit_message_text(
            "↩️ SELECT ORDER FOR REFUND:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("refund_"):

        oid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT price,status,refunded
            FROM orders
            WHERE id=? AND user_id=?
        """, (oid, query.from_user.id))

        row = cur.fetchone()

        if not row:
            con.close()
            await query.edit_message_text(
                "❌ Order not found."
            )
            return

        price, status, refunded = row

        if refunded:
            con.close()
            await query.edit_message_text(
                "❌ This order has already been refunded."
            )
            return

        cur.execute(
            """
            SELECT id FROM refunds
            WHERE order_id=? AND status='Pending'
            """,
            (oid,)
        )

        if cur.fetchone():
            con.close()
            await query.edit_message_text(
                "⏳ Refund request already pending."
            )
            return

        cur.execute(
            """
            INSERT INTO refunds(order_id,user_id,amount)
            VALUES(?,?,?)
            """,
            (oid, query.from_user.id, price)
        )

        con.commit()
        con.close()

        await query.edit_message_text(
            f"↩️ REFUND REQUESTED\n\n"
            f"Order ID: #{oid}\n"
            f"Amount: ${price:.2f}\n\n"
            "⏳ Waiting for admin decision."
        )

        try:
            await query.bot.send_message(
                ADMIN_ID,
                "↩️ NEW REFUND REQUEST\n\n"
                f"Order ID: #{oid}\n"
                f"User ID: {query.from_user.id}\n"
                f"Amount: ${price:.2f}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ Accept",
                            callback_data=f"raccept_{oid}"
                        ),
                        InlineKeyboardButton(
                            "❌ Decline",
                            callback_data=f"rdecline_{oid}"
                        )
                    ]
                ])
            )
        except Exception:
            pass

    elif data == "support":

        await query.edit_message_text(
            "📞 SUPPORT\n\n"
            "Contact us:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💬 Telegram Support",
                        url=SUPPORT
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

    # ADMIN

    elif data.startswith("approve_"):

        if query.from_user.id != ADMIN_ID:
            return

        oid = int(data.split("_")[1])

        context.user_data["approve_order"] = oid

        await query.edit_message_text(
            f"✅ Order #{oid} selected.\n\n"
            "Now send the product details/custom text."
        )

    elif data.startswith("decline_"):

        if query.from_user.id != ADMIN_ID:
            return

        oid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute(
            "UPDATE orders SET status='Declined' WHERE id=?",
            (oid,)
        )

        con.commit()
        con.close()

        await query.edit_message_text(
            f"❌ Order #{oid} declined."
        )

    elif data.startswith("raccept_"):

        if query.from_user.id != ADMIN_ID:
            return

        oid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute(
            """
            SELECT user_id,amount
            FROM refunds
            WHERE order_id=? AND status='Pending'
            """,
            (oid,)
        )

        row = cur.fetchone()

        if not row:
            con.close()
            await query.edit_message_text(
                "❌ Refund request not found."
            )
            return

        uid, amount = row

        cur.execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE user_id=?
            """,
            (amount, uid)
        )

        cur.execute(
            """
            UPDATE refunds
            SET status='Accepted'
            WHERE order_id=? AND status='Pending'
            """,
            (oid,)
        )

        cur.execute(
            """
            UPDATE orders
            SET refunded=1,status='Refunded'
            WHERE id=?
            """,
            (oid,)
        )

        con.commit()
        con.close()

        await query.edit_message_text(
            f"✅ Refund #{oid} accepted.\n"
            f"Amount: ${amount:.2f}"
        )

        try:
            await query.bot.send_message(
                uid,
                f"✅ REFUND ACCEPTED\n\n"
                f"Order ID: #{oid}\n"
                f"Refund: ${amount:.2f}\n\n"
                "Your balance has been updated."
            )
        except Exception:
            pass

    elif data.startswith("rdecline_"):

        if query.from_user.id != ADMIN_ID:
            return

        oid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute(
            """
            UPDATE refunds
            SET status='Declined'
            WHERE order_id=? AND status='Pending'
            """,
            (oid,)
        )

        con.c
