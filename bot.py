import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]

PORT = int(os.environ.get("PORT", 10000))

USD_TO_BDT = 125

# Admin Telegram numeric ID
ADMIN_ID = 8502501681

DB_FILE = "botcard.db"


# =========================
# DATABASE
# =========================

def get_db():
    return sqlite3.connect(DB_FILE)


def setup_database():
    con = get_db()
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
            amount REAL,
            method TEXT,
            trx_id TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            account TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register_user(user):
    con = get_db()
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user.id, user.username or "")
    )

    cur.execute(
        "UPDATE users SET username=? WHERE user_id=?",
        (user.username or "", user.id)
    )

    con.commit()
    con.close()


# =========================
# RENDER HEALTH SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BOT CARD is running")

    def log_message(self, format, *args):
        pass


def run_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# =========================
# MAIN MENU
# =========================

def main_menu():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💳 Buy Card",
                callback_data="products"
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
    ])


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    register_user(update.effective_user)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "Welcome to BOT CARD!\n"
        "👤 BY ABIR\n\n"
        f"💱 Rate: 1 USD = {USD_TO_BDT} BDT\n\n"
        "Choose an option:",
        reply_markup=main_menu()
    )


# =========================
# BALANCE
# =========================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    register_user(update.effective_user)

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (update.effective_user.id,)
    )

    row = cur.fetchone()

    con.close()

    amount = row[0] if row else 0

    await update.message.reply_text(
        "💰 MY BALANCE\n\n"
        f"USD: ${amount:.2f}\n"
        f"BDT: ৳{amount * USD_TO_BDT:.2f}"
    )


# =========================
# PRODUCTS
# =========================

async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):

    register_user(update.effective_user)

    con = get_db()
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

        await update.message.reply_text(
            "💳 BUY CARD\n\n"
            "No products available right now."
        )

        return

    keyboard = []

    for product_id, name, price, stock in rows:

        keyboard.append([
            InlineKeyboardButton(
                f"💳 {name} — ${price:.2f}",
                callback_data=f"product_{product_id}"
            )
        ])

    await update.message.reply_text(
        "💳 AVAILABLE PRODUCTS\n\n"
        f"💱 1 USD = {USD_TO_BDT} BDT",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ORDERS
# =========================

async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT orders.id,
               products.name,
               orders.price,
               orders.status
        FROM orders
        JOIN products
        ON products.id = orders.product_id
        WHERE orders.user_id=?
        ORDER BY orders.id DESC
    """, (update.effective_user.id,))

    rows = cur.fetchall()

    con.close()

    if not rows:

        await update.message.reply_text(
            "🧾 MY ORDERS\n\n"
            "No orders found."
        )

        return

    text = "🧾 MY ORDERS\n\n"

    for order_id, name, price, status in rows:

        text += (
            f"Order #{order_id}\n"
            f"Product: {name}\n"
            f"Price: ${price:.2f}\n"
            f"Status: {status}\n\n"
        )

    await update.message.reply_text(text)


# =========================
# DEPOSIT
# =========================

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "💵 DEPOSIT\n\n"
        "Deposit system requires admin approval.\n\n"
        "📞 Support: @abirhasan6738"
    )


# =========================
# WITHDRAW
# =========================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "💸 WITHDRAW\n\n"
        "Withdraw system requires admin approval.\n\n"
        "📞 Support: @abirhasan6738"
    )


# =========================
# SUPPORT
# =========================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📞 SUPPORT\n\n"
        "Telegram: @abirhasan6738"
    )


# =========================
# PROFILE
# =========================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    register_user(update.effective_user)

    await update.message.reply_text(
        "👤 PROFILE\n\n"
        f"User ID: {update.effective_user.id}\n"
        f"Username: @{update.effective_user.username or 'N/A'}"
    )


# =========================
# ADMIN PANEL
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Access denied."
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
                "📦 Products",
                callback_data="admin_products"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Remove Product",
                callback_data="admin_remove"
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
                "💵 Deposits",
                callback_data="admin_deposits"
            )
        ],
        [
            InlineKeyboardButton(
                "💸 Withdrawals",
                callback_data="admin_withdrawals"
            )
        ],
    ]

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ADD PRODUCT
# =========================

async def addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Access denied."
        )

        return

    text = update.message.text.replace(
        "/addproduct",
        "",
        1
    ).strip()

    parts = [
        x.strip()
        for x in text.split("|")
    ]

    if len(parts) != 4:

        await update.message.reply_text(
            "❌ Wrong format.\n\n"
            "Use:\n"
            "/addproduct Name | PriceUSD | Stock | Description\n\n"
            "Example:\n"
            "/addproduct Example Product | 5 | 10 | Digital product"
        )

        return

    name = parts[0]

    try:
        price = float(parts[1])
        stock = int(parts[2])
    except ValueError:

        await update.message.reply_text(
            "❌ Price must be a number and stock must be a whole number."
        )

        return

    description = parts[3]

    if price <= 0 or stock < 0:

        await update.message.reply_text(
            "❌ Invalid price or stock."
        )

        return

    con = get_db()
    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO products
        (name, price, stock, description)
        VALUES (?, ?, ?, ?)
        """,
        (name, price, stock, description)
    )

    con.commit()
    con.close()

    await update.message.reply_text(
        "✅ PRODUCT ADDED\n\n"
        f"Name: {name}\n"
        f"USD: ${price:.2f}\n"
        f"BDT: ৳{price * USD_TO_BDT:.2f}\n"
        f"Stock: {stock}"
    )


# =========================
# REMOVE PRODUCT
# =========================

async def removeproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Access denied."
        )

        return

    text = update.message.text.replace(
        "/removeproduct",
        "",
        1
    ).strip()

    try:
        product_id = int(text)
    except ValueError:

        await update.message.reply_text(
            "Use:\n"
            "/removeproduct PRODUCT_ID"
        )

        return

    con = get_db()
    cur = con.cursor()

    cur.execute(
        "DELETE FROM products WHERE id=?",
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


# =========================
# BUTTON HANDLER
# =========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data

    # USER

    if data == "products":

        con = get_db()
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
                "💳 AVAILABLE PRODUCTS\n\n"
                "No products available."
            )

            return

        keyboard = []

        for product_id, name, price, stock in rows:

            keyboard.append([
                InlineKeyboardButton(
                    f"💳 {name} — ${price:.2f}",
                    callback_data=f"product_{product_id}"
                )
            ])

        await query.edit_message_text(
            "💳 AVAILABLE PRODUCTS\n\n"
            f"💱 1 USD = {USD_TO_BDT} BDT",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("product_"):

        product_id = int(
            data.split("_")[1]
        )

        con = get_db()
        cur = con.cursor()

        cur.execute(
            """
            SELECT name, price, stock, description
            FROM products
            WHERE id=?
            """,
            (product_id,)
        )

        row = cur.fetchone()

        con.close()

        if not row:

            await query.edit_message_text(
                "❌ Product not found."
            )

            return

        name, price, stock, description = row

        await query.edit_message_text(
            f"💳 {name}\n\n"
            f"💵 Price: ${price:.2f}\n"
            f"🇧🇩 Price: ৳{price * USD_TO_BDT:.2f}\n"
            f"📦 Stock: {stock}\n\n"
            f"{description}\n\n"
            "📞 To order, contact support."
        )

    elif data == "balance":

        con = get_db()
        cur = con.cursor()

        cur.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (query.from_user.id,)
        )

        row = cur.fetchone()

        con.close()

        amount = row[0] if row else 0

        await query.edit_message_text(
            "💰 MY BALANCE\n\n"
            f"USD: ${amount:.2f}\n"
            f"BDT: ৳{amount * USD_TO_BDT:.2f}"
        )

    elif data == "orders":

        await query.edit_message_text(
            "🧾 MY ORDERS\n\n"
            "No orders found."
        )

    elif data == "deposit":

        await query.edit_message_text(
            "💵 DEPOSIT\n\n"
            "Deposit requires admin approval.\n\n"
            "📞 Support: @abirhasan6738"
        )

    elif data == "withdraw":

        await query.edit_message_text(
            "💸 WITHDRAW\n\n"
            "Withdraw requires admin approval.\n\n"
            "📞 Support: @abirhasan6738"
        )

    elif data == "support":

        await query.edit_message_text(
            "📞 SUPPORT\n\n"
            "Telegram: @abirhasan6738"
        )

    elif data == "profile":

        await query.edit_message_text(
            "👤 PROFILE\n\n"
            f"User ID: {query.from_user.id}\n"
            f"Username: @{query.from_user.username or 'N/A'}"
        )

    # ADMIN

    elif data.startswith("admin_"):

        if query.from_user.id != ADMIN_ID:

            await query.edit_message_text(
                "❌ Access denied."
            )

            return

        if data == "admin_add":

            await query.edit_message_text(
                "➕ ADD PRODUCT\n\n"
                "Use this command:\n\n"
                "/addproduct Name | PriceUSD | Stock | Description\n\n"
                "Example:\n"
                "/addproduct Example Product | 5 | 10 | Digital product"
            )

        elif data == "admin_products":

            con = get_db()
            cur = con.cursor()

            cur.execute(
                """
                SELECT id, name, price, stock
                FROM products
                ORDER BY id DESC
                """
            )

            rows = cur.fetchall()

            con.close()

            if not rows:

                await query.edit_message_text(
                    "📦 PRODUCTS\n\n"
                    "No products."
                )

                return

            text = "📦 PRODUCTS\n\n"

            for pid, name, price, stock in rows:

                text += (
                    f"ID: {pid}\n"
                    f"Name: {name}\n"
                    f"Price: ${price:.2f}\n"
                    f"Stock: {stock}\n\n"
                )

            await query.edit_message_text(text)

        elif data == "admin_remove":

            await query.edit_message_text(
                "❌ REMOVE PRODUCT\n\n"
                "Use:\n"
                "/removeproduct PRODUCT_ID"
            )

        elif data == "admin_users":

            con = get_db()
            cur = con.cursor()

            cur.execute(
                "SELECT COUNT(*) FROM users"
            )

            count = cur.fetchone()[0]

            con.close()

            await query.edit_message_text(
                f"👥 USERS\n\n"
                f"Total users: {count}"
            )

        elif data == "admin_deposits":

            await query.edit_message_text(
                "💵 DEPOSITS\n\n"
                "No pending deposits."
            )

        elif data == "admin_withdrawals":

            await query.edit_message_text(
                "💸 WITHDRAWALS\n\n"
                "No pending withdrawals."
            )


# =========================
# START BOT
# =========================

def main():

    setup_database()

    threading.Thread(
        target=run_web_server,
        daemon=True
    ).start()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # User commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("balance", balance)
    )

    app.add_handler(
        CommandHandler("orders", orders)
    )

    app.add_handler(
        CommandHandler("deposit", deposit)
    )

    app.add_handler(
        CommandHandler("withdraw", withdraw)
    )

    app.add_handler(
        CommandHandler("support", support)
    )

    app.add_handler(
        CommandHandler("profile", profile)
    )

    # Admin commands
    app.add_handler(
        CommandHandler("admin", admin)
    )

    app.add_handler(
        CommandHandler("addproduct", addproduct)
    )

    app.add_handler(
        CommandHandler("removeproduct", removeproduct)
    )

    # Buttons
    app.add_handler(
        CallbackQueryHandler(button)
    )

    print("BOT CARD is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
