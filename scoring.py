"""Ball hisoblash va bepul natija matni."""
from questions import INTEREST, TIPI, TYPE_NAMES, TYPE_LIKES, PAIRS, pair_key

TYPES = "RIASEC"

# Bizning taxminiy chegaralarimiz (pilotdan keyin sozlanadi)
FLAT_GAP = 2        # 1- va 3-o'rin farqi shundan kam bo'lsa -> tekis profil
LOW_MAX = 8         # barcha tiplar shundan past bo'lsa -> past profil
TIPI_HIGH = 5.0
TIPI_LOW = 3.0


def riasec_scores(answers: list[int]) -> dict[str, int]:
    """answers: 30 ta javob, har biri 0..4."""
    assert len(answers) == 30
    scores = {t: 0 for t in TYPES}
    for (t, _uz, _ru), a in zip(INTEREST, answers):
        scores[t] += a
    return scores


def tipi_scores(answers: list[int]) -> dict[str, float]:
    """answers: 10 ta javob, har biri 1..7."""
    assert len(answers) == 10
    sums: dict[str, list[float]] = {}
    for (trait, reverse, _uz, _ru), a in zip(TIPI, answers):
        v = 8 - a if reverse else a
        sums.setdefault(trait, []).append(v)
    return {k: sum(v) / len(v) for k, v in sums.items()}


def profile(scores: dict[str, int]) -> dict:
    ranked = sorted(TYPES, key=lambda t: (-scores[t], TYPES.index(t)))
    top1, top2, top3 = ranked[0], ranked[1], ranked[2]
    if all(scores[t] < LOW_MAX for t in TYPES):
        kind = "low"
    elif scores[top1] - scores[top3] < FLAT_GAP:
        kind = "flat"
    else:
        kind = "normal"
    tie = scores[top2] == scores[top3] and kind == "normal"
    return {"ranked": ranked, "top": [top1, top2], "kind": kind, "tie_with": top3 if tie else None}


def bar(score: int) -> str:
    filled = int(score / 2 + 0.5)
    return "█" * filled + "░" * (10 - filled)


def favourite_items(answers: list[int], types: list[str], lang: str, n: int = 2) -> list[str]:
    """Yuqori tiplardagi eng baland baholangan faoliyatlar (natijani aniq qilish uchun)."""
    idx = 1 if lang == "uz" else 2
    cands = [(a, i) for i, ((t, *_), a) in enumerate(zip(INTEREST, answers)) if t in types and a >= 3]
    cands.sort(key=lambda x: (-x[0], x[1]))
    return [INTEREST[i][idx].lower() for _a, i in cands[:n]]


def env_lines(tipi: dict[str, float], lang: str) -> list[str]:
    """Ish muhiti tavsiyalari (pullik hisobot va admin uchun). Hissiy barqarorlik ko'rsatilmaydi."""
    t = {
        "ext": ("Odamlar bilan ko‘p muloqotli jamoa", "Tinch, mustaqil, chuqur e’tibor talab qiladigan muhit",
                "Команда с активным общением", "Спокойная самостоятельная работа с глубоким фокусом"),
        "con": ("Aniq reja va tartib bilan ishlash", "Erkin, o‘zgaruvchan ish vaqti",
                "Чёткий план и структура", "Свободный, гибкий график"),
        "opn": ("Doim yangi, har xil ishlar", "Har kuni aniq va tushunarli ishlar",
                "Новые, меняющиеся проекты", "Стабильная работа с понятными процессами"),
        "agr": ("Bir-biriga yordam beradigan ahil jamoa", "O‘zingiz qaror qiladigan, bahs-munozara bor ish",
                "Команда, построенная на сотрудничестве", "Самостоятельные решения, споры и переговоры"),
    }
    out = []
    for k, (uz_hi, uz_lo, ru_hi, ru_lo) in t.items():
        v = tipi[k]
        if v >= TIPI_HIGH:
            out.append(uz_hi if lang == "uz" else ru_hi)
        elif v <= TIPI_LOW:
            out.append(uz_lo if lang == "uz" else ru_lo)
    return out


def free_result(name: str, answers: list[int], lang: str) -> tuple[str, dict]:
    scores = riasec_scores(answers)
    p = profile(scores)
    lines = []
    if p["kind"] == "low":
        if lang == "uz":
            lines.append(f"{name}, testdagi ishlarning ko‘pi sizga hozircha unchalik yoqmadi.\n")
            lines.append("Bu normal: qiziqish ko‘pincha biror narsani amalda sinab ko‘rgandan keyin paydo bo‘ladi. "
                         "Sizga bitta kasb nomini majburan aytmaymiz — avval bir nechta sohani qisqa tanishuv orqali ko‘rib chiqish foydali.")
        else:
            lines.append(f"{name}, большинство занятий из теста вам пока не очень понравились.\n")
            lines.append("Это нормально: интерес часто появляется после того, как вы что-то попробуете на практике. "
                         "Мы не будем навязывать профессию — сначала полезно коротко познакомиться с несколькими сферами.")
        title_pair = None
    elif p["kind"] == "flat":
        if lang == "uz":
            lines.append(f"{name}, sizning tipingiz: <b>KENG QIZIQISHLI IZLANUVCHI</b>")
        else:
            lines.append(f"{name}, ваш тип: <b>ИССЛЕДОВАТЕЛЬ С ШИРОКИМИ ИНТЕРЕСАМИ</b>")
        title_pair = None
    else:
        a, b = p["top"]
        title_pair = PAIRS[pair_key(a, b)]
        nm = title_pair[0] if lang == "uz" else title_pair[1]
        lines.append(("{}, sizning tipingiz: <b>{}</b>" if lang == "uz" else "{}, ваш тип: <b>{}</b>").format(name, nm.upper()))

    rows = [f"{TYPE_NAMES[t][lang]:<15} {bar(scores[t])} {round(scores[t] / 20 * 100)}%" for t in p["ranked"]]
    lines.append("\n<pre>" + "\n".join(rows) + "</pre>")

    if p["kind"] == "normal":
        a, b = p["top"]
        fav = favourite_items(answers, [a, b], lang)
        if lang == "uz":
            lines.append(f"\n<b>Bu nimani anglatadi?</b>\nSizga ikki narsa yoqadi:\n• {TYPE_LIKES[a]['uz']};\n• {TYPE_LIKES[b]['uz']}.")
            if fav:
                lines.append("Eng yuqori baholaganlaringiz: " + "; ".join(fav) + ".")
            lines.append(f"\n<b>Sizga mos yo‘nalish:</b>\n📊 {title_pair[2]}")
            if p["tie_with"]:
                lines.append(f"\nEslatma: siz {TYPE_NAMES[p['tie_with']]['uz']} tipiga ham xuddi shunchalik yaqinsiz.")
        else:
            lines.append(f"\n<b>Что это значит?</b>\nВам нравятся две вещи:\n• {TYPE_LIKES[a]['ru']};\n• {TYPE_LIKES[b]['ru']}.")
            if fav:
                lines.append("Выше всего вы оценили: " + "; ".join(fav) + ".")
            lines.append(f"\n<b>Подходящее направление:</b>\n📊 {title_pair[3]}")
            if p["tie_with"]:
                lines.append(f"\nВы так же близки к типу «{TYPE_NAMES[p['tie_with']]['ru']}».")
    elif p["kind"] == "flat":
        if lang == "uz":
            lines.append("\nBir nechta yo‘nalish sizga deyarli bir xil yoqadi. Bu kamchilik emas: to‘liq hisobotda "
                         "eng yaqin 3 ta yo‘nalishni sinab ko‘rish rejasini beramiz.")
        else:
            lines.append("\nНесколько направлений нравятся вам почти одинаково. Это не недостаток: в полном отчёте "
                         "мы дадим план, как попробовать 3 ближайших направления.")

    meta = {"scores": scores, "kind": p["kind"], "top": p["top"], "tie_with": p["tie_with"]}
    return "\n".join(lines), meta


def guess_match(guess: list[str], top: list[str]) -> int:
    return len(set(guess) & set(top))
