# 🌧️ MiRastreador Lluvia Bot

Bot de Telegram que te avisa cuando se acerca la lluvia a tu ubicación.

## Características
- Alertas automáticas cada 10 minutos cuando se detecta lluvia
- Estimación de tiempo y distancia de la lluvia
- 30 días gratuitos por usuario
- Soporte en Español e Inglés
- Donativo voluntario de 2€ para continuar

## Tecnologías
- Python 3.11
- python-telegram-bot
- Open-Meteo API (gratuita, sin límites)
- SQLite

## Despliegue en Railway

1. Haz fork de este repositorio
2. Crea proyecto en [Railway](https://railway.app)
3. Conecta tu repositorio de GitHub
4. Añade las variables de entorno:
   - `TELEGRAM_TOKEN` → tu token de @BotFather
   - `DONATION_LINK` → tu enlace de Ko-fi o PayPal

## Comandos del bot
- `/start` - Iniciar y configurar ubicación
- `/estado` - Ver días restantes
- `/consultar` - Consultar lluvia ahora
- `/donar` - Apoyar el proyecto
- `/idioma` - Cambiar idioma
- `/parar` - Pausar alertas
- `/reanudar` - Reanudar alertas
