import logging
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from database import Database
from weather import (
    get_rain_forecast, get_morning_forecast,
    get_afternoon_forecast, weather_emoji, uv_level
)
from config import TELEGRAM_TOKEN, DONATION_LINK, DONATE_REMINDER_DAY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
db = Database()

TEXTS = {
    "es": {
        "welcome": (
            "👋 ¡Bienvenido a *Radar de Lluvia*!\n\n"
            "🌧️ Te mantendré informado con:\n"
            "• ☀️ Resumen meteorológico cada mañana\n"
            "• 🌆 Previsión de tarde cada mediodía\n"
            "• 🚨 Alertas automáticas cuando se acerque lluvia\n\n"
            "Totalmente gratuito. Pulsa el botón y envíame tu ubicación 👇"
        ),
        "send_location": "📍 Enviar mi ubicación",
        "location_saved": "✅ ¡Ubicación guardada! Ya estás activo.\n\nRecibirás el resumen del tiempo cada mañana a las 8:00 y alertas de lluvia automáticas.",
        "no_location": "⚠️ Primero necesito tu ubicación. Usa /start para configurarla.",
        "status": "✅ *Estado:* Activo\n📍 *Ubicación:* guardada\n📅 *Llevas {days} días con nosotros*",
        "rain_alert": (
            "🚨 *¡SE ACERCA LLUVIA!*\n\n"
            "⏱️ Comenzará a las *{start_time}* (en ~{minutes} min)\n"
            "🔚 Se espera que pare a las *{stop_time}*\n"
            "⏳ Duración estimada: *{duration} minutos*\n"
            "💧 Intensidad: *{intensity}*\n\n"
            "☂️ ¡No te pillen sin paraguas!"
        ),
        "no_rain": "☀️ No se detecta lluvia próxima en tu zona.",
        "check": "🔍 Consultando el radar...",
        "donate": (
            "☕ *Un momento...*\n\n"
            "Llevas {days} días usando Radar de Lluvia y nos alegra que te sea útil 🌤️\n\n"
            "Este bot es completamente gratuito y así seguirá siendo. "
            "Pero si alguna vez te ha salvado de mojarte... ¿te apetece invitarme a un café? ☕\n\n"
            "Con 1-2€ cubres el mantenimiento del servidor durante días.\n"
            "👉 {link}\n\n"
            "_No es obligatorio, de verdad. Pero se agradece un montón_ 🙏"
        ),
        "morning": (
            "{emoji} *Buenos días! Aquí tu previsión para hoy:*\n\n"
            "🌡️ Temperatura: *{min}°C — {max}°C*\n"
            "🤔 Sensación térmica: *{feels}°C*\n"
            "💧 Humedad: *{humidity}%*\n"
            "💨 Viento máximo: *{wind} km/h*\n"
            "🌧️ Probabilidad de lluvia: *{precip_prob}%*\n"
            "☔ Lluvia acumulada: *{precip} mm*\n"
            "☀️ Índice UV: *{uv} ({uv_level})*\n"
            "🌅 Amanecer: *{sunrise}* · 🌇 Atardecer: *{sunset}*\n\n"
            "¡Que tengas un buen día! 😊"
        ),
        "afternoon": (
            "🌆 *Previsión para esta tarde:*\n\n"
            "{emoji} Tiempo: *{desc}*\n"
            "🌡️ Temperatura: *{temp}°C* (máx. {max}°C)\n"
            "🤔 Sensación: *{feels}°C*\n"
            "💧 Humedad: *{humidity}%*\n"
            "💨 Viento: *{wind} km/h*\n"
            "🌧️ Prob. lluvia tarde: *{precip_prob}%*\n"
            "☔ Lluvia estimada: *{precip} mm*"
        ),
        "stopped": "⏸️ Alertas pausadas. Usa /reanudar cuando quieras.",
        "resumed": "▶️ ¡Alertas reanudadas! Ya estás activo.",
        "lang_choose": "🌍 Elige tu idioma / Choose your language:",
        "lang_changed": "✅ Idioma cambiado a Español.",
        "help": (
            "📖 *Comandos disponibles:*\n\n"
            "/start — Iniciar y configurar ubicación\n"
            "/consultar — Consultar lluvia ahora mismo\n"
            "/manana — Ver previsión de mañana\n"
            "/estado — Ver tu estado\n"
            "/donar — Invitarme a un café ☕\n"
            "/idioma — Cambiar idioma\n"
            "/parar — Pausar alertas\n"
            "/reanudar — Reanudar alertas"
        ),
        "update_loc": "📍 Envía tu ubicación usando el clip 📎 → Ubicación.",
        "weather_codes": {
            0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado",
            3: "Nublado", 45: "Niebla", 48: "Niebla helada",
            51: "Llovizna ligera", 53: "Llovizna", 55: "Llovizna intensa",
            61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa",
            71: "Nieve ligera", 73: "Nieve", 75: "Nieve intensa",
            80: "Chubascos ligeros", 81: "Chubascos", 82: "Chubascos intensos",
            95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta fuerte"
        }
    },
    "en": {
        "welcome": (
            "👋 Welcome to *Rain Radar*!\n\n"
            "🌧️ I'll keep you informed with:\n"
            "• ☀️ Morning weather summary\n"
            "• 🌆 Afternoon forecast at noon\n"
            "• 🚨 Automatic alerts when rain approaches\n\n"
            "Completely free. Press the button and send me your location 👇"
        ),
        "send_location": "📍 Send my location",
        "location_saved": "✅ Location saved! You're now active.\n\nYou'll receive a weather summary every morning at 8:00 and automatic rain alerts.",
        "no_location": "⚠️ I need your location first. Use /start to set it up.",
        "status": "✅ *Status:* Active\n📍 *Location:* saved\n📅 *You've been with us for {days} days*",
        "rain_alert": (
            "🚨 *RAIN IS APPROACHING!*\n\n"
            "⏱️ Starting at *{start_time}* (in ~{minutes} min)\n"
            "🔚 Expected to stop at *{stop_time}*\n"
            "⏳ Estimated duration: *{duration} minutes*\n"
            "💧 Intensity: *{intensity}*\n\n"
            "☂️ Don't get caught without an umbrella!"
        ),
        "no_rain": "☀️ No rain detected nearby.",
        "check": "🔍 Checking rain radar...",
        "donate": (
            "☕ *Hey there...*\n\n"
            "You've been using Rain Radar for {days} days and we're glad it's useful 🌤️\n\n"
            "This bot is completely free and will stay that way. "
            "But if it's ever saved you from getting soaked... fancy buying me a coffee? ☕\n\n"
            "€1-2 covers the server costs for days.\n"
            "👉 {link}\n\n"
            "_No pressure at all. But it means a lot_ 🙏"
        ),
        "morning": (
            "{emoji} *Good morning! Here's your forecast for today:*\n\n"
            "🌡️ Temperature: *{min}°C — {max}°C*\n"
            "🤔 Feels like: *{feels}°C*\n"
            "💧 Humidity: *{humidity}%*\n"
            "💨 Max wind: *{wind} km/h*\n"
            "🌧️ Rain probability: *{precip_prob}%*\n"
            "☔ Rainfall: *{precip} mm*\n"
            "☀️ UV Index: *{uv} ({uv_level})*\n"
            "🌅 Sunrise: *{sunrise}* · 🌇 Sunset: *{sunset}*\n\n"
            "Have a great day! 😊"
        ),
        "afternoon": (
            "🌆 *Afternoon forecast:*\n\n"
            "{emoji} Conditions: *{desc}*\n"
            "🌡️ Temperature: *{temp}°C* (max {max}°C)\n"
            "🤔 Feels like: *{feels}°C*\n"
            "💧 Humidity: *{humidity}%*\n"
            "💨 Wind: *{wind} km/h*\n"
            "🌧️ Rain probability: *{precip_prob}%*\n"
            "☔ Estimated rainfall: *{precip} mm*"
        ),
        "stopped": "⏸️ Alerts paused. Use /reanudar whenever you want.",
        "resumed": "▶️ Alerts resumed! You're now active.",
        "lang_choose": "🌍 Elige tu idioma / Choose your language:",
        "lang_changed": "✅ Language changed to English.",
        "help": (
            "📖 *Available commands:*\n\n"
            "/start — Start and set location\n"
            "/consultar — Check rain now\n"
            "/manana — See tomorrow's forecast\n"
            "/estado — View your status\n"
            "/donar — Buy me a coffee ☕\n"
            "/idioma — Change language\n"
            "/parar — Pause alerts\n"
            "/reanudar — Resume alerts"
        ),
        "update_loc": "📍 Send your location using the clip 📎 → Location.",
        "weather_codes": {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
            3: "Overcast", 45: "Foggy", 48: "Icy fog",
            51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
            61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Light snow", 73: "Snow", 75: "Heavy snow",
            80: "Light showers", 81: "Showers", 82: "Heavy showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm"
        }
    }
}

def t(user_id, key, **kwargs):
    lang = db.get_language(user_id)
    text = TEXTS.get(lang, TEXTS["es"]).get(key, "")
    return text.format(**kwargs) if kwargs else text

def wcode(user_id, code):
    lang = db.get_language(user_id)
    return TEXTS.get(lang, TEXTS["es"])["weather_codes"].get(code, "—")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.create_user_if_not_exists(user_id)
    keyboard = [[InlineKeyboardButton(t(user_id, "send_location"), callback_data="request_location")]]
    await update.message.reply_text(t(user_id, "welcome"), parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    days = db.days_since_joined(user_id)
    await update.message.reply_text(t(user_id, "status", days=days), parse_mode="Markdown")

async def consultar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or not user["lat"]:
        await update.message.reply_text(t(user_id, "no_location"))
        return
    await update.message.reply_text(t(user_id, "check"))
    alert = await get_rain_forecast(user["lat"], user["lon"])
    if alert:
        await update.message.reply_text(
            t(user_id, "rain_alert",
              minutes=alert["minutes_to_start"],
              start_time=alert["start_time"],
              stop_time=alert["stop_time"],
              duration=alert["duration"],
              intensity=alert["intensity"]),
            parse_mode="Markdown")
    else:
        await update.message.reply_text(t(user_id, "no_rain"))

async def manana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or not user["lat"]:
        await update.message.reply_text(t(user_id, "no_location"))
        return
    data = await get_morning_forecast(user["lat"], user["lon"])
    if data:
        sunrise = data["sunrise"].split("T")[-1][:5] if "T" in str(data["sunrise"]) else data["sunrise"]
        sunset = data["sunset"].split("T")[-1][:5] if "T" in str(data["sunset"]) else data["sunset"]
        await update.message.reply_text(
            t(user_id, "morning",
              emoji=weather_emoji(data["weathercode"]),
              min=data["temp_min"], max=data["temp_max"],
              feels=data["feels_like"], humidity=data["humidity"],
              wind=data["wind"], precip_prob=data["precip_prob"],
              precip=data["precip"], uv=data["uv"],
              uv_level=uv_level(data["uv"]),
              sunrise=sunrise, sunset=sunset),
            parse_mode="Markdown")

async def donar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    days = db.days_since_joined(user_id)
    await update.message.reply_text(
        t(user_id, "donate", days=days, link=DONATION_LINK), parse_mode="Markdown")

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
    keyboard = [[InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
                 InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]]
    await update.message.reply_text(t(user_id, "lang_choose"),
                                    reply_markup=InlineKeyboardMarkup(keyboard))

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
        await query.message.reply_text(t(user_id, "update_loc"))
    elif query.data == "lang_es":
        db.set_language(user_id, "es")
        await query.message.reply_text(TEXTS["es"]["lang_changed"])
    elif query.data == "lang_en":
        db.set_language(user_id, "en")
        await query.message.reply_text(TEXTS["en"]["lang_changed"])

async def job_rain_check(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_active_users()
    for user in users:
        user_id = user["user_id"]
        alert = await get_rain_forecast(user["lat"], user["lon"])
        if not alert:
            continue
        rain_key = alert["rain_key"]
        if not db.should_send_rain_alert(user_id, rain_key):
            continue
        lang = db.get_language(user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=TEXTS[lang]["rain_alert"].format(
                minutes=alert["minutes_to_start"],
                start_time=alert["start_time"],
                stop_time=alert["stop_time"],
                duration=alert["duration"],
                intensity=alert["intensity"]),
            parse_mode="Markdown")
        db.register_rain_alert(user_id, rain_key)

async def job_morning(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_active_users()
    for user in users:
        user_id = user["user_id"]
        data = await get_morning_forecast(user["lat"], user["lon"])
        if data:
            sunrise = data["sunrise"].split("T")[-1][:5] if "T" in str(data["sunrise"]) else data["sunrise"]
            sunset = data["sunset"].split("T")[-1][:5] if "T" in str(data["sunset"]) else data["sunset"]
            lang = db.get_language(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]["morning"].format(
                    emoji=weather_emoji(data["weathercode"]),
                    min=data["temp_min"], max=data["temp_max"],
                    feels=data["feels_like"], humidity=data["humidity"],
                    wind=data["wind"], precip_prob=data["precip_prob"],
                    precip=data["precip"], uv=data["uv"],
                    uv_level=uv_level(data["uv"]),
                    sunrise=sunrise, sunset=sunset),
                parse_mode="Markdown")

async def job_afternoon(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_active_users()
    for user in users:
        user_id = user["user_id"]
        data = await get_afternoon_forecast(user["lat"], user["lon"])
        if data:
            lang = db.get_language(user_id)
            code = data["weathercode"]
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]["afternoon"].format(
                    emoji=weather_emoji(code),
                    desc=TEXTS[lang]["weather_codes"].get(code, "—"),
                    temp=data["temp_avg"], max=data["temp_max"],
                    feels=data["feels"], humidity=data["humidity"],
                    wind=data["wind"], precip_prob=data["precip_prob"],
                    precip=data["precip"]),
                parse_mode="Markdown")

async def job_donate_reminder(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_active_users()
    for user in users:
        user_id = user["user_id"]
        u = db.get_user(user_id)
        if u and not u["donate_reminded"] and db.days_since_joined(user_id) >= DONATE_REMINDER_DAY:
            days = db.days_since_joined(user_id)
            lang = db.get_language(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=TEXTS[lang]["donate"].format(days=days, link=DONATION_LINK),
                parse_mode="Markdown")
            db.set_donate_reminded(user_id)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("consultar", consultar))
    app.add_handler(CommandHandler("manana", manana))
    app.add_handler(CommandHandler("donar", donar))
    app.add_handler(CommandHandler("parar", parar))
    app.add_handler(CommandHandler("reanudar", reanudar))
    app.add_handler(CommandHandler("idioma", idioma))
    app.add_handler(CommandHandler("help", ayuda))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Alertas de lluvia cada 10 minutos
    app.job_queue.run_repeating(job_rain_check, interval=600, first=30)
    # Resumen matutino a las 8:00
    app.job_queue.run_daily(job_morning, time=datetime.strptime("08:00", "%H:%M").time())
    # Previsión de tarde a las 13:00
    app.job_queue.run_daily(job_afternoon, time=datetime.strptime("13:00", "%H:%M").time())
    # Recordatorio de donativo (comprueba una vez al día)
    app.job_queue.run_repeating(job_donate_reminder, interval=86400, first=60)

    app.run_polling()

if __name__ == "__main__":
    main()
