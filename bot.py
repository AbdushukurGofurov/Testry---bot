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
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           Message)

import db
import flow
import report
import scoring
from questions import (DIFFICULTY, FIELD, FORMAT, SUBJECTS, VALUES, FILTER, INTEREST, LICENSE_NOTICE, OPEN_DOUBT, OPEN_DREAM, PAIRS, TIPI, WRONG_PART,
                       pair_key)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
PRICE_TEXT = os.getenv("PRICE_TEXT", "")          # masalan: "49 000 so‘m"
PAYMENT_URL = os.getenv("PAYMENT_URL", "")        # Payme/Click havolasi (ixtiyoriy)
CARD_NUMBER = os.getenv("CARD_NUMBER", "").strip()  # to‘lov qabul qilinadigan karta (Render Environment’da)
CARD_HOLDER = os.getenv("CARD_HOLDER", "").strip()  # karta egasining ismi

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
    "share_text": {"uz": "Men Testry’da qiziqishlarimni aniqladim. Sen ham sinab ko‘r!",
                   "ru": "Я определил(а) свои интересы в Testry. Попробуй и ты!"},
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
               "To‘lov tasdiqlangach, hisobot shu chatga yuboriladi.{price}"),
        "ru": ("📘 <b>Полный отчёт</b>\n\n"
               "✓ 6 подходящих направлений и почему именно они\n"
               "✓ Подходят ли ваши предметы к этим направлениям\n"
               "✓ Комфортная для вас рабочая среда\n"
               "✓ Отдельный ответ на ваши сомнения в выборе профессии\n"
               "✓ Персональный AI-комментарий по вашим ответам\n"
               "✓ План проб на 2 недели\n"
               "✓ Отдельная страница для родителей\n\n"
               "Для точного отчёта ответьте ещё на 16 коротких вопросов (~3 минуты). "
               "После подтверждения оплаты отчёт придёт в этот чат.{price}"),
    },
    "price": {"uz": "\n\n💳 Narxi: <b>{}</b>", "ru": "\n\n💳 Стоимость: <b>{}</b>"},
    "buy": {"uz": "📘 To‘liq hisobotni olish", "ru": "📘 Получить полный отчёт"},
    "no_thanks": {"uz": "Hozircha kerak emas", "ru": "Пока не нужно"},
    "pay_info": {
        "uz": "Rahmat! 🙌\n\n{pay}To‘lovdan keyin chekning rasmini (skrinshotini) shu chatga yuboring. "
              "To‘lov tasdiqlangach, hisobot shu yerga keladi.",
        "ru": "Спасибо! 🙌\n\n{pay}После оплаты отправьте фото (скриншот) чека в этот чат. "
              "После подтверждения оплаты отчёт придёт сюда.",
    },
    "pay_link": {"uz": "To‘lov havolasi: {}\n\n", "ru": "Ссылка на оплату: {}\n\n"},
    "pay_card": {"uz": "💳 To‘lov: <b>{price}</b>\nKarta raqami: <code>{card}</code>\nKarta egasi: {holder}\n"
                       "<i>(raqamni bossangiz, nusxalanadi)</i>\n\n",
                 "ru": "💳 Оплата: <b>{price}</b>\nНомер карты: <code>{card}</code>\nВладелец: {holder}\n"
                       "<i>(нажмите на номер, чтобы скопировать)</i>\n\n"},
    "pay_manual": {"uz": "Tez orada administratorimiz siz bilan bog‘lanib, to‘lov tafsilotlarini yuboradi.\n\n",
                   "ru": "Скоро наш администратор свяжется с вами и отправит детали оплаты.\n\n"},
    "paid_intro": {"uz": "Endi hisobotingizni shaxsiylashtiramiz: 14 ta tugmali savol va 2 ta ochiq savol (~3 daqiqa). 👇",
                   "ru": "Теперь сделаем отчёт персональным: 14 вопросов с кнопками и 2 открытых (~3 минуты). 👇"},
    "open_intro": {"uz": "Deyarli tayyor! Oxirgi 2 ta savol (ixtiyoriy, lekin hisobotni ancha aniq qiladi):",
                   "ru": "Почти готово! Последние 2 вопроса (необязательно, но делают отчёт точнее):"},
    "skip": {"uz": "O‘tkazib yuborish", "ru": "Пропустить"},
    "thanks_end": {"uz": "Rahmat! Javoblaringiz saqlandi. ✅\n\nTestni qayta topshirish: /start",
                   "ru": "Спасибо! Ваши ответы сохранены. ✅\n\nПройти тест заново: /start"},
    "declined": {"uz": "Tushunarli! Testni qayta topshirish: /start\nNatijangiz haqida fikringiz bo‘lsa, shu yerga yozing.",
                 "ru": "Понятно! Пройти тест заново: /start\nЕсли есть мысли о результате — напишите сюда."},
    "receipt_ok": {"uz": "Chek qabul qilindi ✅ To‘lovni tekshiryapmiz, odatda bu bir necha soat ichida bo‘ladi. "
                         "Tasdiqlangach, shu yerga xabar keladi.",
                   "ru": "Чек получен ✅ Проверяем оплату, обычно это занимает несколько часов. "
                         "После подтверждения вы получите сообщение здесь."},
    "pay_ok": {"uz": "To‘lovingiz tasdiqlandi ✅ Rahmat!",
               "ru": "Оплата подтверждена ✅ Спасибо!"},
    "pay_ok_wait_q": {"uz": "Hisobot tayyor bo‘lishi uchun qo‘shimcha savollarni oxirigacha yakunlang. 👆",
                      "ru": "Чтобы отчёт был готов, ответьте на дополнительные вопросы до конца. 👆"},
    "pay_no": {"uz": "Afsuski, to‘lov topilmadi ❌\n\nSumma va karta raqamini tekshirib, chekni qayta yuboring. "
                     "Savol bo‘lsa, shu chatga yozing.",
               "ru": "К сожалению, оплата не найдена ❌\n\nПроверьте сумму и номер карты и отправьте чек ещё раз. "
                     "Если есть вопросы — напишите в этот чат."},
    "answers_saved": {"uz": "Rahmat! Javoblaringiz saqlandi ✅\n\nTo‘lov tasdiqlangach, hisobotingiz shu yerga keladi.",
                      "ru": "Спасибо! Ответы сохранены ✅\n\nПосле подтверждения оплаты отчёт придёт сюда."},
    "report_wait": {"uz": "⏳ Hisobotingiz tayyorlanmoqda...", "ru": "⏳ Готовим ваш отчёт..."},
    "report_rate": {"uz": "Hisobot sizga qanchalik to‘g‘ri va foydali bo‘ldi?\n1 — umuman yo‘q, 5 — juda foydali",
                    "ru": "Насколько отчёт оказался точным и полезным?\n1 — совсем нет, 5 — очень полезен"},
    "report_fb_ask": {"uz": "Rahmat! Hisobotda nima noto‘g‘ri yoki yetishmayotgan bo‘lsa, shu yerga yozing. "
                            "Fikringiz testni yaxshilashga yordam beradi (ixtiyoriy).",
                      "ru": "Спасибо! Если в отчёте что-то неточно или чего-то не хватает, напишите сюда. "
                            "Ваше мнение поможет улучшить тест (необязательно)."},
    "report_fb_thanks": {"uz": "Fikringiz uchun katta rahmat! 🙏\n\nTestni qayta topshirish: /start",
                         "ru": "Большое спасибо за отзыв! 🙏\n\nПройти тест заново: /start"},
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
    last = db.latest(u.id)
    if last and last["finished_at"] is None and last["pos"] > 1:
        lang = lang_of(last)
        await message.answer(T["resume"][lang], reply_markup=kb(
            [[(T["resume_yes"][lang], f"yes:{last['id']}")], [(T["resume_no"][lang], "no:0")]], "resume"))
        return
    ref = command.args if command and command.args else None
    sid = db.new_session(u.id, u.username, u.first_name, ref)
    await show_step(message, sid, edit=False)


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
    await cb.message.answer(T["rate"][lang], reply_markup=kb([[(str(i), str(i)) for i in range(1, 6)]], f"r:{sid}"))


@dp.callback_query(F.data.startswith("r:"))
async def on_rating(cb: CallbackQuery):
    _, sid, val = cb.data.split(":")
    sid = int(sid)
    row = db.get(sid)
    if not row or row["user_id"] != cb.from_user.id or row["stage"] != "rating":
        await cb.answer()
        return
    lang = lang_of(row)
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


async def show_offer(msg: Message, sid: int):
    lang = lang_of(db.get(sid))
    price = T["price"][lang].format(PRICE_TEXT) if PRICE_TEXT else ""
    await msg.answer(T["offer"][lang].format(price=price), reply_markup=kb(
        [[(T["buy"][lang], "buy")], [(T["no_thanks"][lang], "no")]], f"p:{sid}"))


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
    if PAYMENT_URL:
        pay = T["pay_link"][lang].format(PAYMENT_URL)
    elif CARD_NUMBER:
        card = " ".join(CARD_NUMBER.replace(" ", "")[i:i + 4] for i in range(0, len(CARD_NUMBER.replace(" ", "")), 4))
        pay = T["pay_card"][lang].format(price=html.escape(PRICE_TEXT or "—"), card=card,
                                         holder=html.escape(CARD_HOLDER or "—"))
    else:
        pay = T["pay_manual"][lang]
    await cb.message.answer(T["pay_info"][lang].format(pay=pay))
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
            await msg.answer(T["answers_saved"][lang])
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
             "lang", "age", "filter"] + [f"int{i + 1}_{INTEREST[i][0]}" for i in range(30)] +
            [f"tipi{i + 1}_{TIPI[i][0]}{'_R' if TIPI[i][1] else ''}" for i in range(10)] +
            ["subjects", "field", "values", "format", "difficulty", "guess", "R", "I", "A", "S", "E", "C",
             "profile", "top", "guess_match", "ext", "agr", "con", "emo", "opn", "rating", "wrong",
             "paid_click", "receipt", "open_dream", "open_doubt", "pay", "report_rating", "report_feedback"])
    w.writerow(head)
    import json
    for r in db.all_rows():
        d = db.data_of(r)
        res = json.loads(r["result"]) if r["result"] else {}
        sc = res.get("scores", {})
        tp = res.get("tipi", {})
        mins = round((r["finished_at"] - d["first_answer_at"]) / 60, 1) if r["finished_at"] and d.get("first_answer_at") else ""
        w.writerow([r["id"], r["user_id"], r["username"], r["ref"], r["retest_of"], r["started_at"], r["finished_at"], mins,
                    d.get("lang"), d.get("age"), d.get("filter")] +
                   (d.get("interest") or [None] * 30) + (d.get("tipi") or [None] * 10) +
                   [";".join(d.get("subjects", [])), d.get("field"), d.get("values"), d.get("format"),
                    ";".join(d.get("difficulty", [])), ";".join(d.get("guess", []))] +
                   [sc.get(t) for t in "RIASEC"] +
                   [res.get("kind"), "".join(res.get("top", [])), res.get("guess_match")] +
                   [round(tp[k], 1) if k in tp else None for k in ("ext", "agr", "con", "emo", "opn")] +
                   [r["rating"], ";".join(d.get("wrong", [])), r["paid_click"], r["receipt"],
                    d.get("open_dream"), d.get("open_doubt"), d.get("pay"), d.get("report_rating"),
                    d.get("report_feedback")])
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
        db.save(r["id"], retest_invited=1)
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
    who = f"@{row['username']}" if row["username"] else f"id {row['user_id']}"
    filt = dict((o[0], o[1]) for o in FILTER["options"]).get(d.get("filter"), "")

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
    who = f"@{last['username']}" if last["username"] else f"id {last['user_id']}"
    buttons = kb([[("✅ Pul tushdi", "ok"), ("❌ Tushmadi", "no")]], f"pay:{last['id']}")
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
    data["pay"] = "ok" if val == "ok" else "rejected"
    db.save(sid, data=data)
    await cb.answer()
    mark = "✅ Tasdiqlandi" if val == "ok" else "❌ Rad etildi"
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
    """Admin uchun: /report 12 — 12-sessiya hisobotini o‘zingizga ko‘rish uchun yuboradi."""
    if not is_admin(message.from_user.id):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Foydalanish: /report sessiya_raqami (masalan, /report 3)")
        return
    sid = int(command.args.strip())
    row = db.get(sid)
    if not row or not row["result"]:
        await message.answer("Bu sessiyada natija yo‘q")
        return
    await deliver_report(message.bot, sid, to=message.from_user.id)


@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    last = db.latest(message.from_user.id)
    if last and last["stage"] in ("dream", "doubt"):
        await save_open(message, last["id"], message.text[:2000], message.bot)
        return
    if last and last["stage"] == "report_fb":
        await save_report_feedback(message.bot, last["id"], message.text[:2000], message.from_user.id)
        return
    # boshqa matnlar: fikr-mulohaza sifatida adminlarga
    for aid in ADMIN_IDS:
        try:
            await message.bot.send_message(aid, f"💬 Fikr ({html.escape(message.from_user.first_name or '')}, "
                                                f"id {message.from_user.id}):\n{html.escape(message.text[:2000])}")
        except Exception:
            pass


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN o‘rnatilmagan")
    db.init()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
