"""Botni bepul Render web-xizmatida ishga tushirish.

- Avval port ochiladi (Render shuni kutadi), keyin Telegram ulanishi sozlanadi.
- Webhook: Telegram xabarlarni shu manzilga yuboradi va uxlab qolgan xizmatni uyg'otadi.
- Webhook o'rnatilmasa (Telegram xatosi), bot polling rejimida ishlayveradi.
- Bepul xizmat 15 daqiqa so'rovsiz qolsa uxlaydi, shuning uchun bot har 10 daqiqada o'z manzilini tekshirib turadi.
- PORT bo'lmasa (masalan, kompyuterda sinash), oddiy polling rejimida ishlaydi.
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
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

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


async def try_set_webhook(bot: Bot, url: str, secret: str, attempts: int = 6) -> bool:
    delay = 5
    for i in range(1, attempts + 1):
        try:
            await bot.set_webhook(url, secret_token=secret, drop_pending_updates=False)
            logging.info("webhook o‘rnatildi")
            return True
        except Exception as e:
            logging.warning("webhook o‘rnatilmadi (%s/%s): %s", i, attempts, e)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
    return False


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

    # 2) Telegram ulanishi: webhook, bo'lmasa polling
    if BASE_URL and await try_set_webhook(bot, BASE_URL + path, secret):
        await dp.emit_startup(bot=bot)
        await asyncio.Event().wait()
    else:
        logging.warning("polling rejimiga o‘tildi")
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception as e:
            logging.warning("delete_webhook xatosi: %s", e)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
