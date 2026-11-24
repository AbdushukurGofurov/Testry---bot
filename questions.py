"""Testry MVP: barcha savollar va matnlar (o'zbek va rus tillarida).

Savollarni o'zgartirish kerak bo'lsa, faqat shu faylni tahrirlang.
"""

# ---------------------------------------------------------------------------
# Javob shkalalari
# ---------------------------------------------------------------------------

SCALE5 = {
    "uz": ["Umuman yoqmaydi", "Yoqmaydi", "Bilmayman", "Yoqadi", "Juda yoqadi"],
    "ru": ["Совсем не нравится", "Не нравится", "Не уверен(а)", "Нравится", "Очень нравится"],
}

SCALE7 = {
    "uz": [
        "Mutlaqo qo‘shilmayman", "Qo‘shilmayman", "Biroz qo‘shilmayman", "Na u, na bu",
        "Biroz qo‘shilaman", "Qo‘shilaman", "To‘liq qo‘shilaman",
    ],
    "ru": [
        "Совершенно не согласен", "Не согласен", "Скорее не согласен", "Ни да, ни нет",
        "Скорее согласен", "Согласен", "Полностью согласен",
    ],
}

# ---------------------------------------------------------------------------
# 1-blok: Qiziqishlar (O*NET Mini-IP, 30 ta). Tartib asl testdagidek.
# (tip, o'zbekcha, ruscha)
# ---------------------------------------------------------------------------

INTEREST = [
    ("R", "Oshxona javonlarini yasash", "Делать кухонные шкафы"),
    ("I", "Yangi dori ishlab chiqish", "Разрабатывать новое лекарство"),
    ("A", "Kitob yoki pyesa yozish", "Писать книги или пьесы"),
    ("S", "Odamlarga shaxsiy yoki ruhiy muammolarida yordam berish", "Помогать людям с личными или эмоциональными проблемами"),
    ("E", "Katta kompaniyada bo‘limni boshqarish", "Руководить отделом в крупной компании"),
    ("C", "Katta tarmoqdagi kompyuterlarga dasturlar o‘rnatish", "Устанавливать программы на компьютеры в большой сети"),
    ("R", "Maishiy texnikani ta’mirlash", "Ремонтировать бытовую технику"),
    ("I", "Suv ifloslanishini kamaytirish yo‘llarini o‘rganish", "Изучать способы уменьшения загрязнения воды"),
    ("A", "Musiqa bastalash yoki aranjirovka qilish", "Сочинять или аранжировать музыку"),
    ("S", "Odamlarga kasb tanlashda maslahat berish", "Консультировать людей по выбору профессии"),
    ("E", "O‘z biznesingizni ochish", "Открыть собственный бизнес"),
    ("C", "Kalkulyatorda hisob-kitob qilish", "Работать на калькуляторе"),
    ("R", "Elektron qismlarni yig‘ish", "Собирать электронные детали"),
    ("I", "Kimyoviy tajribalar o‘tkazish", "Проводить химические опыты"),
    ("A", "Kinolar uchun maxsus effektlar yaratish", "Создавать спецэффекты для фильмов"),
    ("S", "Jarohat yoki kasallikdan keyin tiklanish mashg‘ulotlarini o‘tkazish", "Проводить реабилитационную терапию"),
    ("E", "Biznes shartnomalari bo‘yicha muzokara olib borish", "Вести переговоры по деловым контрактам"),
    ("C", "Yuk jo‘natish va qabul qilish hisobini yuritish", "Вести учёт отправки и получения грузов"),
    ("R", "Yuk mashinasida ofis va uylarga posilka yetkazish", "Водить грузовик, доставляя посылки в офисы и дома"),
    ("I", "Mikroskop yordamida qon namunalarini tekshirish", "Исследовать образцы крови под микроскопом"),
    ("A", "Spektakllar uchun dekoratsiya chizish", "Расписывать декорации для спектаклей"),
    ("S", "Notijorat tashkilotda ko‘ngilli bo‘lib ishlash", "Работать волонтёром в некоммерческой организации"),
    ("E", "Yangi kiyim kolleksiyasini bozorga olib chiqish va reklama qilish", "Продвигать новую линию одежды"),
    ("C", "Qo‘l skaneri bilan ombordagi tovarlarni ro‘yxatga olish", "Проводить инвентаризацию с помощью ручного терминала"),
    ("R", "Jo‘natishdan oldin detallar sifatini tekshirish", "Проверять качество деталей перед отправкой"),
    ("I", "Ob-havoni aniqroq bashorat qilish usulini ishlab chiqish", "Разрабатывать способ точнее прогнозировать погоду"),
    ("A", "Kino yoki teleko‘rsatuvlar uchun ssenariy yozish", "Писать сценарии для фильмов или телешоу"),
    ("S", "Yuqori sinflarda dars berish", "Преподавать в старших классах школы"),
    ("E", "Katta do‘konda tovar sotish", "Продавать товары в универмаге"),
    ("C", "Tashkilot pochtasini muhrlash, saralash va tarqatish", "Штамповать, сортировать и раздавать почту в организации"),
]

# ---------------------------------------------------------------------------
# 2-blok: Xarakter (TIPI, 10 ta). (xususiyat, teskarimi, o'zbekcha, ruscha)
# ---------------------------------------------------------------------------

TIPI = [
    ("ext", False, "kirishimli, g‘ayratli", "общительный, полный энтузиазма"),
    ("agr", True, "tanqidchi, bahslashishni yoqtiradigan", "критичный, склонный спорить"),
    ("con", False, "ishonchli, intizomli", "надёжный, дисциплинированный"),
    ("emo", True, "xavotirlanuvchan, tez xafa bo‘ladigan", "тревожный, легко расстраивающийся"),
    ("opn", False, "yangilikka ochiq, ko‘p qirrali", "открытый новому, многогранный"),
    ("ext", True, "kamgap, vazmin", "сдержанный, тихий"),
    ("agr", False, "hamdard, mehribon", "сочувствующий, тёплый"),
    ("con", True, "tartibsiz, e’tiborsiz", "неорганизованный, небрежный"),
    ("emo", False, "xotirjam, hissiy jihatdan barqaror", "спокойный, эмоционально устойчивый"),
    ("opn", True, "an’anaviy, ijodkorlikka moyil emas", "традиционный, нетворческий"),
]

TIPI_PREFIX = {"uz": "Men o‘zimni {} deb bilaman.", "ru": "Я считаю себя: {}."}

# ---------------------------------------------------------------------------
# Tanlov savollari. options: (kod, o'zbekcha, ruscha)
# ---------------------------------------------------------------------------

AGE = {
    "text": {"uz": "Yoshingiz nechada?", "ru": "Сколько вам лет?"},
    "options": [("13-15", "13–15", "13–15"), ("16-17", "16–17", "16–17"),
                ("18-22", "18–22", "18–22"), ("23+", "23+", "23+")],
}

FILTER = {
    "text": {"uz": "Hozir kimsiz?", "ru": "Кто вы сейчас?"},
    "options": [
        ("A", "8–9-sinf o‘quvchisi", "Ученик 8–9 класса"),
        ("B", "10–11-sinf, litsey yoki kollej o‘quvchisi", "Ученик 10–11 класса, лицея или колледжа"),
        ("C", "Abituriyent yoki talaba", "Абитуриент или студент"),
        ("D", "Ishlayman, kasbimni almashtirmoqchiman", "Работаю, хочу сменить профессию"),
    ],
}

# Boshidagi "kimsiz" savoli: foydalanuvchi o'zi yozadi (namunaga qarab)
WHO = {
    "text": {
        "uz": "Hozir kimsiz? O‘zingiz haqingizda bir gap bilan yozib yuboring 👇\n\n"
              "<i>Namuna:</i>\n"
              "• 9-sinf o‘quvchisiman, 45-maktab, Toshkent\n"
              "• 11-sinf, akademik litsey, tibbiyotga tayyorlanyapman\n"
              "• Abituriyentman, IT yo‘nalishiga topshirmoqchiman\n"
              "• TATU 2-kurs talabasiman\n"
              "• Buxgalterman, 5 yil ishlayman, kasbimni o‘zgartirmoqchiman",
        "ru": "Кто вы сейчас? Напишите о себе одним предложением 👇\n\n"
              "<i>Пример:</i>\n"
              "• Ученик 9 класса, школа №45, Ташкент\n"
              "• 11 класс, академический лицей, готовлюсь в медицину\n"
              "• Абитуриент, хочу поступать на IT\n"
              "• Студент 2 курса ТУИТ\n"
              "• Бухгалтер, работаю 5 лет, хочу сменить профессию",
    },
    "short": {"uz": "Iltimos, o‘zingiz haqingizda biroz batafsilroq yozing (namunadagidek) 🙂",
              "ru": "Пожалуйста, напишите о себе чуть подробнее (как в примере) 🙂"},
    "wait": {"uz": "Javobingizni shu chatga matn qilib yozing 👇", "ru": "Напишите ответ текстом в этот чат 👇"},
}

SUBJECTS = {
    "text": {"uz": "Qaysi fanlar sizga osonroq? (2 tagacha tanlang)",
             "ru": "Какие предметы даются вам легче? (выберите до двух)"},
    "max": 2,
    "options": [
        ("math", "Matematika", "Математика"),
        ("phys", "Fizika", "Физика"),
        ("chem", "Kimyo", "Химия"),
        ("bio", "Biologiya", "Биология"),
        ("hist", "Tarix", "История"),
        ("lit", "Ona tili va adabiyot", "Родной язык и литература"),
        ("eng", "Ingliz tili", "Английский язык"),
        ("rus", "Rus tili", "Русский язык"),
        ("it", "Informatika", "Информатика"),
        ("law", "Huquq yoki ijtimoiy fanlar", "Право или общественные науки"),
        ("art", "Chizmachilik, san’at yoki musiqa", "Черчение, искусство или музыка"),
    ],
}

FIELD = {
    "text": {"uz": "Hozir qaysi sohada ishlaysiz?", "ru": "В какой сфере вы сейчас работаете?"},
    "options": [
        ("it", "IT", "IT"),
        ("edu", "Ta’lim", "Образование"),
        ("med", "Tibbiyot", "Медицина"),
        ("trade", "Savdo va xizmat ko‘rsatish", "Торговля и услуги"),
        ("fin", "Moliya va buxgalteriya", "Финансы и бухгалтерия"),
        ("prod", "Ishlab chiqarish va qurilish", "Производство и строительство"),
        ("gov", "Davlat xizmati", "Госслужба"),
        ("media", "Media va ijod", "Медиа и творчество"),
        ("other", "Boshqa", "Другое"),
    ],
}

VALUES = {
    "text": {"uz": "Kelajakdagi ishingizda eng muhimi nima?", "ru": "Что для вас главное в будущей работе?"},
    "options": [
        ("stable", "Barqaror oylik va tinch muhit", "Стабильная зарплата и спокойная среда"),
        ("growth", "Karyera o‘sishi va yangi bilimlar", "Карьерный рост и новые знания"),
        ("income", "Katta daromad, erkin grafik, o‘z biznesim", "Высокий доход, свободный график, свой бизнес"),
        ("meaning", "Odamlarga va jamiyatga foyda keltirish", "Приносить пользу людям и обществу"),
    ],
}

FORMAT = {
    "text": {"uz": "Qanday formatda ishlashni xohlaysiz?", "ru": "В каком формате вы хотите работать?"},
    "options": [
        ("remote", "Uydan, masofaviy yoki frilans", "Из дома, удалённо или фриланс"),
        ("office", "Zamonaviy ofisda, kuchli jamoada", "В современном офисе, в сильной команде"),
        ("field", "Harakatda: uchrashuvlar, safarlar, dala ishlari", "В движении: встречи, поездки, работа на местах"),
        ("unknown", "Hali bilmayman", "Пока не знаю"),
    ],
}

DIFFICULTY = {
    "text": {"uz": "Kasb tanlashda sizni nima qiynayapti? (bir nechtasini tanlang)",
             "ru": "Что вам мешает выбрать профессию? (можно несколько)"},
    "max": 8,
    "options": [
        ("not_ready", "Hozir qaror qilishga tayyor emasman", "Пока не готов(а) принимать решение"),
        ("self", "Nimani xohlashimni bilmayman", "Не знаю, чего хочу"),
        ("jobs", "Kasblar haqida yetarli ma’lumotim yo‘q", "Мало знаю о профессиях"),
        ("many", "Ko‘p narsaga qiziqaman, tanlay olmayman", "Многое интересно, не могу выбрать"),
        ("parents", "Ota-onam yoki yaqinlarim boshqa sohani xohlaydi", "Родители или близкие хотят другое"),
        ("money", "Bu soha pul keltirishiga ishonchim yo‘q", "Не уверен(а), что это принесёт деньги"),
        ("score", "Ballim yoki bilimim yetmaydi deb qo‘rqaman", "Боюсь, что не хватит баллов или знаний"),
        ("none", "Hech narsa qiynamayapti", "Ничего не мешает"),
    ],
}

SELF_GUESS = {
    "text": {"uz": "Natijani ko‘rishdan oldin: o‘zingizni qaysi biriga yaqinroq deb bilasiz? (2 tagacha)",
             "ru": "Перед результатом: к чему вы себя относите? (до двух)"},
    "max": 2,
    "options": [
        ("R", "Qo‘l bilan ishlash, texnika, asboblar", "Работа руками, техника, инструменты"),
        ("I", "Ilm, tadqiqot, murakkab masalalar", "Наука, исследования, сложные задачи"),
        ("A", "Ijod: rasm, musiqa, matn, dizayn", "Творчество: рисунок, музыка, тексты, дизайн"),
        ("S", "Odamlarga yordam berish, o‘qitish", "Помощь людям, обучение"),
        ("E", "Boshqarish, sotish, biznes", "Управление, продажи, бизнес"),
        ("C", "Hujjat, raqam, tartib", "Документы, цифры, порядок"),
    ],
}

WRONG_PART = {
    "text": {"uz": "Qaysi qismi noto‘g‘ri tuyuldi? (bir nechtasini tanlang)",
             "ru": "Что показалось неверным? (можно несколько)"},
    "max": 5,
    "options": [
        ("type", "Tip nomi", "Название типа"),
        ("desc", "Tavsif", "Описание"),
        ("direction", "Tavsiya qilingan yo‘nalish", "Рекомендованное направление"),
        ("env", "Ish muhiti", "Рабочая среда"),
        ("all_ok", "Hammasi to‘g‘ri", "Всё верно"),
    ],
}

OPEN_DREAM = {"uz": "Pul va boshqalarning fikri muhim bo‘lmaganida, bir umr qanday ish qilardingiz?",
              "ru": "Если бы деньги и чужое мнение не имели значения, чем бы вы занимались всю жизнь?"}
OPEN_DOUBT = {"uz": "Kasb tanlashdagi qiyinchiligingiz haqida batafsilroq yozing.",
              "ru": "Расскажите подробнее о том, что мешает вам выбрать профессию."}

# ---------------------------------------------------------------------------
# Tiplar va juftliklar
# ---------------------------------------------------------------------------

TYPE_NAMES = {
    "R": {"uz": "Amaliy", "ru": "Практик"},
    "I": {"uz": "Tadqiqotchi", "ru": "Исследователь"},
    "A": {"uz": "Ijodkor", "ru": "Творец"},
    "S": {"uz": "Ijtimoiy", "ru": "Социальный"},
    "E": {"uz": "Tadbirkor", "ru": "Предприниматель"},
    "C": {"uz": "Tartibli", "ru": "Организатор"},
}

TYPE_LIKES = {
    "R": {"uz": "qo‘l, asbob va texnika bilan aniq natija beradigan ish",
          "ru": "работа руками, с инструментами и техникой, дающая конкретный результат"},
    "I": {"uz": "kuzatish, tahlil qilish va “nega?” degan savolga javob izlash",
          "ru": "наблюдать, анализировать и искать ответ на вопрос «почему?»"},
    "A": {"uz": "erkin ijod va o‘zini ifodalash", "ru": "свободное творчество и самовыражение"},
    "S": {"uz": "odamlarga yordam berish va ularni o‘rgatish", "ru": "помогать людям и обучать их"},
    "E": {"uz": "boshqarish, ishontirish va g‘oyani natijaga aylantirish",
          "ru": "управлять, убеждать и превращать идеи в результат"},
    "C": {"uz": "aniq qoida, raqam va tartib bilan ishlash", "ru": "работать с чёткими правилами, цифрами и порядком"},
}

# kalit: ikki harf alifbo tartibida (masalan "EI")
PAIRS = {
    "IR": ("Muhandis-Tadqiqotchi", "Инженер-исследователь", "Muhandislik va robototexnika", "Инженерия и робототехника"),
    "AR": ("Yaratuvchi-Usta", "Мастер-созидатель", "Arxitektura va sanoat dizayni", "Архитектура и промышленный дизайн"),
    "RS": ("Amaliy Yordamchi", "Практический помощник", "Sport murabbiyligi va reabilitatsiya", "Спортивный тренер и реабилитация"),
    "ER": ("Amaliy Tashkilotchi", "Практический организатор", "Qurilish va logistika menejmenti", "Управление строительством и логистикой"),
    "CR": ("Texnik-Tizimchi", "Техник-системщик", "IT-infratuzilma va tizim administratorligi", "IT-инфраструктура и системное администрирование"),
    "AI": ("Ixtirochi", "Изобретатель", "UI/UX dizayn va o‘yin yaratish", "UI/UX-дизайн и разработка игр"),
    "IS": ("Ilmiy Yordamchi", "Научный помощник", "Tibbiyot va psixologiya", "Медицина и психология"),
    "EI": ("Tahlilchi-Strateg", "Аналитик-стратег", "Biznes-tahlil va ma’lumotlar bilan ishlash", "Бизнес-анализ и работа с данными"),
    "CI": ("Ma’lumotlar ustasi", "Мастер данных", "Data-tahlil va moliyaviy tahlil", "Анализ данных и финансовый анализ"),
    "AS": ("Ijodkor-Murabbiy", "Творец-наставник", "Pedagogika va kontent yaratish", "Педагогика и создание контента"),
    "AE": ("Kreativ Lider", "Креативный лидер", "Marketing va brend boshqaruvi", "Маркетинг и управление брендом"),
    "AC": ("Aniqlikdagi Ijodkor", "Точный творец", "Grafik dizayn va muharrirlik", "Графический дизайн и редактура"),
    "ES": ("Ilhomlantiruvchi Lider", "Вдохновляющий лидер", "HR va sotuvni boshqarish", "HR и управление продажами"),
    "CS": ("G‘amxo‘r Tashkilotchi", "Заботливый организатор", "Tibbiy va ijtimoiy xizmatlar boshqaruvi", "Администрирование в медицине и соцсфере"),
    "CE": ("Boshqaruvchi-Menejer", "Управленец-менеджер", "Moliya va bank ishi", "Финансы и банковское дело"),
}


def pair_key(a: str, b: str) -> str:
    return "".join(sorted([a, b]))


# Litsenziya talab qilgan ogohlantirish (O*NET Tools Developer License)
LICENSE_NOTICE = (
    "This application includes information from the O*NET Career Exploration Tools by the "
    "U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the "
    "O*NET Tools Developer License. O*NET® is a trademark of USDOL/ETA. Testry has modified all or "
    "some of this information. USDOL/ETA has not approved, endorsed, or tested these modifications.\n\n"
    "Personality items: Ten Item Personality Inventory (TIPI), Gosling, Rentfrow & Swann (2003)."
)
