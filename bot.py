"""Testry MVP Telegram boti.

Ishga tushirish: BOT_TOKEN va ADMIN_IDS muhit o'zgaruvchilarini o'rnating, keyin: python bot.py
"""
import asyncio
import csv
import html
import io
import logging
import os
import time
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BotCommand, BotCommandScopeChat, BotCommandScopeDefault, BufferedInputFile, CallbackQuery,
                           InlineKeyboardButton, InlineKeyboardMarkup, Message)

import db
import engage
import flow
import report
import scoring
from engage import E
from questions import (DIFFICULTY, FIELD, FORMAT, SUBJECTS, VALUES, FILTER, INTEREST, LICENSE_NOTICE, OPEN_DOUBT, OPEN_DREAM, PAIRS, TIPI, WRONG_PART,
                       WHO, TYPE_NAMES, pair_key)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
PRICE_TEXT = os.getenv("PRICE_TEXT", "")          # masalan: "49 000 so‘m"
PAYMENT_URL = os.getenv("PAYMENT_URL", "")        # Payme/Click havolasi (ixtiyoriy)


def env_any(name: str) -> str:
    """Sozlama nomini katta-kichik harfga qaramay topadi (masalan, Card_number ham CARD_NUMBER deb o‘qiladi)."""
    for k, v in os.environ.items():
        if k.strip().upper() == name:
            return v
    return ""


CARD_NUMBER = env_any("CARD_NUMBER").strip()  # to‘lov qabul qilinadigan karta (Render Environment’da)
CARD_HOLDER = env_any("CARD_HOLDER").strip()  # karta egasining ismi

dp = Dispatcher()

T = {
    "welcome": {
        "uz": ("Salom, {name}! 👋\n\nBu test qiziqishlaringizni aniqlab, sizga mos yo‘nalishlarni ko‘rsatadi.\n"
               "⏱ 4 daqiqa · 30 ta savol · natija darhol\n\n"
               "To‘g‘ri yoki noto‘g‘ri javob yo‘q — o‘zingizga eng yaqinini tanlang.\n\n"
               "<i>Test O*NET va TIPI materiallari asosida moslashtirilgan. O‘zgartirishlar va ogohlantirishlar: /about</i>"),
        "ru": ("Привет, {name}! 👋\n\nЭтот тест определит ваши интересы и покажет подходящие направления.\n"
               "⏱ 4 минуты · 30 вопросов · результат сразу\n\n"
               "Правильных и неправильных ответов нет — выбирайте то, что ближе вам.\n\n"
               "<i>Тест адаптирован на основе материалов O*NET и TIPI. Изменения и оговорки: /about</i>"),
    },
    "resume": {"uz": "Sizda tugallanmagan test bor. Davom ettirasizmi?",
               "ru": "У вас есть незавершённый тест. Продолжить?"},
    "resume_yes": {"uz": "▶️ Davom ettirish", "ru": "▶️ Продолжить"},
    "resume_no": {"uz": "🔄 Qaytadan boshlash", "ru": "🔄 Начать заново"},
    "stale": {"uz": "Bu savolga javob berib bo‘lgansiz", "ru": "Вы уже ответили на этот вопрос"},
    "empty": {"uz": "Kamida bittasini tanlang", "ru": "Выберите хотя бы один вариант"},
    "calc": {"uz": "⏳ Natijangiz hisoblanmoqda...", "ru": "⏳ Считаем результат..."},
    "share": {"uz": "📤 Do‘stlarga ulashish", "ru": "📤 Поделиться с друзьями"},
    "share_text": {"uz": "Men Testry’da qiziqishlarimni aniqladim. Siz ham sinab ko‘ring!",
                   "ru": "Я определил(а) свои интересы в Testry. Попробуйте и вы!"},
    "rate_offer_btn": {"uz": "📘 To‘liq hisobot haqida", "ru": "📘 О полном отчёте"},
    "offer_auto_intro": {"uz": "Natijangiz bo‘yicha yana bir imkoniyat 👇", "ru": "Ещё одна возможность по вашему результату 👇"},
    "rate": {"uz": "Natija sizni qanchalik to‘g‘ri tasvirladi?\n1 — umuman noto‘g‘ri, 5 — juda to‘g‘ri",
             "ru": "Насколько точно результат вас описал?\n1 — совсем неверно, 5 — очень точно"},
    "offer": {
        "uz": ("📘 <b>To‘liq hisobot</b>\n\n"
               "✓ Sizga mos 6 ta yo‘nalish va nega aynan ular\n"
               "✓ Fanlaringiz shu yo‘nalishlarga mosmi\n"
               "✓ Siz uchun qulay ish muhiti\n"
               "✓ Kasb tanlashdagi ikkilanishingizga alohida javob\n"
               "✓ Javoblaringiz asosida shaxsiy AI-izoh\n"
               "✓ 2 haftalik sinov rejasi\n"
               "✓ Ota-onangiz uchun alohida sahifa\n\n"
               "Hisobot aniq chiqishi uchun yana 16 ta qisqa savolga javob berasiz (~3 daqiqa). "
               "To‘lov tasdiqlanishi bilan hisobot darhol shu chatga yuboriladi.{price}"),
        "ru": ("📘 <b>Полный отчёт</b>\n\n"
               "✓ 6 подходящих направлений и почему именно они\n"
               "✓ Подходят ли ваши предметы к этим направлениям\n"
               "✓ Комфортная для вас рабочая среда\n"
               "✓ Отдельный ответ на ваши сомнения в выборе профессии\n"
               "✓ Персональный AI-комментарий по вашим ответам\n"
               "✓ План проб на 2 недели\n"
               "✓ Отдельная страница для родителей\n\n"
               "Для точного отчёта ответьте ещё на 16 коротких вопросов (~3 минуты). "
               "Сразу после подтверждения оплаты отчёт придёт в этот чат.{price}"),
    },
    "price": {"uz": "\n\n💳 Narxi: <b>{}</b>", "ru": "\n\n💳 Стоимость: <b>{}</b>"},
    "buy": {"uz": "📘 To‘liq hisobotni olish", "ru": "📘 Получить полный отчёт"},
    "no_thanks": {"uz": "Hozircha kerak emas", "ru": "Пока не нужно"},
    "pay_info": {
        "uz": "Rahmat! 🙌\n\n{pay}👉 To‘lov qiling va chek rasmini (skrinshotini) shu chatga yuboring. "
              "To‘lov tasdiqlanishi bilan hisobotingiz <b>darhol</b> shu yerga yuboriladi.",
        "ru": "Спасибо! 🙌\n\n{pay}👉 Оплатите и отправьте фото (скриншот) чека в этот чат. "
              "Сразу после подтверждения оплаты отчёт <b>моментально</b> придёт сюда.",
    },
    "pay_link": {"uz": "To‘lov havolasi: {}\n\n", "ru": "Ссылка на оплату: {}\n\n"},
    "pay_card": {"uz": "💳 To‘lov: <b>{price}</b>\nKarta raqami: <code>{card}</code>\nKarta egasi: {holder}\n"
                       "<i>(raqamni bossangiz, nusxalanadi)</i>\n\n",
                 "ru": "💳 Оплата: <b>{price}</b>\nНомер карты: <code>{card}</code>\nВладелец: {holder}\n"
                       "<i>(нажмите на номер, чтобы скопировать)</i>\n\n"},
    "pay_manual": {"uz": "💳 To‘lov: <b>{price}</b>\n\n", "ru": "💳 Оплата: <b>{price}</b>\n\n"},
    "paid_intro": {"uz": "Endi hisobotingizni shaxsiylashtiramiz: 14 ta tugmali savol va 2 ta ochiq savol (~3 daqiqa). 👇",
                   "ru": "Теперь сделаем отчёт персональным: 14 вопросов с кнопками и 2 открытых (~3 минуты). 👇"},
    "open_intro": {"uz": "Deyarli tayyor! Oxirgi 2 ta savol (ixtiyoriy, lekin hisobotni ancha aniq qiladi):",
                   "ru": "Почти готово! Последние 2 вопроса (необязательно, но делают отчёт точнее):"},
    "skip": {"uz": "O‘tkazib yuborish", "ru": "Пропустить"},
    "thanks_end": {"uz": "Rahmat! Javoblaringiz saqlandi. ✅\n\nTestni qayta topshirish: /start",
                   "ru": "Спасибо! Ваши ответы сохранены. ✅\n\nПройти тест заново: /start"},
    "declined": {"uz": "Tushunarli! Testni qayta topshirish: /start\nNatijangiz haqida fikringiz bo‘lsa, shu yerga yozing.",
                 "ru": "Понятно! Пройти тест заново: /start\nЕсли есть мысли о результате — напишите сюда."},
    "receipt_ok": {"uz": "Chek qabul qilindi ✅ To‘lov tasdiqlanishi bilan hisobotingiz darhol shu yerga yuboriladi.",
                   "ru": "Чек получен ✅ Сразу после подтверждения оплаты отчёт придёт сюда."},
    "pay_ok": {"uz": "To‘lovingiz tasdiqlandi ✅ Rahmat!",
               "ru": "Оплата подтверждена ✅ Спасибо!"},
    "pay_ok_wait_q": {"uz": "Hisobot tayyor bo‘lishi uchun qo‘shimcha savollarni oxirigacha yakunlang. 👆",
                      "ru": "Чтобы отчёт был готов, ответьте на дополнительные вопросы до конца. 👆"},
    "pay_no": {"uz": "Afsuski, to‘lov topilmadi ❌\n\nSumma va karta raqamini tekshirib, chekni qayta yuboring. "
                     "Savol bo‘lsa, shu chatga yozing.",
               "ru": "К сожалению, оплата не найдена ❌\n\nПроверьте сумму и номер карты и отправьте чек ещё раз. "
                     "Если есть вопросы — напишите в этот чат."},
    "answers_saved": {
        "uz": "🎉 Barcha savollarga javob berdingiz! Shaxsiy hisobotingiz tayyor turibdi.\n\n"
              "<b>Hisobotda nimalar bor:</b>\n"
              "• sizga mos 6 ta yo‘nalish va nega aynan ular\n"
              "• fanlaringiz shu yo‘nalishlarga mosmi\n"
              "• siz uchun qulay ish muhiti\n"
              "• ikkilanishlaringizga maslahat va shaxsiy izoh\n"
              "• 2 haftalik sinov rejasi va ota-onangiz uchun sahifa\n\n"
              "<b>Hisobotni olish uchun keyingi qadam:</b>\n"
              "1️⃣ Quyidagi kartaga to‘lov qiling\n"
              "2️⃣ Chek rasmini (skrinshotini) shu chatga yuboring\n"
              "3️⃣ To‘lov tasdiqlanishi bilan hisobot <b>darhol</b> shu yerga keladi\n\n{pay}",
        "ru": "🎉 Вы ответили на все вопросы! Ваш персональный отчёт готов.\n\n"
              "<b>Что в отчёте:</b>\n"
              "• 6 подходящих направлений и почему именно они\n"
              "• подходят ли ваши предметы к этим направлениям\n"
              "• комфортная для вас рабочая среда\n"
              "• советы по вашим сомнениям и персональный комментарий\n"
              "• план проб на 2 недели и страница для родителей\n\n"
              "<b>Следующий шаг, чтобы получить отчёт:</b>\n"
              "1️⃣ Оплатите на карту ниже\n"
              "2️⃣ Отправьте фото (скриншот) чека в этот чат\n"
              "3️⃣ Сразу после подтверждения оплаты отчёт <b>моментально</b> придёт сюда\n\n{pay}"},
    "answers_saved_pending": {
        "uz": "🎉 Barcha savollarga javob berdingiz! Chekingiz tekshirilmoqda: to‘lov tasdiqlanishi bilan hisobotingiz darhol shu yerga keladi.",
        "ru": "🎉 Вы ответили на все вопросы! Ваш чек проверяется: сразу после подтверждения оплаты отчёт придёт сюда."},
    "pay_partial": {
        "uz": "To‘lovingiz uchun rahmat! 🙏 Lekin chekdagi summa hisobot narxidan kamroq ekan.\n\n"
              "Hisobot narxi: <b>{price}</b>. Qolgan summani shu kartaga o‘tkazib, yangi chekni shu chatga yuboring. "
              "Tasdiqlanishi bilan hisobot darhol keladi.\n\n{pay}",
        "ru": "Спасибо за оплату! 🙏 Но сумма в чеке меньше стоимости отчёта.\n\n"
              "Стоимость отчёта: <b>{price}</b>. Переведите оставшуюся сумму на эту карту и отправьте новый чек в этот чат. "
              "Сразу после подтверждения отчёт придёт.\n\n{pay}"},
    "report_wait": {"uz": "⏳ Hisobotingiz tayyorlanmoqda...", "ru": "⏳ Готовим ваш отчёт..."},
    "report_rate": {"uz": "Hisobot sizga qanchalik to‘g‘ri va foydali bo‘ldi?\n1 — umuman yo‘q, 5 — juda foydali",
                    "ru": "Насколько отчёт оказался точным и полезным?\n1 — совсем нет, 5 — очень полезен"},
    "report_fb_ask": {"uz": "Rahmat! Hisobotda nima noto‘g‘ri yoki yetishmayotgan bo‘lsa, shu yerga yozing. "
                            "Fikringiz testni yaxshilashga yordam beradi (ixtiyoriy).",
                      "ru": "Спасибо! Если в отчёте что-то неточно или чего-то не хватает, напишите сюда. "
                            "Ваше мнение поможет улучшить тест (необязательно)."},
    "report_fb_thanks": {"uz": "Fikringiz uchun katta rahmat! 🙏\n\nTestni qayta topshirish: /start",
                         "ru": "Большое спасибо за отзыв! 🙏\n\nПройти тест заново: /start"},
    "history": {"uz": "Assalomu alaykum, {name}! 😊 Siz {date} kuni testni yechgansiz.\n\nNatijangiz: <b>{tip}</b>\n"
                      "Eng kuchli qiziqishlaringiz: {types}.\n\n"
                      "Qiziqishlar vaqt o‘tib o‘zgarishi mumkin. Testni qaytadan yechib, tekshirib ko‘rishni xohlaysizmi?",
                "ru": "Здравствуйте, {name}! 😊 Вы проходили тест {date}.\n\nВаш результат: <b>{tip}</b>\n"
                      "Самые сильные интересы: {types}.\n\n"
                      "Интересы со временем могут меняться. Хотите пройти тест заново и проверить?"},
    "again_yes": {"uz": "🔄 Ha, qaytadan yechaman", "ru": "🔄 Да, пройти заново"},
    "again_show": {"uz": "📊 Natijamni ko‘rish", "ru": "📊 Мой результат"},
    "again_report": {"uz": "📘 Hisobotimni qayta ko‘rish", "ru": "📘 Мой отчёт ещё раз"},
    "again_no": {"uz": "Hozircha yo‘q", "ru": "Пока нет"},
    "again_bye": {"uz": "Yaxshi! 😊 Istalgan payt /start bosib, testni qayta yechishingiz mumkin.",
                  "ru": "Хорошо! 😊 Пройти тест заново можно в любой момент: /start"},
    "retest": {"uz": "Salom! 2 hafta oldin Testry testini topshirgandingiz. Qiziqishlaringiz o‘zgarganmi? "
                     "Testni qayta topshirib ko‘ring — bu bizga testni yaxshilashga yordam beradi: /start",
               "ru": "Привет! 2 недели назад вы прошли тест Testry. Изменились ли ваши интересы? "
                     "Пройдите тест ещё раз — это поможет нам улучшить тест: /start"},
}


def kb(rows, prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lbl, callback_data=f"{prefix}:{val}") for lbl, val in row] for row in rows])


def lang_of(row) -> str:
    return db.data_of(row).get("lang", "uz")


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


async def show_step(target, sid: int, edit: bool):
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    steps = flow.build_steps(data.get("filter"), data.get("phase", "free"))
    pos = row["pos"]
    step = steps[pos]
    text, rows = flow.render(step, lang, data)
    markup = kb(rows, f"a:{sid}:{pos}")
    if edit:
        try:
            await target.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest:
            pass
    await (target.answer(text, reply_markup=markup))


@dp.message(CommandStart())
async def on_start(message: Message, command: CommandObject):
    db.init()
    u = message.from_user
    arg = command.args if command and command.args else ""
    if arg.startswith("par"):
        await open_parent_page(message, arg)
        return
    last = db.latest(u.id)
    if last and last["finished_at"] is None and last["pos"] > 1:
        lang = lang_of(last)
        await message.answer(T["resume"][lang], reply_markup=kb(
            [[(T["resume_yes"][lang], f"yes:{last['id']}")], [(T["resume_no"][lang], "no:0")]], "resume"))
        return
    prev = db.last_finished(u.id)
    if prev and prev["result"]:
        await show_history(message, prev)
        return
    ref = command.args if command and command.args else None
    sid = db.new_session(u.id, u.username, u.first_name, ref)
    await show_step(message, sid, edit=False)


async def show_history(message: Message, prev):
    import json
    import time as _t
    d = db.data_of(prev)
    lang = d.get("lang", "uz")
    res = json.loads(prev["result"])
    top = res.get("top") or []
    if res.get("kind") == "normal" and len(top) == 2:
        tip = PAIRS[pair_key(*top)][0 if lang == "uz" else 1]
    else:
        tip = "Keng qiziqishli izlanuvchi" if lang == "uz" else "Исследователь с широкими интересами"
    types = ", ".join(TYPE_NAMES[t][lang] for t in top)
    date = _t.strftime("%d.%m.%Y", _t.gmtime((prev["finished_at"] or 0) + 5 * 3600))
    rows = [[(T["again_yes"][lang], "new")], [(T["again_show"][lang], "show")]]
    if d.get("report_sent"):
        rows.append([(T["again_report"][lang], "report")])
    rows.append([(T["again_no"][lang], "no")])
    await message.answer(T["history"][lang].format(name=html.escape(message.from_user.first_name or ""), date=date,
                                                   tip=html.escape(tip), types=types),
                         reply_markup=kb(rows, f"again:{prev['id']}"))


@dp.callback_query(F.data.startswith("again:"))
async def on_again(cb: CallbackQuery):
    _, sid, val = cb.data.split(":")
    sid = int(sid)
    prev = db.get(sid)
    await cb.answer()
    if not prev or prev["user_id"] != cb.from_user.id:
        return
    d = db.data_of(prev)
    lang = d.get("lang", "uz")
    await cb.message.edit_reply_markup(reply_markup=None)
    if val == "new":
        u = cb.from_user
        new_sid = db.new_session(u.id, u.username, u.first_name)
        await show_step(cb.message, new_sid, edit=False)
    elif val == "show":
        text, _meta = scoring.free_result(html.escape(cb.from_user.first_name or ""), d["interest"], lang)
        await cb.message.answer(text)
        await cb.message.answer(T["again_bye"][lang])
    elif val == "report" and d.get("report_sent"):
        await deliver_report(cb.bot, sid, to=cb.from_user.id)
    else:
        await cb.message.answer(T["again_bye"][lang])


@dp.callback_query(F.data.startswith("resume:"))
async def on_resume(cb: CallbackQuery):
    _, choice, sid = cb.data.split(":")
    u = cb.from_user
    if choice == "yes":
        await show_step(cb.message, int(sid), edit=True)
    else:
        new_sid = db.new_session(u.id, u.username, u.first_name)
        await show_step(cb.message, new_sid, edit=True)
    await cb.answer()


@dp.callback_query(F.data.startswith("a:"))
async def on_answer(cb: CallbackQuery):
    _, sid, pos, value = cb.data.split(":", 3)
    sid, pos = int(sid), int(pos)
    row = db.get(sid)
    if not row or row["user_id"] != cb.from_user.id:
        await cb.answer()
        return
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    phase = data.get("phase", "free")
    active = (row["finished_at"] is None) if phase == "free" else (row["stage"] == "paid_q")
    if not active or row["pos"] != pos:
        await cb.answer(T["stale"][lang])
        return
    steps = flow.build_steps(data.get("filter"), phase)
    new_pos, data, err = flow.apply(steps, pos, data, value, min_pos=1 if phase == "free" else 0)
    lang = data.get("lang", "uz")
    if err == "empty":
        await cb.answer(T["empty"][lang], show_alert=True)
        return
    if err == "max":
        await cb.answer(flow.max_msg(steps[pos], lang), show_alert=True)
        return
    if data.get("first_answer_at") is None and steps[pos].startswith("int"):
        data["first_answer_at"] = int(time.time())
    steps = flow.build_steps(data.get("filter"), phase)
    db.save(sid, data=data, pos=new_pos)
    await cb.answer()
    if new_pos >= len(steps):
        if phase == "free":
            await finish(cb, sid)
        else:
            await finish_paid(cb, sid)
    elif new_pos == 1 and steps[pos] == "lang":
        name = html.escape(cb.from_user.first_name or "")
        await cb.message.edit_text(T["welcome"][lang].format(name=name))
        await show_step(cb.message, sid, edit=False)
    else:
        await show_step(cb.message, sid, edit=True)


async def finish(cb: CallbackQuery, sid: int):
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    await cb.message.edit_text(T["calc"][lang])
    name = html.escape(cb.from_user.first_name or "")
    text, meta = scoring.free_result(name, data["interest"], lang)
    meta["guess_match"] = scoring.guess_match(data.get("guess", []), meta["top"]) if meta["kind"] == "normal" else None
    db.save(sid, result=meta, finished_at=int(time.time()), stage="rating")

    me = await cb.bot.me()
    link = f"https://t.me/{me.username}?start=ref{cb.from_user.id}"
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(T['share_text'][lang])}"
    share = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T["share"][lang], url=share_url)]])
    await cb.message.edit_text(text, reply_markup=share)
    await cb.message.answer(T["rate"][lang], reply_markup=kb(
        [[(str(i), str(i)) for i in range(1, 6)], [(T["rate_offer_btn"][lang], "offer")]], f"r:{sid}"))


@dp.callback_query(F.data.startswith("r:"))
async def on_rating(cb: CallbackQuery):
    _, sid, val = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    if not row or row["user_id"] != cb.from_user.id or row["stage"] != "rating":
        await cb.answer()
        return
    lang = lang_of(row)
    if val == "offer":
        # baho bermasdan to‘g‘ridan-to‘g‘ri pullik taklifni ko‘rmoqchi
        db.save(sid, stage="offer")
        await cb.answer()
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        await show_offer(cb.message, sid)
        return
    rating = int(val)
    db.save(sid, rating=rating, stage="wrong" if rating <= 4 else "offer")
    await cb.answer()
    if rating <= 4:
        await show_wrong(cb.message, sid, edit=True)
    else:
        await cb.message.edit_text(f"{T['rate'][lang]}\n\n✅ {rating}")
        await show_offer(cb.message, sid)


async def show_wrong(msg: Message, sid: int, edit: bool):
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    chosen = set(data.get("wrong", []))
    idx = 1 if lang == "uz" else 2
    rows = [[(("✅ " if o[0] in chosen else "") + o[idx], o[0])] for o in WRONG_PART["options"]]
    rows.append([(flow.UI["next"][lang], "__done")])
    markup = kb(rows, f"w:{sid}")
    if edit:
        await msg.edit_text(WRONG_PART["text"][lang], reply_markup=markup)
    else:
        await msg.answer(WRONG_PART["text"][lang], reply_markup=markup)


@dp.callback_query(F.data.startswith("w:"))
async def on_wrong(cb: CallbackQuery):
    _, sid, val = cb.data.split(":", 2)
    sid = int(sid)
    row = db.get(sid)
    if not row or row["user_id"] != cb.from_user.id or row["stage"] != "wrong":
        await cb.answer()
        return
    data = db.data_of(row)
    if val == "__done":
        db.save(sid, stage="offer")
        await cb.answer()
        await cb.message.delete()
        await show_offer(cb.message, sid)
        return
    chosen = data.get("wrong", [])
    if val == "all_ok":
        chosen = ["all_ok"]
    else:
        chosen = [c for c in chosen if c != "all_ok"]
        chosen = [c for c in chosen if c != val] if val in chosen else chosen + [val]
    data["wrong"] = chosen
    db.save(sid, data=data)
    await cb.answer()
    await show_wrong(cb.message, sid, edit=True)


def offer_message(sid: int):
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    if not data.get("offer_shown"):
        data["offer_shown"] = int(time.time())
        db.save(sid, touch=False, data=data)
    price = T["price"][lang].format(PRICE_TEXT) if PRICE_TEXT else ""
    return T["offer"][lang].format(price=price), kb(
        [[(T["buy"][lang], "buy")], [(T["no_thanks"][lang], "no")]], f"p:{sid}")


async def show_offer(msg: Message, sid: int):
    text, markup = offer_message(sid)
    await msg.answer(text, reply_markup=markup)


OFFER_AFTER_MIN = int(os.getenv("OFFER_AFTER_MIN", "10"))


async def auto_offer_once(bot: Bot):
    """Natijani ko‘rib, baho bermay qolganlarga 10 daqiqadan keyin pullik taklifni o‘zi ko‘rsatadi."""
    now = int(time.time())
    for row in db.latest_per_user():
        if row["stage"] not in ("rating", "wrong"):
            continue
        data = db.data_of(row)
        idle = now - engage.last_active(row)
        if data.get("offer_shown") or data.get("blocked") or idle < OFFER_AFTER_MIN * 60 or idle > 86400:
            continue
        lang = data.get("lang", "uz")
        try:
            db.save(row["id"], touch=False, stage="offer")
            text, markup = offer_message(row["id"])
            await bot.send_message(row["user_id"], T["offer_auto_intro"][lang])
            await bot.send_message(row["user_id"], text, reply_markup=markup)
        except TelegramForbiddenError:
            data["blocked"] = 1
            db.save(row["id"], touch=False, data=data)
        except Exception as e:
            logging.warning("auto_offer xatosi (sessiya %s): %s", row["id"], e)
        await asyncio.sleep(0.1)


@dp.callback_query(F.data.startswith("p:"))
async def on_offer(cb: CallbackQuery):
    _, sid, val = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    if not row or row["user_id"] != cb.from_user.id or row["stage"] != "offer":
        await cb.answer()
        return
    lang = lang_of(row)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    if val == "no":
        db.save(sid, stage="done")
        await cb.message.answer(T["declined"][lang])
        return
    data = db.data_of(row)
    data["phase"] = "paid"
    db.save(sid, paid_click=1, stage="paid_q", data=data, pos=0)
    await cb.message.answer(T["pay_info"][lang].format(pay=pay_text(lang)))
    await notify_admins(cb.bot, sid, "💰 Pullik hisobotni bosdi")
    await cb.message.answer(T["paid_intro"][lang])
    await show_step(cb.message, sid, edit=False)


async def finish_paid(cb: CallbackQuery, sid: int):
    import json
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    res = json.loads(row["result"]) if row["result"] else {}
    res["tipi"] = scoring.tipi_scores(data["tipi"])
    db.save(sid, result=res, stage="dream")
    await cb.message.edit_text(T["open_intro"][lang])
    await cb.message.answer("1/2 · " + OPEN_DREAM[lang], reply_markup=kb([[(T["skip"][lang], "skip")]], f"o:{sid}"))


@dp.callback_query(F.data.startswith("o:"))
async def on_skip(cb: CallbackQuery):
    _, sid, _v = cb.data.split(":")
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await save_open(cb.message, int(sid), None, cb.bot)


async def save_open(msg: Message, sid: int, text: str | None, bot: Bot):
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    if row["stage"] == "dream":
        data["open_dream"] = text
        db.save(sid, data=data, stage="doubt")
        await msg.answer("2/2 · " + OPEN_DOUBT[lang], reply_markup=kb([[(T["skip"][lang], "skip")]], f"o:{sid}"))
    elif row["stage"] == "doubt":
        data["open_doubt"] = text
        db.save(sid, data=data, stage="done")
        if data.get("pay") == "ok":
            await deliver_report(bot, sid)
        else:
            if data.get("pay") == "pending":
                await msg.answer(T["answers_saved_pending"][lang])
            else:
                await msg.answer(T["answers_saved"][lang].format(pay=pay_text(lang)))
            await notify_admins(bot, sid, "📝 16 ta savolga javob berdi (to‘lov hali tasdiqlanmagan)")


@dp.message(Command("about"))
async def on_about(message: Message):
    await message.answer(
        "<b>Modifications and disclaimers</b>\n\n" + html.escape(LICENSE_NOTICE) +
        "\n\nModifications: the O*NET Mini Interest Profiler items and response labels were translated into "
        "Uzbek and Russian by Testry, and Testry added its own result interpretation. "
        "USDOL/ETA has not approved, endorsed, or tested these modifications and is not liable for any damages "
        "arising from their use.\n\n"
        "Natija tavsiya xarakterida, yakuniy qaror sizniki. / Результат носит рекомендательный характер.")


@dp.message(Command("stats"))
async def on_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = db.all_rows()
    started = [r for r in rows if r["pos"] > 2 or r["finished_at"]]
    done = [r for r in rows if r["finished_at"]]
    ratings = [r["rating"] for r in done if r["rating"]]
    matches = [json_get(r, "guess_match") for r in done]
    matches = [m for m in matches if m is not None]
    retests = [r for r in done if r["retest_of"]]
    durations = []
    for r in done:
        d = db.data_of(r)
        if d.get("first_answer_at"):
            durations.append((r["finished_at"] - d["first_answer_at"]) / 60)
    def pct(a, b):
        return f"{(100 * a / b):.0f}%" if b else "—"

    text = (f"📊 <b>Statistika</b>\n\n"
            f"Testni boshlagan: {len(started)}\n"
            f"Oxirigacha yechgan: {len(done)} ({pct(len(done), len(started))})\n")
    if durations:
        text += f"O‘rtacha vaqt: {sum(durations) / len(durations):.1f} daq\n"
    if ratings:
        text += f"O‘rtacha baho (1–5): {sum(ratings) / len(ratings):.2f} (n={len(ratings)})\n"
    if matches:
        text += (f"O‘z taxmini bilan moslik: 2/2 — {matches.count(2)}, 1/2 — {matches.count(1)}, "
                 f"0/2 — {matches.count(0)} (kamida 1 ta mos: {pct(sum(1 for m in matches if m >= 1), len(matches))})\n")
    paid = sum(r["paid_click"] for r in done)
    receipts = sum(r["receipt"] for r in done)
    text += (f"Pullik taklifni bosgan: {paid} ({pct(paid, len(done))})\n"
             f"Chek yuborgan: {receipts}\n"
             f"Qayta topshirganlar: {len(retests)}")
    await message.answer(text)


def json_get(row, key):
    import json
    return json.loads(row["result"]).get(key) if row["result"] else None


@dp.message(Command("export"))
async def on_export(message: Message):
    if not is_admin(message.from_user.id):
        return
    buf = io.StringIO()
    w = csv.writer(buf)
    head = (["session_id", "user_id", "username", "ref", "retest_of", "started_at", "finished_at", "minutes",
             "lang", "age", "filter", "who_text"] + [f"int{i + 1}_{INTEREST[i][0]}" for i in range(30)] +
            [f"tipi{i + 1}_{TIPI[i][0]}{'_R' if TIPI[i][1] else ''}" for i in range(10)] +
            ["subjects", "field", "values", "format", "difficulty", "guess", "R", "I", "A", "S", "E", "C",
             "profile", "top", "guess_match", "ext", "agr", "con", "emo", "opn", "rating", "wrong",
             "paid_click", "receipt", "open_dream", "open_doubt", "pay", "report_rating", "report_feedback",
             "last_step", "last_active", "reminded", "plan_answers", "chosen_direction", "parent_opened"])
    w.writerow(head)
    import json
    for r in db.all_rows():
        d = db.data_of(r)
        res = json.loads(r["result"]) if r["result"] else {}
        sc = res.get("scores", {})
        tp = res.get("tipi", {})
        mins = round((r["finished_at"] - d["first_answer_at"]) / 60, 1) if r["finished_at"] and d.get("first_answer_at") else ""
        w.writerow([r["id"], r["user_id"], r["username"], r["ref"], r["retest_of"], r["started_at"], r["finished_at"], mins,
                    d.get("lang"), d.get("age"), d.get("filter"), d.get("who_text")] +
                   (d.get("interest") or [None] * 30) + (d.get("tipi") or [None] * 10) +
                   [";".join(d.get("subjects", [])), d.get("field"), d.get("values"), d.get("format"),
                    ";".join(d.get("difficulty", [])), ";".join(d.get("guess", []))] +
                   [sc.get(t) for t in "RIASEC"] +
                   [res.get("kind"), "".join(res.get("top", [])), res.get("guess_match")] +
                   [round(tp[k], 1) if k in tp else None for k in ("ext", "agr", "con", "emo", "opn")] +
                   [r["rating"], ";".join(d.get("wrong", [])), r["paid_click"], r["receipt"],
                    d.get("open_dream"), d.get("open_doubt"), d.get("pay"), d.get("report_rating"),
                    d.get("report_feedback"), engage.step_label(engage.step_key(r, d)), engage.last_active(r),
                    d.get("rem"), json.dumps(d.get("fu_answers", {})), d.get("chosen_direction"),
                    len(d.get("parent_opened", []))])
    data = buf.getvalue().encode("utf-8-sig")
    await message.answer_document(BufferedInputFile(data, filename=f"testry_{time.strftime('%Y%m%d_%H%M')}.csv"))


@dp.message(Command("retest"))
async def on_retest(message: Message):
    if not is_admin(message.from_user.id):
        return
    sent = 0
    for r in db.retest_candidates(14):
        try:
            await message.bot.send_message(r["user_id"], T["retest"][lang_of(r)])
            sent += 1
        except Exception:
            pass
        db.save(r["id"], touch=False, retest_invited=1)
        await asyncio.sleep(0.05)
    await message.answer(f"Qayta test taklifi yuborildi: {sent} kishiga")


async def notify_admins(bot: Bot, sid: int, title: str):
    import json
    row = db.get(sid)
    d = db.data_of(row)
    res = json.loads(row["result"]) if row["result"] else {}
    sc = res.get("scores", {})
    top = res.get("top", [])
    pair = PAIRS[pair_key(*top)][0] if res.get("kind") == "normal" else res.get("kind")
    env = scoring.env_lines(res.get("tipi", {}), "uz") if res.get("tipi") else []
    who = (f"@{row['username']}, " if row["username"] else "") + f"id {row['user_id']}"
    filt = html.escape(d.get("who_text") or dict((o[0], o[1]) for o in FILTER["options"]).get(d.get("filter"), ""))

    def labels(q, codes):
        m = {o[0]: o[1] for o in q["options"]}
        return ", ".join(m.get(c, c) for c in (codes if isinstance(codes, list) else [codes]) if c)
    text = (f"{title}\n\n👤 {html.escape(row['first_name'] or '')} ({who}), sessiya #{sid}\n"
            f"Til: {d.get('lang')} · Yosh: {d.get('age')} · {filt}\n\n"
            f"Tip: <b>{html.escape(str(pair))}</b>\n"
            + " · ".join(f"{t} {sc.get(t)}" for t in "RIASEC") +
            f"\nO‘z taxmini: {', '.join(d.get('guess', []))} (moslik: {res.get('guess_match')})\n"
            f"Ish muhiti: {'; '.join(env) or '—'}\n"
            f"Fanlar/soha: {labels(SUBJECTS, d.get('subjects', [])) or labels(FIELD, d.get('field'))}\n"
            f"Qadriyat: {labels(VALUES, d.get('values'))}\nFormat: {labels(FORMAT, d.get('format'))}\n"
            f"Qiyinchilik: {labels(DIFFICULTY, d.get('difficulty', []))}\n"
            f"Baho: {row['rating']} · Noto‘g‘ri: {labels(WRONG_PART, d.get('wrong', [])) or '—'}\n"
            f"Orzu: {html.escape(d.get('open_dream') or '—')}\n"
            f"Ikkilanish: {html.escape(d.get('open_doubt') or '—')}")
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
        except Exception as e:
            logging.warning("admin notify failed: %s", e)


@dp.message(F.photo | F.document)
async def on_receipt(message: Message):
    last = db.latest(message.from_user.id)
    if not last or not last["paid_click"]:
        return
    data = db.data_of(last)
    if data.get("pay") == "ok":
        return
    data["pay"] = "pending"
    db.save(last["id"], receipt=1, data=data)
    who = (f"@{last['username']}, " if last["username"] else "") + f"id {last['user_id']}"
    buttons = kb([[("✅ Pul tushdi", "ok"), ("❌ Tushmadi", "no")],
                  [("⚠️ To‘liq summa tushmadi", "part")]], f"pay:{last['id']}")
    for aid in ADMIN_IDS:
        try:
            await message.forward(aid)
            await message.bot.send_message(
                aid, f"🧾 Chek: sessiya #{last['id']} · {html.escape(last['first_name'] or '')} ({who})\n"
                     f"Kutilgan summa: <b>{html.escape(PRICE_TEXT or '—')}</b>\n\n"
                     "Karta tarixini tekshirib, tugmani bosing:", reply_markup=buttons)
        except Exception as e:
            logging.warning("forward failed: %s", e)
    await message.answer(T["receipt_ok"][lang_of(last)])


@dp.callback_query(F.data.startswith("pay:"))
async def on_pay_decision(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer()
        return
    _, sid, val = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    if not row:
        await cb.answer("Sessiya topilmadi", show_alert=True)
        return
    data = db.data_of(row)
    if data.get("pay") == "ok":
        await cb.answer("Bu to‘lov allaqachon tasdiqlangan", show_alert=True)
        return
    lang = data.get("lang", "uz")
    data["pay"] = {"ok": "ok", "part": "partial"}.get(val, "rejected")
    db.save(sid, data=data)
    await cb.answer()
    mark = {"ok": "✅ Tasdiqlandi", "part": "⚠️ To‘liq summa tushmadi"}.get(val, "❌ Rad etildi")
    try:
        await cb.message.edit_text(cb.message.html_text.split("\n\nKarta tarixini")[0] +
                                   f"\n\n{mark} ({html.escape(cb.from_user.first_name or '')})")
    except TelegramBadRequest:
        pass
    if val == "ok":
        await cb.bot.send_message(row["user_id"], T["pay_ok"][lang])
        if row["stage"] in ("paid_q", "dream", "doubt"):
            await cb.bot.send_message(row["user_id"], T["pay_ok_wait_q"][lang])
        await on_paid_confirmed(cb.bot, sid)
    elif val == "part":
        await cb.bot.send_message(row["user_id"], T["pay_partial"][lang].format(
            price=html.escape(PRICE_TEXT or "—"), pay=pay_text(lang)))
    else:
        await cb.bot.send_message(row["user_id"], T["pay_no"][lang])


async def on_paid_confirmed(bot: Bot, sid: int):
    """To‘lov tasdiqlanganda chaqiriladi: savollar tugagan bo‘lsa, hisobot darhol yuboriladi."""
    row = db.get(sid)
    if row["stage"] == "done":
        await deliver_report(bot, sid)


async def deliver_report(bot: Bot, sid: int, to: int | None = None) -> bool:
    """Hisobotni tuzib yuboradi. to berilsa (admin ko‘rish uchun), faqat o‘sha odamga yuboradi."""
    import json
    row = db.get(sid)
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    if to is None and (data.get("report_sent") or data.get("pay") != "ok" or row["stage"] != "done"):
        return False
    res = json.loads(row["result"]) if row["result"] else {}
    if not res.get("scores"):
        return False
    chat = to or row["user_id"]
    await bot.send_message(chat, T["report_wait"][lang])
    parts = await report.build(row["first_name"] or "", data, res, lang)
    for p in parts:
        await bot.send_message(chat, p)
        await asyncio.sleep(0.3)
    if to is not None:
        return True
    await send_parent_offer(bot, chat, sid, lang)
    data["report_sent"] = int(time.time())
    db.save(sid, data=data, stage="report_rate")
    await bot.send_message(chat, T["report_rate"][lang],
                           reply_markup=kb([[(str(i), str(i)) for i in range(1, 6)]], f"rf:{sid}"))
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, f"📘 Hisobot yuborildi: sessiya #{sid} ({html.escape(row['first_name'] or '')})")
        except Exception:
            pass
    return True


@dp.callback_query(F.data.startswith("rf:"))
async def on_report_rate(cb: CallbackQuery):
    _, sid, val = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    if not row or row["user_id"] != cb.from_user.id or row["stage"] != "report_rate":
        await cb.answer()
        return
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    data["report_rating"] = int(val)
    db.save(sid, data=data, stage="report_fb")
    await cb.answer()
    await cb.message.edit_text(f"{T['report_rate'][lang]}\n\n✅ {val}")
    await cb.message.answer(T["report_fb_ask"][lang], reply_markup=kb([[(T["skip"][lang], "skip")]], f"rfs:{sid}"))


@dp.callback_query(F.data.startswith("rfs:"))
async def on_report_fb_skip(cb: CallbackQuery):
    _, sid, _v = cb.data.split(":")
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await save_report_feedback(cb.bot, int(sid), None, cb.from_user.id)


async def save_report_feedback(bot: Bot, sid: int, text: str | None, uid: int):
    row = db.get(sid)
    if not row or row["user_id"] != uid or row["stage"] != "report_fb":
        return
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    data["report_feedback"] = text
    db.save(sid, data=data, stage="closed")
    await bot.send_message(uid, T["report_fb_thanks"][lang])
    who = f"@{row['username']}" if row["username"] else f"id {row['user_id']}"
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, f"⭐ Hisobotga baho: {data.get('report_rating')} · sessiya #{sid} ({who})\n"
                                        f"Fikr: {html.escape(text or '—')}")
        except Exception:
            pass


@dp.message(Command("report"))
async def on_report_preview(message: Message, command: CommandObject):
    """Foydalanuvchi: o‘z hisobotini qayta oladi. Admin: /report 12 — 12-sessiya hisobotini ko‘radi."""
    if not (is_admin(message.from_user.id) and command.args and command.args.strip().isdigit()):
        prev = db.last_finished(message.from_user.id)
        lang = user_lang(message.from_user.id)
        if prev and db.data_of(prev).get("report_sent"):
            await deliver_report(message.bot, prev["id"], to=message.from_user.id)
        else:
            await message.answer(MENU_T["no_report"][lang])
        return
    sid = int(command.args.strip())
    row = db.get(sid)
    if not row or not row["result"]:
        await message.answer("Bu sessiyada natija yo‘q")
        return
    await deliver_report(message.bot, sid, to=message.from_user.id)


@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    if is_admin(message.from_user.id) and message.reply_to_message:
        if await relay_admin_reply(message):
            return
    last = db.latest(message.from_user.id)
    if last and last["finished_at"] is None:
        data = db.data_of(last)
        steps = flow.build_steps(data.get("filter"), "free")
        pos = last["pos"] or 0
        if pos < len(steps) and steps[pos] == "who":
            lang = data.get("lang", "uz")
            new_pos, data, err = flow.apply(steps, pos, data, message.text)
            if err == "short":
                await message.answer(WHO["short"][lang])
                return
            db.save(last["id"], data=data, pos=new_pos)
            await show_step(message, last["id"], edit=False)
            return
    if last and last["stage"] in ("dream", "doubt"):
        await save_open(message, last["id"], message.text[:2000], message.bot)
        return
    if last and last["stage"] == "report_fb":
        await save_report_feedback(message.bot, last["id"], message.text[:2000], message.from_user.id)
        return
    if last and last["stage"] == "fu_text":
        data = db.data_of(last)
        data["chosen_direction"] = message.text[:500]
        db.save(last["id"], data=data, stage="closed")
        await message.answer(E["fu_text_thanks"][data.get("lang", "uz")])
        await admin_note(message.bot, f"🎯 Yo‘nalishini tanladi: sessiya #{last['id']} · "
                                      f"{html.escape(message.from_user.first_name or '')}, id {message.from_user.id}\n"
                                      f"«{html.escape(message.text[:500])}»")
        return
    # boshqa matnlar: xushmuomala javob + adminlarga (admin “Reply” qilib javob yozishi mumkin)
    lang = lang_of(last) if last else "uz"
    await message.answer(E["ack"][lang])
    await admin_note(message.bot, f"💬 Xabar ({html.escape(message.from_user.first_name or '')}, "
                                  f"id {message.from_user.id}):\n{html.escape(message.text[:2000])}\n\n"
                                  "<i>Javob berish uchun shu xabarga “Reply” qilib yozing.</i>")


async def admin_note(bot: Bot, text: str, markup=None):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text, reply_markup=markup)
        except Exception:
            pass


async def relay_admin_reply(message: Message) -> bool:
    """Admin bot xabariga “Reply” qilsa, javob o‘sha foydalanuvchiga yuboriladi."""
    import re
    src = message.reply_to_message
    if not src or not (src.text or src.caption):
        return False
    m = re.search(r"\bid (\d{4,})", src.text or src.caption)
    if not m:
        return False
    uid = int(m.group(1))
    last = db.latest(uid)
    lang = lang_of(last) if last else "uz"
    try:
        await message.bot.send_message(uid, E["admin_reply"][lang].format(text=html.escape(message.text[:3500])))
        await message.answer("✅ Javob yuborildi")
    except Exception as e:
        await message.answer(f"Yuborilmadi: {html.escape(str(e))[:200]}")
    return True


def pay_text(lang: str) -> str:
    if PAYMENT_URL:
        return T["pay_link"][lang].format(PAYMENT_URL)
    if CARD_NUMBER:
        digits = CARD_NUMBER.replace(" ", "")
        card = " ".join(digits[i:i + 4] for i in range(0, len(digits), 4))
        return T["pay_card"][lang].format(price=html.escape(PRICE_TEXT or "—"), card=card,
                                          holder=html.escape(CARD_HOLDER or "—"))
    logging.warning("CARD_NUMBER o‘rnatilmagan: to‘lov uchun karta raqami ko‘rsatilmadi")
    return T["pay_manual"][lang].format(price=html.escape(PRICE_TEXT or "—"))


# ---------------- Ota-onaga ulashish ----------------

async def send_parent_offer(bot: Bot, chat: int, sid: int, lang: str):
    me = await bot.me()
    link = f"https://t.me/{me.username}?start={engage.parent_param(sid, BOT_TOKEN)}"
    url = f"https://t.me/share/url?url={quote(link)}&text={quote(E['parent_share_text'][lang])}"
    await bot.send_message(chat, E["parent_offer"][lang], reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=E["parent_btn"][lang], url=url)]]))


async def open_parent_page(message: Message, arg: str):
    import json
    sid = engage.parse_parent_param(arg, BOT_TOKEN)
    row = db.get(sid) if sid else None
    data = db.data_of(row) if row else {}
    lang = data.get("lang", "uz")
    if not row or not data.get("report_sent") or not row["result"]:
        await message.answer(E["parent_bad"][lang])
        return
    res = json.loads(row["result"])
    child = html.escape(row["first_name"] or "")
    await message.answer(E["parent_hello"][lang].format(child=child) + "\n\n" +
                         report.section_parents(res, data, lang))
    await message.answer(E["parent_try"][lang])
    opened = data.get("parent_opened", [])
    if message.from_user.id not in opened and message.from_user.id != row["user_id"]:
        opened.append(message.from_user.id)
        data["parent_opened"] = opened
        db.save(sid, touch=False, data=data)
        try:
            await message.bot.send_message(row["user_id"], E["child_parent_opened"][lang])
        except Exception:
            pass
        await admin_note(message.bot, f"👨‍👩‍👧 Ota-ona sahifani ochdi: sessiya #{sid} ({child})")


# ---------------- Eslatmalar va reja bo‘yicha so‘rovlar ----------------

@dp.callback_query(F.data.startswith("rem:"))
async def on_reminder_button(cb: CallbackQuery):
    _, sid, kind = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    await cb.answer()
    if not row or row["user_id"] != cb.from_user.id:
        return
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    await cb.message.edit_reply_markup(reply_markup=None)
    st = row["stage"]
    if kind == "cont" and row["finished_at"] is None:
        await show_step(cb.message, sid, edit=False)
    elif kind == "cont" and st == "paid_q":
        await show_step(cb.message, sid, edit=False)
    elif kind == "cont" and st == "dream":
        await cb.message.answer("1/2 · " + OPEN_DREAM[lang], reply_markup=kb([[(T["skip"][lang], "skip")]], f"o:{sid}"))
    elif kind == "cont" and st == "doubt":
        await cb.message.answer("2/2 · " + OPEN_DOUBT[lang], reply_markup=kb([[(T["skip"][lang], "skip")]], f"o:{sid}"))
    elif kind == "offer" and st in ("rating", "wrong", "offer"):
        db.save(sid, stage="offer")
        await show_offer(cb.message, sid)
    elif kind == "pay" and st == "done" and data.get("phase") == "paid" and data.get("pay") != "ok":
        await cb.message.answer(T["pay_info"][lang].format(pay=pay_text(lang)))
    else:
        await cb.message.answer(E["gone"][lang])


@dp.callback_query(F.data.startswith("fu:"))
async def on_followup_button(cb: CallbackQuery):
    _, sid, idx, val = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    await cb.answer()
    if not row or row["user_id"] != cb.from_user.id:
        return
    data = db.data_of(row)
    lang = data.get("lang", "uz")
    answers = data.get("fu_answers", {})
    answers[idx] = val
    data["fu_answers"] = answers
    stage = "fu_text" if val == "chosen" else row["stage"]
    db.save(sid, data=data, stage=stage)
    labels = {v: t for t, v in E["fu_btn"][int(idx)][lang]}
    try:
        await cb.message.edit_text(cb.message.html_text + f"\n\n<b>{labels.get(val, val)}</b>")
    except TelegramBadRequest:
        pass
    await cb.message.answer(E["fu_reply"][val][lang])
    who = (f"@{row['username']}, " if row["username"] else "") + f"id {row['user_id']}"
    await admin_note(cb.bot, f"📅 Reja so‘rovi ({[3, 7, 14][int(idx)]}-kun): sessiya #{sid} · "
                             f"{html.escape(row['first_name'] or '')} ({who})\nJavob: {labels.get(val, val)}"
                     + ("\n\n<i>Yordam so‘radi: shu xabarga “Reply” qilib javob yozing.</i>" if val in ("help", "hard") else ""))


async def send_reminder(bot: Bot, row, data: dict) -> str | None:
    """Kerak bo‘lsa eslatma yuboradi va eslatma turini qaytaradi."""
    import json
    lang = data.get("lang", "uz")
    name = html.escape(row["first_name"] or "")
    sid = row["id"]
    st = row["stage"]
    if row["finished_at"] is None:
        pos = row["pos"] or 0
        done = max(0, pos - 3)
        if done == 0:
            text = E["rem_start"][lang].format(name=name)
        else:
            text = E["rem_free"][lang].format(name=name, done=done, left=max(1, 30 - done))
        markup = kb([[(E["btn_continue"][lang], f"yes:{sid}")]], "resume")
        key = "free"
    elif st in ("rating", "wrong", "offer"):
        res = json.loads(row["result"]) if row["result"] else {}
        top = res.get("top") or []
        tip = PAIRS[pair_key(*top)][0 if lang == "uz" else 1] if res.get("kind") == "normal" and len(top) == 2 else "—"
        text = E["rem_offer"][lang].format(name=name, tip=html.escape(tip))
        markup = kb([[(E["btn_offer"][lang], "offer")]], f"rem:{sid}")
        key = "offer"
    elif st == "paid_q":
        text = E["rem_paid_q"][lang].format(name=name, left=max(1, 14 - (row["pos"] or 0)))
        markup = kb([[(E["btn_continue"][lang], "cont")]], f"rem:{sid}")
        key = "paid_q"
    elif st in ("dream", "doubt"):
        text = E["rem_open"][lang].format(name=name)
        markup = kb([[(E["btn_continue"][lang], "cont")]], f"rem:{sid}")
        key = "open"
    elif st == "done" and data.get("phase") == "paid" and data.get("pay") in (None, "partial"):
        text = E["rem_pay"][lang].format(name=name)
        markup = kb([[(E["btn_pay"][lang], "pay")]], f"rem:{sid}")
        key = "pay"
    else:
        return None
    if data.get("rem") == key:
        return None
    await bot.send_message(row["user_id"], text, reply_markup=markup)
    return key


async def engage_once(bot: Bot):
    if not engage.can_send_now():
        return
    now = engage.now()
    for row in db.latest_per_user():
        data = db.data_of(row)
        if data.get("blocked"):
            continue
        lang = data.get("lang", "uz")
        try:
            # 1) Hisobot olganlarga reja bo‘yicha so‘rov (3, 7, 14-kun)
            if data.get("report_sent"):
                days = (now - data["report_sent"]) / 86400
                sent = data.get("fu", [])
                due = [i for i, d in enumerate(engage.FOLLOWUP_DAYS) if days >= d and i not in sent]
                if due:
                    i = due[-1]
                    name = html.escape(row["first_name"] or "")
                    btns = [[(t, v)] for t, v in E["fu_btn"][i][lang]]
                    await bot.send_message(row["user_id"], E[f"fu{i}"][lang].format(name=name),
                                           reply_markup=kb(btns, f"fu:{row['id']}:{i}"))
                    data["fu"] = sorted(set(sent) | set(range(i + 1)))
                    db.save(row["id"], touch=False, data=data)
                continue
            # 2) Admin: tasdiqlanmagan chek 6 soatdan oshsa, bir marta eslatish
            if data.get("pay") == "pending" and not data.get("pay_nag") and now - engage.last_active(row) > 6 * 3600:
                await admin_note(bot, f"⏰ Chek tasdiqlanishini kutyapti: sessiya #{row['id']} "
                                      f"({html.escape(row['first_name'] or '')}). Yuqoridagi ✅/❌ tugmasini bosing.")
                data["pay_nag"] = 1
                db.save(row["id"], touch=False, data=data)
                continue
            # 3) 3 kun faolsiz qolganlarga, to‘xtagan joyiga qarab eslatma
            if now - engage.last_active(row) < engage.REMIND_DAYS * 86400:
                continue
            key = await send_reminder(bot, row, data)
            if key:
                data["rem"] = key
                db.save(row["id"], touch=False, data=data)
        except TelegramForbiddenError:
            data["blocked"] = 1
            db.save(row["id"], touch=False, data=data)
        except Exception as e:
            logging.warning("engage xatosi (sessiya %s): %s", row["id"], e)
        await asyncio.sleep(0.1)


async def engage_loop(bot: Bot):
    await asyncio.sleep(120)
    tick = 0
    while True:
        try:
            await auto_offer_once(bot)
        except Exception as e:
            logging.warning("auto_offer_loop: %s", e)
        if tick % 6 == 0:
            try:
                await engage_once(bot)
            except Exception as e:
                logging.warning("engage_loop: %s", e)
        tick += 1
        await asyncio.sleep(5 * 60)


_engage_started = False


@dp.startup()
async def on_startup(bot: Bot):
    global _engage_started
    if not _engage_started:
        _engage_started = True
        asyncio.create_task(engage_loop(bot))
        asyncio.create_task(setup_menu(bot))


# ---------------- Menyu (chap pastdagi "Menu" tugmasi) ----------------

USER_COMMANDS = {
    "uz": [("start", "🚀 Testni boshlash"), ("result", "📊 Mening natijam"), ("report", "📘 To‘liq hisobotim"),
           ("language", "🌐 Tilni o‘zgartirish"), ("help", "💬 Yordam va savollar"), ("about", "ℹ️ Test haqida")],
    "ru": [("start", "🚀 Начать тест"), ("result", "📊 Мой результат"), ("report", "📘 Мой полный отчёт"),
           ("language", "🌐 Сменить язык"), ("help", "💬 Помощь и вопросы"), ("about", "ℹ️ О тесте")],
}
ADMIN_COMMANDS = [("stats", "📊 Statistika"), ("funnel", "📉 Kim qayerda to‘xtadi"), ("users", "👥 Oxirgi foydalanuvchilar"),
                  ("export", "📁 Barcha javoblar (fayl)"), ("retest", "🔁 Qayta test taklifi")]

MENU_T = {
    "no_result": {"uz": "Siz hali testni yechmagansiz 🙂 Boshlash uchun: /start",
                  "ru": "Вы ещё не проходили тест 🙂 Начать: /start"},
    "no_report": {"uz": "Sizda hali to‘liq hisobot yo‘q 🙂 Testni yechib, natijadan keyin “To‘liq hisobotni olish” tugmasini bosing: /start",
                  "ru": "У вас пока нет полного отчёта 🙂 Пройдите тест и после результата нажмите «Получить полный отчёт»: /start"},
    "lang_ask": {"uz": "Tilni tanlang:", "ru": "Выберите язык:"},
    "lang_ok": {"uz": "Til o‘zgartirildi ✅", "ru": "Язык изменён ✅"},
    "help": {"uz": "💬 <b>Yordam</b>\n\nSavolingiz yoki fikringizni shu chatga oddiy xabar qilib yozing. "
                   "Jamoamiz albatta o‘qiydi va shu yerda javob beradi. 😊\n\n"
                   "<b>Buyruqlar:</b>\n/start — testni boshlash\n/result — mening natijam\n"
                   "/report — to‘liq hisobotim\n/language — tilni o‘zgartirish\n/about — test haqida",
             "ru": "💬 <b>Помощь</b>\n\nНапишите свой вопрос или отзыв обычным сообщением в этот чат. "
                   "Наша команда обязательно прочитает и ответит здесь. 😊\n\n"
                   "<b>Команды:</b>\n/start — начать тест\n/result — мой результат\n"
                   "/report — мой полный отчёт\n/language — сменить язык\n/about — о тесте"},
}


def user_lang(uid: int) -> str:
    last = db.latest(uid)
    return lang_of(last) if last else "uz"


async def setup_menu(bot: Bot):
    """Telegram'dagi “Menu” tugmasi uchun buyruqlar ro‘yxati: o‘zbekcha (asosiy), ruscha, adminlar uchun alohida."""
    try:
        for lang_code, lang in ((None, "uz"), ("ru", "ru")):
            await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in USER_COMMANDS[lang]],
                                      scope=BotCommandScopeDefault(), language_code=lang_code)
        for aid in ADMIN_IDS:
            cmds = USER_COMMANDS["uz"] + ADMIN_COMMANDS
            await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in cmds],
                                      scope=BotCommandScopeChat(chat_id=aid))
        logging.info("menyu buyruqlari o‘rnatildi")
    except Exception as e:
        logging.warning("menyu o‘rnatilmadi: %s", e)


@dp.message(Command("result"))
async def on_result_cmd(message: Message):
    prev = db.last_finished(message.from_user.id)
    if not prev or not prev["result"]:
        await message.answer(MENU_T["no_result"][user_lang(message.from_user.id)])
        return
    d = db.data_of(prev)
    text, _meta = scoring.free_result(html.escape(message.from_user.first_name or ""), d["interest"], d.get("lang", "uz"))
    await message.answer(text)


@dp.message(Command("help"))
async def on_help_cmd(message: Message):
    await message.answer(MENU_T["help"][user_lang(message.from_user.id)])


@dp.message(Command("language"))
async def on_language_cmd(message: Message):
    lang = user_lang(message.from_user.id)
    await message.answer(MENU_T["lang_ask"][lang], reply_markup=kb([[("🇺🇿 O‘zbekcha", "uz"), ("🇷🇺 Русский", "ru")]], "setlang"))


@dp.callback_query(F.data.startswith("setlang:"))
async def on_setlang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await cb.answer()
    for row in (db.latest(cb.from_user.id), db.last_finished(cb.from_user.id)):
        if row:
            d = db.data_of(row)
            d["lang"] = lang
            db.save(row["id"], touch=False, data=d)
    await cb.message.edit_text(MENU_T["lang_ok"][lang])


# ---------------- Voronka: kim qayerda to‘xtadi ----------------

@dp.message(Command("funnel"))
async def on_funnel(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = db.latest_per_user()
    counts = {}
    for r in rows:
        k = engage.step_key(r, db.data_of(r))
        counts[k] = counts.get(k, 0) + 1
    total = len(rows) or 1
    lines = [f"📉 <b>Kim qayerda to‘xtagan</b> (har bir foydalanuvchining oxirgi urinishi, jami {len(rows)})\n"]
    for k in engage.FUNNEL_ORDER:
        if counts.get(k):
            lines.append(f"{engage.step_label(k)} — <b>{counts[k]}</b> ({100 * counts[k] / total:.0f}%)")
    stuck = sorted(((v, k) for k, v in counts.items() if k != "closed"), reverse=True)[:3]
    if stuck:
        lines.append("\n🔎 Eng ko‘p to‘xtagan joylar: " + "; ".join(f"{engage.step_label(k)} ({v})" for v, k in stuck))
    lines.append("\nBatafsil ro‘yxat: /users")
    await message.answer("\n".join(lines))


@dp.message(Command("users"))
async def on_users(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    n = int(command.args) if command.args and command.args.strip().isdigit() else 20
    rows = sorted(db.latest_per_user(), key=engage.last_active, reverse=True)[:min(n, 50)]
    lines = [f"👥 <b>Oxirgi {len(rows)} foydalanuvchi</b>\n"]
    for r in rows:
        who = f"@{r['username']}" if r["username"] else f"id {r['user_id']}"
        lines.append(f"#{r['id']} {html.escape(r['first_name'] or '')} ({who}) — "
                     f"{engage.step_label(engage.step_key(r, db.data_of(r)))} · {engage.ago(engage.last_active(r))}")
    await message.answer("\n".join(lines))


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN o‘rnatilmagan")
    db.init()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
