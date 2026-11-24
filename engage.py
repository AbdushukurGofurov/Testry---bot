"""Foydalanuvchini ushlab qolish: eslatmalar, reja bo'yicha so'rovlar, voronka (qayerda to'xtadi), ota-onaga ulashish.

Matnlar shu yerda, Telegram bilan ishlaydigan qism bot.py da.
"""
import hashlib
import os
import time

import flow

REMIND_DAYS = float(os.getenv("REMIND_DAYS", "3"))
FOLLOWUP_DAYS = [3, 7, 14]
LOCAL_UTC_OFFSET = 5          # Toshkent vaqti
SEND_HOURS = (9, 21)          # xabarlar faqat 09:00–21:00 oralig'ida yuboriladi

E = {
    # --- 3 kundan keyingi eslatmalar (qolgan joyiga qarab) ---
    "rem_start": {
        "uz": "Assalomu alaykum, {name}! 😊 Siz Testry testini boshlagan edingiz. Atigi 4 daqiqada qiziqishlaringizga "
              "mos yo‘nalishlarni bilib olishingiz mumkin. Davom ettiramizmi?",
        "ru": "Здравствуйте, {name}! 😊 Вы начали тест Testry. Всего за 4 минуты вы узнаете, какие направления "
              "подходят вашим интересам. Продолжим?"},
    "rem_free": {
        "uz": "Assalomu alaykum, {name}! 😊 Siz testning {done}-savoligacha yetib kelgan edingiz. Natijangizgacha "
              "bor-yo‘g‘i {left} ta savol qoldi, bu 2 daqiqa ham olmaydi. Javoblaringiz saqlangan, to‘xtagan joyingizdan davom etasiz.",
        "ru": "Здравствуйте, {name}! 😊 Вы дошли до {done}-го вопроса теста. До результата осталось всего {left} "
              "вопросов, это меньше 2 минут. Ваши ответы сохранены, продолжите с того же места."},
    "rem_offer": {
        "uz": "Assalomu alaykum, {name}! 😊 Natijangiz bo‘yicha sizning tipingiz: <b>{tip}</b>. To‘liq hisobotda sizga mos "
              "6 ta yo‘nalish, fanlaringiz tahlili, 2 haftalik sinov rejasi va ota-onangiz uchun alohida sahifa bor. "
              "Batafsil ko‘rib chiqasizmi?",
        "ru": "Здравствуйте, {name}! 😊 По результату ваш тип: <b>{tip}</b>. В полном отчёте 6 подходящих направлений, "
              "анализ ваших предметов, план проб на 2 недели и отдельная страница для родителей. Посмотрите подробнее?"},
    "rem_paid_q": {
        "uz": "Assalomu alaykum, {name}! 😊 To‘liq hisobotingiz uchun bor-yo‘g‘i {left} ta savol qoldi. "
              "Javoblaringiz saqlangan, to‘xtagan joyingizdan davom etasiz.",
        "ru": "Здравствуйте, {name}! 😊 Для полного отчёта осталось всего {left} вопросов. "
              "Ответы сохранены, продолжите с того же места."},
    "rem_open": {
        "uz": "Assalomu alaykum, {name}! 😊 To‘liq hisobotingizga oxirgi ochiq savollar qoldi. Ularni o‘tkazib yuborsangiz ham bo‘ladi.",
        "ru": "Здравствуйте, {name}! 😊 До полного отчёта остались последние открытые вопросы. Их можно и пропустить."},
    "rem_pay": {
        "uz": "Assalomu alaykum, {name}! 😊 Barcha savollarga javob berdingiz, hisobotingiz tayyorlanishga tayyor. "
              "To‘lov qilib, chek rasmini shu chatga yuborsangiz, hisobot darhol keladi.",
        "ru": "Здравствуйте, {name}! 😊 Вы ответили на все вопросы, отчёт готов к подготовке. "
              "Оплатите и отправьте фото чека в этот чат, и отчёт придёт сразу."},
    "btn_continue": {"uz": "▶️ Davom ettirish", "ru": "▶️ Продолжить"},
    "btn_offer": {"uz": "📘 To‘liq hisobot haqida", "ru": "📘 О полном отчёте"},
    "btn_pay": {"uz": "💳 To‘lov ma’lumotlari", "ru": "💳 Данные для оплаты"},
    "gone": {"uz": "Bu bosqich allaqachon yakunlangan 🙂 Yangi test: /start",
             "ru": "Этот этап уже завершён 🙂 Новый тест: /start"},

    # --- Hisobotdan keyingi so'rovlar (3, 7, 14-kun) ---
    "fu0": {"uz": "Assalomu alaykum, {name}! 😊 Hisobotingizni olganingizga 3 kun bo‘ldi. 2 haftalik sinov rejasini boshladingizmi?",
            "ru": "Здравствуйте, {name}! 😊 Прошло 3 дня с получения отчёта. Вы начали 2-недельный план проб?"},
    "fu1": {"uz": "Assalomu alaykum, {name}! 😊 Bir hafta o‘tdi. Tanlagan yo‘nalishingizdagi biror mutaxassis bilan suhbatlashishga ulgurdingizmi?",
            "ru": "Здравствуйте, {name}! 😊 Прошла неделя. Удалось ли поговорить со специалистом из выбранного направления?"},
    "fu2": {"uz": "Assalomu alaykum, {name}! 🎉 2 haftalik reja yakuniga yetdi. Qaysi yo‘nalish sizga ko‘proq yoqdi?",
            "ru": "Здравствуйте, {name}! 🎉 2-недельный план подошёл к концу. Какое направление понравилось больше?"},
    "fu_btn": {
        0: {"uz": [("✅ Ha, boshladim", "yes"), ("⏳ Hali boshlamadim", "notyet"), ("🤔 Qiyin bo‘lyapti", "hard")],
            "ru": [("✅ Да, начал(а)", "yes"), ("⏳ Ещё не начал(а)", "notyet"), ("🤔 Трудно", "hard")]},
        1: {"uz": [("✅ Ha, gaplashdim", "yes"), ("⏳ Hali yo‘q", "notyet"), ("🙋 Yordam kerak", "help")],
            "ru": [("✅ Да, поговорил(а)", "yes"), ("⏳ Ещё нет", "notyet"), ("🙋 Нужна помощь", "help")]},
        2: {"uz": [("🎯 Yo‘nalishimni tanladim", "chosen"), ("🔍 Hali izlanyapman", "searching"), ("🙋 Maslahat kerak", "help")],
            "ru": [("🎯 Выбрал(а) направление", "chosen"), ("🔍 Ещё ищу", "searching"), ("🙋 Нужен совет", "help")]},
    },
    "fu_reply": {
        "yes": {"uz": "Ajoyib! 👏 Siz to‘g‘ri yo‘ldasiz. Har bir sinovdan keyin “Vaqt qanday o‘tdi?” degan savolga javob yozib boring, "
                      "oxirida tanlash ancha oson bo‘ladi.",
                "ru": "Отлично! 👏 Вы на верном пути. После каждой пробы записывайте ответ на вопрос «Как прошло время?», "
                      "в конце выбирать будет намного легче."},
        "notyet": {"uz": "Hechqisi yo‘q 🙂 Eng kichik qadamdan boshlang: bugun shu yo‘nalish haqida bitta 10 daqiqalik video ko‘ring. "
                         "Rejangiz hisobotning 7-bo‘limida turibdi.",
                   "ru": "Ничего страшного 🙂 Начните с самого маленького шага: посмотрите сегодня одно 10-минутное видео об этом направлении. "
                         "План — в 7-м разделе отчёта."},
        "hard": {"uz": "Tushunamiz, bu tabiiy holat 🤝 Qaysi qadam qiyin bo‘layotganini shu yerga yozib qoldiring, jamoamiz sizga yordam beradi.",
                 "ru": "Понимаем, это естественно 🤝 Напишите сюда, какой шаг даётся тяжело, наша команда поможет."},
        "help": {"uz": "Albatta yordam beramiz 🤝 Savolingizni shu yerga yozib qoldiring, jamoamiz tez orada javob beradi.",
                 "ru": "Конечно, поможем 🤝 Напишите свой вопрос сюда, наша команда скоро ответит."},
        "chosen": {"uz": "Tabriklaymiz! 🎉 Bu katta qadam. Qaysi yo‘nalishni tanlaganingizni shu yerga yozib qoldirasizmi? "
                         "Bu bizga testni yanada aniqroq qilishga yordam beradi.",
                   "ru": "Поздравляем! 🎉 Это большой шаг. Напишите, пожалуйста, какое направление вы выбрали? "
                         "Это поможет нам сделать тест точнее."},
        "searching": {"uz": "Bu juda normal 🙂 Izlanish ham natija. Yana bir yo‘nalishni sinab ko‘ring yoki testni qayta topshirib, "
                            "qiziqishlaringiz o‘zgarganini tekshiring: /start",
                      "ru": "Это совершенно нормально 🙂 Поиск — тоже результат. Попробуйте ещё одно направление или пройдите тест заново, "
                            "чтобы проверить, изменились ли интересы: /start"},
    },
    "fu_text_thanks": {"uz": "Rahmat! 🙏 Yo‘lingizda omad tilaymiz. Savol tug‘ilsa, shu yerga yozing.",
                       "ru": "Спасибо! 🙏 Желаем удачи на вашем пути. Если появятся вопросы, пишите сюда."},

    # --- Ota-onaga ulashish ---
    "parent_offer": {
        "uz": "👨‍👩‍👧 <b>Hisobotni ota-onangiz bilan ulashing</b>\n\nOta-onangiz uchun alohida sahifa tayyorladik. "
              "Pastdagi tugmani bosib, ularning Telegram chatini tanlang: ular havolani ochganda sahifa botda ko‘rinadi.",
        "ru": "👨‍👩‍👧 <b>Поделитесь отчётом с родителями</b>\n\nМы подготовили отдельную страницу для родителей. "
              "Нажмите кнопку ниже и выберите их чат в Telegram: открыв ссылку, они увидят страницу в боте."},
    "parent_btn": {"uz": "📤 Ota-onamga yuborish", "ru": "📤 Отправить родителям"},
    "parent_share_text": {
        "uz": "Assalomu alaykum! Men Testry’da kasb tanlash testini topshirdim. Natijam va siz uchun tayyorlangan sahifani shu havolada ko‘ring:",
        "ru": "Здравствуйте! Я прошёл(ла) тест на выбор профессии в Testry. Мой результат и страница для вас — по ссылке:"},
    "parent_hello": {
        "uz": "Assalomu alaykum! 😊 Farzandingiz <b>{child}</b> Testry’da kasb tanlash testini topshirdi va natijasini siz bilan ulashdi.",
        "ru": "Здравствуйте! 😊 Ваш ребёнок <b>{child}</b> прошёл тест на выбор профессии в Testry и поделился результатом с вами."},
    "parent_try": {
        "uz": "Agar o‘zingiz ham qiziqishlaringizni bilmoqchi bo‘lsangiz, testni bepul topshirishingiz mumkin: /start",
        "ru": "Если хотите узнать и свои интересы, тест можно пройти бесплатно: /start"},
    "parent_bad": {"uz": "Havola eskirgan yoki noto‘g‘ri. Testni o‘zingiz topshirib ko‘rishingiz mumkin: /start",
                   "ru": "Ссылка устарела или неверна. Вы можете пройти тест сами: /start"},
    "child_parent_opened": {"uz": "👨‍👩‍👧 Ota-onangiz hisobot sahifasini ochdi.",
                            "ru": "👨‍👩‍👧 Ваши родители открыли страницу отчёта."},

    # --- Erkin yozilgan xabarlarga javob ---
    "ack": {"uz": "Xabaringiz uchun rahmat! 😊 Jamoamiz uni albatta o‘qiydi va kerak bo‘lsa shu yerda javob beradi.",
            "ru": "Спасибо за сообщение! 😊 Наша команда обязательно его прочитает и при необходимости ответит здесь."},
    "admin_reply": {"uz": "💬 <b>Testry jamoasidan javob:</b>\n\n{text}", "ru": "💬 <b>Ответ команды Testry:</b>\n\n{text}"},
}


def now() -> int:
    return int(time.time())


def local_hour() -> int:
    return (time.gmtime().tm_hour + LOCAL_UTC_OFFSET) % 24


def can_send_now() -> bool:
    return SEND_HOURS[0] <= local_hour() < SEND_HOURS[1]


def parent_sig(sid: int, secret: str) -> str:
    return hashlib.sha256(f"parent:{sid}:{secret}".encode()).hexdigest()[:10]


def parent_param(sid: int, secret: str) -> str:
    return f"par{sid}_{parent_sig(sid, secret)}"


def parse_parent_param(arg: str, secret: str) -> int | None:
    if not arg or not arg.startswith("par") or "_" not in arg:
        return None
    num, sig = arg[3:].split("_", 1)
    if not num.isdigit() or sig != parent_sig(int(num), secret):
        return None
    return int(num)


def last_active(row) -> int:
    return row["updated_at"] or row["finished_at"] or row["started_at"] or 0


# ---------- Qayerda to'xtadi ----------

FUNNEL_ORDER = (["lang", "age", "filter"] + [f"int{i}" for i in range(30)] + ["guess", "rating", "wrong", "offer",
                 "declined"] + [f"paid{i}" for i in range(14)] +
                ["open", "pay_none", "pay_pending", "pay_rejected", "report_rate", "report_fb", "closed"])

LABELS = {"lang": "Til tanlash", "age": "Yosh savoli", "filter": "Kimligi (filtr)", "guess": "O‘z taxmini savoli",
          "rating": "Natijaga baho bermadi", "wrong": "“Noto‘g‘ri qism” savoli", "offer": "Pullik taklif: qaror qilmadi",
          "declined": "Pullik taklifni rad etdi", "open": "Ochiq savollar (orzu/ikkilanish)",
          "pay_none": "Savollar tugadi, chek yubormadi", "pay_pending": "Chek yubordi, tasdiq kutilmoqda",
          "pay_rejected": "To‘lov rad etilgan", "report_rate": "Hisobot oldi, baho bermadi",
          "report_fb": "Hisobotga baho berdi, fikr yozmadi", "closed": "✅ To‘liq yakunladi"}


def step_key(row, data: dict) -> str:
    if row["finished_at"] is None:
        steps = flow.build_steps(data.get("filter"), "free")
        return steps[min(row["pos"] or 0, len(steps) - 1)]
    st = row["stage"]
    if st in ("rating", "wrong", "offer"):
        return st
    if st == "paid_q":
        return f"paid{min(row['pos'] or 0, 13)}"
    if st in ("dream", "doubt"):
        return "open"
    if st == "done":
        if data.get("phase") != "paid":
            return "declined"
        pay = data.get("pay")
        return {"pending": "pay_pending", "rejected": "pay_rejected"}.get(pay, "pay_none")
    if st in ("report_rate", "report_fb"):
        return st
    return "closed"


def step_label(key: str) -> str:
    if key.startswith("int"):
        return f"{int(key[3:]) + 1}-savol (bepul test)"
    if key.startswith("paid"):
        return f"{int(key[4:]) + 1}-qo‘shimcha savol"
    return LABELS.get(key, key)


def ago(ts: int) -> str:
    d = now() - (ts or 0)
    if d < 3600:
        return f"{d // 60} daq oldin"
    if d < 86400:
        return f"{d // 3600} soat oldin"
    return f"{d // 86400} kun oldin"
