"""
SMS Service for sending text messages via TextBelt API.
Migrated and enhanced from original Streamlit application.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from app.core.config import settings
from app.models.message import MessageCreate
from app.models.tenant import Tenant


logger = logging.getLogger(__name__)


class SMSService:
    """
    Service for sending SMS messages using TextBelt API.
    Handles both test and production environments.
    """

    def __init__(self):
        self.api_base = "https://textbelt.com/text"
        self.api_key = settings.sms_api_key
        self.api_key_test = f"{self.api_key}_test" if self.api_key else None
        self.company_name = settings.company_name
        self.footer_message = f"Thank you!\n{self.company_name}"

        # Message templates from original code
        self.templates = {
            "rent_reminder": f"Hello {{name}}, this is {self.company_name}\nJust a reminder, your rent is due on {{rent_day}}. Please note a fee will be charged for any late payments. Thank you!",
            "rent_reminder_short": f"Hi {{name}} - Just a reminder, your rent is due on {{due_date}}",
            "payment_received": f"Hello {{name}}, this is {self.company_name}\nWe have received your payment on-time. Thank you!",
            "maintenance_notice": f"Hi {{name}} - Just a reminder, your maintenance will be conducted on {{date}}",
            "trash_reminder": f"Hi {{name}} - Trash is collected on Monday and Sunday, thank you!",
            "trash_thanks": f"Hi {{name}} - Thank you for timely throwing out the trash!",
            "late_fee_notice": f"Hello {{name}}, this is {self.company_name}\nYour rent is now overdue. A late fee has been applied to your account. Please contact us immediately to arrange payment.",
            "custom": "{{message}}",
        }

    async def test_api_key(self, test_mode: bool = True) -> Dict[str, Any]:
        """
        Test the SMS API key to ensure it's valid.

        Args:
            test_mode: Whether to use test key

        Returns:
            Dict with success status and message
        """
        try:
            key = self.api_key_test if test_mode else self.api_key
            if not key:
                return {"success": False, "error": "SMS API key not configured"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base,
                    data={
                        "phone": "5555551234",  # Test number
                        "message": "API key test",
                        "key": key,
                    },
                ) as response:
                    result = await response.json()

                    logger.info(f"API key test result: {result}")
                    return {
                        "success": result.get("success", False),
                        "message": result.get("message", "Unknown error"),
                        "quotaRemaining": result.get("quotaRemaining"),
                    }

        except Exception as e:
            logger.error(f"SMS API key test failed: {str(e)}")
            return {"success": False, "error": f"API key test failed: {str(e)}"}

    def _replace_placeholders(self, message: str, tenant: Tenant, **kwargs) -> str:
        """
        Replace placeholders in message with tenant data.

        Args:
            message: Template message with placeholders
            tenant: Tenant object
            **kwargs: Additional replacement values (including rent_day)

        Returns:
            Message with placeholders replaced
        """
        # Calculate dynamic due date from tenant's due_date field
        current_due_date = tenant.due_date
        if isinstance(current_due_date, str):
            try:
                current_due_date = datetime.strptime(current_due_date, "%Y-%m-%d").date()
            except ValueError:
                # Default to first of current month if parsing fails
                current_due_date = date.today().replace(day=1)
        elif not current_due_date:
            # Default to first of current month if no due date
            current_due_date = date.today().replace(day=1)
        
        # Format due date for display
        formatted_due_date = current_due_date.strftime("%B %d") if current_due_date else "the due date"
        
        # Calculate dynamic rent_day - always use current month with specified day
        rent_day_num = kwargs.get("rent_day", 5)  # Default to 5th
        today = date.today()
        current_month_rent_day = today.replace(day=min(rent_day_num, 28))  # Cap at 28 to avoid month-end issues
        formatted_rent_day = current_month_rent_day.strftime("%B %d")
        
        # For display with ordinal suffix
        day = current_month_rent_day.day
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        formatted_rent_day_ordinal = f"{current_month_rent_day.strftime('%B')} {day}{suffix}"
        
        replacements = {
            # Original placeholders
            "name": tenant.name,
            "unit": tenant.unit_number or "your unit", 
            "phone": tenant.contact,  # Fixed: use contact instead of phone
            "due_date": formatted_due_date,
            "date": kwargs.get("date", "the scheduled date"),
            "amount": kwargs.get("amount", ""),
            "message": kwargs.get("message", ""),
            
            # Dynamic rent day placeholders
            "rent_day": formatted_rent_day_ordinal,  # e.g., "August 5th"
            "rent_date": formatted_rent_day,  # e.g., "August 05"
            
            # Additional common placeholders
            "tenant_name": tenant.name,
            "tenant_phone": tenant.contact,
            "tenant_contact": tenant.contact,
            "rent_amount": str(tenant.rent) if tenant.rent else "your rent amount",
            "rent": str(tenant.rent) if tenant.rent else "your rent amount",
            "building": tenant.building or "your building",
            "company_name": self.company_name,
        }

        # Replace placeholders
        formatted_message = message
        for key, value in replacements.items():
            formatted_message = formatted_message.replace(f"{{{key}}}", str(value))

        return formatted_message

    async def send_sms(
        self,
        tenant: Tenant,
        message: str,
        test_mode: bool = False,
        template_name: Optional[str] = None,
        **template_vars,
    ) -> Dict[str, Any]:
        """
        Send SMS to a single tenant.

        Args:
            tenant: Tenant to send message to
            message: Message content or template name
            test_mode: Whether to use test mode
            template_name: Name of template to use
            **template_vars: Variables for template replacement

        Returns:
            Dict with sending result
        """
        try:
            # Use template if specified
            if template_name and template_name in self.templates:
                message = self.templates[template_name]

            # Replace placeholders
            formatted_message = self._replace_placeholders(
                message, tenant, **template_vars
            )

            # Add footer
            full_message = f"{formatted_message}\n\n{self.footer_message}"

            # Select API key
            key = self.api_key_test if test_mode else self.api_key
            if not key:
                return {
                    "success": False,
                    "error": "SMS API key not configured",
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                }

            # Prepare SMS data
            sms_data = {
                "phone": tenant.contact,  # Fixed: use contact instead of phone
                "message": full_message,
                "key": key,
            }
            
            # Add webhook URL for replies (only for non-test mode)
            if not test_mode:
                # In production, this should be your actual domain
                webhook_url = "https://your-domain.com/api/v1/webhooks/sms-reply"
                sms_data["replyWebhookUrl"] = webhook_url

            # Send SMS
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base,
                    data=sms_data,
                ) as response:
                    result = await response.json()

                    success = result.get("success", False)

                    logger.info(
                        f"SMS {'sent' if success else 'failed'} to {tenant.name} "
                        f"({tenant.contact}): {result}"
                    )

                    return {
                        "success": success,
                        "message_id": result.get("textId"),
                        "error": result.get("error"),
                        "quota_remaining": result.get("quotaRemaining"),
                        "tenant_id": tenant.id,
                        "tenant_name": tenant.name,
                        "phone": tenant.contact,  # Fixed: use contact instead of phone
                        "content": full_message,
                        "test_mode": test_mode,
                    }

        except Exception as e:
            error_msg = f"Failed to send SMS to {tenant.name}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
            }

    async def send_bulk_sms(
        self,
        tenants: List[Tenant],
        message: str,
        test_mode: bool = False,
        template_name: Optional[str] = None,
        delay_seconds: float = 1.0,
        **template_vars,
    ) -> Dict[str, Any]:
        """
        Send SMS to multiple tenants with rate limiting.

        Args:
            tenants: List of tenants to send to
            message: Message content or template name
            test_mode: Whether to use test mode
            template_name: Name of template to use
            delay_seconds: Delay between messages for rate limiting
            **template_vars: Variables for template replacement

        Returns:
            Dict with bulk sending results
        """
        results = []
        successful_sends = 0
        failed_sends = 0

        logger.info(f"Starting bulk SMS send to {len(tenants)} tenants")

        for tenant in tenants:
            try:
                result = await self.send_sms(
                    tenant=tenant,
                    message=message,
                    test_mode=test_mode,
                    template_name=template_name,
                    **template_vars,
                )

                results.append(result)

                if result["success"]:
                    successful_sends += 1
                else:
                    failed_sends += 1

                # Rate limiting delay
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            except Exception as e:
                logger.error(f"Error in bulk SMS for tenant {tenant.id}: {str(e)}")
                failed_sends += 1
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "tenant_id": tenant.id,
                        "tenant_name": tenant.name,
                    }
                )

        success_rate = (successful_sends / len(tenants)) * 100 if tenants else 0

        logger.info(
            f"Bulk SMS completed: {successful_sends} successful, {failed_sends} failed "
            f"({success_rate:.1f}% success rate)"
        )

        return {
            "total_tenants": len(tenants),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "success_rate": round(success_rate, 1),
            "results": results,
            "test_mode": test_mode,
        }

    async def send_rent_reminders(
        self, unpaid_tenants: List[Tenant], due_date: str, test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send rent reminder messages to unpaid tenants.

        Args:
            unpaid_tenants: List of tenants who haven't paid
            due_date: Rent due date string
            test_mode: Whether to use test mode

        Returns:
            Bulk sending results
        """
        return await self.send_bulk_sms(
            tenants=unpaid_tenants,
            message="",  # Will use template
            template_name="rent_reminder",
            test_mode=test_mode,
            due_date=due_date,
        )

    async def send_late_fee_notices(
        self, late_tenants: List[Tenant], test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send late fee notices to tenants with overdue rent.

        Args:
            late_tenants: List of tenants with late rent
            test_mode: Whether to use test mode

        Returns:
            Bulk sending results
        """
        return await self.send_bulk_sms(
            tenants=late_tenants,
            message="",  # Will use template
            template_name="late_fee_notice",
            test_mode=test_mode,
        )

    async def send_payment_confirmations(
        self, paid_tenants: List[Tenant], test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send payment confirmation messages to tenants who paid.

        Args:
            paid_tenants: List of tenants who paid rent
            test_mode: Whether to use test mode

        Returns:
            Bulk sending results
        """
        return await self.send_bulk_sms(
            tenants=paid_tenants,
            message="",  # Will use template
            template_name="payment_received",
            test_mode=test_mode,
        )

    def get_available_templates(self) -> Dict[str, str]:
        """
        Get all available message templates.

        Returns:
            Dict of template names and their content
        """
        return self.templates.copy()

    async def get_quota_remaining(self, test_mode: bool = False) -> Optional[int]:
        """
        Get remaining SMS quota from API.

        Args:
            test_mode: Whether to check test quota

        Returns:
            Remaining quota or None if failed
        """
        try:
            result = await self.test_api_key(test_mode)
            return result.get("quotaRemaining")
        except Exception as e:
            logger.error(f"Failed to get SMS quota: {str(e)}")
            return None


# Global SMS service instance
sms_service = SMSService()
