import os
import sqlite3
import asyncio
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = 8502501681
RATE = 125  # 1 USD = 125 BDT
DB_NAME = "shop.db"

PAYMENT_INFO = {
    "bKash": "01326630510",
    "Nagad": "01326630510",
    "Bybit": "531771545",
    "Binance": "780473636"
}

SUPPORT_URL = "https://t.me/abirhasan6738"

# Conversation States
(
    # Add Product States
    ADD_PROD_NAME, ADD_PROD_DETAILS, ADD_PROD_PRICE, ADD_PROD_STOCK,
    # Deposit States
    DEP_METHOD, DEP_AMOUNT, DEP_TXID,
    # Withdraw States
    WD_METHOD, WD_AMOUNT, WD_INFO,
    # Refund State
    REFUND_REASON
) = range(11)

# ==========================================
# DATABASE SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, details TEXT, price REAL, stock INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, 
                       price REAL, status TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS deposits 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, 
                       amount REAL, transaction_id TEXT, status TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdraws 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, 
                       amount REAL, account_info TEXT, status TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS refunds 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, user_id INTEGER, 
                       status TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetchone: res = cursor.fetchone()
    elif fetchall: res = cursor.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# ==========================================
# HEALTH SERVER FOR RENDER
# ==========================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

# ==========================================
# KEYBOARDS
# ==========================================
def main_menu_kb(user_id):
    kb = [
        [InlineKeyboardButton("💳 Buy Card", callback_data="buy_card"), InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance"), InlineKeyboardButton("🧾 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"), InlineKeyboardButton("↩️ Refund", callback_data="refund_req")],
        [InlineKeyboardButton("📞 Support", callback_data="support"), InlineKeyboardButton("👤 Profile", callback_data="profile")]
    ]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🔐 ADMIN PANEL", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def admin_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Product", callback_data="add_product"), InlineKeyboardButton("📦 Product List", callback_data="admin_prod_list")],
        [InlineKeyboardButton("🗑️ Remove Product", callback_data="remove_prod_list")],
        [InlineKeyboardButton("💵 Deposit Requests", callback_data="admin_deposits"), InlineKeyboardButton("🧾 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users"), InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])

def back_btn(target):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=target)]])

# ==========================================
# USER HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db_query("SELECT user_id FROM users WHERE user_id=?", (user_id,), fetchone=True)
    if not user:
        db_query("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0.0), commit=True)
    
    text = (
        "💳 BOT CARD\n\n"
        "✨ Welcome to BOT CARD!\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💱 Rate: 1 USD = {RATE} BDT\n"
        "━━━━━━━━━━━━━━━━"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_kb(user_id))
    else:
        await update.message.reply_text(text, reply_markup=main_menu_kb(user_id))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db_query("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)
    order_count = db_query("SELECT COUNT(*) FROM orders WHERE user_id=?", (user_id,), fetchone=True)[0]
    
    text = (
        "👤 PROFILE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 User ID: {user_id}\n"
        f"👤 Username: @{update.effective_user.username or 'N/A'}\n"
        f"💰 Balance: ${user_data[0]:.2f}\n"
        f"📦 Orders: {order_count}\n"
        "━━━━━━━━━━━━━━━━"
    )
    await update.callback_query.edit_message_text(text, reply_markup=back_btn("start_menu"))

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db_query("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)
    usd = user_data[0]
    bdt = usd * RATE
    text = (
        "💰 MY BALANCE\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💵 USD: ${usd:.2f}\n"
        f"🇧🇩 BDT: ৳{bdt:.2f}\n"
        "━━━━━━━━━━━━━━━━"
    )
    await update.callback_query.edit_message_text(text, reply_markup=back_btn("start_menu"))

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📞 SUPPORT\n\nNeed help? Click the button below."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Telegram Support", url=SUPPORT_URL)],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await update.callback_query.edit_message_text(text, reply_markup=kb)

# ==========================================
# PRODUCT & PURCHASE LOGIC
# ==========================================
async def buy_card_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = db_query("SELECT id, name, price FROM products WHERE stock > 0", fetchall=True)
    if not products:
        await update.callback_query.edit_message_text("❌ No products available.", reply_markup=back_btn("start_menu"))
        return
    
    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(f"📦 {p[1]} — ${p[2]:.2f}", callback_data=f"view_prod_{p[0]}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="start_menu")])
    await update.callback_query.edit_message_text("🛒 Select a product to view details:", reply_markup=InlineKeyboardMarkup(kb))

async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prod_id = update.callback_query.data.split("_")[2]
    p = db_query("SELECT id, name, details, price, stock FROM products WHERE id=?", (prod_id,), fetchone=True)
    if not p:
        await update.callback_query.answer("Product not found.")
        return
    
    text = (
        "📦 PRODUCT DETAILS\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🏷️ Name: {p[1]}\n"
        f"📝 Details:\n{p[2]}\n\n"
        f"💵 Price: ${p[3]:.2f}\n"
        f"🇧🇩 Price: ৳{p[3]*RATE:.2f}\n"
        f"📊 Stock: {p[4]}\n"
        "━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"order_now_{p[0]}")],
        [InlineKeyboardButton("🔙 Products", callback_data="buy_card")]
    ])
    await update.callback_query.edit_message_text(text, reply_markup=kb)

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prod_id = update.callback_query.data.split("_")[2]
    
    p = db_query("SELECT name, price, stock FROM products WHERE id=?", (prod_id,), fetchone=True)
    u = db_query("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)
    
    if not p or p[2] <= 0:
        await update.callback_query.answer("❌ Out of stock or product missing.")
        return
    
    if u[0] < p[1]:
        text = (
            "❌ INSUFFICIENT BALANCE\n\n"
            f"Price: ${p[1]:.2f}\n"
            f"Your Balance: ${u[0]:.2f}"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💵 Deposit", callback_data="deposit")], [InlineKeyboardButton("🔙 Back", callback_data="buy_card")]])
        await update.callback_query.edit_message_text(text, reply_markup=kb)
        return

    # Atomic-like update
    new_bal = u[0] - p[1]
    db_query("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id), commit=True)
    db_query("UPDATE products SET stock = stock - 1 WHERE id=?", (prod_id,), commit=True)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    db_query("INSERT INTO orders (user_id, product_id, price, status, created_at) VALUES (?, ?, ?, ?, ?)",
             (user_id, prod_id, p[1], "Pending", created_at), commit=True)
    
    order_id = db_query("SELECT last_insert_rowid()", fetchone=True)[0]
    
    text = (
        "✅ ORDER CREATED\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: #{order_id}\n"
        f"📦 Product: {p[0]}\n"
        f"💵 Price: ${p[1]:.2f}\n"
        f"📌 Status: Pending\n"
        "━━━━━━━━━━━━━━━━"
    )
    await update.callback_query.edit_message_text(text, reply_markup=back_btn("start_menu"))

# ==========================================
# ADMIN PANEL HANDLERS
# ==========================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("❌ Access denied.")
        return
    await update.callback_query.edit_message_text("🔐 ADMIN PANEL", reply_markup=admin_menu_kb())

async def admin_prod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods = db_query("SELECT id, name, price, stock FROM products", fetchall=True)
    text = "📦 PRODUCT LIST\n\n"
    for p in prods:
        text += f"🆔 {p[0]} | {p[1]} | ${p[2]} | Stock: {p[3]}\n"
    if not prods: text += "No products found."
    await update.callback_query.edit_message_text(text, reply_markup=back_btn("admin_panel"))

async def remove_prod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods = db_query("SELECT id, name FROM products", fetchall=True)
    kb = []
    for p in prods:
        kb.append([InlineKeyboardButton(f"🗑️ Remove {p[1]}", callback_data=f"del_conf_{p[0]}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    await update.callback_query.edit_message_text("Select product to remove:", reply_markup=InlineKeyboardMarkup(kb))

async def remove_prod_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.callback_query.data.split("_")[2]
    p = db_query("SELECT name FROM products WHERE id=?", (pid,), fetchone=True)
    text = f"⚠️ REMOVE PRODUCT?\n\n📦 {p[0]}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data=f"del_exec_{pid}"), InlineKeyboardButton("❌ Cancel", callback_data="remove_prod_list")]
    ])
    await update.callback_query.edit_message_text(text, reply_markup=kb)

async def remove_prod_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.callback_query.data.split("_")[2]
    db_query("DELETE FROM products WHERE id=?", (pid,), commit=True)
    await update.callback_query.answer("Product deleted.")
    await remove_prod_list(update, context)

# ==========================================
# ADD PRODUCT CONVERSATION
# ==========================================
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Step 1:\n📦 Enter Product Name:")
    return ADD_PROD_NAME

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_name'] = update.message.text
    await update.message.reply_text("Step 2:\n📝 Enter Product Details (Multi-line text allowed):")
    return ADD_PROD_DETAILS

async def add_product_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_details'] = update.message.text
    await update.message.reply_text("Step 3:\n💵 Enter Price in USD (e.g. 5.00):")
    return ADD_PROD_PRICE

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_prod_price'] = price
        await update.message.reply_text("Step 4:\n📊 Enter Stock Quantity:")
        return ADD_PROD_STOCK
    except:
        await update.message.reply_text("❌ Invalid price. Enter a number:")
        return ADD_PROD_PRICE

async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text)
        name = context.user_data['new_prod_name']
        details = context.user_data['new_prod_details']
        price = context.user_data['new_prod_price']
        
        db_query("INSERT INTO products (name, details, price, stock) VALUES (?, ?, ?, ?)",
                 (name, details, price, stock), commit=True)
        pid = db_query("SELECT last_insert_rowid()", fetchone=True)[0]
        
        text = (
            "✅ PRODUCT ADDED\n\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 Product ID: {pid}\n"
            f"📦 Product Name: {name}\n"
            f"📝 Product Details: {details}\n"
            f"💵 USD Price: ${price:.2f}\n"
            f"🇧🇩 BDT Price: ৳{price*RATE:.2f}\n"
            f"📊 Stock: {stock}\n"
            "━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(text, reply_markup=admin_menu_kb())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Invalid stock. Enter a number:")
        return ADD_PROD_STOCK

# ==========================================
# DEPOSIT SYSTEM
# ==========================================
async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📱 bKash", callback_data="dep_meth_bKash"), InlineKeyboardButton("📱 Nagad", callback_data="dep_meth_Nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="dep_meth_Bybit"), InlineKeyboardButton("🪙 Binance", callback_data="dep_meth_Binance")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ]
    await update.callback_query.edit_message_text("Select Deposit Method:", reply_markup=InlineKeyboardMarkup(kb))
    return DEP_METHOD

async def deposit_method_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.callback_query.data.split("_")[2]
    context.user_data['dep_method'] = method
    info = PAYMENT_INFO[method]
    text = (
        f"📱 {method} Payment\n\n"
        f"Send money to:\n`{info}`\n\n"
        "After sending, enter the amount in USD you deposited:"
    )
    await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    return DEP_AMOUNT

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text)
        context.user_data['dep_amount'] = amt
        await update.message.reply_text("Enter Transaction ID:")
        return DEP_TXID
    except:
        await update.message.reply_text("Invalid amount. Enter a number:")
        return DEP_AMOUNT

async def deposit_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = update.message.text
    method = context.user_data['dep_method']
    amt = context.user_data['dep_amount']
    user_id = update.effective_user.id
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    db_query("INSERT INTO deposits (user_id, method, amount, transaction_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
             (user_id, method, amt, txid, "Pending", created_at), commit=True)
    
    text = (
        "✅ DEPOSIT REQUEST SUBMITTED\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💳 Method: {method}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🧾 Transaction ID: {txid}\n"
        f"📌 Status: Pending\n"
        "━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, reply_markup=main_menu_kb(user_id))
    return ConversationHandler.END

# ==========================================
# WITHDRAW SYSTEM
# ==========================================
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📱 bKash", callback_data="wd_meth_bKash"), InlineKeyboardButton("📱 Nagad", callback_data="wd_meth_Nagad")],
        [InlineKeyboardButton("💳 Bybit", callback_data="wd_meth_Bybit"), InlineKeyboardButton("🪙 Binance", callback_data="wd_meth_Binance")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ]
    await update.callback_query.edit_message_text("Select Withdrawal Method:", reply_markup=InlineKeyboardMarkup(kb))
    return WD_METHOD

async def withdraw_method_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.callback_query.data.split("_")[2]
    context.user_data['wd_method'] = method
    await update.callback_query.edit_message_text(f"Enter Withdrawal Amount (USD) for {method}:")
    return WD_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text)
        user_id = update.effective_user.id
        u = db_query("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)
        if u[0] < amt:
            await update.message.reply_text("❌ Insufficient balance. Enter a smaller amount:")
            return WD_AMOUNT
        context.user_data['wd_amount'] = amt
        await update.message.reply_text("Enter your Account Number / UID / Wallet Address:")
        return WD_INFO
    except:
        await update.message.reply_text("Invalid amount. Enter a number:")
        return WD_AMOUNT

async def withdraw_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = update.message.text
    method = context.user_data['wd_method']
    amt = context.user_data['wd_amount']
    user_id = update.effective_user.id
    
    # Deduct balance immediately for safety
    db_query("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, user_id), commit=True)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    db_query(
        "INSERT INTO withdraws "
        "(user_id, method, amount, account_info, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, method, amt, info, "Pending", created_at),
        commit=True
    )

    await update.message.reply_text(
        "✅ Withdrawal Request Submitted!\n\n"
        f"💳 Method: {method}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"📌 Status: Pending\n\n"
        "⏳ Waiting for admin approval."
    )

    context.user_data.clear()
    return ConversationHandler.END
