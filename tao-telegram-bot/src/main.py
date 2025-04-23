import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from tao_analyzer import TAOAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from alerts import AlertManager, Alert, AlertType
from datetime import datetime

# Load environment variables from .env.local
load_dotenv('.env.local')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize managers
alert_manager = AlertManager()
analyzer = TAOAnalyzer()
sentiment_analyzer = SentimentAnalyzer()

# Store user data (in production, use a database)
user_data: Dict[int, Dict[str, Any]] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("📊 Analyze Wallet", callback_data='analyze'),
            InlineKeyboardButton("ℹ️ Help", callback_data='help')
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
            InlineKeyboardButton("📝 About", callback_data='about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        f"👋 Welcome {user.mention_html()}!\n\n"
        "I'm your TAO Wallet Analyzer Bot. I can help you analyze your TAO holdings and generate detailed reports.\n\n"
        "🔍 What would you like to do?"
    )
    await update.message.reply_html(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Wallet Analysis", callback_data='help_analysis'),
            InlineKeyboardButton("📈 Portfolio", callback_data='help_portfolio')
        ],
        [
            InlineKeyboardButton("⚙️ Settings Guide", callback_data='help_settings'),
            InlineKeyboardButton("🔍 Quick Start", callback_data='help_quickstart')
        ],
        [
            InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
        ]
    ]
    
    help_text = """
📚 *Welcome to TAO Wallet Analyzer Help*

*Essential Commands:*
• /start - Initialize the bot and see main menu
• /help - Display this help message
• /analyze <address> - Analyze a TAO wallet
• /portfolio - View your saved wallets
• /settings - Configure your preferences
• /about - Bot information and updates

*Key Features:*
1️⃣ *Wallet Analysis*
   • Real-time balance tracking
   • Transaction history
   • Performance metrics
   • Activity level assessment

2️⃣ *Portfolio Management*
   • Save multiple wallets
   • Track total holdings
   • Set custom alerts
   • Daily/weekly reports

3️⃣ *Alert System*
   • Price alerts
   • Balance changes
   • Transaction notifications
   • Staking rewards

4️⃣ *Customization*
   • Multiple currencies
   • Report styles
   • Language options
   • Notification preferences

*Tips:*
• Use `/analyze` with a wallet address to start
• Save important wallets to your portfolio
• Set up alerts for price changes
• Check documentation for detailed guides

Select a topic below for more detailed information:
"""
    if isinstance(update.message, Message):
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def analyze_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze a TAO wallet."""
    if not context.args:
        await update.message.reply_text(
            "Please provide a wallet address.\n"
            "Example: `/analyze your_tao_wallet_address`\n\n"
            "Or use the button below to enter your address:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Enter Wallet Address", callback_data='enter_wallet')
            ]]),
            parse_mode='Markdown'
        )
        return

    wallet_address = context.args[0]
    await update.message.reply_text(
        f"🔍 Analyzing wallet: `{wallet_address}`\n\n"
        "⏳ This may take a few moments...",
        parse_mode='Markdown'
    )

    try:
        # Validate wallet address
        if not await analyzer.validate_wallet(wallet_address):
            await update.message.reply_text(
                "❌ Invalid TAO wallet address. Please check and try again."
            )
            return

        # Generate report
        report = await analyzer.generate_report(wallet_address)
        
        if "error" in report:
            await update.message.reply_text(
                f"❌ Error: {report['error']}\n\n"
                "Please try again later or contact support if the issue persists."
            )
            return

        # Get sentiment analysis
        market_context = await analyzer.get_market_context(wallet_address)
        sentiment = await sentiment_analyzer.analyze(report, market_context)

        # Format and send the report
        report_text = (
            f"📊 *Wallet Analysis Report*\n\n"
            f"*Wallet:* `{wallet_address}`\n"
            f"*Current Balance:* {report['current_balance']} TAO\n"
            f"*Transaction Count:* {report['transaction_analysis']['transaction_count']}\n"
            f"*Activity Level:* {report['activity_level']}\n\n"
            f"*Market Context:*\n"
            f"• 24h Price Change: {market_context.price_change_24h}%\n"
            f"• Market Volume: {market_context.market_volume} TAO\n\n"
            f"*Sentiment Analysis:*\n{sentiment}\n\n"
            f"*Last Updated:* {report['last_updated']}\n\n"
            "Use /portfolio to save this wallet for tracking."
        )

        keyboard = [
            [
                InlineKeyboardButton("📈 View History", callback_data=f'history_{wallet_address}'),
                InlineKeyboardButton("💾 Save to Portfolio", callback_data=f'save_{wallet_address}')
            ],
            [
                InlineKeyboardButton("🔔 Set Alerts", callback_data=f'alerts_{wallet_address}'),
                InlineKeyboardButton("📊 Advanced Stats", callback_data=f'stats_{wallet_address}')
            ]
        ]

        await update.message.reply_text(
            report_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in analyze_wallet: {e}")
        await update.message.reply_text(
            "❌ An error occurred while analyzing the wallet. Please try again later."
        )

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View saved portfolio."""
    user_id = update.effective_user.id
    if user_id not in user_data or 'portfolio' not in user_data[user_id]:
        keyboard = [
            [
                InlineKeyboardButton("🔍 Analyze Wallet", callback_data='analyze'),
                InlineKeyboardButton("ℹ️ Learn More", callback_data='help_portfolio')
            ]
        ]
        await update.message.reply_text(
            "📊 *Your Portfolio*\n\n"
            "You haven't saved any wallets yet.\n"
            "Use /analyze to analyze a wallet and save it to your portfolio.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # Get saved wallets
    saved_wallets = user_data[user_id]['portfolio']
    
    # Create buttons for each saved wallet
    keyboard = []
    for wallet in saved_wallets:
        keyboard.append([
            InlineKeyboardButton(
                f"🔍 {wallet['address'][:8]}...",
                callback_data=f'view_{wallet["address"]}'
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("➕ Add Wallet", callback_data='analyze'),
        InlineKeyboardButton("⚙️ Portfolio Settings", callback_data='portfolio_settings')
    ])

    await update.message.reply_text(
        "📊 *Your Portfolio*\n\n"
        "Select a wallet to view its details:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configure bot preferences."""
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            'notifications': True,
            'report_style': 'detailed',
            'currency': 'USD',
            'language': 'en'
        }
    
    current_settings = user_data[user_id]
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"🔔 Notifications: {'ON' if current_settings['notifications'] else 'OFF'}",
                callback_data='toggle_notifications'
            )
        ],
        [
            InlineKeyboardButton(
                f"📊 Report Style: {current_settings['report_style'].title()}",
                callback_data='change_report_style'
            )
        ],
        [
            InlineKeyboardButton(
                f"💱 Currency: {current_settings['currency']}",
                callback_data='change_currency'
            )
        ],
        [
            InlineKeyboardButton(
                f"🌐 Language: {current_settings['language'].upper()}",
                callback_data='change_language'
            )
        ],
        [
            InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
        ]
    ]
    
    settings_text = (
        "⚙️ *Bot Settings*\n\n"
        "Configure your preferences below:\n\n"
        f"• Notifications: {'Enabled' if current_settings['notifications'] else 'Disabled'}\n"
        f"• Report Style: {current_settings['report_style'].title()}\n"
        f"• Currency: {current_settings['currency']}\n"
        f"• Language: {current_settings['language'].upper()}"
    )
    
    if isinstance(update.message, Message):
        await update.message.reply_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.message.reply_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show information about the bot."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Features", callback_data='about_features'),
            InlineKeyboardButton("🔒 Privacy", callback_data='about_privacy')
        ],
        [
            InlineKeyboardButton("📈 Data Sources", callback_data='about_data'),
            InlineKeyboardButton("🔄 Updates", callback_data='about_updates')
        ],
        [
            InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
        ]
    ]
    
    about_text = """
🤖 *TAO Wallet Analyzer Bot*

*Version:* 1.0.0
*Data Source:* MCP (Market Cap Protocol)

*Core Features:*
• Real-time TAO holdings analysis
• Detailed portfolio reports
• Price tracking and alerts
• Historical performance data
• Customizable settings

*Technology Stack:*
• Python 3.9+
• Telegram Bot API
• MCP Integration
• Real-time Data Processing

Select a topic to learn more:
"""
    if isinstance(update.message, Message):
        await update.message.reply_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.message.reply_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    if query.data == 'back_to_main':
        keyboard = [
            [
                InlineKeyboardButton("📊 Analyze Wallet", callback_data='analyze'),
                InlineKeyboardButton("ℹ️ Help", callback_data='help')
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
                InlineKeyboardButton("📝 About", callback_data='about')
            ]
        ]
        welcome_message = (
            f"👋 Welcome {query.from_user.mention_html()}!\n\n"
            "I'm your TAO Wallet Analyzer Bot. I can help you analyze your TAO holdings and generate detailed reports.\n\n"
            "🔍 What would you like to do?"
        )
        await query.message.edit_text(
            welcome_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    elif query.data == 'analyze':
        keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]]
        await query.message.edit_text(
            "Please enter your TAO wallet address:\n"
            "Example: `/analyze your_tao_wallet_address`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'help':
        keyboard = [
            [
                InlineKeyboardButton("📊 Wallet Analysis", callback_data='help_analysis'),
                InlineKeyboardButton("📈 Portfolio", callback_data='help_portfolio')
            ],
            [
                InlineKeyboardButton("⚙️ Settings Guide", callback_data='help_settings'),
                InlineKeyboardButton("🔍 Quick Start", callback_data='help_quickstart')
            ],
            [
                InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
            ]
        ]
        help_text = """
📚 *Welcome to TAO Wallet Analyzer Help*

*Essential Commands:*
• /start - Initialize the bot and see main menu
• /help - Display this help message
• /analyze <address> - Analyze a TAO wallet
• /portfolio - View your saved wallets
• /settings - Configure your preferences
• /about - Bot information and updates

*Key Features:*
1️⃣ *Wallet Analysis*
   • Real-time balance tracking
   • Transaction history
   • Performance metrics
   • Activity level assessment

2️⃣ *Portfolio Management*
   • Save multiple wallets
   • Track total holdings
   • Set custom alerts
   • Daily/weekly reports

3️⃣ *Alert System*
   • Price alerts
   • Balance changes
   • Transaction notifications
   • Staking rewards

4️⃣ *Customization*
   • Multiple currencies
   • Report styles
   • Language options
   • Notification preferences

*Tips:*
• Use `/analyze` with a wallet address to start
• Save important wallets to your portfolio
• Set up alerts for price changes
• Check documentation for detailed guides

Select a topic below for more detailed information:
"""
        await query.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'settings':
        user_id = query.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {
                'notifications': True,
                'report_style': 'detailed',
                'currency': 'USD',
                'language': 'en'
            }
        
        current_settings = user_data[user_id]
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🔔 Notifications: {'ON' if current_settings['notifications'] else 'OFF'}",
                    callback_data='toggle_notifications'
                )
            ],
            [
                InlineKeyboardButton(
                    f"📊 Report Style: {current_settings['report_style'].title()}",
                    callback_data='change_report_style'
                )
            ],
            [
                InlineKeyboardButton(
                    f"💱 Currency: {current_settings['currency']}",
                    callback_data='change_currency'
                )
            ],
            [
                InlineKeyboardButton(
                    f"🌐 Language: {current_settings['language'].upper()}",
                    callback_data='change_language'
                )
            ],
            [
                InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
            ]
        ]
        settings_text = (
            "⚙️ *Bot Settings*\n\n"
            "Configure your preferences below:\n\n"
            f"• Notifications: {'Enabled' if current_settings['notifications'] else 'Disabled'}\n"
            f"• Report Style: {current_settings['report_style'].title()}\n"
            f"• Currency: {current_settings['currency']}\n"
            f"• Language: {current_settings['language'].upper()}"
        )
        await query.message.edit_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'about':
        keyboard = [
            [
                InlineKeyboardButton("📊 Features", callback_data='about_features'),
                InlineKeyboardButton("🔒 Privacy", callback_data='about_privacy')
            ],
            [
                InlineKeyboardButton("📈 Data Sources", callback_data='about_data'),
                InlineKeyboardButton("🔄 Updates", callback_data='about_updates')
            ],
            [
                InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
            ]
        ]
        about_text = """
🤖 *TAO Wallet Analyzer Bot*

*Version:* 1.0.0
*Data Source:* MCP (Market Cap Protocol)

*Core Features:*
• Real-time TAO holdings analysis
• Detailed portfolio reports
• Price tracking and alerts
• Historical performance data
• Customizable settings

*Technology Stack:*
• Python 3.9+
• Telegram Bot API
• MCP Integration
• Real-time Data Processing

Select a topic to learn more:
"""
        await query.message.edit_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'help_analysis':
        keyboard = [[InlineKeyboardButton("🔙 Back to Help", callback_data='help')]]
        await query.message.edit_text(
            """📊 *Wallet Analysis Guide*

*How to Analyze a Wallet:*
1. Use `/analyze <wallet_address>`
2. Wait for the analysis to complete
3. View the comprehensive report

*Report Contents:*
• Current TAO Balance
• Staked Amount
• Total Portfolio Value
• 24h/7d Performance
• Transaction History
• Activity Level

*Advanced Features:*
• Historical Performance
• Price Tracking
• Volume Analysis
• Staking Statistics

*Example Usage:*
• Basic: `/analyze your_wallet_address`
• With alerts: Set up notifications
• With tracking: Save to portfolio

*Tips:*
• Refresh data every 24 hours
• Set up price alerts
• Monitor staking rewards
• Track multiple wallets

Need more help? Use the buttons below:""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'help_portfolio':
        keyboard = [[InlineKeyboardButton("🔙 Back to Help", callback_data='help')]]
        await query.message.edit_text(
            """📈 *Portfolio Management Guide*

*Managing Your Portfolio:*
1. Save wallets for easy tracking
2. View aggregated statistics
3. Monitor multiple wallets
4. Get performance reports

*Key Features:*
• Multi-wallet Tracking
• Total Value Calculation
• Performance Comparison
• Custom Alerts

*Available Reports:*
• Daily Summaries
• Weekly Analysis
• Monthly Performance
• Custom Date Ranges

*Portfolio Tools:*
• Add/Remove Wallets
• Set Alert Thresholds
• Export Statistics
• Compare Performance

*Best Practices:*
• Regular portfolio review
• Set meaningful alerts
• Track important metrics
• Update preferences

Use /portfolio to access these features.""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'help_settings':
        keyboard = [[InlineKeyboardButton("🔙 Back to Help", callback_data='help')]]
        await query.message.edit_text(
            """⚙️ *Settings Guide*

*Available Settings:*

1️⃣ *Notifications*
• Enable/disable alerts
• Choose alert types
• Set update frequency
• Custom thresholds

2️⃣ *Report Style*
• Simple view
• Detailed analysis
• Advanced metrics
• Custom layouts

3️⃣ *Currency Options*
• USD (default)
• EUR
• GBP
• JPY

4️⃣ *Language Settings*
• English (EN)
• Spanish (ES)
• French (FR)
• German (DE)

*How to Configure:*
1. Use /settings command
2. Select preference
3. Choose your option
4. Save changes

*Pro Tips:*
• Customize for your needs
• Review settings monthly
• Adjust alert thresholds
• Update preferences""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'help_quickstart':
        keyboard = [[InlineKeyboardButton("🔙 Back to Help", callback_data='help')]]
        await query.message.edit_text(
            """🚀 *Quick Start Guide*

*Getting Started:*

1️⃣ *First Steps*
• Start bot with /start
• Review available commands
• Check settings

2️⃣ *Analyze Your First Wallet*
• Use `/analyze <address>`
• Wait for results
• Review the report

3️⃣ *Portfolio Setup*
• Save important wallets
• Configure alerts
• Set preferences

4️⃣ *Regular Usage*
• Monitor holdings
• Check performance
• Review alerts
• Update settings

*Common Commands:*
• /analyze - Check wallet
• /portfolio - View holdings
• /settings - Configure bot
• /help - Get assistance

*Pro Tips:*
• Save frequently used wallets
• Set meaningful alerts
• Check daily updates
• Use detailed reports

Need more help? Just ask!""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'about_features':
        keyboard = [[InlineKeyboardButton("🔙 Back to About", callback_data='about')]]
        await query.message.edit_text(
            "🌟 *Advanced Features*\n\n"
            "*Real-time Analysis:*\n"
            "• Instant wallet balance updates\n"
            "• Live price tracking\n"
            "• Transaction history\n\n"
            "*Portfolio Management:*\n"
            "• Multiple wallet tracking\n"
            "• Performance analytics\n"
            "• Custom alerts\n\n"
            "*Customization:*\n"
            "• Report styles\n"
            "• Notification preferences\n"
            "• Currency options",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'about_privacy':
        keyboard = [[InlineKeyboardButton("🔙 Back to About", callback_data='about')]]
        await query.message.edit_text(
            "🔒 *Privacy & Security*\n\n"
            "*Data Protection:*\n"
            "• Your wallet addresses are only used to fetch public blockchain data\n"
            "• No private keys or sensitive information is stored\n"
            "• All data is encrypted in transit\n\n"
            "*Transparency:*\n"
            "• Open-source codebase\n"
            "• Regular security audits\n"
            "• Clear data usage policies",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'about_data':
        keyboard = [[InlineKeyboardButton("🔙 Back to About", callback_data='about')]]
        await query.message.edit_text(
            "📊 *Data Sources*\n\n"
            "*Primary Sources:*\n"
            "• MCP (Market Cap Protocol)\n"
            "• TAO Network API\n"
            "• Real-time price feeds\n\n"
            "*Data Updates:*\n"
            "• Prices: Every 5 minutes\n"
            "• Holdings: Real-time\n"
            "• Historical: Daily snapshots\n\n"
            "*Accuracy:*\n"
            "• Multiple data sources\n"
            "• Cross-verification\n"
            "• Error correction",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'about_updates':
        keyboard = [[InlineKeyboardButton("🔙 Back to About", callback_data='about')]]
        await query.message.edit_text(
            "🔄 *Recent Updates*\n\n"
            "*Version 1.0.0*\n"
            "• Initial release\n"
            "• Basic wallet analysis\n"
            "• Portfolio tracking\n"
            "• Customizable settings\n\n"
            "*Coming Soon:*\n"
            "• Advanced analytics\n"
            "• More currencies\n"
            "• Additional languages\n"
            "• API integration",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == 'toggle_notifications':
        user_id = query.from_user.id
        user_data[user_id]['notifications'] = not user_data[user_id]['notifications']
        await query.message.edit_text(
            f"🔔 Notifications {'enabled' if user_data[user_id]['notifications'] else 'disabled'}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Settings", callback_data='settings')
            ]]),
            parse_mode='Markdown'
        )

    elif query.data == 'change_report_style':
        user_id = query.from_user.id
        styles = ['simple', 'detailed', 'advanced']
        current_index = styles.index(user_data[user_id]['report_style'])
        user_data[user_id]['report_style'] = styles[(current_index + 1) % len(styles)]
        await query.message.edit_text(
            f"📊 Report style changed to: {user_data[user_id]['report_style'].title()}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Settings", callback_data='settings')
            ]]),
            parse_mode='Markdown'
        )

    elif query.data == 'change_currency':
        user_id = query.from_user.id
        currencies = ['USD', 'EUR', 'GBP', 'JPY']
        current_index = currencies.index(user_data[user_id]['currency'])
        user_data[user_id]['currency'] = currencies[(current_index + 1) % len(currencies)]
        await query.message.edit_text(
            f"💱 Currency changed to: {user_data[user_id]['currency']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Settings", callback_data='settings')
            ]]),
            parse_mode='Markdown'
        )

    elif query.data == 'change_language':
        user_id = query.from_user.id
        languages = ['en', 'es', 'fr', 'de']
        current_index = languages.index(user_data[user_id]['language'])
        user_data[user_id]['language'] = languages[(current_index + 1) % len(languages)]
        await query.message.edit_text(
            f"🌐 Language changed to: {user_data[user_id]['language'].upper()}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Settings", callback_data='settings')
            ]]),
            parse_mode='Markdown'
        )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_wallet))
    application.add_handler(CommandHandler("portfolio", portfolio))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("about", about))

    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 