import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🧾 My Orders", callback_data="orders")],
        [InlineKeyboardButton("📞 Support", callback_data="support")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")]
    ]

    await update.message.reply_text(
        "💳 BOT CARD\n\n"
        "Welcome to BOT CARD!\n"
        "👤 BY ABIR",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "balance":
        text = "💰 My Balance\n\nBalance: 0.00 USD"
    elif query.data == "orders":
        text = "🧾 My Orders\n\nNo orders found."
    elif query.data == "support":
        text = "📞 Support\n\nTelegram: @abirhasan6738"
    elif query.data == "profile":
        text = f"👤 Profile\n\nUser ID: {query.from_user.id}"
    else:
        text = "BOT CARD"

    await query.edit_message_text(text)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("BOT CARD is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
