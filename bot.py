import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 8502501681
RATE = 125
PORT = int(os.environ.get("PORT", "10000"))


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
            status TEXT DEFAULT 'Pending'
        )
    """)

    con.commit()
    con.close()


def register_user(user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users(user_id, balance) VALUES(?, 0)",
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

    user_id = update.effective_user.id
    register_user(user_id)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "✨ Welcome to BOT CARD!\n\n"
        "━━━━━━━━━━━━━━\n"
        "💱 Rate: 1 USD = 125 BDT\n"
        "━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option:",
        reply_markup=main_menu(user_id)
    )


# ================= ADMIN PANEL =================

async def show_admin(query):

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

    products = cur.fetchall()
    con.close()

    if not products:
        await query.edit_message_text(
            "📦 PRODUCTS\n\n"
            "❌ No products available."
        )
        return

    keyboard = []

    for product_id, name, price, stock in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {name} — ${price:.2f}",
                callback_data=f"product_{product_id}"
            )
        ])

    await query.edit_message_text(
        "💳 AVAILABLE PRODUCTS\n\n"
        "👇 Select a product:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= PRODUCT DETAILS =================

async def product_details(query, product_id):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT name, price, stock, description
        FROM products
        WHERE id = ?
    """, (product_id,))

    product = cur.fetchone()
    con.close()

    if not product:
        await query.edit_message_text(
            "❌ Product not found."
        )
        return

    name, price, stock, description = product

    keyboard = [
        [
            InlineKeyboardButton(
                "🛒 Buy",
                callback_data=f"buy_{product_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Products",
                callback_data="buy"
            )
        ]
    ]

    await query.edit_message_text(
        f"📦 {name}\n\n"
        f"💵 Price: ${price:.2f}\n"
        f"🇧🇩 Price: ৳{price * RATE:.2f}\n"
        f"📦 Stock: {stock}\n\n"
        f"📝 {description}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= BUY PRODUCT =================

async def buy_product(query, product_id):

    user_id = query.from_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT name, price, stock
        FROM products
        WHERE id = ?
    """, (product_id,))

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
            "❌ Product is out of stock."
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
            f"💵 Price: ${price:.2f}\n"
            f"💰 Balance: ${balance:.2f}\n\n"
            "Please deposit balance first."
        )
        return

    cur.execute("""
        UPDATE users
        SET balance = balance - ?
        WHERE user_id = ?
    """, (price, user_id))

    cur.execute("""
        UPDATE products
        SET stock = stock - 1
        WHERE id = ?
    """, (product_id,))

    cur.execute("""
        INSERT INTO orders(user_id, product_id, price, status)
        VALUES(?, ?, ?, 'Pending')
    """, (user_id, product_id, price))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    await query.edit_message_text(
        "📦 ORDER CREATED\n\n"
        f"🆔 Order ID: #{order_id}\n"
        f"📦 Product: {name}\n"
        f"💵 Price: ${price:.2f}\n\n"
        "⏳ Waiting for admin approval."
    )

    await query.bot.send_message(
        ADMIN_ID,
        "📦 NEW ORDER\n\n"
        f"🆔 Order: #{order_id}\n"
        f"👤 User: {user_id}\n"
        f"📦 Product: {name}\n"
        f"💵 Price: ${price:.2f}",
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


# ================= ADMIN ADD PRODUCT =================

async def add_product_info(query, context):

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Access denied!",
            show_alert=True
        )
        return

    context.user_data["add_product"] = True

    await query.edit_message_text(
        "➕ ADD PRODUCT\n\n"
        "Send in this format:\n\n"
        "Product Name | Price | Stock | Description\n\n"
        "Example:\n"
        "Premium Product | 5 | 10 | Digital product"
    )


async def receive_admin_text(update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("add_product"):
        return

    text = update.message.text

    parts = [x.strip() for x in text.split("|")]

    if len(parts) != 4:
        await update.message.reply_text(
            "❌ Wrong format.\n\n"
            "Use:\n"
            "Product Name | Price | Stock | Description"
        )
        return

    name = parts[0]

    try:
        price = float(parts[1])
        stock = int(parts[2])
    except ValueError:
        await update.message.reply_text(
            "❌ Price বা Stock ভুল হয়েছে।"
        )
        return

    description = parts[3]

    if price <= 0 or stock < 0:
        await update.message.reply_text(
            "❌ Price/Stock invalid."
        )
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO products(name, price, stock, description)
        VALUES(?, ?, ?, ?)
    """, (name, price, stock, description))

    product_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data.pop("add_product", None)

    await update.message.reply_text(
        "✅ PRODUCT ADDED\n\n"
        f"🆔 ID: {product_id}\n"
        f"📦 Name: {name}\n"
        f"💵 Price: ${price:.2f}\n"
        f"🇧🇩 Price: ৳{price * RATE:.2f}\n"
        f"📦 Stock: {stock}"
    )


# ================= ADMIN PRODUCT LIST =================

async def admin_products(query):

    if query.from_user.id != ADMIN_ID:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name, price, stock
        FROM products
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "📦 PRODUCT LIST\n\n"
            "No products added."
        )
        return

    text = "📦 PRODUCT LIST\n\n"

    for product_id, name, price, stock in rows:
        text += (
            f"🆔 #{product_id}\n"
            f"📦 {name}\n"
            f"💵 ${price:.2f}\n"
            f"📦 Stock: {stock}\n\n"
        )

    await query.edit_message_text(text)


# ================= ADMIN REMOVE =================

async def admin_remove(query):

    if query.from_user.id != ADMIN_ID:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name
        FROM products
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "🗑️ REMOVE PRODUCT\n\n"
            "No products found."
        )
        return

    keyboard = []

    for product_id, name in rows:
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {name}",
                callback_data=f"remove_{product_id}"
            )
        ])

    await query.edit_message_text(
        "🗑️ REMOVE PRODUCT\n\n"
        "Select a product:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def remove_product(query, product_id):

    if query.from_user.id != ADMIN_ID:
        return

    con = db()
    cur = con.cursor()

    cur.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    deleted = cur.rowcount

    con.commit()
    con.close()

    if deleted:
        await query.edit_message_text(
            "✅ Product removed successfully."
        )
    else:
        await query.edit_message_text(
            "❌ Product not found."
        )


# ================= ORDERS =================

async def my_orders(query):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT orders.id, products.name, orders.price, orders.status
        FROM orders
        JOIN products ON products.id = orders.product_id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
    """, (query.from_user.id,))

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "🧾 MY ORDERS\n\n"
            "No orders found."
        )
        return

    text = "🧾 MY ORDERS\n\n"

    for order_id, name, price, status in rows:
        text += (
            f"🆔 #{order_id}\n"
            f"📦 {name}\n"
            f"💵 ${price:.2f}\n"
            f"📌 Status: {status}\n\n"
        )

    await query.edit_message_text(text)


# ================= BUTTONS =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data == "admin":
        await show_admin(query)

    elif data == "admin_add":
        await add_product_info(query, context)

    elif data == "admin_products":
        await admin_products(query)

    elif data == "admin_remove":
        await admin_remove(query)

    elif data.startswith("remove_"):
        await remove_product(
            query,
            int(data.split("_")[1])
        )

    elif data == "buy":
        await product_list(query)

    elif data.startswith("product_"):
        await product_details(
            query,
            int(data.split("_")[1])
        )

    elif data.startswith("buy_"):
        await buy_product(
            query,
            int(data.split("_")[1])
        )

    elif data.startswith("approve_"):

        if user_id != ADMIN_ID:
            return

        order_id = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute("""
            UPDATE orders
            SET status = 'Approved'
            WHERE id = ?
        """, (order_id,))

        cur.execute("""
            SELECT user_id
            FROM orders
            WHERE id = ?
        """, (order_id,))

        row = cur.fetchone()

        con.commit()
        con.close()

        await query.edit_message_text(
            f"✅ Order #{order_id} approved."
        )

        if row:
            await query.bot.send_message(
                row[0],
                f"✅ ORDER #{order_id} APPROVED\n\n"
                "Product details will be sent by admin."
            )

    elif data.startswith("decline_"):

        if user_id != ADMIN_ID:
            return

        order_id = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute("""
            UPDATE orders
            SET status = 'Declined'
            WHERE id = ?
        """, (order_id,))

        con.commit()
        con.close()

        await query.edit_message_text(
            f"❌ Order #{order_id} declined."
        )

    elif data == "orders":
        await my_orders(query)

    elif data == "balance":

        con = db()
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
            f"💵 USD: ${balance:.2f}\n"
            f"🇧🇩 BDT: ৳{balance * RATE:.2f}"
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


# ================= MAIN =================

def main():

    setup_database()

    Thread(
        target=start_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", lambda u, c: show_admin_command(u, c))
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    from telegram.ext import MessageHandler, filters

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_admin_text
        )
    )

    print("BOT CARD IS RUNNING")

    app.run_polling()


async def show_admin_command(update, context):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔐 Open Admin Panel",
                    callback_data="admin"
                )
            ]
        ])
    )


if __name__ == "__main__":
    main()
