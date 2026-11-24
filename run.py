"""Botni bepul Render web-xizmatida ishga tushirish (webhook rejimi).

- Render PORT va RENDER_EXTERNAL_URL beradi: bot shu manzilda Telegram xabarlarini qabul qiladi.
- Bepul xizmat 15 daqiqa so'rovsiz qolsa uxlaydi, shuning uchun bot har 10 daqiqada o'z manzilini tekshirib turadi.
- Bu o'zgaruvchilar bo'lmasa (masalan, kompyuterda sinash), oddiy polling rejimida ishlaydi.
"""
import asyncio
import hashlib
import logging
import os

import aiohttp
from aiohttp import web
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import db
from bot import BOT_TOKEN, dp

logging.basicConfig(level=logging.INFO)

PORT = int(os.getenv("PORT", "0") or 0)
BASE_URL = (os.getenv("WEBHOOK_BASE") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
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


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN o‘rnatilmagan")
    db.init()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    if not PORT:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
        return

    app = web.Application()
    app.router.add_get("/", health)

    if BASE_URL:
        secret = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]
        path = f"/tg/{secret[:16]}"
        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret).register(app, path=path)
        setup_application(app, dp, bot=bot)
        await bot.set_webhook(BASE_URL + path, secret_token=secret, drop_pending_updates=False)
        logging.info("webhook o‘rnatildi")
        asyncio.create_task(keep_awake(BASE_URL))
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        await asyncio.Event().wait()
    else:
        # Manzil noma'lum: sog'liq tekshiruvi uchun port ochamiz va polling qilamiz
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
