"""
Webhook endpoints for external services.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.message import Message, MessageReply, TextBeltWebhookPayload
from app.models.tenant import TenantDB
from app.services.sms_service import sms_service
from app.utils import normalize_phone

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_opt_in_reply(text: str) -> bool:
    """Check if message is an opt-in reply."""
    normalized = text.strip().upper()
    opt_in_keywords = ["YES", "Y", "START", "UNSTOP", "JOIN", "SUBSCRIBE"]
    return normalized in opt_in_keywords


def _is_opt_out_reply(text: str) -> bool:
    """Check if message is an opt-out reply."""
    normalized = text.strip().upper()
    opt_out_keywords = ["STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"]
    return normalized in opt_out_keywords


@router.post("/sms-reply")
async def receive_sms_reply(
    request: Request, payload: TextBeltWebhookPayload, db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive SMS replies from TextBelt.
    Handles opt-in/opt-out for A2P compliance.
    """
    try:
        logger.info(f"Received SMS reply: {payload.dict()}")

        # Find the original message by text_id
        original_message = (
            db.query(Message).filter(Message.message_id == payload.textId).first()
        )

        if not original_message:
            logger.warning(f"Original message not found for text_id: {payload.textId}")
            original_message_id = None
        else:
            original_message_id = original_message.id

        # Create reply record
        reply = MessageReply(
            original_message_id=original_message_id,
            text_id=payload.textId,
            from_number=payload.fromNumber,
            reply_text=payload.text,
            processed=False,
        )

        db.add(reply)
        db.flush()  # Get the reply ID without committing yet

        # Find tenant by phone number
        normalized = normalize_phone(payload.fromNumber)
        tenant = (
            db.query(TenantDB)
            .filter(TenantDB.contact.contains(normalized[-10:]))  # Match last 10 digits
            .first()
        )

        if tenant:
            # Process opt-in/opt-out
            if _is_opt_in_reply(payload.text):
                logger.info(f"Processing opt-in for tenant {tenant.id} ({tenant.name})")
                tenant.sms_opt_in_status = "opted_in"
                tenant.sms_opt_in_date = datetime.utcnow()
                tenant.sms_opt_out_date = None
                reply.processed = True

                # Send confirmation message (skip opt-in check for confirmation messages)
                try:
                    confirmation_result = await sms_service.send_sms(
                        tenant=tenant,
                        message=sms_service.templates["opt_in_confirmation"],
                        test_mode=False,
                    )
                    logger.info(f"Sent opt-in confirmation to {tenant.name}")
                except Exception as e:
                    logger.error(f"Failed to send opt-in confirmation: {e}")

            elif _is_opt_out_reply(payload.text):
                logger.info(
                    f"Processing opt-out for tenant {tenant.id} ({tenant.name})"
                )
                tenant.sms_opt_in_status = "opted_out"
                tenant.sms_opt_out_date = datetime.utcnow()
                tenant.sms_opt_in_date = None
                reply.processed = True

                # Send confirmation message (required by A2P regulations, skip opt-in check)
                try:
                    confirmation_result = await sms_service.send_sms(
                        tenant=tenant,
                        message=sms_service.templates["opt_out_confirmation"],
                        test_mode=False,
                    )
                    logger.info(f"Sent opt-out confirmation to {tenant.name}")
                except Exception as e:
                    logger.error(f"Failed to send opt-out confirmation: {e}")
            else:
                logger.info(
                    "Reply is not opt-in/opt-out keyword, saved for manual review"
                )
        else:
            logger.warning(f"Tenant not found for phone number: {payload.fromNumber}")

        db.commit()
        db.refresh(reply)

        logger.info(f"SMS reply saved with ID: {reply.id}")

        return {"status": "success", "reply_id": reply.id}

    except Exception as e:
        logger.error(f"Error processing SMS reply webhook: {e!s}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process webhook")
