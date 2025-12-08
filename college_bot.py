import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta, datetime
from pathlib import Path
import json
import time

# ====== мини-вебсервер для Render ======
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    # host 0.0.0.0 обязателен, иначе Render не увидит порт
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()
# =======================================


# ================== НАСТРОЙКИ ==================

TOKEN = "7762300503:AAF17NRUSz6aeUG6Ek8rXMMtuYT3GQ2lPEM"

bot = telebot.TeleBot(TOKEN)

# на всякий случай выпиливаем вебхук, чтобы не ловить 409
try:
    bot.remove_webhook()
except Exception as e:
    print("Ошибка при удалении webhook:", e)

# твой Telegram ID + сюда можешь добавить ещё одного адміна
ADMIN_IDS = {
    1509389908,  # твій ID
    1573294591,  # 👉 сюди впиши ID другого адміна
}

# Неделя, которая начинается в ПН 01.12.2025 – це ЗНАМЕННИК
REFERENCE_MONDAY = date(2025, 12, 1)
REFERENCE_WEEK_TYPE = "знаменник"

SCHEDULE_FILE = "schedule.json"
USERS_FILE = "users.json"   # тут будем хранить хто писав боту

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

    # п’ятниця
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

# ==== Google Meet ссылки по предметам ====

SUBJECT_MEET_LINKS = {
    "Фізика і астрономія": "https://meet.google.com/yqs-gkhh-xqm?authuser=0&hs=179",
    "Всесвітня історія": "https://meet.google.com/ejg-gvrv-iox?authuser=0&hs=179",
    "Історія України": "https://meet.google.com/mpc-znwb-gkq?authuser=0&hs=179",
    "Іноземна мова": "https://meet.google.com/xfq-qeab-vis?authuser=0&hs=179",
    "Інформатика": "https://meet.google.com/qhx-qkcv-sds?authuser=0&hs=179",
    "Математика": "https://meet.google.com/nnn-qzzy-yjf?authuser=0&hs=179",
    "Фізична культура": "https://meet.google.com/swm-bpmx-dfb?authuser=0&hs=179",
    "Географія": "https://meet.google.com/euh-zuqa-igg?authuser=0&hs=179",
    "Організаційна година": "https://meet.google.com/hai-zbrq-pnb?authuser=0&hs=179",
    "Зарубіжна література": "https://meet.google.com/hug-ddec-mop?authuser=0&hs=179",
    "Українська література": "https://meet.google.com/ogm-ssbj-jzd?authuser=0&hs=179",
    "Громадянська освіта": "https://meet.google.com/mzw-uedt-fzf?authuser=0&hs=179",
    "Технології": "https://meet.google.com/oap-sefr-fgc?authuser=0&hs=179",
    "Українська мова": "https://meet.google.com/wof-fggd-pet?authuser=0&hs=179",
    # базовый вариант Захисту (если вдруг пригодится)
    "Захист України": "https://meet.google.com/mev-azeu-tiw?authuser=0&hs=179",
    "Хімія": "https://meet.google.com/nup-vusc-tgs?authuser=0&hs=179",
    "Біологія і екологія": "https://meet.google.com/dgr-knfu-apt?authuser=0&hs=179",
}

# отдельные ссылки по Захисту
DEFENCE_SAPKO_URL = "https://meet.google.com/mev-azeu-tiw?authuser=0&hs=179"
DEFENCE_KYYASHCHUK_URL = "https://meet.google.com/nmf-wxwf-ouv"

# предметы, которые считаем "немає пари" — по ним не слать нагадування
NO_LESSON_SUBJECTS = {
    "немає пари",
    "нема пари",
    "нет пары",
    "немає уроку",
    "нема уроку",
    "уроку немає",
    "-",
    "—",
    "",
}


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
        "monday": {"чисельник": monday_chys, "знаменник": monday_znam},
        "tuesday": {"чисельник": tuesday_chys, "знаменник": tuesday_znam},
        "wednesday": {"чисельник": wednesday_chys, "знаменник": wednesday_znam},
        "thursday": {"чисельник": thursday_chys, "знаменник": thursday_znam},
        "friday": {"чисельник": friday_chys, "знаменник": friday_znam},
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


# ================== USERS (для /who и уведомлений) ==================

def load_users():
    path = Path(USERS_FILE)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_users():
    path = Path(USERS_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


users = load_users()


def remember_user(message):
    u = message.from_user
    uid = str(u.id)
    info = users.get(uid, {})
    info["id"] = u.id
    info["username"] = u.username or ""
    info["first_name"] = u.first_name or ""
    info["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    users[uid] = info
    save_users()


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

def get_week_type(target_date=None):
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


def get_meet_link_for_subject(subj: str):
    """Ищем Meet-ссылку по предмету без учета регистра и лишних пробелов."""
    if not subj:
        return None
    s = subj.strip().lower()
    for key, url in SUBJECT_MEET_LINKS.items():
        if key.strip().lower() == s:
            return url
    return None


def is_empty_pair(pair: dict) -> bool:
    """Проверяем, що по цій парі фактично 'немає пари'."""
    subj = (pair.get("subject") or "").strip().lower()
    return subj in NO_LESSON_SUBJECTS


def get_day_struct(d):
    """Возвращает (day_key, used_week_type, day_schedule)"""
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

    return day_key, used_week_type, day_schedule


def format_day_schedule(d):
    day_key, used_week_type, day_schedule = get_day_struct(d)

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


def build_day_markup(d):
    """Кнопки с Meet-ссылками для конкретной даты."""
    day_key, used_week_type, day_schedule = get_day_struct(d)
    markup = InlineKeyboardMarkup(row_width=1)
    has_buttons = False

    for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x)):
        pair_num = int(pair_str)
        pair = day_schedule[pair_str]
        subj = pair.get("subject", "—")
        subj_norm = subj.strip().lower()

        # если пари фактично немає — ні кнопок, ні нічого
        if is_empty_pair(pair):
            continue

        # Особый случай: Захист України — две кнопки (Сапко и Киящук)
        if subj_norm == "захист україни":
            markup.add(InlineKeyboardButton(
                text=f"{pair_num}) {subj} — Сапко",
                url=DEFENCE_SAPKO_URL
            ))
            markup.add(InlineKeyboardButton(
                text=f"{pair_num}) {subj} — Киящук",
                url=DEFENCE_KYYASHCHUK_URL
            ))
            has_buttons = True
            continue

        url = get_meet_link_for_subject(subj)
        if not url:
            continue
        text = f"{pair_num}) {subj}"
        markup.add(InlineKeyboardButton(text=text, url=url))
        has_buttons = True

    return markup if has_buttons else None


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
    remember_user(message)
    text = (
        "Привіт! Я бот розкладу групи 📚\n\n"
        "Команди:\n"
        "/week – яка зараз тиждень (чисельник / знаменник)\n"
        "/today – розклад на сьогодні + кнопки з Meet\n"
        "/tomorrow – розклад на завтра + кнопки з Meet\n"
        "/day <день> – розклад на конкретний день (/day середа)\n"
        "/all – повний розклад (без кнопок)\n"
        "/bells – розклад дзвінків\n"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["week"])
def week_cmd(message):
    remember_user(message)
    wt = get_week_type()
    bot.reply_to(message, f"Зараз тиждень: *{wt.upper()}*", parse_mode="Markdown")


@bot.message_handler(commands=["today"])
def today_cmd(message):
    remember_user(message)
    d = date.today()
    text = format_day_schedule(d)
    markup = build_day_markup(d)
    bot.reply_to(message, text, reply_markup=markup)


@bot.message_handler(commands=["tomorrow"])
def tomorrow_cmd(message):
    remember_user(message)
    d = date.today() + timedelta(days=1)
    text = format_day_schedule(d)
    markup = build_day_markup(d)
    bot.reply_to(message, text, reply_markup=markup)


@bot.message_handler(commands=["day"])
def day_cmd(message):
    remember_user(message)
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

    text = format_day_schedule(target_date)
    markup = build_day_markup(target_date)
    bot.reply_to(message, text, reply_markup=markup)


@bot.message_handler(commands=["all"])
def all_cmd(message):
    remember_user(message)
    text = format_full_schedule()
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i + 4000])
    else:
        bot.reply_to(message, text)


@bot.message_handler(commands=["bells"])
def bells_cmd(message):
    remember_user(message)
    txt = "🔔 Розклад дзвінків\n\nПонеділок:\n"
    for num in sorted(BELL_SCHEDULE["monday"].keys()):
        txt += f"{num}) {BELL_SCHEDULE['monday'][num]}\n"
    txt += "\nВівторок–Пʼятниця:\n"
    for num in sorted(BELL_SCHEDULE["other"].keys()):
        txt += f"{num}) {BELL_SCHEDULE['other'][num]}\n"
    bot.reply_to(message, txt)


# ================== АДМИН-КОМАНДЫ ==================

@bot.message_handler(commands=["adminhelp"])
def admin_help(message):
    remember_user(message)
    if not is_admin(message):
        return
    text = (
        "Адмін-команди:\n\n"
        "/setpair <день> <номер> <тиждень> <предмет> ; <аудиторія>\n"
        "/who – список користувачів, які писали боту\n\n"
        "Приклади:\n"
        "/setpair понеділок 2 чисельник Інформатика ; 202\n"
        "/setpair середа 3 знаменник Математика ; 121\n\n"
        "День: понеділок/вівторок/середа/четвер/пʼятниця (можна скорочено: пн, вт, ср...).\n"
        "Тиждень: чисельник/знаменник (можна: чис / зн)."
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["setpair"])
def setpair_cmd(message):
    remember_user(message)
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

    # обновляем расписание
    schedule.setdefault(day_key, {}).setdefault(week_type, {})
    schedule[day_key][week_type][str(pair_num)] = {
        "subject": subject,
        "room": room,
    }
    save_schedule(schedule)

    time_txt = get_pair_time(day_key, pair_num) or "час ?"

    # ответ админу
    bot.reply_to(
        message,
        f"Ок, оновив:\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type})\n"
        f"{time_txt} — {subject} {f'({room})' if room else ''}"
    )

    # ====== РОЗСИЛКА ВСІМ, ХТО ПИСАВ БОТУ ======
    changer = message.from_user.first_name or ""
    subj_norm = subject.strip().lower()
    meet_url = get_meet_link_for_subject(subject)

    change_text = (
        "⚠ Зміни в розкладі!\n\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type.upper()}):\n"
        f"{time_txt} — {subject}{f' ({room})' if room else ''}"
    )

    # если Захист України — сразу два линка
    if subj_norm == "захист україни":
        change_text += (
            f"\n🔗 Meet (Сапко): {DEFENCE_SAPKO_URL}"
            f"\n🔗 Meet (Киящук): {DEFENCE_KYYASHЧУK_URL}"
        )
    elif meet_url:
        change_text += f"\n🔗 Meet: {meet_url}"

    change_text += f"\n\nЗмінено користувачем: {changer}"

    for uid_str in list(users.keys()):
        try:
            uid = int(uid_str)
            bot.send_message(uid, change_text)
        except Exception as e:
            print(f"Не зміг відправити повідомлення про зміну {uid}: {e}")


@bot.message_handler(commands=["who"])
def who_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    if not users:
        bot.reply_to(message, "Поки що ніхто не писав боту 😅")
        return

    lines = []
    # сортируем по last_seen (новые сверху)
    def sort_key(item):
        return item[1].get("last_seen", "")

    for uid, info in sorted(users.items(), key=sort_key, reverse=True):
        uname = info.get("username") or ""
        name = info.get("first_name") or ""
        last_seen = info.get("last_seen", "")
        line = f"{uid} "
        if uname:
            line += f"@{uname} "
        if name:
            line += f"{name} "
        if last_seen:
            line += f"— {last_seen}"
        lines.append(line.strip())

    text = "👥 Користувачі, які писали боту:\n\n" + "\n".join(lines[:50])
    bot.reply_to(message, text)


# ================== ТРЕКИНГ ВСЕХ СООБЩЕНИЙ ==================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def tracking_handler(message):
    # просто запоминаем юзера, НИЧЕГО не отвечаем
    remember_user(message)


# ================== УВЕДОМЛЕНИЯ ЗА 5 МИНУТ ДО ПАРЫ ==================

notified_pairs = set()  # типа "2025-12-04_1"

def send_pair_notification(pair_key, pair_num, pair, day_key):
    # якщо по цій парі стоїть "немає пари" — нічого не шлем
    if is_empty_pair(pair):
        return

    text = "Через ~5 хвилин пара:\n"
    time_txt = get_pair_time(day_key, pair_num) or "час ?"
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    text += f"{pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"

    subj_norm = subj.strip().lower()
    markup = None

    if subj_norm == "захист україни":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=DEFENCE_SAPKO_URL))
        markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=DEFENCE_KYYASHCHUK_URL))
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))

    # рассылаем всем, кто хоть раз писал боту
    for uid_str in list(users.keys()):
        uid = int(uid_str)
        try:
            bot.send_message(uid, text, reply_markup=markup)
        except Exception as e:
            print(f"Не зміг відправити нотіфікацію {uid}: {e}")


def notifications_loop():
    global notified_pairs
    while True:
        try:
            # локальное время: UTC+2 (Україна)
            now = datetime.utcnow() + timedelta(hours=2)
            d = now.date()
            day_key, used_week_type, day_schedule = get_day_struct(d)
            date_key = d.isoformat()

            # очищаем старые уведомления в районе полуночи
            if now.hour == 0 and now.minute < 5:
                notified_pairs = set()

            for pair_str, pair in day_schedule.items():
                try:
                    pair_num = int(pair_str)
                except ValueError:
                    continue

                # якщо тут "немає пари" — пропускаємо і не нагадуємо
                if is_empty_pair(pair):
                    continue

                time_txt = get_pair_time(day_key, pair_num)
                if not time_txt:
                    continue

                start_str = time_txt.split("–")[0]  # "08:30"
                try:
                    hh, mm = map(int, start_str.split(":"))
                except Exception:
                    continue

                pair_dt = datetime(d.year, d.month, d.day, hh, mm)
                delta_sec = (pair_dt - now).total_seconds()

                # окно от 4 до 6 минут до пари
                if 240 <= delta_sec <= 360:
                    key = f"{date_key}_{pair_str}"
                    if key not in notified_pairs:
                        print("Отправляю уведомление для пары", key)
                        send_pair_notification(key, pair_num, pair, day_key)
                        notified_pairs.add(key)

        except Exception as e:
            print("Ошибка в notifications_loop:", e)

        time.sleep(60)


threading.Thread(target=notifications_loop, daemon=True).start()


# ================== СТАРТ БОТА ==================

print("Бот запущен...")
bot.infinity_polling()
