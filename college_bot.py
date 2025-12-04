# ================== IMPORTS ==================
import telebot
from datetime import date, datetime, timedelta
from pathlib import Path
import json
import os

from flask import Flask
import threading


# ================== FLASK ДЛЯ RENDER ==================
app = Flask(__name__)

@app.route("/")
def home():
    # сюда будет стучаться UptimeRobot, чтобы Render не засыпал
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


# ================== НАСТРОЙКИ БОТА ==================
# !!! СЮДА ВСТАВЬ СВОЙ ТОКЕН ОТ BotFather !!!
TOKEN = "8279399872:AAH7NjweBtoYs97WZ9Vme-6BRzE219LP0T4"

# твой Telegram ID (для будущих админ-фич, можешь не трогать)
ADMIN_IDS = [1509389908]

bot = telebot.TeleBot(TOKEN)


# ================== КОНСТАНТЫ ==================
# Неделя, которая начинается в ПН 01.12.2025 — это ЗНАМЕННИК
REFERENCE_MONDAY = date(2025, 12, 1)
REFERENCE_WEEK_TYPE = "ЗНАМЕННИК"   # в эту неделю

WEEK_TYPES = ("ЗНАМЕННИК", "ЧИСЕЛЬНИК")

# файл с расписанием (если захочешь потом допилить изменение расписания)
SCHEDULE_FILE = "schedule.json"


# ================== РАСПИСАНИЕ ЗВОНКОВ ==================
BELL_SCHEDULE = {
    "monday": {
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "14:00–15:20",
    },
    "other": {  # вівторок–пʼятниця
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "13:20–14:40",
        5: "14:50–16:10",
    },
}


# ================== РАСПИСАНИЕ ПАР ==================
# ВНИМАНИЕ: тут уже учтены все нюансы, про которые ты писал:
# - ПН: 3 пара матем / физика
# - ВТ: в чисельник нет 1 пары
# - СР: история Украины / всесвітня історія
# - ЧТ: в чисельник нет 1 пары
# - ПТ: всегда 3 пары, но 2-я: зарубіжна / фізра

SCHEDULE = {
    "ЗНАМЕННИК": {
        "monday": {
            1: "Фізична культура (с/з №2)",
            2: "Інформатика (202)",
            3: "Математика (121)",
            4: "Організаційна година (205)",
        },
        "tuesday": {
            1: "Інформатика (239)",
            2: "Хімія (16)",
            3: "Біологія і екологія (16)",
            4: "Громадянська освіта (114)",
        },
        "wednesday": {
            1: "Іноземна мова (224а)",
            2: "Історія України (114)",
            3: "Математика (121)",
            4: "Географія (123)",
        },
        "thursday": {
            1: "Технології (207)",
            2: "Українська мова (307)",
            3: "Фізика і астрономія (129)",
        },
        "friday": {
            1: "Українська література (209)",
            2: "Зарубіжна література (116)",
            3: "Захист України (242 / 201)",
        },
    },
    "ЧИСЕЛЬНИК": {
        "monday": {
            1: "Фізична культура (с/з №2)",
            2: "Інформатика (202)",
            3: "Фізика і астрономія (129)",
            4: "Організаційна година (205)",
        },
        "tuesday": {
            # первой пары нет
            2: "Хімія (16)",
            3: "Біологія і екологія (16)",
            4: "Громадянська освіта (114)",
        },
        "wednesday": {
            1: "Іноземна мова (224а)",
            2: "Всесвітня історія (114)",
            3: "Математика (121)",
            4: "Географія (123)",
        },
        "thursday": {
            # первой пары нет
            2: "Українська мова (307)",
            3: "Фізика і астрономія (129)",
        },
        "friday": {
            1: "Українська література (209)",
            2: "Фізична культура (с/з №2)",
            3: "Захист України (242 / 201)",
        },
    },
}


# ================== ДНИ НЕДЕЛИ ==================
DAY_ALIASES = {
    "понеділок": "monday",
    "понедельник": "monday",
    "пн": "monday",

    "вівторок": "tuesday",
    "вторник": "tuesday",
    "вт": "tuesday",

    "середа": "wednesday",
    "среда": "wednesday",
    "ср": "wednesday",

    "четвер": "thursday",
    "четверг": "thursday",
    "чт": "thursday",

    "пʼятниця": "friday",
    "пятница": "friday",
    "пт": "friday",
}

DAYS_UA = {
    "monday": "Понеділок",
    "tuesday": "Вівторок",
    "wednesday": "Середа",
    "thursday": "Четвер",
    "friday": "Пʼятниця",
}


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def get_week_type(d: date) -> str:
    """
    Возвращает тип недели для даты: 'ЗНАМЕННИК' или 'ЧИСЕЛЬНИК'
    """
    delta_days = (d - REFERENCE_MONDAY).days
    week_index = delta_days // 7
    if week_index % 2 == 0:
        return REFERENCE_WEEK_TYPE
    else:
        return "ЧИСЕЛЬНИК" if REFERENCE_WEEK_TYPE == "ЗНАМЕННИК" else "ЗНАМЕННИК"


def get_schedule_for_day(d: date) -> tuple[str, dict]:
    """
    Для конкретной даты возвращает (тип_недели, словарь_пар_на_этот_день)
    """
    week_type = get_week_type(d)
    weekday_key = d.strftime("%A").lower()  # 'monday', 'tuesday', ...
    day_schedule = SCHEDULE.get(week_type, {}).get(weekday_key, {})
    return week_type, day_schedule


def format_day_schedule(d: date) -> str:
    """
    Собирает красивый текст для расписания на конкретный день.
    """
    week_type, day_schedule = get_schedule_for_day(d)
    weekday_key = d.strftime("%A").lower()
    weekday_name = DAYS_UA.get(weekday_key, weekday_key)

    if not day_schedule:
        return f"{weekday_name} ({d.strftime('%d.%m.%Y')})\nТиждень: {week_type}\n\nПар немає ✨"

    lines = []
    for pair_num in sorted(day_schedule.keys()):
        subj = day_schedule[pair_num]
        lines.append(f"{pair_num} пара — {subj}")

    header = f"{weekday_name} ({d.strftime('%d.%m.%Y')})\nТиждень: {week_type}"
    return header + "\n\n" + "\n".join(lines)


def format_week_schedule(d: date) -> str:
    """
    Возвращает расписание на всю неделю, где находится дата d.
    """
    week_type = get_week_type(d)
    monday = d - timedelta(days=d.weekday())  # понедельник этой недели

    lines = [f"Тиждень: {week_type}", ""]

    for offset in range(5):  # ПН–ПТ
        day = monday + timedelta(days=offset)
        weekday_key = day.strftime("%A").lower()
        weekday_name = DAYS_UA.get(weekday_key, weekday_key)
        _, day_schedule = get_schedule_for_day(day)

        lines.append(f"{weekday_name} ({day.strftime('%d.%m.%Y')})")

        if not day_schedule:
            lines.append("  пар немає ✨")
        else:
            for pair_num in sorted(day_schedule.keys()):
                subj = day_schedule[pair_num]
                lines.append(f"  {pair_num} пара — {subj}")

        lines.append("")  # пустая строка между днями

    return "\n".join(lines)


def format_bells() -> str:
    """
    Текст для /bells — розклад дзвінків
    """
    lines = ["🔔 Розклад дзвінків", ""]

    lines.append("Понеділок:")
    for num in sorted(BELL_SCHEDULE["monday"].keys()):
        lines.append(f"{num} пара — {BELL_SCHEDULE['monday'][num]}")

    lines.append("")
    lines.append("Вівторок – Пʼятниця:")
    for num in sorted(BELL_SCHEDULE["other"].keys()):
        lines.append(f"{num} пара — {BELL_SCHEDULE['other'][num]}")

    return "\n".join(lines)


# ================== КЛАВИАТУРА ==================
def main_keyboard():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Розклад на сьогодні", "Розклад на завтра")
    kb.row("Розклад на тиждень")
    kb.row("Розклад дзвінків")
    return kb


# ================== ХЕНДЛЕРЫ КОМАНД ==================
@bot.message_handler(commands=["start"])
def cmd_start(message: telebot.types.Message):
    bot.send_message(
        message.chat.id,
        "Привіт! Я бот для розкладу коледжу.\n\n"
        "Команди:\n"
        "/today – пари на сьогодні\n"
        "/tomorrow – пари на завтра\n"
        "/week – пари на тиждень\n"
        "/bells – розклад дзвінків\n\n"
        "Або користуйся кнопками нижче 👇",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["today"])
def cmd_today(message: telebot.types.Message):
    today = date.today()
    text = format_day_schedule(today)
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


@bot.message_handler(commands=["tomorrow"])
def cmd_tomorrow(message: telebot.types.Message):
    tomorrow = date.today() + timedelta(days=1)
    text = format_day_schedule(tomorrow)
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


@bot.message_handler(commands=["week"])
def cmd_week(message: telebot.types.Message):
    today = date.today()
    text = format_week_schedule(today)
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


@bot.message_handler(commands=["bells"])
def cmd_bells(message: telebot.types.Message):
    bot.send_message(message.chat.id, format_bells(), reply_markup=main_keyboard())


@bot.message_handler(commands=["day"])
def cmd_day(message: telebot.types.Message):
    """
    /day понеділок  -> показати розклад на конкретний день поточного тижня
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Напиши день: /day понеділок")
        return

    day_text = parts[1].strip().lower()
    weekday_key = DAY_ALIASES.get(day_text)
    if not weekday_key:
        bot.reply_to(message, "Не розумію день. Приклад: /day понеділок")
        return

    today = date.today()
    week_type = get_week_type(today)
    day_index = ["monday", "tuesday", "wednesday", "thursday", "friday"].index(
        weekday_key
    )
    monday = today - timedelta(days=today.weekday())
    target_date = monday + timedelta(days=day_index)

    text = format_day_schedule(target_date)
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


# ================== ОБРАБОТКА ТЕКСТОВЫХ КНОПОК ==================
@bot.message_handler(func=lambda m: m.text is not None)
def handle_text(message: telebot.types.Message):
    text = message.text.strip().lower()

    if text in ["розклад на сьогодні", "расписание на сегодня"]:
        cmd_today(message)
    elif text in ["розклад на завтра", "расписание на завтра"]:
        cmd_tomorrow(message)
    elif text in ["розклад на тиждень", "расписание на неделю"]:
        cmd_week(message)
    elif text in ["розклад дзвінків", "расписание звонков"]:
        cmd_bells(message)
    else:
        bot.reply_to(
            message,
            "Не розумію 🤔\n"
            "Спробуй команди /today, /tomorrow, /week, /bells або скористайся кнопками.",
            reply_markup=main_keyboard(),
        )


# ================== ЗАПУСК БОТА ==================
def main():
    # на всякий случай снимаем webhook
    try:
        bot.remove_webhook()
    except Exception:
        pass

    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    # запускаем Flask в отдельном потоке, чтобы Render видел открытый порт
    threading.Thread(target=run_flask, daemon=True).start()

    # запускаем телеграм-бота
    main()
