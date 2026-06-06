import os
import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from app.services.bedrock_service import bedrock_service
from app.core.database import AsyncSessionLocal
from app.models.request import BloodRequest, UrgencyLevel
from app.models.user import BloodGroup
from app.tasks.optimization_tasks import run_ilp_batch_async
from app.api.v1.ws import manager

logger = structlog.get_logger()

TELEGRAM_PATIENT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# States
ASK_NAME, ASK_BLOOD_GROUP, ASK_LOCATION, ASK_URGENCY = range(4)

async def start_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"start_form triggered by user {update.effective_user.id} with message: {update.message.text}")
    welcome_msg = (
        "🩸 Welcome to BloodWarriors Patient Bot! 🩸\n\n"
        "Let's get some details so we can find a donor for you.\n\n"
        "First, what is the <b>Patient's Name</b>?"
    )
    await update.message.reply_text(welcome_msg, parse_mode="HTML")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    
    reply_keyboard = [['A+', 'A-', 'B+', 'B-'], ['AB+', 'AB-', 'O+', 'O-']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Thanks! Now, what is the required <b>Blood Group</b> for {context.user_data['name']}?",
        reply_markup=markup, parse_mode="HTML"
    )
    return ASK_BLOOD_GROUP

async def ask_blood_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bg_str = update.message.text.upper().replace(" ", "")
    
    bg_map = {
        "A+": BloodGroup.A_POS, "A-": BloodGroup.A_NEG,
        "B+": BloodGroup.B_POS, "B-": BloodGroup.B_NEG,
        "AB+": BloodGroup.AB_POS, "AB-": BloodGroup.AB_NEG,
        "O+": BloodGroup.O_POS, "O-": BloodGroup.O_NEG,
    }
    
    if bg_str not in bg_map:
        await update.message.reply_text("Please choose a valid blood group from the keyboard.")
        return ASK_BLOOD_GROUP
        
    context.user_data['blood_group'] = bg_str
    
    # We ask for a location string (we can use fake geocoding or ask for a Telegram Location)
    # For Telegram Location, we can provide a Location button.
    location_keyboard = [[KeyboardButton(text="Send Location", request_location=True)]]
    markup = ReplyKeyboardMarkup(location_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Got it! Next, where is the patient located? You can tap 'Send Location' or just type the hospital name/city.",
        reply_markup=markup
    )
    return ASK_LOCATION

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        context.user_data['latitude'] = update.message.location.latitude
        context.user_data['longitude'] = update.message.location.longitude
        context.user_data['hospital'] = "Telegram Location"
    else:
        # Default fallback for typed location
        context.user_data['hospital'] = update.message.text
        context.user_data['latitude'] = 12.9716  # default Bangalore
        context.user_data['longitude'] = 77.5946
        
    reply_keyboard = [['NORMAL', 'URGENT', 'CRITICAL']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Thanks. Lastly, what is the <b>Urgency Level</b>?",
        reply_markup=markup, parse_mode="HTML"
    )
    return ASK_URGENCY

async def ask_urgency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urgency_str = update.message.text.upper()
    if urgency_str not in ['NORMAL', 'URGENT', 'CRITICAL']:
        await update.message.reply_text("Please select NORMAL, URGENT, or CRITICAL.")
        return ASK_URGENCY
        
    context.user_data['urgency'] = UrgencyLevel(urgency_str)
    
    await update.message.reply_text(
        "All set! Processing your request now...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Convert form data to standard parsed_data
    parsed_data = {
        "name": context.user_data['name'],
        "blood_group": context.user_data['blood_group'],
        "latitude": context.user_data['latitude'],
        "longitude": context.user_data['longitude'],
        "hospital": context.user_data['hospital'],
        "urgency": context.user_data['urgency']
    }
    
    await process_parsed_data(update, parsed_data)
    
    return ConversationHandler.END

async def cancel_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Form cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    logger.info(f"Received Telegram photo from patient {user_id}")
    
    await update.message.reply_text("Analyzing your medical record using AWS Bedrock Vision...")
    
    # Get the largest photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    
    # Download into memory
    import io
    out = io.BytesIO()
    await file.download_to_memory(out=out)
    image_bytes = out.getvalue()
    
    parsed_data = bedrock_service.extract_medical_record(image_bytes)
    
    if "latitude" not in parsed_data or parsed_data.get("latitude") is None:
        parsed_data["latitude"] = 12.9716  
        parsed_data["longitude"] = 77.5946
        
    # Convert urgency string to UrgencyLevel if present
    urgency_str = parsed_data.get("urgency", "URGENT").upper()
    if urgency_str in ['NORMAL', 'URGENT', 'CRITICAL']:
        parsed_data['urgency'] = UrgencyLevel(urgency_str)
    else:
        parsed_data['urgency'] = UrgencyLevel.URGENT
        
    await process_parsed_data(update, parsed_data)
    
async def process_parsed_data(update: Update, parsed_data: dict):
    if "error" in parsed_data:
        await update.message.reply_text(f"Sorry, I couldn't understand the request. Error: {parsed_data['error']}")
        return
        
    name = parsed_data.get("name", "Unknown Patient")
    blood_group_str = parsed_data.get("blood_group")
    lat = parsed_data.get("latitude")
    lng = parsed_data.get("longitude")
    urgency = parsed_data.get("urgency", UrgencyLevel.URGENT)
    
    if not blood_group_str or lat is None or lng is None:
        await update.message.reply_text(
            f"I understood this:\nName: {name}\nBlood: {blood_group_str}\nLat: {lat}, Lng: {lng}\n\n"
            "But I am missing some required details. Please specify the blood group and location."
        )
        return
        
    # Map blood group
    bg_map = {
        "A+": BloodGroup.A_POS, "A-": BloodGroup.A_NEG,
        "B+": BloodGroup.B_POS, "B-": BloodGroup.B_NEG,
        "AB+": BloodGroup.AB_POS, "AB-": BloodGroup.AB_NEG,
        "O+": BloodGroup.O_POS, "O-": BloodGroup.O_NEG,
    }
    bg = bg_map.get(blood_group_str.replace(" ", "").upper())
    
    if not bg:
        await update.message.reply_text(f"Invalid blood group recognized: {blood_group_str}")
        return
        
    await update.message.reply_text(f"Creating request for {name} ({blood_group_str}) at coordinates {lat}, {lng}...")
    
    # Save Request to DB
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=3)
        if urgency == UrgencyLevel.CRITICAL:
            deadline = now + timedelta(days=1)
        
        req = BloodRequest(
            patient_name=name,
            blood_group=bg,
            units_required=1,
            hospital_name=parsed_data.get("hospital", "Telegram Request"),
            latitude=float(lat),
            longitude=float(lng),
            urgency=urgency,
            deadline=deadline,
            status="OPEN"
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        
        await manager.broadcast("NEW_PATIENT_REQUEST", {
            "id": str(req.id),
            "name": name,
            "blood_group": blood_group_str
        })
        
        await update.message.reply_text("✅ Request created! Triggering optimization engine to find donors...")
        chat_id = update.message.chat_id
        logger.info(f"Patient {name} requested from chat_id {chat_id}")
        
    # Trigger optimization
    try:
        asyncio.create_task(run_and_notify_match(update, req.id))
    except Exception as e:
        logger.error(f"Failed to run optimization: {e}")
        await update.message.reply_text("⚠️ Optimization engine failed to start.")

async def run_and_notify_match(update: Update, request_id):
    from app.tasks.optimization_tasks import run_ilp_single_async
    result = await run_ilp_single_async(request_id)
    await update.message.reply_text(f"Optimization engine finished: {result}. We have found a donor (Rank 1) and are awaiting their confirmation...")

async def notify_patient_of_match(request_id, donor):
    from telegram import Bot
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not TELEGRAM_PATIENT_TOKEN or not chat_id:
        return
        
    # Fetch request to get urgency level
    urgency = UrgencyLevel.URGENT
    async with AsyncSessionLocal() as session:
        from app.models.request import BloodRequest
        req = await session.get(BloodRequest, request_id)
        if req:
            urgency = req.urgency

    # Determine optimal days
    if urgency == UrgencyLevel.CRITICAL:
        optimal_days = "Immediately (within 24 hours)"
    elif urgency == UrgencyLevel.URGENT:
        optimal_days = "Within 1-2 days"
    else:
        optimal_days = "Within 3-7 days"

    bot = Bot(token=TELEGRAM_PATIENT_TOKEN)
    msg = (
        f"🎉 GREAT NEWS! 🎉\n\n"
        f"A donor has accepted your request!\n"
        f"<b>Donor Name:</b> {donor.name}\n"
        f"<b>Blood Group:</b> {donor.blood_group.value}\n"
        f"<b>Contact:</b> {donor.phone}\n\n"
        f"🕒 <b>Optimal Donation Time:</b> {optimal_days}\n\n"
        f"Please contact them immediately to arrange the donation."
    )
    
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to notify patient: {e}")

patient_app = None

async def start_patient_bot():
    global patient_app
    if not TELEGRAM_PATIENT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Patient bot will not start.")
        return
        
    patient_app = Application.builder().token(TELEGRAM_PATIENT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_form),
            MessageHandler(filters.Regex("(?i)^(hi|hello|start)$"), start_form)
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_BLOOD_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_blood_group)],
            ASK_LOCATION: [MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, ask_location)],
            ASK_URGENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_urgency)]
        },
        fallbacks=[CommandHandler("cancel", cancel_form)]
    )
    
    patient_app.add_handler(conv_handler)
    
    # Standalone photo handler (bypasses conversation)
    patient_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Catch-all fallback to debug why "hi" might not be matching
    async def debug_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Unrecognized message received: '{update.message.text}' from {update.effective_user.id}")
        await update.message.reply_text(f"I didn't understand that. Please type 'hi' to start.")
        
    patient_app.add_handler(MessageHandler(filters.TEXT, debug_fallback))
    
    logger.info("Starting Patient Telegram Bot long-polling...")
    await patient_app.initialize()
    await patient_app.start()
    await patient_app.updater.start_polling()
