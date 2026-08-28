import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 8502501681
RATE = 125

DB = "botcard.db"


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
            details TEXT NOT NULL,
            price REAL NOT NULL
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
    con.execute(
        "INSERT OR IGNORE INTO users(user_id) VALUES(?)",
        (user_id,)
    )
    con.commit()
    con.close()


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("💳 Buy Product", callback_data="products")
        ],
        [
            InlineKeyboardButton("💰 My Balance", callback_data="balance"),
            InlineKeyboardButton("🧾 My Orders", callback_data="orders")
        ],
        [
            InlineKeyboardButton("💵 Deposit", callback_data="deposit")
        ],
        [
            InlineKeyboardButton("📞 Support", callback_data="support"),
            InlineKeyboardButton("👤 Profile", callback_data="profile")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id)

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "👋 Welcome!\n\n"
        f"💱 Rate: 1 USD = {RATE} BDT\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "Choose an option:",
        reply_markup=main_menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "products":
        con = db()
        products = con.execute(
            "SELECT id, name, price FROM products"
        ).fetchall()
        con.close()

        if not products:
            await query.edit_message_text(
                "📦 PRODUCTS\n\n"
                "No products available right now.\n\n"
                "Please check again later."
            )
            return

        keyboard = []

        for product_id, name, price in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {name} — ${price:.2f}",
                    callback_data=f"product_{product_id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 Back", callback_data="home")
        ])

        await query.edit_message_text(
            "📦 PRODUCTS\n\n"
            "Select a product:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("product_"):
        product_id = int(query.data.split("_")[1])

        con = db()
        product = con.execute(
            "SELECT name, details, price FROM products WHERE id=?",
            (product_id,)
        ).fetchone()
        con.close()

        if not product:
            await query.edit_message_text(
                "❌ Product not found."
            )
            return

        name, details, price = product

        keyboard = [
            [
                InlineKeyboardButton(
                    "🛒 Buy Now",
                    callback_data=f"buy_{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Products",
                    callback_data="products"
                )
            ]
        ]

        await query.edit_message_text(
            "📦 PRODUCT DETAILS\n\n"
            f"🏷️ Name: {name}\n"
            f"💵 Price: ${price:.2f}\n\n"
            f"📝 Details:\n{details}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("buy_"):
        product_id = int(query.data.split("_")[1])

        con = db()

        product = con.execute(
            "SELECT name, price FROM products WHERE id=?",
            (product_id,)
        ).fetchone()

        user = con.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if not product or not user:
            con.close()
            await query.edit_message_text(
                "❌ Something went wrong."
            )
            return

        name, price = product
        balance = float(user[0])

        if balance < price:
            con.close()
            await query.edit_message_text(
                "❌ Insufficient balance.\n\n"
                f"💰 Balance: ${balance:.2f}\n"
                f"💵 Price: ${price:.2f}\n\n"
                "Please deposit first."
            )
            return

        con.execute(
            "UPDATE users SET balance=balance-? WHERE user_id=?",
            (price, user_id)
        )

        con.execute(
            "INSERT INTO orders(user_id, product_id, price, status) "
            "VALUES(?, ?, ?, ?)",
            (user_id, product_id, price, "Paid")
        )

        con.commit()
        con.close()

        await query.edit_message_text(
            "✅ ORDER SUCCESSFUL\n\n"
            f"📦 Product: {name}\n"
            f"💵 Paid: ${price:.2f}\n\n"
            "🧾 Your order has been recorded."
        )

    elif query.data == "balance":
        con = db()

        row = con.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        con.close()

        balance = float(row[0]) if row else 0

        await query.edit_message_text(
            "💰 MY BALANCE\n\n"
            f"💵 USD: ${balance:.2f}\n"
            f"🇧🇩 BDT: ৳{balance * RATE:.2f}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="home"
                    )
                ]
            ])
        )

    elif query.data == "orders":
        con = db()

        orders = con.execute(
            "SELECT id, product_id, price, status "
            "FROM orders WHERE user_id=? ORDER BY id DESC",
            (user_id,)
        ).fetchall()

        con.close()

        if not orders:
            text = "🧾 MY ORDERS\n\nNo orders yet."
        else:
            text = "🧾 MY ORDERS\n\n"

            for order_id, product_id, price, status in orders:
                text += (
                    f"🆔 Order: #{order_id}\n"
                    f"📦 Product ID: {product_id}\n"
                    f"💵 Price: ${price:.2f}\n"
                    f"📌 Status: {status}\n\n"
                )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="home"
                    )
                ]
            ])
        )

    elif query.data == "deposit":
        await query.edit_message_text(
            "💵 DEPOSIT\n\n"
            "Available methods:\n\n"
            "📱 bKash\n"
            "📱 Nagad\n"
            "💳 Bybit\n"
            "🪙 Binance\n\n"
            "Contact admin for deposit instructions.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="home"
                    )
                ]
            ])
        )

    elif query.data == "support":
        await query.edit_message_text(
            "📞 SUPPORT\n\n"
            "Please contact the administrator for help.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="home"
                    )
                ]
            ])
        )

    elif query.data == "profile":
        await query.edit_message_text(
            "👤 PROFILE\n\n"
            f"🆔 User ID: {user_id}\n"
            f"👤 Username: @{query.from_user.username or 'N/A'}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="home"
                    )
                ]
            ])
        )

    elif query.data == "home":
        await query.edit_message_text(
            "💳 BOT CARD\n\n"
            "Choose an option:",
            reply_markup=main_menu()
        )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Access denied."
        )
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Admin access verified.\n\n"
        "Product management will be added next."
    )


def main():
    setup_database()

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

    print("🤖 BOT CARD is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
