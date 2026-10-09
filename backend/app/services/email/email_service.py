"""
Email service for automated clinical notifications and report delivery.
"""

import logging
from typing import Any, Optional

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Handles all outgoing transactional emails for the Rural AI platform."""

    def __init__(self) -> None:
        # Integrated with core settings for 2026 production security standards
        self.conf = ConnectionConfig(
            MAIL_USERNAME=getattr(settings, "MAIL_USERNAME", "admin@rural-ai.doc"),
            MAIL_PASSWORD=getattr(settings, "MAIL_PASSWORD", ""),
            MAIL_FROM=getattr(settings, "MAIL_FROM", "noreply@rural-ai.doc"),
            MAIL_PORT=getattr(settings, "MAIL_PORT", 587),
            MAIL_SERVER=getattr(settings, "MAIL_SERVER", "smtp.gmail.com"),
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        self.fast_mail = FastMail(self.conf)

    async def send_welcome_email(self, email: str, name: str) -> None:
        """Sends a personalized onboarding email to new clinical users."""
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
            <h2 style="color: #1e40af;">Welcome to Rural AI Doctor!</h2>
            <p>Hi {name},</p>
            <p>Thank you for joining our mission to provide accessible healthcare. Your account is now active.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px;">
                <strong>Available Tools:</strong>
                <ul>
                    <li>Multimodal AI Diagnostic Agents</li>
                    <li>Radiological Image Analysis</li>
                    <li>Real-time Voice Consultations</li>
                </ul>
            </div>
            <p style="margin-top: 20px;">
                <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/dashboard" 
                   style="background: #1e40af; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   Access Your Dashboard
                </a>
            </p>
            <p style="font-size: 0.8em; color: #6b7280; margin-top: 30px;">
                Best regards,<br>The Rural AI Doctor Engineering Team
            </p>
        </div>
        """
        
        await self._dispatch_email(
            subject="Welcome to Rural AI Doctor",
            recipients=[email],
            body=html
        )

    async def send_password_reset_email(self, email: str, reset_token: str) -> None:
        """Sends secure time-bound password reset links."""
        reset_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={reset_token}"
        
        html = f"""
        <div style="font-family: sans-serif;">
            <h2>Password Reset Request</h2>
            <p>We received a request to reset your password. Click the button below to proceed:</p>
            <p><a href="{reset_url}" style="color: #2563eb; font-weight: bold;">Reset My Password</a></p>
            <p>This link will expire in 24 hours for your security.</p>
            <p>If you did not request this change, you can safely ignore this email.</p>
        </div>
        """
        
        await self._dispatch_email(
            subject="Password Reset - Rural AI Doctor",
            recipients=[email],
            body=html
        )

    async def send_diagnosis_report_email(
        self,
        email: str,
        name: str,
        diagnosis_title: str,
        pdf_content: Optional[bytes] = None,
        report_id: str = "REF-DOC"
    ) -> None:
        """Delivers medical findings with secure PDF attachments."""
        html = f"""
        <div style="font-family: sans-serif;">
            <h2 style="color: #1e40af;">Clinical Summary Ready</h2>
            <p>Hi {name},</p>
            <p>Your AI-assisted diagnosis report for <strong>{diagnosis_title}</strong> is now available.</p>
            <p>Please find the clinical summary attached as a PDF for your records.</p>
            <p style="border-left: 4px solid #f59e0b; padding-left: 10px; color: #92400e;">
                <strong>Notice:</strong> This report is for informational use and should be reviewed by a licensed physician.
            </p>
        </div>
        """
        
        attachments = []
        if pdf_content:
            attachments.append({
                "file": pdf_content,
                "filename": f"Medical_Report_{report_id}.pdf",
                "content_type": "application/pdf"
            })

        await self._dispatch_email(
            subject=f"Medical Report: {diagnosis_title}",
            recipients=[email],
            body=html,
            attachments=attachments
        )

    async def send_emergency_alert_email(
        self,
        alert_email: str,
        user_id: Optional[int],
        user_location: dict[str, float],
        emergency_info: dict[str, Any],
    ) -> None:
        """Sends emergency escalation details to on-call health workers."""
        facilities = emergency_info.get("nearby_facilities") or []
        top_facility = facilities[0] if facilities else {}
        html = f"""
        <div style="font-family: sans-serif; max-width: 640px;">
            <h2 style="color: #b91c1c;">Emergency Alert Triggered</h2>
            <p><strong>User ID:</strong> {user_id or 'guest'}</p>
            <p><strong>Status:</strong> {emergency_info.get('status', 'CRITICAL')}</p>
            <p><strong>Location:</strong> {user_location.get('lat')}, {user_location.get('lng')}</p>
            <p><strong>Red Flags:</strong> {', '.join(emergency_info.get('red_flags') or ['not specified'])}</p>
            <hr />
            <p><strong>Nearest Facility:</strong> {top_facility.get('name', 'N/A')}</p>
            <p><strong>Contact:</strong> {top_facility.get('contact_number', 'N/A')}</p>
        </div>
        """
        await self._dispatch_email(
            subject="Emergency Escalation - Rural AI Doctor",
            recipients=[alert_email],
            body=html,
        )

    async def _dispatch_email(
        self, 
        subject: str, 
        recipients: list[str], 
        body: str, 
        attachments: list[dict[str, Any]] = None
    ) -> None:
        """Internal helper to manage FastMail execution and logging."""
        try:
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=body,
                subtype=MessageType.html,
                attachments=attachments or []
            )
            await self.fast_mail.send_message(message)
            logger.info(f"Successfully dispatched '{subject}' to {recipients}")
        except Exception as e:
            logger.error(f"Failed to dispatch email to {recipients}: {str(e)}")

# Global Singleton for FastAPI dependencies
email_service = EmailService()
