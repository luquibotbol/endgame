from typing import Dict, Any
from datetime import datetime

class ReportFormatter:
    @staticmethod
    def format_report(report_data: dict) -> str:
        """Format the complete analysis report with all metrics."""
        if "error" in report_data:
            return f"❌ Error: {report_data['error']}"

        sections = [
            ReportFormatter._format_header(report_data),
            ReportFormatter._format_balance_section(report_data),
            ReportFormatter._format_predictive_section(report_data),
            ReportFormatter._format_whale_section(report_data),
            ReportFormatter._format_risk_section(report_data),
            ReportFormatter._format_market_section(report_data),
            ReportFormatter._format_transaction_section(report_data),
            ReportFormatter._format_social_section(report_data.get("social_metrics", {}))
        ]

        return "\n\n".join(filter(None, sections))

    @staticmethod
    def _format_header(data: dict) -> str:
        """Format the report header with wallet information."""
        return (
            f"📊 *TAO Wallet Analysis Report*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Wallet: `{data['wallet_address']}`\n"
            f"🕒 Last Updated: {data['last_updated']}"
        )

    @staticmethod
    def _format_balance_section(data: dict) -> str:
        """Format the balance summary section."""
        return (
            f"💰 *Balance Summary*\n"
            f"Current Balance: {data['current_balance']:,.2f} TAO\n"
            f"Staked Amount: {data['staked_amount']:,.2f} TAO\n"
            f"Total Value: {data['total_value']:,.2f} TAO"
        )

    @staticmethod
    def _format_predictive_section(data: dict) -> str:
        """Format the predictive metrics section."""
        pred = data.get('predictive_metrics', {})
        if not pred:
            return ""

        trend_emoji = "📈" if pred['trend_direction'] == "Upward" else "📉"
        confidence_bar = ReportFormatter._get_progress_bar(pred['trend_confidence'])
        
        return (
            f"{trend_emoji} *Price Trend Analysis*\n"
            f"Direction: {pred['trend_direction']}\n"
            f"Confidence: {confidence_bar} ({pred['trend_confidence']:.1%})\n"
            f"Predicted Change: {pred['predicted_change']:+.2f}%\n"
            f"Support Level: {pred['support_level']:,.2f} TAO\n"
            f"Resistance Level: {pred['resistance_level']:,.2f} TAO"
        )

    @staticmethod
    def _format_whale_section(data: dict) -> str:
        """Format the whale activity section."""
        whale = data.get('transaction_analysis', {}).get('whale_activity', {})
        if not whale or "error" in whale:
            return ""

        activity_status = "🐋 Active" if whale.get('is_whale_active') else "😴 Inactive"
        
        return (
            f"🐋 *Whale Activity*\n"
            f"Status: {activity_status}\n"
            f"Recent Transactions: {whale.get('recent_whale_activity', 0)}\n"
            f"Total Volume: {whale.get('whale_volume', 0):,.2f} TAO\n"
            f"Threshold: {whale.get('whale_threshold', 0):,.2f} TAO"
        )

    @staticmethod
    def _format_risk_section(data: dict) -> str:
        """Format the risk metrics section with visual indicators."""
        risk = data.get('risk_metrics', {})
        if not risk:
            return ""

        risk_level = ReportFormatter._get_risk_indicator(risk['risk_score'])
        var_formatted = f"{abs(risk.get('value_at_risk_95', 0) * 100):.2f}%"
        beta_formatted = f"{risk.get('beta', 0):.2f}"
        
        return (
            f"⚠️ *Risk Analysis*\n"
            f"Risk Level: {risk_level}\n"
            f"Value at Risk (95%): {var_formatted}\n"
            f"Market Beta: {beta_formatted}\n"
            f"Volatility: {risk['volatility']:.2f}%\n"
            f"Sharpe Ratio: {risk['sharpe_ratio']:.2f}\n"
            f"Max Drawdown: {risk['max_drawdown']:.2f}%\n"
            f"Diversification: {ReportFormatter._get_progress_bar(risk['diversification_score'])}"
        )

    @staticmethod
    def _format_market_section(data: dict) -> str:
        """Format the market context section."""
        market = data.get('market_context', {})
        if not market:
            return ""

        volume_change = market.get('volume_change_24h', 0)
        volume_emoji = "📈" if volume_change > 0 else "📉"
        
        return (
            f"📊 *Market Context*\n"
            f"Rank: #{market['market_cap_rank']}\n"
            f"Market Share: {market['market_dominance']:.2f}%\n"
            f"24h Volume: {market['volume_24h']:,.2f} TAO\n"
            f"Volume Change: {volume_emoji} {volume_change:+.2f}%\n"
            f"BTC Correlation: {market['correlation_btc']:.2f}\n"
            f"ETH Correlation: {market['correlation_eth']:.2f}\n"
            f"Sentiment: {ReportFormatter._get_sentiment_emoji(market['market_sentiment'])}"
        )

    @staticmethod
    def _format_transaction_section(data: dict) -> str:
        """Format the transaction patterns section."""
        patterns = data.get('transaction_analysis', {}).get('patterns', [])
        if not patterns:
            return ""

        pattern_lines = []
        for pattern in patterns:
            confidence_bar = ReportFormatter._get_progress_bar(pattern['confidence'])
            pattern_lines.append(
                f"• {pattern['amount']:,.2f} TAO {pattern['frequency']}\n"
                f"  Confidence: {confidence_bar}"
            )

        return (
            f"🔄 *Transaction Patterns*\n"
            f"{chr(10).join(pattern_lines)}"
        )

    @staticmethod
    def _get_progress_bar(value: float, length: int = 10) -> str:
        """Generate a visual progress bar."""
        filled = int(value * length)
        empty = length - filled
        return f"{'▓' * filled}{'░' * empty}"

    @staticmethod
    def _get_risk_indicator(risk_score: float) -> str:
        """Generate a visual risk indicator."""
        if risk_score < 0.3:
            return "🟢 Low"
        elif risk_score < 0.7:
            return "🟡 Medium"
        else:
            return "🔴 High"

    @staticmethod
    def _format_social_section(social: dict) -> str:
        """Format social metrics with engagement indicators."""
        if not social:
            return (
                f"👥 *Social Activity*\n"
                f"━━━━━━━━━━━━━\n"
                f"No social data available"
            )

        # Calculate engagement level
        engagement_level = "High" if social['total_engagement'] > 1000 else "Medium" if social['total_engagement'] > 100 else "Low"
        engagement_emoji = "🔥" if engagement_level == "High" else "📈" if engagement_level == "Medium" else "📉"

        return (
            f"👥 *Social Activity*\n"
            f"━━━━━━━━━━━━━\n"
            f"• Tweet Volume: {social['tweet_count']} tweets\n"
            f"• Engagement: {engagement_emoji} {social['total_engagement']} ({engagement_level})\n"
            f"• Sentiment: {ReportFormatter._get_sentiment_emoji(social['average_sentiment'])} "
            f"({social['average_sentiment']:.2f})"
        )

    @staticmethod
    def _get_sentiment_emoji(sentiment: str) -> str:
        """Get appropriate emoji for sentiment."""
        sentiments = {
            "Very Bullish": "🚀",
            "Bullish": "📈",
            "Neutral": "➡️",
            "Bearish": "📉",
            "Very Bearish": "💥"
        }
        return f"{sentiments.get(sentiment, '❓')} {sentiment}" 