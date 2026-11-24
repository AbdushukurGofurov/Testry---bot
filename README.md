# Testry MVP boti

Telegram bot: 45 savollik qiziqish testi, bepul natija, baho, pullik hisobot taklifi va jamoa uchun statistika.

## Fayllar

- questions.py — barcha savollar va matnlar (o‘zbek, rus). Savolni o‘zgartirish kerak bo‘lsa — faqat shu fayl
- scoring.py — ball hisoblash va bepul natija matni
- flow.py — savollar ketma-ketligi
- bot.py — Telegram bilan ishlash, admin buyruqlari
- db.py — javoblarni saqlash (SQLite)

## Sozlamalar (muhit o‘zgaruvchilari)

- BOT_TOKEN (majburiy) — @BotFather bergan kalit. Hech kimga yubormang, faqat hostingga kiriting
- ADMIN_IDS (majburiy) — adminlarning Telegram ID raqamlari, vergul bilan
- PRICE_TEXT — pullik hisobot narxi, masalan "49 000 so‘m"
- PAYMENT_URL — Payme/Click to‘lov havolasi. Bo‘lmasa, bot "admin bog‘lanadi" deydi
- DB_PATH — baza fayli joyi. Render’da: /data/testry.db

## Admin buyruqlari

- /stats — nechta odam boshladi, tugatdi, o‘rtacha baho, o‘z taxmini bilan moslik, pullik bosganlar
- /export — barcha javoblar CSV faylda (Excel’da ochiladi)
- /retest — 14 kun oldin test topshirganlarga qayta test taklifini yuboradi

## Litsenziya

Qiziqish savollari O*NET Mini Interest Profiler’dan olingan va tarjima qilingan (O*NET Tools Developer License).
This application includes information from the O*NET Career Exploration Tools by the U.S. Department of Labor,
Employment and Training Administration (USDOL/ETA). Used under the O*NET Tools Developer License.
O*NET® is a trademark of USDOL/ETA. Testry has modified all or some of this information.
USDOL/ETA has not approved, endorsed, or tested these modifications.

Xarakter savollari: Ten Item Personality Inventory (TIPI), Gosling, Rentfrow & Swann (2003).
