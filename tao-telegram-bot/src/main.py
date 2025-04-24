import os
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from tao_analyzer import TAOAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from alerts import AlertManager, Alert, AlertType
from datetime import datetime, timedelta
import json

# Load environment variables
load_dotenv('../.env.local')  # Use relative path from src directory
token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env.local file")

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

# Conversation states
ENTERING_ALERT_VALUE = 1

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

        # Get wallet analysis
        analysis = await analyzer.analyze_wallet(wallet_address)
        
        if "error" in analysis:
            await update.message.reply_text(
                f"❌ Error: {analysis['error']}\n\n"
                "Please try again later or contact support if the issue persists."
            )
            return

        # Get market context
        market_context = await analyzer.get_market_context()
        
        # Get sentiment analysis
        sentiment = await sentiment_analyzer.analyze(analysis, market_context._asdict())

        # Format and send the report
        report_text = (
            f"📊 *Wallet Analysis Report*\n\n"
            f"*Wallet:* `{wallet_address}`\n"
            f"*Current Balance:* {analysis['current_balance']} TAO\n"
            f"*Transaction Count:* {analysis['transaction_analysis']['transaction_count']}\n"
            f"*Activity Level:* {analysis['activity_level']}\n\n"
            f"*Market Context:*\n"
            f"• 24h Price Change: {market_context.price_change_24h}%\n"
            f"• Market Volume: {market_context.market_volume} TAO\n"
            f"• Market Sentiment: {market_context.market_sentiment}\n\n"
            f"*Sentiment Analysis:*\n{sentiment}\n\n"
            f"*Last Updated:* {analysis['last_updated']}\n\n"
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
        logger.error(f"Error analyzing wallet: {e}")
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
                f"🔍 {wallet[:8]}...",
                callback_data=f'view_{wallet}'
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
    
    data = query.data
    
    # Main Menu Buttons
    if data == 'back_to_main':
        await start(update, context)
        
    elif data == 'analyze':
        keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]]
        await query.message.edit_text(
            "Please enter your TAO wallet address:\n"
            "Example: `/analyze your_tao_wallet_address`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data == 'help':
        await help_command(update, context)
        
    elif data == 'settings':
        await settings(update, context)
        
    elif data == 'about':
        await about(update, context)
        
    # Help Menu Buttons
    elif data == 'help_analysis':
        keyboard = [
            [InlineKeyboardButton("📈 View Example", callback_data='help_analysis_example')],
            [InlineKeyboardButton("🔙 Back to Help", callback_data='help')]
        ]
        await query.message.edit_text(
            """📊 *Wallet Analysis Guide*\n\n
*How to Analyze a Wallet:*
1. Use `/analyze <wallet_address>`
2. Wait for the analysis to complete
3. View the comprehensive report

*Report Contents:*
• Current TAO Balance
• Transaction History
• Performance Metrics
• Activity Level
• Market Context
• Risk Analysis

*Advanced Features:*
• Historical Data
• Price Tracking
• Alert System
• Portfolio Integration""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    elif data == 'help_portfolio':
        keyboard = [
            [InlineKeyboardButton("💼 View Portfolio", callback_data='view_portfolio')],
            [InlineKeyboardButton("🔙 Back to Help", callback_data='help')]
        ]
        await query.message.edit_text(
            """📈 *Portfolio Management*\n\n
*Features:*
• Save multiple wallets
• Track total holdings
• Monitor performance
• Set custom alerts

*Available Tools:*
• Add/Remove wallets
• Set alert thresholds
• View statistics
• Export data

Use /portfolio to manage your wallets.""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    # Wallet Analysis Buttons
    elif data.startswith('analyze_'):
        wallet_address = data.replace('analyze_', '')
        try:
            # Get wallet analysis
            analysis = await analyzer.analyze_wallet(wallet_address)
            if "error" in analysis:
                await query.message.edit_text(
                    f"❌ Error: {analysis['error']}\n\n"
                    "Please try again later or contact support if the issue persists.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
                    ]])
                )
                return

            # Get market context and sentiment
            market_context = await analyzer.get_market_context()
            sentiment = await sentiment_analyzer.analyze(analysis, market_context._asdict())

            # Format and send the report
            report_text = (
                f"📊 *Wallet Analysis Report*\n\n"
                f"*Wallet:* `{wallet_address}`\n"
                f"*Current Balance:* {analysis['current_balance']} TAO\n"
                f"*Transaction Count:* {analysis['transaction_analysis']['transaction_count']}\n"
                f"*Activity Level:* {analysis['activity_level']}\n\n"
                f"*Market Context:*\n"
                f"• 24h Price Change: {market_context.price_change_24h}%\n"
                f"• Market Volume: {market_context.market_volume} TAO\n"
                f"• Market Sentiment: {market_context.market_sentiment}\n\n"
                f"*Sentiment Analysis:*\n{sentiment}\n\n"
                f"*Last Updated:* {analysis['last_updated']}"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📈 View History", callback_data=f'history_{wallet_address}'),
                    InlineKeyboardButton("💾 Save to Portfolio", callback_data=f'save_{wallet_address}')
                ],
                [
                    InlineKeyboardButton("🔔 Set Alerts", callback_data=f'alerts_{wallet_address}'),
                    InlineKeyboardButton("📊 Advanced Stats", callback_data=f'stats_{wallet_address}')
                ],
                [
                    InlineKeyboardButton("🔄 Update", callback_data=f'analyze_{wallet_address}'),
                    InlineKeyboardButton("🔙 Main Menu", callback_data='back_to_main')
                ]
            ]

            await query.message.edit_text(
                report_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error analyzing wallet: {e}")
            await query.message.edit_text(
                "❌ An error occurred while analyzing the wallet.\n"
                "Please try again later or contact support if the issue persists.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
                ]])
            )
            
    # History View Buttons
    elif data.startswith('history_'):
        wallet_address = data.replace('history_', '')
        await view_history(update, context, wallet_address)
        
    elif data.startswith('refresh_history_'):
        wallet_address = data.replace('refresh_history_', '')
        await view_history(update, context, wallet_address)
        
    # Portfolio Buttons
    elif data.startswith('save_'):
        wallet_address = data.replace('save_', '')
        await save_to_portfolio(update, context, wallet_address)
        
    elif data == 'view_portfolio':
        await portfolio(update, context)
        
    elif data.startswith('remove_wallet_'):
        wallet_address = data.replace('remove_wallet_', '')
        user_id = query.from_user.id
        if user_id in user_data and "portfolio" in user_data[user_id]:
            if wallet_address in user_data[user_id]["portfolio"]:
                user_data[user_id]["portfolio"].remove(wallet_address)
                await query.message.edit_text(
                    f"✅ Wallet removed from portfolio: `{wallet_address}`",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📊 View Portfolio", callback_data='view_portfolio')
                    ]]),
                    parse_mode='Markdown'
                )
                return
        await query.message.edit_text(
            "❌ Wallet not found in portfolio",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data='view_portfolio')
            ]])
        )
        
    # Alert Buttons
    elif data.startswith('alerts_'):
        wallet_address = data.replace('alerts_', '')
        await set_alert(update, context, wallet_address)
        
    elif data.startswith('alert_'):
        _, alert_type, wallet_address = data.split('_')
        context.user_data['pending_alert'] = {
            'wallet_address': wallet_address,
            'alert_type': AlertType[alert_type.upper()]
        }
        
        await query.message.edit_text(
            f"Please enter the threshold value for your {alert_type} alert:\n\n"
            "Examples:\n"
            "• Balance: 1000 (TAO)\n"
            "• Price: 50 (USD)\n"
            "• Activity: 10 (transactions)\n"
            "• Whale: 5000 (minimum TAO for whale tx)\n",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data=f'alerts_{wallet_address}')
            ]]),
            parse_mode='Markdown'
        )
        return ENTERING_ALERT_VALUE
        
    elif data.startswith('remove_alert_'):
        alert_index = int(data.split('_')[2])
        user_id = query.from_user.id
        if alert_manager.remove_alert(user_id, alert_index):
            await query.message.edit_text(
                "✅ Alert removed successfully",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Alerts", callback_data='view_alerts')
                ]])
            )
        else:
            await query.message.edit_text(
                "❌ Error removing alert",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Alerts", callback_data='view_alerts')
                ]])
            )
            
    # Advanced Stats Buttons
    elif data.startswith('stats_'):
        wallet_address = data.replace('stats_', '')
        await view_advanced_stats(update, context, wallet_address)
        
    elif data.startswith('refresh_stats_'):
        wallet_address = data.replace('refresh_stats_', '')
        await view_advanced_stats(update, context, wallet_address)
        
    # Settings Buttons
    elif data == 'toggle_notifications':
        user_id = query.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {'notifications': True}
        user_data[user_id]['notifications'] = not user_data[user_id].get('notifications', True)
        await settings(update, context)
        
    elif data == 'change_currency':
        user_id = query.from_user.id
        currencies = ['USD', 'EUR', 'GBP', 'JPY']
        if user_id not in user_data:
            user_data[user_id] = {'currency': 'USD'}
        current = user_data[user_id].get('currency', 'USD')
        next_idx = (currencies.index(current) + 1) % len(currencies)
        user_data[user_id]['currency'] = currencies[next_idx]
        await settings(update, context)
        
    elif data == 'change_language':
        user_id = query.from_user.id
        languages = ['EN', 'ES', 'FR', 'DE']
        if user_id not in user_data:
            user_data[user_id] = {'language': 'EN'}
        current = user_data[user_id].get('language', 'EN')
        next_idx = (languages.index(current) + 1) % len(languages)
        user_data[user_id]['language'] = languages[next_idx]
        await settings(update, context)
        
    # About Buttons
    elif data.startswith('about_'):
        section = data.replace('about_', '')
        keyboard = [[InlineKeyboardButton("🔙 Back to About", callback_data='about')]]
        
        if section == 'features':
            await query.message.edit_text(
                """🌟 *Features*\n\n
• Real-time wallet analysis
• Portfolio management
• Custom alerts
• Advanced statistics
• Historical data tracking
• Market sentiment analysis""",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        elif section == 'privacy':
            await query.message.edit_text(
                """🔒 *Privacy*\n\n
• No private keys stored
• Public data only
• Encrypted communications
• Regular security audits
• Transparent data usage""",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        elif section == 'updates':
            await query.message.edit_text(
                """🔄 *Updates*\n\n
*Current Version:* 1.0.0
*Last Updated:* 2025-04-23
*Latest Features:*
• Advanced analytics
• Portfolio tracking
• Alert system
• Market insights""",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

async def view_history(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Display historical data for a wallet."""
    try:
        historical_data = await analyzer.get_historical_data(wallet_address)
        
        # Format historical data
        history_text = (
            f"📈 *Historical Data for* `{wallet_address}`\n\n"
            "*Balance History (Last 30 days):*\n"
            f"Current: {historical_data['balance_history'][-1]} TAO\n"
            f"30d High: {max(historical_data['balance_history'])} TAO\n"
            f"30d Low: {min(historical_data['balance_history'])} TAO\n\n"
            "*Recent Transactions:*\n"
        )

        for tx in historical_data['transaction_history'][:5]:
            direction = "📥" if tx['type'] == "in" else "📤"
            history_text += (
                f"{direction} {tx['amount']} TAO\n"
                f"Time: {tx['timestamp'].strftime('%Y-%m-%d %H:%M')}\n\n"
            )

        keyboard = [
            [
                InlineKeyboardButton("📊 Price Chart", callback_data=f'price_chart_{wallet_address}'),
                InlineKeyboardButton("🔄 Update", callback_data=f'refresh_history_{wallet_address}')
            ],
            [
                InlineKeyboardButton("🔙 Back to Analysis", callback_data=f'analyze_{wallet_address}')
            ]
        ]

        await update.callback_query.message.edit_text(
            history_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error viewing history: {e}")
        await update.callback_query.message.edit_text(
            "❌ Error retrieving historical data. Please try again later."
        )

async def save_to_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Save a wallet to user's portfolio."""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {"portfolio": []}
    
    if wallet_address not in user_data[user_id]["portfolio"]:
        user_data[user_id]["portfolio"].append(wallet_address)
        
        keyboard = [
            [
                InlineKeyboardButton("📊 View Portfolio", callback_data='view_portfolio'),
                InlineKeyboardButton("🔙 Back", callback_data=f'analyze_{wallet_address}')
            ]
        ]
        
        await update.callback_query.message.edit_text(
            f"✅ Wallet `{wallet_address}` has been added to your portfolio!\n\n"
            f"You can view all your saved wallets using /portfolio",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.message.edit_text(
            "This wallet is already in your portfolio!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data=f'analyze_{wallet_address}')
            ]])
        )

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Set up alerts for a wallet."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance Change", callback_data=f'alert_balance_{wallet_address}'),
            InlineKeyboardButton("💱 Price Alert", callback_data=f'alert_price_{wallet_address}')
        ],
        [
            InlineKeyboardButton("📊 Activity Alert", callback_data=f'alert_activity_{wallet_address}'),
            InlineKeyboardButton("🐋 Whale Alert", callback_data=f'alert_whale_{wallet_address}')
        ],
        [
            InlineKeyboardButton("🔙 Back to Analysis", callback_data=f'analyze_{wallet_address}')
        ]
    ]
    
    await update.callback_query.message.edit_text(
        "🔔 *Alert Settings*\n\n"
        "Choose the type of alert you want to set up:\n\n"
        "• *Balance Change*: Get notified of significant balance changes\n"
        "• *Price Alert*: Set price targets for notifications\n"
        "• *Activity Alert*: Monitor transaction frequency\n"
        "• *Whale Alert*: Track large transactions\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def view_advanced_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Display advanced statistics for a wallet."""
    try:
        # Get comprehensive analytics
        analysis = await analyzer.analyze_wallet(wallet_address)
        risk_metrics = analysis['risk_metrics']
        transaction_analysis = analysis['transaction_analysis']
        market_context = analysis['market_context']
        
        # Format advanced statistics
        stats_text = (
            f"📊 *Advanced Statistics for* `{wallet_address}`\n\n"
            "*Risk Analysis:*\n"
            f"• Risk Score: {risk_metrics['risk_score']:.2f}\n"
            f"• Risk Level: {risk_metrics['risk_level']}\n"
            f"• Concentration Risk: {risk_metrics['concentration_risk']:.2f}\n"
            f"• Liquidity Risk: {risk_metrics['liquidity_risk']:.2f}\n\n"
            "*Transaction Patterns:*\n"
            f"• Total Transactions: {transaction_analysis['transaction_count']}\n"
            f"• Average Amount: {transaction_analysis['average_amount']:.2f} TAO\n"
            f"• Activity Frequency: {transaction_analysis['frequency']}\n"
            f"• Whale Activity: {'Yes' if transaction_analysis['whale_activity']['is_whale_active'] else 'No'}\n\n"
            "*Market Context:*\n"
            f"• Market Volume: {market_context['market_volume']} TAO\n"
            f"• 24h Price Change: {market_context['price_change_24h']}%\n"
            f"• Market Sentiment: {market_context['market_sentiment']}\n"
        )

        keyboard = [
            [
                InlineKeyboardButton("📈 Performance", callback_data=f'performance_{wallet_address}'),
                InlineKeyboardButton("📊 Risk Analysis", callback_data=f'risk_{wallet_address}')
            ],
            [
                InlineKeyboardButton("🔄 Update Stats", callback_data=f'refresh_stats_{wallet_address}'),
                InlineKeyboardButton("🔙 Back", callback_data=f'analyze_{wallet_address}')
            ]
        ]

        await update.callback_query.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error viewing advanced stats: {e}")
        await update.callback_query.message.edit_text(
            "❌ Error retrieving advanced statistics. Please try again later."
        )

async def handle_alert_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle alert value input from user."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    try:
        alert_value = float(message_text)
        alert_data = context.user_data.get('pending_alert', {})
        
        if not alert_data:
            await update.message.reply_text("❌ Alert setup expired. Please start over.")
            return ConversationHandler.END
            
        alert = Alert(
            user_id=user_id,
            wallet_address=alert_data['wallet_address'],
            alert_type=alert_data['alert_type'],
            threshold=alert_value,
            created_at=datetime.now()
        )
        
        alert_manager.add_alert(alert)
        
        await update.message.reply_text(
            f"✅ Alert set successfully!\n\n"
            f"You will be notified when the condition is met.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Alerts", callback_data=f'alerts_{alert_data["wallet_address"]}')
            ]])
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number.\n"
            "Example: 100.5"
        )
        return ENTERING_ALERT_VALUE

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add conversation handler for alerts
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^alert_')],
        states={
            ENTERING_ALERT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert_value)]
        },
        fallbacks=[CallbackQueryHandler(button_handler)]
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_wallet))
    application.add_handler(CommandHandler("portfolio", portfolio))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()