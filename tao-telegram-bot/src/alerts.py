import logging
from typing import List, Dict, Any
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types of alerts supported by the system."""
    BALANCE = auto()
    PRICE = auto()
    ACTIVITY = auto()
    WHALE = auto()

class Alert:
    """Alert configuration for a wallet."""
    def __init__(
        self,
        user_id: int,
        wallet_address: str,
        alert_type: AlertType,
        threshold: float,
        created_at: datetime
    ):
        self.user_id = user_id
        self.wallet_address = wallet_address
        self.alert_type = alert_type
        self.threshold = threshold
        self.created_at = created_at
        self.last_triggered = None
        self.is_active = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary format."""
        return {
            "user_id": self.user_id,
            "wallet_address": self.wallet_address,
            "alert_type": self.alert_type.name,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create alert from dictionary format."""
        return cls(
            user_id=data["user_id"],
            wallet_address=data["wallet_address"],
            alert_type=AlertType[data["alert_type"]],
            threshold=data["threshold"],
            created_at=datetime.fromisoformat(data["created_at"])
        )

class AlertManager:
    """Manages alerts for all users."""
    def __init__(self):
        self.alerts: Dict[int, List[Alert]] = {}  # user_id -> list of alerts

    def add_alert(self, alert: Alert) -> None:
        """Add a new alert for a user."""
        if alert.user_id not in self.alerts:
            self.alerts[alert.user_id] = []
        self.alerts[alert.user_id].append(alert)
        logger.info(f"Added alert for user {alert.user_id}: {alert.alert_type.name}")

    def remove_alert(self, user_id: int, alert_index: int) -> bool:
        """Remove an alert by its index."""
        try:
            if user_id in self.alerts and 0 <= alert_index < len(self.alerts[user_id]):
                self.alerts[user_id].pop(alert_index)
                logger.info(f"Removed alert {alert_index} for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing alert: {e}")
            return False

    def get_user_alerts(self, user_id: int) -> List[Alert]:
        """Get all alerts for a user."""
        return self.alerts.get(user_id, [])

    def get_wallet_alerts(self, user_id: int, wallet_address: str) -> List[Alert]:
        """Get all alerts for a specific wallet."""
        return [
            alert for alert in self.get_user_alerts(user_id)
            if alert.wallet_address == wallet_address
        ]

    def toggle_alert(self, user_id: int, alert_index: int) -> bool:
        """Toggle an alert's active status."""
        try:
            if user_id in self.alerts and 0 <= alert_index < len(self.alerts[user_id]):
                alert = self.alerts[user_id][alert_index]
                alert.is_active = not alert.is_active
                logger.info(f"Toggled alert {alert_index} for user {user_id}: {alert.is_active}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error toggling alert: {e}")
            return False

    async def check_alerts(self, wallet_data: Dict[str, Any]) -> List[Alert]:
        """Check if any alerts should be triggered based on wallet data."""
        triggered_alerts = []
        
        try:
            for user_alerts in self.alerts.values():
                for alert in user_alerts:
                    if not alert.is_active:
                        continue
                        
                    if alert.wallet_address != wallet_data["address"]:
                        continue

                    should_trigger = False
                    
                    if alert.alert_type == AlertType.BALANCE:
                        current_balance = wallet_data.get("current_balance", 0)
                        should_trigger = current_balance >= alert.threshold
                        
                    elif alert.alert_type == AlertType.PRICE:
                        current_price = wallet_data.get("market_context", {}).get("price", 0)
                        should_trigger = current_price >= alert.threshold
                        
                    elif alert.alert_type == AlertType.ACTIVITY:
                        tx_count = wallet_data.get("transaction_analysis", {}).get("transaction_count", 0)
                        should_trigger = tx_count >= alert.threshold
                        
                    elif alert.alert_type == AlertType.WHALE:
                        transactions = wallet_data.get("transaction_analysis", {}).get("transactions", [])
                        for tx in transactions:
                            if tx.get("amount", 0) >= alert.threshold:
                                should_trigger = True
                                break

                    if should_trigger:
                        alert.last_triggered = datetime.now()
                        triggered_alerts.append(alert)
                        logger.info(f"Alert triggered for user {alert.user_id}: {alert.alert_type.name}")
                        
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            
        return triggered_alerts