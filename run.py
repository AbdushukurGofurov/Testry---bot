"""Botni bepul Render web-xizmatida ishga tushirish.

- Avval port ochiladi (Render shuni kutadi), keyin Telegram ulanishi sozlanadi.
- Telegram "kuting" (flood control) desa, aytilgan vaqtcha kutadi va hech qachon o'chib qolmaydi.
- Webhook: Telegram xabarlarni shu manzilga yuboradi va uxlab qolgan xizmatni uyg'otadi.
- Webhook o'rnatilmasa, bot polling rejimida ishlayveradi.
- Bepul xizmat 15 daqiqa so'rovsiz qolsa uxlaydi, shuning uchun bot har 10 daqiqada o'z manzilini tekshirib turadi.
- PORT bo'lmasa (masalan, kompyuterda sinash), oddiy polling rejimida ishlaydi.
- TELEGRAM_API_BASE berilsa, Telegram'ga shu ko'prik (proxy) orqali murojaat qilinadi.
"""
import asyncio
import hashlib
import logging
import os

import aiohttp
from aiohttp import web
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

import db
from bot import BOT_TOKEN, dp

logging.basicConfig(level=logging.INFO)

PORT = int(os.getenv("PORT", "0") or 0)
BASE_URL = (os.getenv("WEBHOOK_BASE") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
API_BASE = os.getenv("TELEGRAM_API_BASE", "").rstrip("/")
PING_EVERY = 10 * 60


async def health(_request):
    return web.Response(text="ok")


async def keep_awake(base: str):
    await asyncio.sleep(60)
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                async with s.get(base + "/", timeout=aiohttp.ClientTimeout(total=30)) as r:
                    logging.info("keep-awake ping: %s", r.status)
            except Exception as e:
                logging.warning("keep-awake ping failed: %s", e)
            await asyncio.sleep(PING_EVERY)


async def patient(call, what: str, tries: int = 0):
    """Telegram so'rovini bajaradi; 'kuting' desa kutadi. tries=0 -> cheksiz urinish."""
    n = 0
    while True:
        n += 1
        try:
            return await call()
        except TelegramRetryAfter as e:
            wait = e.retry_after + 2
            logging.warning("%s: Telegram %s s kutishni so‘radi (%s-urinish)", what, e.retry_after, n)
        except Exception as e:
            wait = min(15 * n, 120)
            logging.warning("%s xatosi (%s-urinish): %s", what, n, e)
        if tries and n >= tries:
            raise RuntimeError(f"{what}: {tries} urinishdan keyin ham bo‘lmadi")
        await asyncio.sleep(wait)


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN o‘rnatilmagan")
    db.init()
    session = AiohttpSession(api=TelegramAPIServer.from_base(API_BASE)) if API_BASE else None
    bot = Bot(BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    if not PORT:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
        return

    app = web.Application()
    app.router.add_get("/", health)
    secret = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]
    path = f"/tg/{secret[:16]}"
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret).register(app, path=path)

    # 1) Avval portni ochamiz, shunda Render xizmatni "ishlayapti" deb biladi
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logging.info("port %s ochildi", PORT)
    if BASE_URL:
        asyncio.create_task(keep_awake(BASE_URL))

    # 2) Telegram bilan aloqa tiklanguncha sabr bilan kutamiz
    me = await patient(bot.get_me, "getMe")
    logging.info("Telegram bilan aloqa bor: @%s", me.username)

    # 3) Webhook, bo'lmasa polling
    if BASE_URL:
        try:
            await patient(lambda: bot.set_webhook(BASE_URL + path, secret_token=secret,
                                                  drop_pending_updates=False), "setWebhook", tries=5)
            logging.info("webhook o‘rnatildi")
            await dp.emit_startup(bot=bot)
            await asyncio.Event().wait()
            return
        except RuntimeError as e:
            logging.warning("%s; polling rejimiga o‘tildi", e)

    await patient(lambda: bot.delete_webhook(drop_pending_updates=False), "deleteWebhook")
    while True:
        try:
            await dp.start_polling(bot, handle_signals=False)
        except Exception as e:
            logging.warning("polling to‘xtadi: %s; 30 s dan keyin qayta", e)
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
