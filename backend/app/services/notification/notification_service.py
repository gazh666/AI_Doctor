import logging
from typing import Any, Optional

from app.core.config import settings
from app.services.email.email_service import email_service

logger = logging.getLogger(__name__)


class NotificationService:
    async def notify_emergency_worker(
        self,
        user_id: Optional[int],
        user_location: dict[str, float],
        emergency_info: dict[str, Any],
    ) -> None:
        """Simulates async emergency escalation to a healthcare worker."""
        alert_text = (
            f"[EMERGENCY ALERT] user_id={user_id or 'guest'} "
            f"location=({user_location.get('lat')}, {user_location.get('lng')}) "
            f"status={emergency_info.get('status')}"
        )
        logger.warning(alert_text)

        recipient = getattr(settings, "EMERGENCY_ALERT_EMAIL", "").strip()
        if not recipient:
            return

        try:
            await email_service.send_emergency_alert_email(
                alert_email=recipient,
                user_id=user_id,
                user_location=user_location,
                emergency_info=emergency_info,
            )
        except Exception as exc:
            logger.error("Failed to send emergency alert email: %s", exc)


notification_service = NotificationService()
