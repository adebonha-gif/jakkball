import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- News Fetching Function ---
def get_top_headlines(country: str):
    """Fetch top 5 headlines for a given country using NewsAPI."""
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": country,
        "pageSize": 5,
        "apiKey": NEWS_API_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok" and data.get("articles"):
            return data["articles"]
        return []
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return []

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    keyboard = [
        [InlineKeyboardButton("📰 Get News", callback_data="news")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏆 **Welcome to the Sports News Bot!**\n\n"
        "I fetch the latest sports headlines from around the world.\n"
        "Use the buttons below to get started.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "news":
        # Show country selection
        countries = [
            ("🇺🇸 US", "us"), ("🇬🇧 UK", "gb"), ("🇩🇪 Germany", "de"),
            ("🇫🇷 France", "fr"), ("🇪🇸 Spain", "es"), ("🇮🇹 Italy", "it")
        ]
        keyboard = [[InlineKeyboardButton(name, callback_data=f"country_{code}")] 
                    for name, code in countries]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌍 **Select a country** to get sports news:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data == "about":
        await query.edit_message_text(
            "⚽ **About This Bot**\n\n"
            "This bot fetches top sports headlines using NewsAPI.\n"
            "It's designed to provide quick, real-time news updates.\n\n"
            "📌 Use /start to return to the main menu."
        )
    
    elif query.data.startswith("country_"):
        country_code = query.data.split("_")[1]
        country_names = {"us": "🇺🇸 United States", "gb": "🇬🇧 United Kingdom", 
                         "de": "🇩🇪 Germany", "fr": "🇫🇷 France", 
                         "es": "🇪🇸 Spain", "it": "🇮🇹 Italy"}
        
        await query.edit_message_text(f"📡 Fetching sports news for {country_names.get(country_code, country_code)}...")
        
        articles = get_top_headlines(country_code)
        
        if not articles:
            await query.edit_message_text(
                f"❌ No sports news found for {country_names.get(country_code, country_code)}.\n"
                "Please try another country or try again later."
            )
            return
        
        # Format and send news
        message = f"📰 **Top Sports Headlines for {country_names.get(country_code, country_code)}**\n\n"
        for i, article in enumerate(articles, 1):
            title = article.get("title", "No title")
            url = article.get("url", "#")
            source = article.get("source", {}).get("name", "Unknown")
            message += f"{i}. **{title}**\n   📍 {source}\n   🔗 [Read more]({url})\n\n"
        
        # Telegram has message length limits - truncate if needed
        if len(message) > 4000:
            message = message[:4000] + "...\n\n📌 Truncated - too many headlines."
        
        # Add a "Back to menu" button
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="news")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    await update.message.reply_text(
        "🤔 **How to use this bot:**\n\n"
        "1. Press /start to see the main menu\n"
        "2. Click 'Get News' to select a country\n"
        "3. Choose a country to see top sports headlines\n\n"
        "You can also just send me any message and I'll respond!"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo any non-command message."""
    await update.message.reply_text(
        f"👋 You said: *{update.message.text}*\n\n"
        "Use /start to get sports news!",
        parse_mode="Markdown"
    )

# --- Main Application ---
def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        return
    
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY is not set! News fetching will fail.")
    
    logger.info("Starting bot with long polling...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
