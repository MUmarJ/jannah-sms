"""
Webhook endpoints for external services.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.message import TextBeltWebhookPayload, MessageReply, Message

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sms-reply")
async def receive_sms_reply(
    request: Request,
    payload: TextBeltWebhookPayload,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive SMS replies from TextBelt.
    """
    try:
        logger.info(f"Received SMS reply: {payload.dict()}")
        
        # Find the original message by text_id
        original_message = db.query(Message).filter(
            Message.message_id == payload.textId
        ).first()
        
        if not original_message:
            logger.warning(f"Original message not found for text_id: {payload.textId}")
            # Still save the reply for manual processing
            original_message_id = None
        else:
            original_message_id = original_message.id
        
        # Create reply record
        reply = MessageReply(
            original_message_id=original_message_id,
            text_id=payload.textId,
            from_number=payload.fromNumber,
            reply_text=payload.text,
            processed=False
        )
        
        db.add(reply)
        db.commit()
        db.refresh(reply)
        
        logger.info(f"SMS reply saved with ID: {reply.id}")
        
        return {"status": "success", "reply_id": reply.id}
        
    except Exception as e:
        logger.error(f"Error processing SMS reply webhook: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process webhook")