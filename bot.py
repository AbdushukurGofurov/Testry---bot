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
import scoring
from questions import (DIFFICULTY, FIELD, FORMAT, SUBJECTS, VALUES, FILTER, INTEREST, LICENSE_NOTICE, OPEN_DOUBT, OPEN_DREAM, PAIRS, TIPI, WRONG_PART,
                       pair_key)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
PRICE_TEXT = os.getenv("PRICE_TEXT", "")          # masalan: "49 000 so‘m"
PAYMENT_URL = os.getenv("PAYMENT_URL", "")        # Payme/Click havolasi (ixtiyoriy)

dp = Dispatcher()

T = {
    "welcome": {
        "uz": ("Salom, {name}! 👋\n\nBu test qiziqishlaringizni aniqlab, sizga mos yo‘nalishlarni ko‘rsatadi.\n"
               "⏱ 7–8 daqiqa · 45 ta savol · natija darhol\n\n"
               "To‘g‘ri yoki noto‘g‘ri javob yo‘q — o‘zingizga eng yaqinini tanlang.\n\n"
               "<i>Test O*NET va TIPI materiallari asosida moslashtirilgan. O‘zgartirishlar va ogohlantirishlar: /about</i>"),
        "ru": ("Привет, {name}! 👋\n\nЭтот тест определит ваши интересы и покажет подходящие направления.\n"
               "⏱ 7–8 минут · 45 вопросов · результат сразу\n\n"
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
               "✓ Sizga mos 3–5 ta yo‘nalish va nega aynan ular\n"
               "✓ Siz uchun qulay ish muhiti\n"
               "✓ O‘zbekistondagi OTM yo‘nalishlari va imtihon fanlari\n"
               "✓ Kasb tanlashdagi ikkilanishingizga alohida javob\n"
               "✓ 2 haftalik sinov rejasi\n"
               "✓ Ota-onangiz uchun alohida sahifa\n\n"
               "Hisobotni mutaxassisimiz 24 soat ichida tayyorlaydi.{price}"),
        "ru": ("📘 <b>Полный отчёт</b>\n\n"
               "✓ 3–5 подходящих направлений и почему именно они\n"
               "✓ Комфортная для вас рабочая среда\n"
               "✓ Направления вузов Узбекистана и вступительные предметы\n"
               "✓ Отдельный ответ на ваши сомнения в выборе профессии\n"
               "✓ План проб на 2 недели\n"
               "✓ Отдельная страница для родителей\n\n"
               "Отчёт подготовит наш специалист в течение 24 часов.{price}"),
    },
    "price": {"uz": "\n\n💳 Narxi: <b>{}</b>", "ru": "\n\n💳 Стоимость: <b>{}</b>"},
    "buy": {"uz": "📘 To‘liq hisobotni olish", "ru": "📘 Получить полный отчёт"},
    "no_thanks": {"uz": "Hozircha kerak emas", "ru": "Пока не нужно"},
    "pay_info": {
        "uz": "Rahmat! 🙌\n\n{pay}To‘lovdan keyin chekning rasmini shu chatga yuboring. Hisobot 24 soat ichida tayyor bo‘ladi.",
        "ru": "Спасибо! 🙌\n\n{pay}После оплаты отправьте фото чека в этот чат. Отчёт будет готов в течение 24 часов.",
    },
    "pay_link": {"uz": "To‘lov havolasi: {}\n\n", "ru": "Ссылка на оплату: {}\n\n"},
    "pay_manual": {"uz": "Tez orada administratorimiz siz bilan bog‘lanib, to‘lov tafsilotlarini yuboradi.\n\n",
                   "ru": "Скоро наш администратор свяжется с вами и отправит детали оплаты.\n\n"},
    "open_intro": {"uz": "Hisobot aniqroq bo‘lishi uchun 2 ta qisqa savol (ixtiyoriy):",
                   "ru": "Чтобы отчёт был точнее, 2 коротких вопроса (необязательно):"},
    "skip": {"uz": "O‘tkazib yuborish", "ru": "Пропустить"},
    "thanks_end": {"uz": "Rahmat! Javoblaringiz saqlandi. ✅\n\nTestni qayta topshirish: /start",
                   "ru": "Спасибо! Ваши ответы сохранены. ✅\n\nПройти тест заново: /start"},
    "declined": {"uz": "Tushunarli! Testni qayta topshirish: /start\nNatijangiz haqida fikringiz bo‘lsa, shu yerga yozing.",
                 "ru": "Понятно! Пройти тест заново: /start\nЕсли есть мысли о результате — напишите сюда."},
    "receipt_ok": {"uz": "Chek qabul qilindi ✅ Hisobotingiz 24 soat ichida tayyor bo‘ladi.",
                   "ru": "Чек получен ✅ Отчёт будет готов в течение 24 часов."},
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
    steps = flow.build_steps(data.get("filter"))
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
    if row["finished_at"] is not None or row["pos"] != pos:
        await cb.answer(T["stale"][lang])
        return
    steps = flow.build_steps(data.get("filter"))
    new_pos, data, err = flow.apply(steps, pos, data, value)
    lang = data.get("lang", "uz")
    if err == "empty":
        await cb.answer(T["empty"][lang], show_alert=True)
        return
    if err == "max":
        await cb.answer(flow.max_msg(steps[pos], lang), show_alert=True)
        return
    if data.get("first_answer_at") is None and steps[pos].startswith("int"):
        data["first_answer_at"] = int(time.time())
    steps = flow.build_steps(data.get("filter"))
    db.save(sid, data=data, pos=new_pos)
    await cb.answer()
    if new_pos >= len(steps):
        await finish(cb, sid)
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
    meta["tipi"] = scoring.tipi_scores(data["tipi"])
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
    db.save(sid, paid_click=1, stage="dream")
    pay = T["pay_link"][lang].format(PAYMENT_URL) if PAYMENT_URL else T["pay_manual"][lang]
    await cb.message.answer(T["pay_info"][lang].format(pay=pay))
    await notify_admins(cb.bot, sid, "💰 Pullik hisobotni bosdi")
    await cb.message.answer(T["open_intro"][lang])
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
        await msg.answer(T["thanks_end"][lang])
        await notify_admins(bot, sid, "📝 To‘liq ma’lumot (hisobot tayyorlash uchun)")


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
             "paid_click", "receipt", "open_dream", "open_doubt"])
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
                    d.get("open_dream"), d.get("open_doubt")])
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
            f"Baho: {row['rating']} · Noto‘g‘ri: {', '.join(d.get('wrong', [])) or '—'}\n"
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
    db.save(last["id"], receipt=1)
    for aid in ADMIN_IDS:
        try:
            await message.bot.send_message(aid, f"🧾 Chek: sessiya #{last['id']}")
            await message.forward(aid)
        except Exception as e:
            logging.warning("forward failed: %s", e)
    await message.answer(T["receipt_ok"][lang_of(last)])


@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    last = db.latest(message.from_user.id)
    if last and last["stage"] in ("dream", "doubt"):
        await save_open(message, last["id"], message.text[:2000], message.bot)
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
