import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from database import Database
from weather import get_rain_alert, get_current_weather
from config import TELEGRAM_TOKEN, TRIAL_DAYS, DONATION_LINK

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

TEXTS = {
    "es": {
        "welcome": (
            "👋 ¡Bienvenido a *MiRastreador Lluvia*!\n\n"
            "🌧️ Te avisaré cuando se acerque la lluvia a tu ubicación con:\n"
            "• Tiempo estimado antes de que llueva\n"
            "• Distancia de la lluvia\n"
            "• Alertas cada 10 minutos cuando se acerque\n\n"
            "Tienes *30 días gratuitos* para probarlo.\n\n"
            "Pulsa el botón para enviarme tu ubicación 👇"
        ),
        "send_location": "📍 Enviar mi ubicación",
        "location_saved": "✅ Ubicación guardada. ¡Ya estás activo! Te avisaré cuando se acerque lluvia.",
        "no_location": "⚠️ Primero necesito tu ubicación. Usa /start para configurarla.",
        "status_active": "✅ *Estado:* Activo\n📍 *Ubicación:* guardada\n⏳ *Días restantes:* {days} días gratis",
        "status_premium": "⭐ *Estado:* Premium\n📍 *Ubicación:* guardada\n🙏 ¡Gracias por tu donativo!",
        "trial_expired": (
            "⏰ Tu período de prueba de 30 días ha terminado.\n\n"
            "Para seguir recibiendo alertas de lluvia, considera hacer un pequeño donativo de 2€ "
            "para el mantenimiento del bot.\n\n"
            "👉 {link}\n\n"
            "Tras donar, escribe /activar para reactivar tu cuenta."
        ),
        "donate_msg": (
            "🙏 *Apoya el proyecto*\n\n"
            "Este bot es gratuito pero tiene costes de mantenimiento.\n"
            "Con un donativo de 2€ mantienes el servicio activo.\n\n"
            "👉 {link}\n\n"
            "Tras donar escribe /activar y te reactivo manualmente."
        ),
        "activated": "⭐ ¡Cuenta activada como Premium! Gracias por tu apoyo 🙏",
        "rain_alert": (
            "🌧️ *¡ALERTA DE LLUVIA!*\n\n"
            "⏱️ Llegará en aproximadamente *{minutes} minutos*\n"
            "📏 Distancia: *{distance} km*\n"
            "🕐 Hora estimada: *{time}*\n"
            "💧 Intensidad: *{intensity}*"
        ),
        "no_rain": "☀️ No se detecta lluvia en las próximas 2 horas en tu zona.",
        "check": "🔍 Consultando el radar de lluvia...",
        "lang_changed": "✅ Idioma cambiado a Español.",
        "choose_lang": "🌍 Elige tu idioma / Choose your language:",
        "update_location": "📍 Actualizar ubicación",
        "help": (
            "📖 *Comandos disponibles:*\n\n"
            "/start - Iniciar el bot\n"
            "/estado - Ver tu estado y días restantes\n"
            "/consultar - Consultar lluvia ahora mismo\n"
            "/donar - Apoyar el proyecto\n"
            "/idioma - Cambiar idioma\n"
            "/activar - Activar tras donativo\n"
            "/parar - Pausar alertas\n"
            "/reanudar - Reanudar alertas"
        ),
        "stopped": "⏸️ Alertas pausadas. Usa /reanudar para activarlas de nuevo.",
        "resumed": "▶️ Alertas reanudadas. ¡Ya estás activo!",
        "update_loc_prompt": "📍 Envía tu nueva ubicación pulsando el clip 📎 → Ubicación.",
    },
    "en": {
        "welcome": (
            "👋 Welcome to *MiRastreador Rain*!\n\n"
            "🌧️ I'll alert you when rain is approaching with:\n"
            "• Estimated time before rain arrives\n"
            "• Distance of the rain\n"
            "• Alerts every 10 minutes as it approaches\n\n"
            "You have *30 free days* to try it.\n\n"
            "Press the button to send me your location 👇"
        ),
        "send_location": "📍 Send my location",
        "location_saved": "✅ Location saved. You're now active! I'll alert you when rain approaches.",
        "no_location": "⚠️ I need your location first. Use /start to set it up.",
        "status_active": "✅ *Status:* Active\n📍 *Location:* saved\n⏳ *Days remaining:* {days} free days",
        "status_premium": "⭐ *Status:* Premium\n📍 *Location:* saved\n🙏 Thank you for your donation!",
        "trial_expired": (
            "⏰ Your 30-day trial has ended.\n\n"
            "To keep receiving rain alerts, consider a small €2 donation "
            "to keep the bot running.\n\n"
            "👉 {link}\n\n"
            "After donating, type /activar to reactivate your account."
        ),
        "donate_msg": (
            "🙏 *Support the project*\n\n"
            "This bot is free but has maintenance costs.\n"
            "A €2 donation keeps the service running.\n\n"
            "👉 {link}\n\n"
            "After donating write /activar and I'll reactivate you manually."
        ),
        "activated": "⭐ Account activated as Premium! Thank you for your support 🙏",
        "rain_alert": (
            "🌧️ *RAIN ALERT!*\n\n"
            "⏱️ Arriving in approximately *{minutes} minutes*\n"
            "📏 Distance: *{distance} km*\n"
            "🕐 Estimated time: *{time}*\n"
            "💧 Intensity: *{intensity}*"
        ),
        "no_rain": "☀️ No rain detected in the next 2 hours in your area.",
        "check": "🔍 Checking rain radar...",
        "lang_changed": "✅ Language changed to English.",
        "choose_lang": "🌍 Elige tu idioma / Choose your language:",
        "update_location": "📍 Update location",
        "help": (
            "📖 *Available commands:*\n\n"
            "/start - Start the bot\n"
            "/estado - View your status and remaining days\n"
            "/consultar - Check rain right now\n"
            "/donar - Support the project\n"
            "/idioma - Change language\n"
            "/activar - Activate after donation\n"
            "/parar - Pause alerts\n"
            "/reanudar - Resume alerts"
        ),
        "stopped": "⏸️ Alerts paused. Use /reanudar to resume.",
        "resumed": "▶️ Alerts resumed. You're now active!",
        "update_loc_prompt": "📍 Send your new location using the clip 📎 → Location.",
    }
}

def t(user_id, key, **kwargs):
    lang = db.get_language(user_id)
    text = TEXTS.get(lang, TEXTS["es"]).get(key, "")
    return text.format(**kwargs) if kwargs else text

def is_active(user_id):
    user = db.get_user(user_id)
    if not user:
        return False
    if user["premium"]:
        return True
    created = datetime.fromisoformat(user["created_at"])
    return datetime.now() < created + timedelta(days=TRIAL_DAYS)

def days_remaining(user_id):
    user = db.get_user(user_id)
    if not user:
        return 0
    created = datetime.fromisoformat(user["created_at"])
    delta = (created + timedelta(days=TRIAL_DAYS)) - datetime.now()
    return max(0, delta.days)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.create_user_if_not_exists(user_id)
    lang = db.get_language(user_id)
    keyboard = [[InlineKeyboardButton(t(user_id, "send_location"), callback_data="request_location")]]
    await update.message.reply_text(
        t(user_id, "welcome"),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text(t(user_id, "no_location"))
        return
    if user["premium"]:
        await update.message.reply_text(t(user_id, "status_premium"), parse_mode="Markdown")
    else:
        days = days_remaining(user_id)
        await update.message.reply_text(t(user_id, "status_active", days=days), parse_mode="Markdown")

async def consultar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or not user["lat"]:
        await update.message.reply_text(t(user_id, "no_location"))
        return
    await update.message.reply_text(t(user_id, "check"))
    alert = await get_rain_alert(user["lat"], user["lon"])
    if alert:
        eta = datetime.now() + timedelta(minutes=alert["minutes"])
        await update.message.reply_text(
            t(user_id, "rain_alert",
              minutes=alert["minutes"],
              distance=alert["distance"],
              time=eta.strftime("%H:%M"),
              intensity=alert["intensity"]),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(t(user_id, "no_rain"))

async def donar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        t(user_id, "donate_msg", link=DONATION_LINK),
        parse_mode="Markdown"
    )

async def activar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # En producción aquí verificarías el pago manualmente o con webhook
    db.set_premium(user_id, True)
    await update.message.reply_text(t(user_id, "activated"))

async def parar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.set_active(user_id, False)
    await update.message.reply_text(t(user_id, "stopped"))

async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.set_active(user_id, True)
    await update.message.reply_text(t(user_id, "resumed"))

async def idioma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        t(user_id, "choose_lang"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(t(user_id, "help"), parse_mode="Markdown")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    loc = update.message.location
    db.create_user_if_not_exists(user_id)
    db.update_location(user_id, loc.latitude, loc.longitude)
    db.set_active(user_id, True)
    await update.message.reply_text(t(user_id, "location_saved"))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == "request_location":
        await query.message.reply_text(t(user_id, "update_loc_prompt"))
    elif query.data == "lang_es":
        db.set_language(user_id, "es")
        await query.message.reply_text(TEXTS["es"]["lang_changed"])
    elif query.data == "lang_en":
        db.set_language(user_id, "en")
        await query.message.reply_text(TEXTS["en"]["lang_changed"])

async def check_rain_job(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_active_users()
    for user in users:
        user_id = user["user_id"]
        if not is_active(user_id):
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[db.get_language(user_id)]["trial_expired"].format(link=DONATION_LINK)
            )
            db.set_active(user_id, False)
            continue
        if not user["lat"]:
            continue
        alert = await get_rain_alert(user["lat"], user["lon"])
        if alert:
            eta = datetime.now() + timedelta(minutes=alert["minutes"])
            lang = db.get_language(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]["rain_alert"].format(
                    minutes=alert["minutes"],
                    distance=alert["distance"],
                    time=eta.strftime("%H:%M"),
                    intensity=alert["intensity"]
                ),
                parse_mode="Markdown"
            )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("consultar", consultar))
    app.add_handler(CommandHandler("donar", donar))
    app.add_handler(CommandHandler("activar", activar))
    app.add_handler(CommandHandler("parar", parar))
    app.add_handler(CommandHandler("reanudar", reanudar))
    app.add_handler(CommandHandler("idioma", idioma))
    app.add_handler(CommandHandler("help", ayuda))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.job_queue.run_repeating(check_rain_job, interval=600, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
