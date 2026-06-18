import aiohttp
from datetime import datetime, timezone, timedelta

async def get_rain_forecast(lat, lon):
    """
    Devuelve la previsión completa de lluvia para las próximas 2 horas.
    Retorna dict con: minutes_to_start, minutes_to_stop, intensity
    O None si no va a llover.
    Solo avisa si la lluvia empieza en los próximos 15 minutos.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&minutely_15=precipitation,precipitation_probability"
        f"&forecast_minutely_15=12"
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

        rain_start_idx = None
        rain_stop_idx = None

        for i, (t, p, pr) in enumerate(zip(times, precip, prob)):
            slot_time = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
            if slot_time < now:
                continue
            is_rain = p > 0.1 or pr > 50
            if is_rain and rain_start_idx is None:
                rain_start_idx = i
            elif not is_rain and rain_start_idx is not None and rain_stop_idx is None:
                rain_stop_idx = i
                break

        if rain_start_idx is None:
            return None

        start_time = datetime.fromisoformat(times[rain_start_idx]).replace(tzinfo=timezone.utc)
        minutes_to_start = int((start_time - now).total_seconds() / 60)

        # Solo avisar si empieza en los próximos 15 minutos
        if minutes_to_start > 15:
            return None

        if rain_stop_idx is not None:
            stop_time = datetime.fromisoformat(times[rain_stop_idx]).replace(tzinfo=timezone.utc)
            minutes_to_stop = int((stop_time - now).total_seconds() / 60)
            stop_time_str = stop_time.strftime("%H:%M")
        else:
            # Si no encontramos fin, estimamos que dura al menos 30 min más
            minutes_to_stop = minutes_to_start + 45
            stop_time_str = (now + timedelta(minutes=minutes_to_stop)).strftime("%H:%M")

        # Calcular intensidad máxima durante la lluvia
        max_precip = max(precip[rain_start_idx:rain_stop_idx or len(precip)])

        return {
            "minutes_to_start": max(0, minutes_to_start),
            "start_time": start_time.strftime("%H:%M"),
            "stop_time": stop_time_str,
            "duration": minutes_to_stop - minutes_to_start,
            "intensity": _intensity(max_precip),
            "rain_key": start_time.strftime("%Y%m%d%H%M"),  # clave única para este episodio
        }

    except Exception as e:
        print(f"Error rain forecast: {e}")
        return None


async def get_morning_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"precipitation_probability_max,windspeed_10m_max,uv_index_max,"
        f"sunrise,sunset,weathercode"
        f"&hourly=relativehumidity_2m,apparent_temperature"
        f"&forecast_days=1"
        f"&timezone=auto"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})
        humidity = hourly.get("relativehumidity_2m", [None]*12)[12] or "--"
        feels = hourly.get("apparent_temperature", [None]*12)[12] or "--"
        return {
            "temp_max": daily.get("temperature_2m_max", [None])[0],
            "temp_min": daily.get("temperature_2m_min", [None])[0],
            "precip": daily.get("precipitation_sum", [0])[0],
            "precip_prob": daily.get("precipitation_probability_max", [0])[0],
            "wind": daily.get("windspeed_10m_max", [0])[0],
            "uv": daily.get("uv_index_max", [0])[0],
            "sunrise": daily.get("sunrise", ["--"])[0],
            "sunset": daily.get("sunset", ["--"])[0],
            "weathercode": daily.get("weathercode", [0])[0],
            "humidity": humidity,
            "feels_like": feels,
        }
    except Exception as e:
        print(f"Error morning forecast: {e}")
        return None


async def get_afternoon_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,precipitation_probability,precipitation,"
        f"windspeed_10m,apparent_temperature,weathercode,relativehumidity_2m"
        f"&forecast_days=1"
        f"&timezone=auto"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
        hourly = data.get("hourly", {})
        afternoon = slice(15, 22)
        temps = hourly.get("temperature_2m", [])
        feels = hourly.get("apparent_temperature", [])
        precip_prob = hourly.get("precipitation_probability", [])
        precip = hourly.get("precipitation", [])
        wind = hourly.get("windspeed_10m", [])
        humidity = hourly.get("relativehumidity_2m", [])
        codes = hourly.get("weathercode", [])
        avg = lambda lst: round(sum(lst[afternoon]) / len(lst[afternoon]), 1) if lst else "--"
        max_ = lambda lst: round(max(lst[afternoon]), 1) if lst else "--"
        return {
            "temp_avg": avg(temps),
            "temp_max": max_(temps),
            "feels": avg(feels),
            "precip_prob": max_(precip_prob),
            "precip": round(sum(precip[afternoon]), 1) if precip else 0,
            "wind": max_(wind),
            "humidity": avg(humidity),
            "weathercode": codes[18] if len(codes) > 18 else 0,
        }
    except Exception as e:
        print(f"Error afternoon forecast: {e}")
        return None


def _intensity(mm):
    if mm < 0.5: return "🌦️ Llovizna"
    elif mm < 2: return "🌧️ Lluvia moderada"
    elif mm < 5: return "🌧️ Lluvia intensa"
    else: return "⛈️ Tormenta"

def weather_emoji(code):
    if code == 0: return "☀️"
    elif code in [1, 2]: return "🌤️"
    elif code == 3: return "☁️"
    elif code in [45, 48]: return "🌫️"
    elif code in [51, 53, 55]: return "🌦️"
    elif code in [61, 63, 65]: return "🌧️"
    elif code in [71, 73, 75]: return "❄️"
    elif code in [80, 81, 82]: return "🌧️"
    elif code in [95, 96, 99]: return "⛈️"
    else: return "🌡️"

def uv_level(uv):
    if uv <= 2: return "Bajo"
    elif uv <= 5: return "Moderado"
    elif uv <= 7: return "Alto"
    elif uv <= 10: return "Muy alto"
    else: return "Extremo ☠️"
