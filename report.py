"""To'liq (pullik) hisobot generatori.

Hisobot ikki qismdan iborat:
1) Shablon qismlar: ballar, yo'nalishlar, fanlar, ish muhiti, maslahatlar, 2 haftalik reja, ota-onaga sahifa.
   Bular oldindan yozilgan matnlardan yig'iladi: har doim bir xil sifat, bepul va darhol.
2) AI-izoh (ixtiyoriy): GEMINI_API_KEY berilsa, o'quvchining o'z so'zlari (orzu, ikkilanish) va
   javoblari asosida shaxsiy izoh yoziladi. Kalit bo'lmasa yoki xato bo'lsa, shablon izoh ishlatiladi.
"""
import html
import json
import re
import logging
import os

import aiohttp

import scoring
from questions import DIFFICULTY, FORMAT, PAIRS, SUBJECTS, TYPE_LIKES, TYPE_NAMES, VALUES, pair_key

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

L = {"uz": 0, "ru": 1}

# Har bir tip uchun yo'nalishlar: (uz nomi, ru nomi, uz izoh, ru izoh)
DIRECTIONS = {
    "R": [
        ("Mashinasozlik va mexanika", "Машиностроение и механика",
         "mexanizm qanday ishlashini tushunib, uni o‘z qo‘li bilan yig‘ish va tuzatish",
         "понимать, как работает механизм, и собирать или чинить его своими руками"),
        ("Elektr energetikasi va elektronika", "Электроэнергетика и электроника",
         "aniq natija beradigan texnik ish, asbob-uskuna bilan ishlash",
         "техническая работа с конкретным результатом, работа с оборудованием"),
        ("Qurilish muhandisligi", "Строительная инженерия",
         "ko‘z oldida o‘sib boradigan real obyektlar yaratish",
         "создание реальных объектов, которые растут на глазах"),
        ("Transport va logistika texnikasi", "Транспорт и логистическая техника",
         "harakat, texnika va amaliy masalalar",
         "движение, техника и практические задачи"),
        ("Agronomiya va agrotexnologiyalar", "Агрономия и агротехнологии",
         "tabiat bilan, ochiq havoda, qo‘l mehnati va texnologiya uyg‘unligida ishlash",
         "работа с природой, на открытом воздухе, сочетание ручного труда и технологий"),
    ],
    "I": [
        ("Dasturiy injiniring va kompyuter fanlari", "Программная инженерия и компьютерные науки",
         "murakkab masalani bo‘laklarga ajratib, mantiq bilan yechish",
         "разбивать сложную задачу на части и решать её логикой"),
        ("Data science va sun’iy intellekt", "Data science и искусственный интеллект",
         "ma’lumotlar ichidan qonuniyat topish va “nega?” savoliga javob izlash",
         "находить закономерности в данных и искать ответ на вопрос «почему?»"),
        ("Tibbiyot (davolash ishi)", "Медицина (лечебное дело)",
         "inson organizmini chuqur o‘rganish va tashxis qo‘yish mantig‘i",
         "глубокое изучение организма и логика постановки диагноза"),
        ("Biotexnologiya va kimyo", "Биотехнологии и химия",
         "tajriba, laboratoriya va kashfiyot",
         "эксперименты, лаборатория и открытия"),
        ("Fizika va matematika (ilmiy yo‘l)", "Физика и математика (научный путь)",
         "fundamental savollar va aniq isbot",
         "фундаментальные вопросы и строгие доказательства"),
    ],
    "A": [
        ("Grafik va UI/UX dizayn", "Графический и UI/UX-дизайн",
         "g‘oyani ko‘rinadigan va qulay shaklga keltirish",
         "превращать идею в наглядную и удобную форму"),
        ("Jurnalistika va kontent yaratish", "Журналистика и создание контента",
         "so‘z, video va hikoya orqali o‘zini ifodalash",
         "самовыражение через слово, видео и историю"),
        ("Arxitektura va interyer dizayni", "Архитектура и дизайн интерьера",
         "ijod va makonni birlashtirish",
         "соединение творчества и пространства"),
        ("Kino, video va animatsiya", "Кино, видео и анимация",
         "tasvir va harakat orqali hikoya qilish",
         "рассказывать истории через изображение и движение"),
        ("San’at, musiqa va madaniyat sohasi", "Искусство, музыка и сфера культуры",
         "erkin ijod va estetika",
         "свободное творчество и эстетика"),
    ],
    "S": [
        ("Pedagogika (fan o‘qituvchisi)", "Педагогика (учитель предмета)",
         "bilimni boshqalarga tushuntirish va ularning o‘sishini ko‘rish",
         "объяснять знания другим и видеть их рост"),
        ("Psixologiya", "Психология",
         "odamlarni tushunish va ularga qiyin paytda yordam berish",
         "понимать людей и помогать им в трудный момент"),
        ("Hamshiralik ishi va reabilitatsiya", "Сестринское дело и реабилитация",
         "odamlar sog‘lig‘iga bevosita g‘amxo‘rlik qilish",
         "непосредственная забота о здоровье людей"),
        ("Ijtimoiy ish", "Социальная работа",
         "jamiyatdagi muammolarni hal qilishda odamlarga yelkadosh bo‘lish",
         "поддерживать людей в решении социальных проблем"),
        ("Sport murabbiyligi", "Спортивная тренерская работа",
         "harakat va odamlarni rivojlantirishni birlashtirish",
         "сочетание движения и развития людей"),
    ],
    "E": [
        ("Menejment va tadbirkorlik", "Менеджмент и предпринимательство",
         "g‘oyani loyihaga, loyihani natijaga aylantirish",
         "превращать идею в проект, а проект — в результат"),
        ("Marketing va sotuv", "Маркетинг и продажи",
         "odamlarni ishontirish va bozorni tushunish",
         "убеждать людей и понимать рынок"),
        ("Huquqshunoslik", "Юриспруденция",
         "dalil bilan himoya qilish va muzokara olib borish",
         "защищать с помощью аргументов и вести переговоры"),
        ("Xalqaro munosabatlar", "Международные отношения",
         "muzokara, diplomatiya va katta miqyosdagi qarorlar",
         "переговоры, дипломатия и решения большого масштаба"),
        ("Turizm va mehmonxona biznesi", "Туризм и гостиничный бизнес",
         "odamlar bilan faol muloqot va xizmatni boshqarish",
         "активное общение с людьми и управление сервисом"),
    ],
    "C": [
        ("Buxgalteriya va audit", "Бухгалтерия и аудит",
         "raqamlar, aniqlik va qoidaga asoslangan ish",
         "цифры, точность и работа по правилам"),
        ("Bank ishi va moliya", "Банковское дело и финансы",
         "tartibli tizimda pul va hisob-kitob bilan ishlash",
         "работа с деньгами и расчётами в упорядоченной системе"),
        ("Logistika va ta’minot zanjiri", "Логистика и цепи поставок",
         "jarayonlarni rejalashtirish va nazorat qilish",
         "планирование и контроль процессов"),
        ("Davlat boshqaruvi va hujjatchilik", "Госуправление и документооборот",
         "aniq tartib va barqaror tizim ichida ishlash",
         "работа в чёткой и стабильной системе"),
        ("Statistika va ma’lumotlar bazasi", "Статистика и базы данных",
         "katta hajmdagi ma’lumotni tartibga solish",
         "упорядочивание больших объёмов данных"),
    ],
}

# Fan -> u ko'proq bog'liq bo'lgan qiziqish turlari
SUBJECT_TYPES = {
    "math": "ICR", "phys": "RI", "chem": "IR", "bio": "IS", "hist": "SE", "lit": "AS",
    "eng": "ESA", "rus": "SE", "it": "ICR", "law": "ESC", "art": "AR",
}

DIFF_ADVICE = {
    "not_ready": ("Hozir qaror qilishga tayyor emasligingiz normal holat. Yakuniy tanlov o‘rniga bitta "
                  "kichik qadam qo‘ying: shu hisobotdagi 2 ta yo‘nalishni 2 hafta sinab ko‘ring. Qaror tajribadan keyin osonlashadi.",
                  "Не быть готовым(ой) к решению сейчас — нормально. Вместо окончательного выбора сделайте маленький шаг: "
                  "2 недели попробуйте 2 направления из этого отчёта. После опыта решать легче."),
    "self": ("“Nimani xohlashimni bilmayman” degani hali yetarli tajriba bo‘lmagani. Xohish tajribadan keyin paydo bo‘ladi. "
             "Har bir sinovdan keyin o‘zingizga savol bering: “Vaqt qanday o‘tdi? Yana qilgim keladimi?”",
             "«Не знаю, чего хочу» обычно значит, что ещё мало опыта. Желание появляется после пробы. "
             "После каждой пробы спросите себя: «Как прошло время? Хочу ли я ещё?»"),
    "jobs": ("Kasblar haqida ma’lumot yetishmasa, eng tez yo‘l — shu sohada ishlaydigan odam bilan 15 daqiqa gaplashish. "
             "Undan so‘rang: oddiy ish kuni qanday o‘tadi, nimasi yoqadi, nimasi qiyin?",
             "Если мало знаете о профессиях, самый быстрый путь — 15 минут поговорить с человеком из этой сферы. "
             "Спросите: как проходит обычный рабочий день, что нравится, что трудно?"),
    "many": ("Ko‘p narsaga qiziqish — kuchli tomon. Tanlashni osonlashtirish uchun yo‘nalishlarni 3 mezon bo‘yicha "
             "1–5 ball bilan baholang: qiziqish, qobiliyat, daromad. Eng yuqori yig‘indili 2 tasini sinab ko‘ring.",
             "Широкие интересы — это сила. Чтобы выбрать, оцените направления по 3 критериям от 1 до 5: интерес, "
             "способности, доход. Попробуйте 2 направления с самой высокой суммой."),
    "parents": ("Ota-onangiz bilan bahslashish o‘rniga ularga shu hisobotning “Ota-onalar uchun” qismini ko‘rsating. "
                "Ularning tashvishi odatda kelajakdagi barqarorlik haqida: tanlagan yo‘nalishingizning daromad va ish o‘rni tomonini birga o‘rganing.",
                "Вместо спора покажите родителям раздел «Для родителей» этого отчёта. Обычно их тревожит стабильность: "
                "вместе изучите, сколько зарабатывают и где работают в выбранном направлении."),
    "money": ("Daromad sohaga emas, ko‘proq mahoratga bog‘liq: har qanday sohada kuchli mutaxassis yaxshi topadi. "
              "Tanlagan yo‘nalishingizda tajribali mutaxassislar qancha ishlashini 2–3 ta vakansiyadan tekshirib ko‘ring.",
              "Доход зависит больше от мастерства, чем от сферы: сильный специалист хорошо зарабатывает почти везде. "
              "Проверьте по 2–3 вакансиям, сколько получают опытные специалисты в выбранном направлении."),
    "score": ("Ball qo‘rquvi bo‘lsa, maqsadni bo‘laklarga ajrating: kerakli fanlar bo‘yicha hozirgi darajangizni "
              "sinov testi bilan aniqlang va haftalik reja tuzing. Bir nechta OTM va o‘qish shaklini (kunduzgi, sirtqi, xorijiy) zaxira sifatida ko‘rib chiqing.",
              "Если боитесь не набрать баллы, разбейте цель на шаги: определите текущий уровень по нужным предметам "
              "пробным тестом и составьте недельный план. Держите запасные варианты: несколько вузов и форм обучения."),
}

VALUE_NOTE = {
    "stable": ("Siz uchun barqarorlik muhim: davlat sektori, yirik kompaniyalar va bank kabi tizimli joylarga e’tibor bering.",
               "Для вас важна стабильность: обратите внимание на госсектор, крупные компании и банки."),
    "growth": ("Siz uchun o‘sish muhim: tez rivojlanayotgan sohalar va kuchli jamoalar sizga mos.",
               "Для вас важен рост: вам подходят быстро развивающиеся сферы и сильные команды."),
    "income": ("Siz uchun daromad va erkinlik muhim: frilans, o‘z biznesi yoki natijaga qarab haq to‘lanadigan ishlarga qarang.",
               "Для вас важны доход и свобода: смотрите на фриланс, свой бизнес или работу с оплатой за результат."),
    "meaning": ("Siz uchun foyda keltirish muhim: ta’lim, tibbiyot, ijtimoiy loyihalar yoki jamiyatga ta’sir qiladigan ishlar sizni ilhomlantiradi.",
                "Для вас важно приносить пользу: вас вдохновят образование, медицина, социальные проекты."),
}

FORMAT_NOTE = {
    "remote": ("Masofaviy ishlash istagingiz bor: IT, dizayn, kontent va tahlil kabi yo‘nalishlarda bu imkoniyat ko‘proq.",
               "Вы хотите работать удалённо: такая возможность чаще есть в IT, дизайне, контенте и аналитике."),
    "office": ("Ofis va kuchli jamoa sizga yoqadi: yirik kompaniyalardagi jamoaviy rollarga e’tibor bering.",
               "Вам нравятся офис и сильная команда: присмотритесь к командным ролям в крупных компаниях."),
    "field": ("Siz harakatda ishlashni xohlaysiz: uchrashuvlar, safarlar va joyida ishlash ko‘p bo‘ladigan kasblar mos.",
              "Вы хотите работать в движении: подходят профессии со встречами, поездками и работой на местах."),
    "unknown": ("Ish formatini hali bilmasligingiz normal: 2 haftalik sinov paytida qaysi muhit yoqqanini kuzating.",
                "Нормально пока не знать формат: во время 2-недельной пробы понаблюдайте, какая среда вам нравится."),
}

MINI_TASK = {
    "R": ("uyda biror narsani yig‘ing yoki tuzating, yoki ustaxona/garajda bir kun yordam bering",
          "соберите или почините что-нибудь дома, или помогите день в мастерской"),
    "I": ("shu sohadagi bepul onlayn kursning birinchi modulini o‘ting va bitta masala yeching",
          "пройдите первый модуль бесплатного онлайн-курса и решите одну задачу"),
    "A": ("kichik ijodiy ish yarating (dizayn, matn, video) va 2–3 kishiga ko‘rsatib fikr so‘rang",
          "создайте небольшую творческую работу (дизайн, текст, видео) и покажите 2–3 людям"),
    "S": ("kimgadir bir mavzuni o‘rgating yoki bir kun ko‘ngilli bo‘lib yordam bering",
          "объясните кому-то тему или помогите один день волонтёром"),
    "E": ("kichik tadbir uyushtiring yoki biror narsani sotib ko‘ring",
          "организуйте небольшое мероприятие или попробуйте что-нибудь продать"),
    "C": ("oilaviy byudjet yoki biror ro‘yxatni jadvalga solib, tartibga keltiring",
          "сведите семейный бюджет или какой-нибудь список в таблицу и упорядочьте"),
}

H = {
    "title": ("📘 <b>Testry · To‘liq hisobot</b>", "📘 <b>Testry · Полный отчёт</b>"),
    "for": ("{name} uchun", "для {name}"),
    "s1": ("<b>Qiziqishlar profilingiz</b>", "<b>Ваш профиль интересов</b>"),
    "s2": ("<b>Sizga mos yo‘nalishlar</b>", "<b>Подходящие направления</b>"),
    "s3": ("<b>Fanlaringiz va yo‘nalishlar</b>", "<b>Ваши предметы и направления</b>"),
    "s4": ("<b>Siz uchun qulay ish muhiti</b>", "<b>Комфортная для вас рабочая среда</b>"),
    "s5": ("<b>Ikkilanishingiz bo‘yicha maslahat</b>", "<b>Совет по вашим сомнениям</b>"),
    "s6": ("<b>Shaxsiy izoh</b>", "<b>Персональный комментарий</b>"),
    "s7": ("<b>2 haftalik sinov rejasi</b>", "<b>План проб на 2 недели</b>"),
    "s8": ("<b>Ota-onalar uchun</b>", "<b>Для родителей</b>"),
    "disclaimer": ("<i>Hisobot tavsiya xarakterida. Yakuniy qaror sizniki.</i>",
                   "<i>Отчёт носит рекомендательный характер. Окончательное решение за вами.</i>"),
}


def _t(pair, lang):
    return pair[L[lang]]


def _typename(t, lang):
    return TYPE_NAMES[t][lang]


def pick_directions(top: list[str], n: int = 6) -> list[tuple]:
    a, b = top[0], top[1]
    out = DIRECTIONS[a][:3] + DIRECTIONS[b][:2] + [DIRECTIONS[a][3]]
    return out[:n]


def subject_check(subjects: list[str], top: list[str], lang: str) -> str:
    opts = {o[0]: o for o in SUBJECTS["options"]}
    if not subjects:
        return ("Fanlar tanlanmagan." if lang == "uz" else "Предметы не выбраны.")
    lines = []
    hits = 0
    for s in subjects:
        name = opts[s][1 if lang == "uz" else 2] if s in opts else s
        common = [t for t in SUBJECT_TYPES.get(s, "") if t in top]
        if common:
            hits += 1
            tn = ", ".join(_typename(t, lang) for t in common)
            lines.append(f"✅ {name} — " + (f"{tn} yo‘nalishlarini qo‘llab-quvvatlaydi" if lang == "uz"
                                             else f"поддерживает направления типа «{tn}»"))
        else:
            lines.append(f"➖ {name} — " + ("asosiy qiziqishlaringiz bilan to‘g‘ridan-to‘g‘ri bog‘liq emas" if lang == "uz"
                                             else "напрямую не связан с главными интересами"))
    if hits == len(subjects):
        tail = ("Fanlaringiz qiziqishlaringizga mos keladi: bu yaxshi asos." if lang == "uz"
                else "Ваши предметы совпадают с интересами — это хорошая основа.")
    elif hits == 0:
        tail = ("Osonroq fanlaringiz va qiziqishlaringiz turli tomonga qaragan. Bu xato emas: ikkalasini birlashtiradigan "
                "yo‘nalishlarni qidiring yoki 2 haftalik sinovda ikkala tomonni ham tekshirib ko‘ring."
                if lang == "uz" else
                "Лёгкие для вас предметы и интересы смотрят в разные стороны. Это не ошибка: ищите направления на стыке "
                "или проверьте обе стороны во время 2-недельной пробы.")
    else:
        tail = ("Fanlaringizning bir qismi qiziqishlaringizga mos: mos fanni chuqurlashtirish foydali bo‘ladi."
                if lang == "uz" else
                "Часть предметов совпадает с интересами: углубите именно совпадающий предмет.")
    return "\n".join(lines) + "\n\n" + tail


def section_profile(res: dict, data: dict, lang: str) -> str:
    sc = res["scores"]
    top = res["top"]
    ranked = sorted(sc, key=lambda t: -sc[t])
    width = max(len(_typename(t, lang)) for t in "RIASEC")
    chart = "\n".join(f"{_typename(t, lang).ljust(width)} {scoring.bar(sc[t])} {sc[t]:>2}" for t in ranked)
    lines = [H["s1"][L[lang]], f"<pre>{html.escape(chart)}</pre>"]
    if res.get("kind") == "normal":
        p = PAIRS[pair_key(*top)]
        lines.append(("Sizning tipingiz: <b>{}</b>" if lang == "uz" else "Ваш тип: <b>{}</b>").format(p[0 if lang == "uz" else 1]))
    elif res.get("kind") == "flat":
        lines.append("Qiziqishlaringiz bir nechta sohaga deyarli teng taqsimlangan: bu keng imkoniyat degani."
                     if lang == "uz" else "Ваши интересы почти поровну распределены между несколькими сферами — это широкие возможности.")
    else:
        lines.append("Ballaringiz umuman pastroq: qiziqishlaringiz hali shakllanmoqda. Quyidagi yo‘nalishlar eng kuchli tomoningizga asoslangan."
                     if lang == "uz" else "Баллы в целом невысокие: интересы ещё формируются. Направления ниже основаны на самых сильных сторонах.")
    for t in top:
        lines.append(f"• <b>{_typename(t, lang)}</b>: {TYPE_LIKES[t][lang]}")
    g = res.get("guess_match")
    guess = data.get("guess", [])
    if guess and g is not None:
        gn = ", ".join(_typename(x, lang) for x in guess)
        if g == 2:
            msg = (f"Siz o‘zingizni “{gn}” deb taxmin qilgansiz va natija buni to‘liq tasdiqladi."
                   if lang == "uz" else f"Вы предполагали «{gn}», и результат это полностью подтвердил.")
        elif g == 1:
            msg = (f"Siz o‘zingizni “{gn}” deb taxmin qilgansiz: natija qisman mos keldi."
                   if lang == "uz" else f"Вы предполагали «{gn}»: результат совпал частично.")
        else:
            msg = (f"Siz o‘zingizni “{gn}” deb taxmin qilgansiz, test esa boshqa natija berdi. Bu ko‘p uchraydi: "
                   "odam ko‘pincha o‘zini osonroq fanlariga yoki atrofdagilar fikriga qarab baholaydi."
                   if lang == "uz" else
                   f"Вы предполагали «{gn}», а тест показал другое. Это частое явление: люди часто оценивают себя "
                   "по лёгким предметам или по мнению окружающих.")
        lines.append("\n" + msg)
    return "\n".join(lines)


def section_directions(res: dict, lang: str) -> str:
    top = res["top"]
    lines = [H["s2"][L[lang]]]
    if res.get("kind") == "normal":
        p = PAIRS[pair_key(*top)]
        lines.append(("⭐ Eng kuchli moslik: <b>{}</b> ({} + {})" if lang == "uz" else "⭐ Наибольшее совпадение: <b>{}</b> ({} + {})")
                     .format(p[2 if lang == "uz" else 3], _typename(top[0], lang), _typename(top[1], lang)))
    for i, d in enumerate(pick_directions(top), 1):
        name, why = (d[0], d[2]) if lang == "uz" else (d[1], d[3])
        lines.append(f"{i}. <b>{name}</b>: {why}")
    return "\n\n".join([lines[0], "\n".join(lines[1:])])


def section_subjects(data: dict, res: dict, lang: str) -> str:
    if data.get("field"):
        return ""
    return H["s3"][L[lang]] + "\n\n" + subject_check(data.get("subjects", []), res["top"], lang)


def section_env(data: dict, res: dict, lang: str) -> str:
    lines = [H["s4"][L[lang]]]
    env = scoring.env_lines(res.get("tipi", {}), lang) if res.get("tipi") else []
    lines += [f"• {e}" for e in env]
    if data.get("values") in VALUE_NOTE:
        lines.append("\n💡 " + _t(VALUE_NOTE[data["values"]], lang))
    if data.get("format") in FORMAT_NOTE:
        lines.append("🏢 " + _t(FORMAT_NOTE[data["format"]], lang))
    return "\n".join(lines)


def section_difficulty(data: dict, lang: str) -> str:
    diffs = [d for d in data.get("difficulty", []) if d in DIFF_ADVICE]
    if not diffs:
        return ""
    opts = {o[0]: o for o in DIFFICULTY["options"]}
    lines = [H["s5"][L[lang]]]
    for d in diffs:
        lines.append(f"\n<b>“{opts[d][1 if lang == 'uz' else 2]}”</b>\n{_t(DIFF_ADVICE[d], lang)}")
    return "\n".join(lines)


def section_plan(res: dict, lang: str) -> str:
    top = res["top"]
    dirs = pick_directions(top)
    d1 = dirs[0][0] if lang == "uz" else dirs[0][1]
    d2 = dirs[3][0] if lang == "uz" else dirs[3][1]
    if lang == "uz":
        steps = [
            f"<b>1–3-kun.</b> “{d1}” va “{d2}” haqida o‘qing, “bir kunim” uslubidagi 2–3 ta video ko‘ring.",
            "<b>4–7-kun.</b> Har bir yo‘nalishdan bitta mutaxassis toping (tanishlar, Telegram, LinkedIn) va 15 daqiqa savol bering.",
            f"<b>8–12-kun.</b> Amaliy sinov: {MINI_TASK[top[0]][0]}. Keyin: {MINI_TASK[top[1]][0]}.",
            "<b>13–14-kun.</b> Har bir sinovni 1–5 ball bilan baholang: qiziq bo‘ldimi, vaqt qanday o‘tdi, yana qilgim keladimi? "
            "Eng yuqori ball olgan yo‘nalish bilan davom eting.",
        ]
    else:
        steps = [
            f"<b>Дни 1–3.</b> Почитайте о направлениях «{d1}» и «{d2}», посмотрите 2–3 видео в стиле «один мой день».",
            "<b>Дни 4–7.</b> Найдите по одному специалисту из каждого направления (знакомые, Telegram, LinkedIn) и задайте вопросы 15 минут.",
            f"<b>Дни 8–12.</b> Практическая проба: {MINI_TASK[top[0]][1]}. Затем: {MINI_TASK[top[1]][1]}.",
            "<b>Дни 13–14.</b> Оцените каждую пробу от 1 до 5: было ли интересно, как шло время, хочется ли ещё? "
            "Продолжайте с направлением, набравшим больше всего баллов.",
        ]
    return H["s7"][L[lang]] + "\n\n" + "\n".join(steps)


def section_parents(res: dict, data: dict, lang: str) -> str:
    top = res["top"]
    t1, t2 = _typename(top[0], lang), _typename(top[1], lang)
    all_dirs = pick_directions(top)
    dirs = [all_dirs[0], all_dirs[3], all_dirs[1]]
    names = ", ".join(d[0] if lang == "uz" else d[1] for d in dirs)
    if lang == "uz":
        text = (f"Farzandingizning eng kuchli qiziqishlari: <b>{t1}</b> va <b>{t2}</b>. "
                f"Ular {TYPE_LIKES[top[0]]['uz']} bilan bog‘liq ishlarda eng ko‘p ilhomlanadi.\n\n"
                f"Mos yo‘nalishlardan: {names}.\n\n"
                "Qanday yordam berish mumkin:\n"
                "• Tanlovni majburlamang, birga o‘rganing: 2 haftalik sinov rejasida hamroh bo‘ling.\n"
                "• Tanishlaringiz orasida shu sohada ishlaydiganlar bilan uchrashuv tashkil qiling.\n"
                "• Tashvishingiz daromad yoki barqarorlik bo‘lsa, shu yo‘nalishdagi real vakansiyalarni birga ko‘ring.\n"
                "• Qiziqish bilan ishlagan odam odatda uzoqroq va natijaliroq ishlaydi.")
    else:
        text = (f"Самые сильные интересы вашего ребёнка: <b>{t1}</b> и <b>{t2}</b>. "
                f"Больше всего его вдохновляет: {TYPE_LIKES[top[0]]['ru']}.\n\n"
                f"Подходящие направления: {names}.\n\n"
                "Как можно помочь:\n"
                "• Не навязывайте выбор, изучайте вместе: будьте рядом в 2-недельном плане проб.\n"
                "• Организуйте встречу со знакомыми, которые работают в этой сфере.\n"
                "• Если вас волнуют доход или стабильность, вместе посмотрите реальные вакансии.\n"
                "• Человек, работающий с интересом, обычно работает дольше и результативнее.")
    return H["s8"][L[lang]] + "\n\n" + text


def fallback_comment(data: dict, res: dict, lang: str) -> str:
    dream = (data.get("open_dream") or "").strip()
    doubt = (data.get("open_doubt") or "").strip()
    top = res["top"]
    parts = []
    if dream:
        parts.append((f"Siz orzuingizni shunday yozdingiz: “{html.escape(dream[:300], quote=False)}”. Bu javobni yuqoridagi "
                      f"yo‘nalishlar bilan solishtiring: qaysi biri orzuingizga eng yaqin bo‘lsa, sinovni o‘shandan boshlang.")
                     if lang == "uz" else
                     (f"О своей мечте вы написали: «{html.escape(dream[:300], quote=False)}». Сравните это с направлениями выше: "
                      f"начните пробу с того, что ближе всего к мечте."))
    if doubt:
        parts.append((f"Ikkilanishingiz: “{html.escape(doubt[:300], quote=False)}”. Bunday ikkilanish ko‘pchilikda bo‘ladi; uni fikrlash bilan emas, "
                      "kichik amaliy sinovlar bilan yechish osonroq.")
                     if lang == "uz" else
                     (f"Ваше сомнение: «{html.escape(doubt[:300], quote=False)}». Такие сомнения бывают у многих; их легче решить "
                      "не размышлениями, а маленькими практическими пробами."))
    if not parts:
        parts.append((f"Profilingizda {_typename(top[0], lang)} va {_typename(top[1], lang)} tomonlari yetakchi. "
                      "Shu ikkalasini birlashtiradigan ish sizga eng ko‘p zavq beradi.")
                     if lang == "uz" else
                     (f"В вашем профиле лидируют стороны «{_typename(top[0], lang)}» и «{_typename(top[1], lang)}». "
                      "Больше всего удовольствия принесёт работа, которая сочетает обе."))
    return "\n\n".join(parts)


def _ai_prompt(data: dict, res: dict, lang: str) -> str:
    sc = res["scores"]
    top = res["top"]
    subj = {o[0]: o[1] for o in SUBJECTS["options"]}
    diff = {o[0]: o[1] for o in DIFFICULTY["options"]}
    val = {o[0]: o[1] for o in VALUES["options"]}
    fmt = {o[0]: o[1] for o in FORMAT["options"]}
    dirs = [d[0] for d in pick_directions(top)]
    facts = {
        "yosh_guruhi": data.get("age"),
        "riasec_ballari_0_20": sc,
        "eng_kuchli_ikki_tip": [TYPE_NAMES[t]["uz"] for t in top],
        "profil_turi": res.get("kind"),
        "osonroq_fanlar": [subj.get(s, s) for s in data.get("subjects", [])],
        "ishdagi_qadriyat": val.get(data.get("values")),
        "ish_formati": fmt.get(data.get("format")),
        "qiyinchiliklar": [diff.get(d, d) for d in data.get("difficulty", [])],
        "tavsiya_etilgan_yonalishlar": dirs,
        "orzu_ochiq_javob": (data.get("open_dream") or "")[:600],
        "ikkilanish_ochiq_javob": (data.get("open_doubt") or "")[:600],
    }
    language = "o‘zbek tilida (lotin yozuvida)" if lang == "uz" else "на русском языке"
    return (
        "Sen kasb tanlashda yoshlarga yordam beradigan tajribali karyera maslahatchisisan. "
        "Quyida o‘quvchining test natijalari va o‘z so‘zlari bor (JSON). "
        f"Unga {language}, “siz” deb murojaat qilib, 120–180 so‘zli shaxsiy izoh yoz.\n\n"
        "Talablar:\n"
        "- O‘quvchining orzu va ikkilanish haqidagi o‘z so‘zlariga albatta to‘xtal (agar bo‘sh bo‘lmasa).\n"
        "- Ballar, fanlar va qadriyatlar o‘rtasidagi mos kelish yoki ziddiyatni ochiq ayt.\n"
        "- Tavsiya etilgan yo‘nalishlardan 1–2 tasini nomlab, nega mosligini tushuntir.\n"
        "- Bitta aniq keyingi qadam bilan yakunla.\n"
        "- Doim hurmat bilan, iliq va ijobiy ohangda yoz: tanqid qilma, ruhlantir.\n"
        "- Kafolat berma, OTM nomlari, ballar, maosh raqamlari va faktlarni to‘qima.\n"
        "- Faqat oddiy matn: markdown, sarlavha va ro‘yxat ishlatma.\n\n"
        + json.dumps(facts, ensure_ascii=False)
    )


async def ai_comment(data: dict, res: dict, lang: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": _ai_prompt(data, res, lang)}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
    }
    if "2.5" in GEMINI_MODEL:
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=body, headers={"x-goog-api-key": GEMINI_API_KEY},
                              timeout=aiohttp.ClientTimeout(total=40)) as r:
                js = await r.json(content_type=None)
                if r.status != 200:
                    logging.warning("AI izoh xatosi %s: %s", r.status, str(js)[:300])
                    return None
        text = "".join(p.get("text", "") for p in js["candidates"][0]["content"]["parts"]).strip()
        text = text.replace("**", "").replace("##", "").strip()
        return html.escape(text[:2500], quote=False) if text else None
    except Exception as e:
        logging.warning("AI izoh olinmadi: %s", e)
        return None


async def build(name: str, data: dict, res: dict, lang: str) -> list[str]:
    """Hisobotni Telegram xabarlari ro'yxati sifatida qaytaradi (har biri 4096 belgidan qisqa)."""
    head = H["title"][L[lang]] + "\n" + H["for"][L[lang]].format(name=html.escape(name or ""))
    comment = await ai_comment(data, res, lang) or fallback_comment(data, res, lang)
    parts = [
        head + "\n\n" + section_profile(res, data, lang),
        section_directions(res, lang),
        section_subjects(data, res, lang),
        section_env(data, res, lang),
        section_difficulty(data, lang),
        H["s6"][L[lang]] + "\n\n" + comment,
        section_plan(res, lang),
        section_parents(res, data, lang) + "\n\n" + H["disclaimer"][L[lang]],
    ]
    parts = [p for p in parts if p.strip()]
    # bo'limlarni ketma-ket raqamlash (bo'sh bo'limlar tushib qolsa ham raqamlar uzilmasin)
    out, n = [], 0
    for p in parts:
        def num(m):
            nonlocal n
            n += 1
            return f"{m.group(1)}{n}. "
        out.append(re.sub(r"(\n?<b>)(?=(?:Qiziqishlar|Sizga mos|Fanlaringiz|Siz uchun qulay|Ikkilanishingiz|Shaxsiy izoh|2 haftalik|Ota-onalar|Ваш профиль|Подходящие|Ваши предметы|Комфортная|Совет по|Персональный|План проб|Для родителей))", num, p, count=1))
    return out
