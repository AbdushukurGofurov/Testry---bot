"""Test oqimi: qaysi savol qachon chiqadi va javob qanday saqlanadi.

Bu fayl Telegram'ga bog'liq emas, shuning uchun uni alohida sinash mumkin.
"""
import html
from questions import (SCALE5, SCALE7, INTEREST, TIPI, TIPI_PREFIX, AGE, FILTER, SUBJECTS, FIELD,
                       VALUES, FORMAT, DIFFICULTY, SELF_GUESS)

TOTAL = 45  # filtr + 30 + 10 + 4

UI = {
    "next": {"uz": "Tayyor ➡️", "ru": "Готово ➡️"},
    "back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "q": {"uz": "Savol", "ru": "Вопрос"},
    "interest_head": {"uz": "Qiziqishlar", "ru": "Интересы"},
    "interest_ask": {"uz": "Bu ish sizga qanchalik yoqadi?", "ru": "Насколько вам нравится это занятие?"},
    "interest_hint": {
        "uz": "<i>O‘qish, tajriba yoki maosh haqida o‘ylamang — faqat shu ish sizga yoqadimi yoki yo‘qmi.</i>",
        "ru": "<i>Не думайте об обучении, опыте или зарплате — только о том, нравится ли вам это дело.</i>",
    },
    "tipi_head": {"uz": "Xarakter", "ru": "Характер"},
    "tipi_hint": {
        "uz": "<i>Juftlik sizni qanchalik to‘g‘ri tasvirlaydi? Bir so‘z ko‘proq mos kelsa ham, umumiy baholang.</i>",
        "ru": "<i>Насколько пара слов описывает вас? Оцените пару целиком.</i>",
    },
    "ctx_head": {"uz": "Siz haqingizda", "ru": "О вас"},
    "half": {"uz": "👏 Yarmidan o‘tdingiz!", "ru": "👏 Половина пройдена!"},
    "max": {"uz": "{} tagacha tanlash mumkin", "ru": "Можно выбрать до {}"},
}


def build_steps(filter_code: str | None) -> list[str]:
    steps = ["lang", "age", "filter"]
    steps += [f"int{i}" for i in range(30)]
    steps += [f"tipi{i}" for i in range(10)]
    steps += ["field" if filter_code == "D" else "subjects", "values", "format", "difficulty", "guess"]
    return steps


def numbered(step: str) -> int | None:
    """Foydalanuvchiga ko'rinadigan savol raqami (1..45)."""
    if step == "filter":
        return 1
    if step.startswith("int"):
        return 2 + int(step[3:])
    if step.startswith("tipi"):
        return 32 + int(step[4:])
    order = {"subjects": 42, "field": 42, "values": 43, "format": 44, "difficulty": 45}
    return order.get(step)


CHOICE = {"age": AGE, "filter": FILTER, "subjects": SUBJECTS, "field": FIELD, "values": VALUES,
          "format": FORMAT, "difficulty": DIFFICULTY, "guess": SELF_GUESS}
MULTI = {"subjects", "difficulty", "guess"}


def render(step: str, lang: str, data: dict) -> tuple[str, list[list[tuple[str, str]]]]:
    """Savol matni va tugmalar: [[(yozuv, qiymat), ...], ...]."""
    if step == "lang":
        return ("Tilni tanlang / Выберите язык", [[("🇺🇿 O‘zbekcha", "uz"), ("🇷🇺 Русский", "ru")]])

    n = numbered(step)
    head = f"<b>{UI['q'][lang]} {n}/{TOTAL}</b>" if n else ""
    back = [[(UI["back"][lang], "__back")]] if step not in ("lang",) else []

    if step.startswith("int"):
        i = int(step[3:])
        item = INTEREST[i][1 if lang == "uz" else 2]
        extra = ("\n" + UI["half"][lang]) if i == 15 else ""
        hint = ("\n\n" + UI["interest_hint"][lang]) if i == 0 else ""
        text = f"{head} · {UI['interest_head'][lang]}{extra}\n\n{UI['interest_ask'][lang]}\n\n<b>{html.escape(item)}</b>{hint}"
        rows = [[(lbl, str(v))] for v, lbl in enumerate(SCALE5[lang])]
        return text, rows + back

    if step.startswith("tipi"):
        i = int(step[4:])
        words = TIPI[i][2 if lang == "uz" else 3]
        stmt = TIPI_PREFIX[lang].format(f"<b>{html.escape(words)}</b>")
        hint = ("\n\n" + UI["tipi_hint"][lang]) if i == 0 else ""
        text = f"{head} · {UI['tipi_head'][lang]}\n\n{stmt}{hint}"
        rows = [[(lbl, str(v + 1))] for v, lbl in enumerate(SCALE7[lang])]
        return text, rows + back

    q = CHOICE[step]
    idx = 1 if lang == "uz" else 2
    text = (f"{head} · {UI['ctx_head'][lang]}\n\n" if head else "") + q["text"][lang]
    rows = []
    if step in MULTI:
        chosen = set(data.get(step, []))
        for opt in q["options"]:
            mark = "✅ " if opt[0] in chosen else ""
            rows.append([(mark + opt[idx], opt[0])])
        rows.append([(UI["next"][lang], "__done")])
    else:
        rows = [[(opt[idx], opt[0])] for opt in q["options"]]
    if step == "age":
        back = []
    return text, rows + back


def apply(steps: list[str], pos: int, data: dict, value: str) -> tuple[int, dict, str | None]:
    """Javobni qo'llaydi. Qaytaradi: (yangi pozitsiya, data, xato_xabari)."""
    step = steps[pos]
    if value == "__back":
        return max(pos - 1, 1), data, None   # tilga qaytmaymiz

    if step == "lang":
        if value not in ("uz", "ru"):
            return pos, data, None
        data["lang"] = value
        return pos + 1, data, None

    if step.startswith("int"):
        v = int(value)
        if not 0 <= v <= 4:
            return pos, data, None
        ans = data.setdefault("interest", [None] * 30)
        ans[int(step[3:])] = v
        return pos + 1, data, None

    if step.startswith("tipi"):
        v = int(value)
        if not 1 <= v <= 7:
            return pos, data, None
        ans = data.setdefault("tipi", [None] * 10)
        ans[int(step[4:])] = v
        return pos + 1, data, None

    q = CHOICE[step]
    codes = [o[0] for o in q["options"]]
    if step in MULTI:
        chosen = list(data.get(step, []))
        if value == "__done":
            if not chosen:
                return pos, data, "empty"
            return pos + 1, data, None
        if value not in codes:
            return pos, data, None
        if value in chosen:
            chosen.remove(value)
        else:
            if step == "difficulty" and value == "none":
                chosen = []
            elif step == "difficulty" and "none" in chosen:
                chosen.remove("none")
            if len(chosen) >= q.get("max", 99):
                return pos, data, "max"
            chosen.append(value)
        data[step] = chosen
        return pos, data, None

    if value not in codes:
        return pos, data, None
    data[step] = value
    return pos + 1, data, None


def max_msg(step: str, lang: str) -> str:
    return UI["max"][lang].format(CHOICE[step].get("max", 1))
