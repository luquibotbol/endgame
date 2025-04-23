import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AlertType(Enum):
    PRICE = "price"
    BALANCE = "balance"
    VOLUME = "volume"
    STAKING = "staking"
    TRANSACTION = "transaction"

@dataclass
class Alert:
    wallet_address: str
    alert_type: AlertType
    threshold: float
    condition: str  # "above" or "below"
    user_id: int
    created_at: datetime
    last_triggered: datetime = None
    notification_frequency: str = "hourly"  # hourly, daily, weekly
    is_active: bool = True

class AlertManager:
    def __init__(self):
        self.alerts: Dict[str, List[Alert]] = {}
        self.notification_history: Dict[str, List[datetime]] = {}

    def add_alert(self, alert: Alert) -> bool:
        """Add a new alert."""
        if alert.wallet_address not in self.alerts:
            self.alerts[alert.wallet_address] = []
            self.notification_history[alert.wallet_address] = []
        
        # Check for duplicate alerts
        for existing_alert in self.alerts[alert.wallet_address]:
            if (existing_alert.alert_type == alert.alert_type and
                existing_alert.threshold == alert.threshold and
                existing_alert.condition == alert.condition):
                return False
        
        self.alerts[alert.wallet_address].append(alert)
        return True

    def remove_alert(self, wallet_address: str, alert_type: AlertType, user_id: int) -> bool:
        """Remove an existing alert."""
        if wallet_address not in self.alerts:
            return False
        
        alerts = self.alerts[wallet_address]
        for i, alert in enumerate(alerts):
            if alert.alert_type == alert_type and alert.user_id == user_id:
                del alerts[i]
                if not alerts:
                    del self.alerts[wallet_address]
                    del self.notification_history[wallet_address]
                return True
        
        return False

    def toggle_alert(self, wallet_address: str, alert_type: AlertType, user_id: int) -> bool:
        """Toggle an alert's active status."""
        if wallet_address not in self.alerts:
            return False
        
        for alert in self.alerts[wallet_address]:
            if alert.alert_type == alert_type and alert.user_id == user_id:
                alert.is_active = not alert.is_active
                return True
        
        return False

    def get_alerts(self, wallet_address: str, user_id: int) -> List[Alert]:
        """Get all alerts for a specific wallet and user."""
        if wallet_address not in self.alerts:
            return []
        
        return [alert for alert in self.alerts[wallet_address] if alert.user_id == user_id]

    def can_send_notification(self, alert: Alert) -> bool:
        """Check if a notification can be sent based on frequency."""
        if not alert.is_active:
            return False

        if alert.wallet_address not in self.notification_history:
            return True

        last_notification = self.notification_history[alert.wallet_address][-1] if self.notification_history[alert.wallet_address] else None
        
        if not last_notification:
            return True

        now = datetime.now()
        if alert.notification_frequency == "hourly":
            return now - last_notification >= timedelta(hours=1)
        elif alert.notification_frequency == "daily":
            return now - last_notification >= timedelta(days=1)
        elif alert.notification_frequency == "weekly":
            return now - last_notification >= timedelta(weeks=1)
        
        return True

    def record_notification(self, wallet_address: str):
        """Record a notification for rate limiting."""
        if wallet_address not in self.notification_history:
            self.notification_history[wallet_address] = []
        
        self.notification_history[wallet_address].append(datetime.now())
        # Keep only the last 100 notifications
        self.notification_history[wallet_address] = self.notification_history[wallet_address][-100:]

    def check_price_alert(self, wallet_address: str, current_price: float) -> List[Alert]:
        """Check if any price alerts should be triggered."""
        triggered_alerts = []
        if wallet_address not in self.alerts:
            return triggered_alerts
        
        for alert in self.alerts[wallet_address]:
            if alert.alert_type != AlertType.PRICE or not alert.is_active:
                continue
            
            should_trigger = False
            if alert.condition == "above" and current_price > alert.threshold:
                should_trigger = True
            elif alert.condition == "below" and current_price < alert.threshold:
                should_trigger = True
            
            if should_trigger and self.can_send_notification(alert):
                alert.last_triggered = datetime.now()
                triggered_alerts.append(alert)
                self.record_notification(wallet_address)
        
        return triggered_alerts

    def check_balance_alert(self, wallet_address: str, current_balance: float) -> List[Alert]:
        """Check if any balance alerts should be triggered."""
        triggered_alerts = []
        if wallet_address not in self.alerts:
            return triggered_alerts
        
        for alert in self.alerts[wallet_address]:
            if alert.alert_type != AlertType.BALANCE or not alert.is_active:
                continue
            
            should_trigger = False
            if alert.condition == "above" and current_balance > alert.threshold:
                should_trigger = True
            elif alert.condition == "below" and current_balance < alert.threshold:
                should_trigger = True
            
            if should_trigger and self.can_send_notification(alert):
                alert.last_triggered = datetime.now()
                triggered_alerts.append(alert)
                self.record_notification(wallet_address)
        
        return triggered_alerts

    def check_volume_alert(self, wallet_address: str, current_volume: float) -> List[Alert]:
        """Check if any volume alerts should be triggered."""
        triggered_alerts = []
        if wallet_address not in self.alerts:
            return triggered_alerts
        
        for alert in self.alerts[wallet_address]:
            if alert.alert_type != AlertType.VOLUME or not alert.is_active:
                continue
            
            should_trigger = False
            if alert.condition == "above" and current_volume > alert.threshold:
                should_trigger = True
            elif alert.condition == "below" and current_volume < alert.threshold:
                should_trigger = True
            
            if should_trigger and self.can_send_notification(alert):
                alert.last_triggered = datetime.now()
                triggered_alerts.append(alert)
                self.record_notification(wallet_address)
        
        return triggered_alerts

    def check_staking_alert(self, wallet_address: str, staking_info: Dict[str, Any]) -> List[Alert]:
        """Check if any staking alerts should be triggered."""
        triggered_alerts = []
        if wallet_address not in self.alerts:
            return triggered_alerts
        
        for alert in self.alerts[wallet_address]:
            if alert.alert_type != AlertType.STAKING or not alert.is_active:
                continue
            
            should_trigger = False
            if alert.condition == "above" and staking_info.get("rewards", 0) > alert.threshold:
                should_trigger = True
            elif alert.condition == "below" and staking_info.get("rewards", 0) < alert.threshold:
                should_trigger = True
            
            if should_trigger and self.can_send_notification(alert):
                alert.last_triggered = datetime.now()
                triggered_alerts.append(alert)
                self.record_notification(wallet_address)
        
        return triggered_alerts

    def check_transaction_alert(self, wallet_address: str, transaction_info: Dict[str, Any]) -> List[Alert]:
        """Check if any transaction alerts should be triggered."""
        triggered_alerts = []
        if wallet_address not in self.alerts:
            return triggered_alerts
        
        for alert in self.alerts[wallet_address]:
            if alert.alert_type != AlertType.TRANSACTION or not alert.is_active:
                continue
            
            should_trigger = False
            if alert.condition == "above" and transaction_info.get("amount", 0) > alert.threshold:
                should_trigger = True
            elif alert.condition == "below" and transaction_info.get("amount", 0) < alert.threshold:
                should_trigger = True
            
            if should_trigger and self.can_send_notification(alert):
                alert.last_triggered = datetime.now()
                triggered_alerts.append(alert)
                self.record_notification(wallet_address)
        
        return triggered_alerts 