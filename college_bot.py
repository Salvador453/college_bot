import telebot
from datetime import date, timedelta
from pathlib import Path
import json

# ================== НАСТРОЙКИ ==================

TOKEN = "8279399872:AAErEd7JODe8bwj9_EYfaM7Un8XHe-c8kxI"

# твой Telegram ID (узнаешь в @userinfobot / @getmyid_bot)
ADMIN_IDS = {123456789}  # <-- замени на своё число

# Неделя, которая начинается в ПН 01.12.2025 – це ЗНАМЕННИК
REFERENCE_MONDAY = date(2025, 12, 1)
REFERENCE_WEEK_TYPE = "знаменник"

SCHEDULE_FILE = "schedule.json"

# Расклад дзвінків
BELL_SCHEDULE = {
    "monday": {
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "13:20–13:50",   # орг. год.
        5: "14:00–15:20",   # про запас
    },
    "other": {  # вівторок–пʼятниця
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "13:20–14:40",
        5: "14:50–16:10",
    },
}

DAY_ALIASES = {
    # понеділок
    "понеділок": "monday",
    "понедельник": "monday",
    "пн": "monday",
    "mon": "monday",
    "monday": "monday",

    # вівторок
    "вівторок": "tuesday",
    "вторник": "tuesday",
    "вт": "tuesday",
    "tue": "tuesday",
    "tuesday": "tuesday",

    # середа
    "середа": "wednesday",
    "ср": "wednesday",
    "wed": "wednesday",
    "wednesday": "wednesday",

    # четвер
    "четвер": "thursday",
    "чт": "thursday",
    "thu": "thursday",
    "thursday": "thursday",

    # п’ятниця (все варианты апострофа)
    "пʼятниця": "friday",
    "п'ятниця": "friday",
    "пятниця": "friday",
    "пятница": "friday",
    "пт": "friday",
    "fri": "friday",
    "friday": "friday",

    # субота
    "субота": "saturday",
    "суббота": "saturday",
    "сб": "saturday",
    "sat": "saturday",
    "saturday": "saturday",

    # неділя
    "неділя": "sunday",
    "воскресенье": "sunday",
    "нд": "sunday",
    "sun": "sunday",
    "sunday": "sunday",
}

DAYS_RU = {
    "monday": "Понеділок",
    "tuesday": "Вівторок",
    "wednesday": "Середа",
    "thursday": "Четвер",
    "friday": "Пʼятниця",
    "saturday": "Субота",
    "sunday": "Неділя",
}

bot = telebot.TeleBot(TOKEN)


# ================== РАСПИСАНИЕ (LOAD / SAVE) ==================

def default_schedule():
    # ---------- ПОНЕДІЛОК ----------

    monday_chys = {
        "1": {"subject": "Фізична культура", "room": "с/з №2"},
        "2": {"subject": "Інформатика", "room": "202"},
        "3": {"subject": "Фізика і астрономія", "room": "129"},
        "4": {"subject": "Організаційна година", "room": "205"},
    }
    monday_znam = {
        "1": {"subject": "Фізична культура", "room": "с/з №2"},
        "2": {"subject": "Інформатика", "room": "202"},
        "3": {"subject": "Математика", "room": "121"},
        "4": {"subject": "Організаційна година", "room": "205"},
    }

    # ---------- ВІВТОРОК ----------
    # чисельник – без 1-ї пари

    tuesday_chys = {
        "2": {"subject": "Хімія", "room": "16"},
        "3": {"subject": "Біологія і екологія", "room": "16"},
        "4": {"subject": "Громадянська освіта", "room": "114"},
    }
    tuesday_znam = {
        "1": {"subject": "Інформатика", "room": "239"},
        "2": {"subject": "Хімія", "room": "16"},
        "3": {"subject": "Біологія і екологія", "room": "16"},
        "4": {"subject": "Громадянська освіта", "room": "114"},
    }

    # ---------- СЕРЕДА ----------

    wednesday_chys = {
        "1": {"subject": "Іноземна мова", "room": "224а"},
        "2": {"subject": "Всесвітня історія", "room": "114"},
        "3": {"subject": "Математика", "room": "121"},
        "4": {"subject": "Географія", "room": "123"},
    }
    wednesday_znam = {
        "1": {"subject": "Іноземна мова", "room": "224а"},
        "2": {"subject": "Історія України", "room": "114"},
        "3": {"subject": "Математика", "room": "121"},
        "4": {"subject": "Географія", "room": "123"},
    }

    # ---------- ЧЕТВЕР ----------
    # чисельник – без 1-ї пари

    thursday_chys = {
        "2": {"subject": "Українська мова", "room": "307"},
        "3": {"subject": "Фізика і астрономія", "room": "129"},
    }
    thursday_znam = {
        "1": {"subject": "Технології", "room": "207"},
        "2": {"subject": "Українська мова", "room": "307"},
        "3": {"subject": "Фізика і астрономія", "room": "129"},
    }

    # ---------- ПʼЯТНИЦЯ ----------
    # Чисельник: 1 Укр. літ, 2 Фізра, 3 Захист України
    # Знаменник: 1 Укр. літ, 2 Зарубіжна, 3 Захист України

    friday_chys = {
        "1": {"subject": "Українська література", "room": "209"},
        "2": {"subject": "Фізична культура", "room": "с/з №2"},
        "3": {"subject": "Захист України", "room": "242 / 201"},
    }
    friday_znam = {
        "1": {"subject": "Українська література", "room": "209"},
        "2": {"subject": "Зарубіжна література", "room": "116"},
        "3": {"subject": "Захист України", "room": "242 / 201"},
    }

    return {
        "monday": {
            "чисельник": monday_chys,
            "знаменник": monday_znam,
        },
        "tuesday": {
            "чисельник": tuesday_chys,
            "знаменник": tuesday_znam,
        },
        "wednesday": {
            "чисельник": wednesday_chys,
            "знаменник": wednesday_znam,
        },
        "thursday": {
            "чисельник": thursday_chys,
            "знаменник": thursday_znam,
        },
        "friday": {
            "чисельник": friday_chys,
            "знаменник": friday_znam,
        },
        "saturday": {"чисельник": {}, "знаменник": {}},
        "sunday": {"чисельник": {}, "знаменник": {}},
    }


def load_schedule():
    path = Path(SCHEDULE_FILE)
    if not path.exists():
        return default_schedule()
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule(data):
    path = Path(SCHEDULE_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


schedule = load_schedule()


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

def get_week_type(target_date=None):
    """Чисельник / знаменник по референс-неделе."""
    if target_date is None:
        target_date = date.today()
    delta_days = (target_date - REFERENCE_MONDAY).days
    weeks_passed = delta_days // 7
    if weeks_passed % 2 == 0:
        return REFERENCE_WEEK_TYPE
    else:
        return "чисельник" if REFERENCE_WEEK_TYPE == "знаменник" else "знаменник"


def get_day_key(target_date=None):
    if target_date is None:
        target_date = date.today()
    weekday = target_date.weekday()
    mapping = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
        5: "saturday",
        6: "sunday",
    }
    return mapping[weekday]


def get_pair_time(day_key, pair_num):
    if day_key == "monday":
        return BELL_SCHEDULE["monday"].get(pair_num)
    else:
        return BELL_SCHEDULE["other"].get(pair_num)


def format_day_schedule(d):
    """Розклад на день. Якщо на цю тиждень пусто, але на іншу є – підтягуємо її."""
    week_type = get_week_type(d)
    day_key = get_day_key(d)

    day_data = schedule.get(day_key, {})
    day_schedule = day_data.get(week_type, {})

    used_week_type = week_type

    if not day_schedule:
        other = "знаменник" if week_type == "чисельник" else "чисельник"
        if day_data.get(other):
            day_schedule = day_data[other]
            used_week_type = f"{week_type} (як у {other})"

    header = f"{DAYS_RU[day_key]}, {d.strftime('%d.%m.%Y')}\nТиждень: {used_week_type.upper()}\n\n"

    if not day_schedule:
        return header + "Пар немає ✅"

    lines = [header]
    for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x)):
        pair_num = int(pair_str)
        pair = day_schedule[pair_str]
        time_txt = get_pair_time(day_key, pair_num) or "час ?"
        subj = pair.get("subject", "—")
        room = pair.get("room", "")
        line = f"{pair_num}) {time_txt} — {subj}"
        if room:
            line += f" ({room})"
        lines.append(line)

    return "\n".join(lines)


def format_full_schedule():
    lines = []
    for day_key in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        lines.append(f"📅 {DAYS_RU[day_key]}")
        for wt in ["чисельник", "знаменник"]:
            lines.append(f"  🔹 {wt.upper()}:")
            day_schedule = schedule.get(day_key, {}).get(wt, {})
            if not day_schedule:
                lines.append("    — немає пар")
            else:
                for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x)):
                    pair_num = int(pair_str)
                    pair = day_schedule[pair_str]
                    time_txt = get_pair_time(day_key, pair_num) or "час ?"
                    subj = pair.get("subject", "—")
                    room = pair.get("room", "")
                    line = f"    {pair_num}) {time_txt} — {subj}"
                    if room:
                        line += f" ({room})"
                    lines.append(line)
        lines.append("")
    return "\n".join(lines)


def is_admin(message) -> bool:
    return message.from_user.id in ADMIN_IDS


# ================== КОМАНДЫ ДЛЯ ВСЕХ ==================

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    text = (
        "Привіт! Я бот розкладу групи 📚\n\n"
        "Команди:\n"
        "/week – яка зараз тиждень (чисельник / знаменник)\n"
        "/today – розклад на сьогодні\n"
        "/tomorrow – розклад на завтра\n"
        "/day <день> – розклад на конкретний день (напр.: /day середа)\n"
        "/all – повний розклад\n"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["week"])
def week_cmd(message):
    wt = get_week_type()
    bot.reply_to(message, f"Зараз тиждень: *{wt.upper()}*", parse_mode="Markdown")


@bot.message_handler(commands=["today"])
def today_cmd(message):
    d = date.today()
    bot.reply_to(message, format_day_schedule(d))


@bot.message_handler(commands=["tomorrow"])
def tomorrow_cmd(message):
    d = date.today() + timedelta(days=1)
    bot.reply_to(message, format_day_schedule(d))


@bot.message_handler(commands=["day"])
def day_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.reply_to(message, "Приклад: /day вівторок")
        return
    day_raw = parts[1].strip().lower()
    day_key = DAY_ALIASES.get(day_raw)
    if not day_key:
        bot.reply_to(message, "Не розумію день. Приклад: /day понеділок")
        return

    today = date.today()
    today_key = get_day_key(today)
    keys_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    idx_today = keys_order.index(today_key)
    idx_target = keys_order.index(day_key)
    shift = (idx_target - idx_today) % 7
    target_date = today + timedelta(days=shift)

    bot.reply_to(message, format_day_schedule(target_date))


@bot.message_handler(commands=["all"])
def all_cmd(message):
    text = format_full_schedule()
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i + 4000])
    else:
        bot.reply_to(message, text)


# ================== АДМИН-КОМАНДЫ (ШВИДКА ЗМІНА ПАР) ==================

@bot.message_handler(commands=["adminhelp"])
def admin_help(message):
    if not is_admin(message):
        return
    text = (
        "Адмін-команди:\n\n"
        "/setpair <день> <номер> <тиждень> <предмет> ; <аудиторія>\n\n"
        "Приклади:\n"
        "/setpair понеділок 2 чисельник Інформатика ; 202\n"
        "/setpair середа 3 знаменник Математика ; 121\n\n"
        "День: понеділок/вівторок/середа/четвер/пʼятниця (можна скорочено: пн, вт, ср...).\n"
        "Тиждень: чисельник/знаменник (можна: чис / зн)."
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["setpair"])
def setpair_cmd(message):
    if not is_admin(message):
        return

    try:
        _, rest = message.text.split(" ", 1)
    except ValueError:
        bot.reply_to(message, "Формат: /setpair <день> <номер> <тиждень> <предмет> ; <аудиторія>")
        return

    parts = rest.split(maxsplit=3)
    if len(parts) < 4:
        bot.reply_to(message, "Формат: /setpair <день> <номер> <тиждень> <предмет> ; <аудиторія>")
        return

    day_raw, pair_str, week_raw, subj_room_raw = parts
    day_key = DAY_ALIASES.get(day_raw.lower())
    if not day_key:
        bot.reply_to(message, "День некоректний. Приклад: понеділок / вівторок / середа / четвер / пʼятниця.")
        return

    try:
        pair_num = int(pair_str)
    except ValueError:
        bot.reply_to(message, "Номер пари має бути числом, напр.: 1, 2, 3, 4")
        return

    w_raw = week_raw.lower()
    if w_raw.startswith("чис"):
        week_type = "чисельник"
    elif w_raw.startswith("зн"):
        week_type = "знаменник"
    else:
        bot.reply_to(message, "Тиждень має бути 'чисельник' або 'знаменник'")
        return

    if ";" in subj_room_raw:
        subject, room = [x.strip() for x in subj_room_raw.split(";", 1)]
    else:
        subject = subj_room_raw.strip()
        room = ""

    schedule.setdefault(day_key, {}).setdefault(week_type, {})
    schedule[day_key][week_type][str(pair_num)] = {
        "subject": subject,
        "room": room,
    }
    save_schedule(schedule)

    time_txt = get_pair_time(day_key, pair_num) or "час ?"
    bot.reply_to(
        message,
        f"Ок, оновив:\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type})\n"
        f"{time_txt} — {subject} {f'({room})' if room else ''}"
    )


# ================== СТАРТ БОТА ==================

print("Бот запущен...")
bot.infinity_polling()
