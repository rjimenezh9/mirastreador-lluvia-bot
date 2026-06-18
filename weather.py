import aiohttp
from datetime import datetime, timezone

async def get_rain_alert(lat, lon):
    """
    Consulta Open-Meteo (gratuito, sin API key) y devuelve
    alerta de lluvia si se detecta en los próximos 120 minutos.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&minutely_15=precipitation,precipitation_probability"
        f"&forecast_minutely_15=8"
        f"&timezone=auto"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()

        minutely = data.get("minutely_15", {})
        times = minutely.get("time", [])
        precip = minutely.get("precipitation", [])
        prob = minutely.get("precipitation_probability", [])

        now = datetime.now(timezone.utc)

        for i, (t, p, pr) in enumerate(zip(times, precip, prob)):
            slot_time = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
            if slot_time < now:
                continue
            if p > 0.1 or pr > 50:
                minutes = int((slot_time - now).total_seconds() / 60)
                distance = round(minutes * 0.8, 1)  # estimación ~50km/h frente de lluvia
                intensity = _intensity(p)
                return {
                    "minutes": max(1, minutes),
                    "distance": distance,
                    "intensity": intensity
                }
        return None

    except Exception as e:
        print(f"Error consultando Open-Meteo: {e}")
        return None

def _intensity(mm):
    if mm < 0.5:
        return "🌦️ Llovizna / Drizzle"
    elif mm < 2:
        return "🌧️ Lluvia moderada / Moderate rain"
    elif mm < 5:
        return "🌧️ Lluvia intensa / Heavy rain"
    else:
        return "⛈️ Tormenta / Storm"

async def get_current_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,precipitation,weather_code"
        f"&timezone=auto"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
        return data.get("current", {})
    except Exception:
        return {}
