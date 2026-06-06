import os
import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from app.core.database import AsyncSessionLocal
from app.models.match import MatchRequest
from app.models.request import BloodRequest
from app.services.waterfall_service import trigger_next_donor
import uuid

logger = structlog.get_logger()

TELEGRAM_DONOR_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_2")
TELEGRAM_DONOR_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_2")

async def start_donor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🩸 Welcome to BloodWarriors Donor Bot! 🩸\n\nI will notify you here when you match with a patient in need.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, match_id_str = data.split(":", 1)
    match_id = uuid.UUID(match_id_str)
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(MatchRequest).where(MatchRequest.id == match_id))
        match_req = result.scalars().first()
        
        if not match_req:
            await query.edit_message_text(text="Sorry, this match request could not be found.")
            return
            
        if match_req.status != "PENDING":
            await query.edit_message_text(text=f"This request has already been processed (Current status: {match_req.status}).")
            return
            
        if action == "ACCEPT":
            match_req.status = "ACCEPTED"
            
            # Update blood request status
            req_result = await session.execute(select(BloodRequest).where(BloodRequest.id == match_req.request_id))
            blood_req = req_result.scalars().first()
            if blood_req:
                blood_req.status = "FULFILLED"
            
            await session.commit()
            
            await query.edit_message_text(text="✅ You have accepted the request! We are notifying the patient now. They will contact you shortly.")
            
            # Notify patient bot
            from app.services.patient_bot import notify_patient_of_match
            # Need to get the donor's contact details to send to the patient
            from app.models.user import User
            donor_res = await session.execute(select(User).where(User.id == match_req.donor_id))
            donor = donor_res.scalars().first()
            if donor:
                await notify_patient_of_match(blood_req.id, donor)
                
            from app.api.v1.ws import manager
            await manager.broadcast("MATCH_ACCEPTED", {
                "request_id": str(blood_req.id),
                "donor_id": str(donor.id) if donor else None
            })
            
        elif action == "DECLINE":
            match_req.status = "DECLINED"
            await session.commit()
            
            await query.edit_message_text(text="❌ You have declined this request. We will look for another donor.")
            
            # Trigger next donor
            has_next = await trigger_next_donor(match_req.request_id)
            if not has_next:
                # Need to update request to FAILED if no donors left, but for now we leave it OPEN or MATCHING
                logger.info(f"No more donors for request {match_req.request_id}")


async def notify_donor_via_telegram(match_id: str, donor_name: str, patient_name: str, hospital_name: str, distance_km: float, reason: str = ""):
    from telegram import Bot
    if not TELEGRAM_DONOR_TOKEN or not TELEGRAM_DONOR_CHAT_ID:
        logger.warning(f"Missing TELEGRAM_BOT_TOKEN_2 or TELEGRAM_CHAT_ID_2, skipping donor notification.")
        return
        
    bot = Bot(token=TELEGRAM_DONOR_TOKEN)
    msg = (
        f"🚨 URGENT MATCH ALERT 🚨\n\n"
        f"Hello {donor_name}, you have been matched with a patient in need!\n"
        f"Patient: {patient_name}\n"
        f"Location: {hospital_name} ({distance_km:.1f} km away)\n\n"
    )
    if reason:
        msg += f"Why you? {reason}\n\n"
        
    msg += "Please accept or decline immediately:"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"ACCEPT:{match_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"DECLINE:{match_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await bot.send_message(chat_id=TELEGRAM_DONOR_CHAT_ID, text=msg, reply_markup=reply_markup)
        logger.info(f"Successfully sent telegram notification to donor {donor_name}.")
    except Exception as e:
        logger.error(f"Failed to send donor telegram notification: {e}")

donor_app = None

async def start_donor_bot():
    global donor_app
    if not TELEGRAM_DONOR_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN_2 is not set. Donor bot will not start.")
        return
        
    donor_app = Application.builder().token(TELEGRAM_DONOR_TOKEN).build()
    donor_app.add_handler(CommandHandler("start", start_donor))
    donor_app.add_handler(CallbackQueryHandler(handle_button))
    
    logger.info("Starting Donor Telegram Bot long-polling...")
    await donor_app.initialize()
    await donor_app.start()
    await donor_app.updater.start_polling()
