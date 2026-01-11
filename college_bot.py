import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta, datetime
from pathlib import Path
import json
import time
import re
import threading
from flask import Flask
import os

# ====== мини-вебсервер для Render ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()
# =======================================

# ================== НАСТРОЙКИ ==================
TOKEN = "7762300503:AAF17NRUSz6aeUG6Ek8rXMMtuYT3GQ2lPEM"
bot = telebot.TeleBot(TOKEN)

try:
    bot.remove_webhook()
except Exception as e:
    print("Ошибка при удалении webhook:", e)

MAIN_ADMIN_ID = 1509389908
ADMIN_IDS = {1509389908, 1573294591, 5180067949}

# Неделя, которая начинается в ПН 12.01.2026 – это ЧИСЕЛЬНИК
REFERENCE_MONDAY = date(2026, 1, 12)
REFERENCE_WEEK_TYPE = "чисельник"

SCHEDULE_FILE = "schedule.json"
USERS_FILE = "users.json"
ABSENCES_FILE = "absences.json"
CHANGELOG_FILE = "changelog.json"
HOLIDAYS_FILE = "holidays.json"
MEET_LINKS_FILE = "meet_links.json"

# ------------ звонки ------------
BELL_SCHEDULE = {
    "monday": {
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "14:00–15:20",
        5: "15:30–16:50",
    },
    "other": {   # вівторок – п’ятниця
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "13:20–14:40",
        5: "14:50–16:10",
    },
}

DAY_ALIASES = {
    "понеділок": "monday", "понедельник": "monday", "пн": "monday", "пн.": "monday", "пон": "monday", "пон.": "monday", "mon": "monday", "monday": "monday",
    "вівторок": "tuesday", "вторник": "tuesday", "вт": "tuesday", "вт.": "tuesday", "втор": "tuesday", "tue": "tuesday", "tuesday": "tuesday",
    "середа": "wednesday", "середу": "wednesday", "ср": "wednesday", "ср.": "wednesday", "среда": "wednesday", "среду": "wednesday", "wed": "wednesday", "wednesday": "wednesday",
    "четвер": "thursday", "четверг": "thursday", "чт": "thursday", "чт.": "thursday", "чтв": "thursday", "thu": "thursday", "thursday": "thursday",
    "пʼятниця": "friday", "п'ятниця": "friday", "пʼятницю": "friday", "п'ятницю": "friday", "пятница": "friday", "пятницу": "friday", "пт": "friday", "пт.": "friday", "пят": "friday", "fri": "friday", "friday": "friday",
    "субота": "saturday", "суботу": "saturday", "суббота": "saturday", "субботу": "saturday", "сб": "saturday", "сб.": "saturday", "sat": "saturday", "saturday": "saturday",
    "неділя": "sunday", "неділю": "sunday", "воскресенье": "sunday", "неделя": "sunday", "нд": "sunday", "нд.": "sunday", "вс": "sunday", "вс.": "sunday", "вск": "sunday", "sun": "sunday", "sunday": "sunday",
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

NO_LESSON_SUBJECTS = {
    "немає пари", "нема пари", "нет пары", "немає уроку", "нема уроку", 
    "уроку немає", "-", "—", "", " ",
}

# ================== РАСПИСАНИЯ ==================
def create_schedule_bcig():
    return {
        "monday": {
            "чисельник": {
                "1": {"subject": "Фізика і астрономія",  "room": "129", "teacher": "Гуленко І.А."},
                "2": {"subject": "Українська література","room": "115", "teacher": "Лосєва К.С."},
                "3": {"subject": "Історія України",      "room": "114", "teacher": "Мелещук Ю.Л."},
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."},
                "4": {"subject": "Зарубіжна література", "room": "116", "teacher": "Мещерякова О.В."},
                "5": {"subject": "Фізична культура",     "room": "с/з №2","teacher": "Багрін В.С."},
            },
            "знаменник": {
                "1": {"subject": "Фізика і астрономія",  "room": "129", "teacher": "Гуленко І.А."},
                "2": {"subject": "Українська література","room": "115", "teacher": "Лосєва К.С."},
                "3": {"subject": "Всесвітня історія",    "room": "114", "teacher": "Мелещук Ю.Л."},
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."},
                "4": {"subject": "Фізична культура",     "room": "с/з №2","teacher": "Багрін В.С."},
            },
        },
        "tuesday": {
            "чисельник": {
                "2": {"subject": "Математика",      "room": "121", "teacher": "Приймак О.В."},
                "3": {"subject": "Українська мова", "room": "307", "teacher": "Гавриленко С.Т."},
            },
            "знаменник": {
                "2": {"subject": "Математика",      "room": "121", "teacher": "Приймак О.В."},
                "3": {"subject": "Українська мова", "room": "307", "teacher": "Гавриленко С.Т."},
            },
        },
        "wednesday": {
            "чисельник": {
                "1": {"subject": "Технології",          "room": "208", "teacher": "Потапова А.О."},
                "2": {"subject": "Математика",          "room": "121", "teacher": "Приймак О.В."},
                "3": {"subject": "Біологія і екологія", "room": "16",  "teacher": "Золотова К.В."},
                "4": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
            },
            "знаменник": {
                "1": {"subject": "Технології",          "room": "208", "teacher": "Потапова А.О."},
                "2": {"subject": "Математика",          "room": "121", "teacher": "Приймак О.В."},
                "3": {"subject": "Біологія і екологія", "room": "16",  "teacher": "Золотова К.В."},
                "4": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
            },
        },
        "thursday": {
            "чисельник": {
                "1": {"subject": "Історія України",     "room": "114", "teacher": "Мелещук Ю.Л."},
                "2": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "3": {"subject": "Інформатика",         "room": "39",  "teacher": "Короленко / Єреп"},
                "4": {"subject": "Географія",           "room": "123", "teacher": "Баранець Т.О."},
            },
            "знаменник": {
                "1": {"subject": "Історія України",     "room": "114", "teacher": "Мелещук Ю.Л."},
                "2": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "3": {"subject": "Інформатика",         "room": "39",  "teacher": "Короленко / Єреп"},
                "4": {"subject": "Географія",           "room": "123", "teacher": "Баранець Т.О."},
            },
        },
        "friday": {
            "чисельник": {
                "1": {"subject": "Іноземна мова",       "room": "224 a", "teacher": "Криваноченкова Л.І."},
                "2": {"subject": "Хімія",               "room": "16",    "teacher": "Золотова К.В."},
                "3": {"subject": "Фізика і астрономія", "room": "129",   "teacher": "Гуленко І.А."},
                "4": {"subject": "Фізична культура",    "room": "с/з №2", "teacher": "Багрін В.С."},
            },
            "знаменник": {
                "1": {"subject": "Іноземна мова",       "room": "224 a", "teacher": "Криваноченкова Л.І."},
                "2": {"subject": "Хімія",               "room": "16",    "teacher": "Золотова К.В."},
                "3": {"subject": "Фізика і астрономія", "room": "129",   "teacher": "Гуленко І.А."},
                "4": {"subject": "Фізична культура",    "room": "с/з №2", "teacher": "Багрін В.С."},
            },
        },
        "saturday": {},
        "sunday":   {},
    }

def create_schedule_bcis():
    return {
        "monday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Іноземна мова",    "room": "224 а", "teacher": "Криваноченкова Л.І."},
                "3": {"subject": "Математика",       "room": "121",  "teacher": "Приймак О.В."},
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."},
                "4": {"subject": "Випорядник",       "room": "",     "teacher": ""},
            },
            "знаменник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Іноземна мова",    "room": "224 а", "teacher": "Криваноченкова Л.І."},
                "3": {"subject": "Математика",       "room": "121",  "teacher": "Приймак О.В."},
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."},
                "4": {"subject": "Випорядник",       "room": "",     "teacher": ""},
            },
        },
        "tuesday": {
            "чисельник": {
                "1": {"subject": "Біологія і екологія", "room": "16",  "teacher": "Золотова К.В."},
                "2": {"subject": "Історія України",     "room": "114", "teacher": "Меленчук Ю.Д."},
                "3": {"subject": "Всесвітня історія",   "room": "114", "teacher": "Меленчук Ю.Д."},
                "4": {"subject": "Інформатика",         "room": "39",  "teacher": "Короленко / Єреп"},
            },
            "знаменник": {
                "1": {"subject": "Біологія і екологія", "room": "16",  "teacher": "Золотова К.В."},
                "2": {"subject": "Всесвітня історія",   "room": "114", "teacher": "Меленчук Ю.Д."},
                "3": {"subject": "Інформатика",         "room": "39",  "teacher": "Короленко / Єреп"},
            },
        },
        "wednesday": {
            "чисельник": {
                "1": {"subject": "Хімія",               "room": "16",  "teacher": "Золотова К.В."},
                "2": {"subject": "Математика",          "room": "121", "teacher": "Приймак О.В."},
                "3": {"subject": "Технології",          "room": "208", "teacher": "Потапова А.О."},
                "4": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
                "5": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
            },
            "знаменник": {
                "1": {"subject": "Хімія",               "room": "16",  "teacher": "Золотова К.В."},
                "3": {"subject": "Технології",          "room": "208", "teacher": "Потапова А.О."},
                "4": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
                "5": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
            },
        },
        "thursday": {
            "чисельник": {
                "1": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
                "2": {"subject": "Українська мова",     "room": "307", "teacher": "Гавриленко С.Т."},
                "3": {"subject": "Зарубіжна література","room": "116", "teacher": "Менцєрякова О.В."},
            },
            "знаменник": {
                "1": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "2": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
                "3": {"subject": "Українська мова",     "room": "307", "teacher": "Гавриленко С.Т."},
                "4": {"subject": "Зарубіжна література","room": "116", "teacher": "Менцєрякова О.В."},
            },
        },
        "friday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "3": {"subject": "Історія України",     "room": "114", "teacher": "Меленчук Ю.Д."},
                "4": {"subject": "Українська література","room": "115", "teacher": "Лосєва К.С."},
            },
            "знаменник": {
                "1": {"subject": "Географія",         "room": "123", "teacher": "Бараненко Т.О."},
                "2": {"subject": "Історія України",   "room": "114", "teacher": "Меленчук Ю.Д."},
                "3": {"subject": "Українська література","room": "115", "teacher": "Лосєва К.С."},
            },
        },
        "saturday": {},
        "sunday":   {},
    }

# ================== ЗАГРУЗКА / СОХРАНЕНИЕ ДАННЫХ ==================
def load_schedule():
    path = Path(SCHEDULE_FILE)
    if not path.exists():
        return {
            "БЦІГ-25": create_schedule_bcig(),
            "БЦІСТ-25": create_schedule_bcis()
        }
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_schedule(data):
    path = Path(SCHEDULE_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

schedule = load_schedule()

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

def load_absences():
    path = Path(ABSENCES_FILE)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_absences():
    path = Path(ABSENCES_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(absences, f, ensure_ascii=False, indent=2)

absences = load_absences()

def load_changelog():
    path = Path(CHANGELOG_FILE)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_changelog():
    path = Path(CHANGELOG_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(changelog, f, ensure_ascii=False, indent=2)

changelog = load_changelog()

def load_holidays():
    path = Path(HOLIDAYS_FILE)
    if not path.exists():
        return {"is_holiday": False, "holiday_message": "", "school_start_message": ""}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_holidays():
    path = Path(HOLIDAYS_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(holidays, f, ensure_ascii=False, indent=2)

holidays = load_holidays()

def load_meet_links():
    path = Path(MEET_LINKS_FILE)
    if not path.exists():
        return {
            "Фізика і астрономія": "https://meet.google.com/yqs-gkhh-xqm?authuser=0&hs=179 ",
            "Всесвітня історія": "https://meet.google.com/ejg-gvrv-iox?authuser=0&hs=179 ",
            "Історія України": "https://meet.google.com/mpc-znwb-gkq?authuser=0&hs=179 ",
            "Іноземна мова": "https://meet.google.com/xfq-qeab-vis?authuser=0&hs=179 ",
            "Інформатика": "https://meet.google.com/qhx-qkcv-sds?authuser=0&hs=179 ",
            "Математика": "https://meet.google.com/nnn-qzzy-yjf?authuser=0&hs=179 ",
            "Фізична культура": "https://meet.google.com/swm-bpmx-dfb?authuser=0&hs=179 ",
            "Географія": "https://meet.google.com/euh-zuqa-igg?authuser=0&hs=179 ",
            "Організаційна година": "https://meet.google.com/hai-zbrq-pnb?authuser=0&hs=179 ",
            "Зарубіжна література": "https://meet.google.com/hug-ddec-mop?authuser=0&hs=179 ",
            "Українська література": "https://meet.google.com/ogm-ssbj-jzd?authuser=0&hs=179 ",
            "Громадянська освіта": "https://meet.google.com/mzw-uedt-fzf?authuser=0&hs=179 ",
            "Технології": "https://meet.google.com/oap-sefr-fgc?authuser=0&hs=179 ",
            "Українська мова": "https://meet.google.com/wof-fggd-pet?authuser=0&hs=179 ",
            "Захист України": "https://meet.google.com/mev-azeu-tiw?authuser=0&hs=179 ",
            "Хімія": "https://meet.google.com/nup-vusc-tgs?authuser=0&hs=179 ",
            "Біологія і екологія": "https://meet.google.com/dgr-knfu-apt?authuser=0&hs=179 ",
            "Полезна мова": "https://meet.google.com/xfq-qeab-vis?authuser=0&hs=179 ",
            "Захист України Сапко": "https://meet.google.com/mev-azeu-tiw?authuser=0&hs=179 ",
            "Захист України Киящук": "https://meet.google.com/nmf-wxwf-ouv ",
        }
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_meet_links():
    path = Path(MEET_LINKS_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(meet_links, f, ensure_ascii=False, indent=2)

meet_links = load_meet_links()

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def remember_user(message):
    u = message.from_user
    uid = str(u.id)
    info = users.get(uid, {})
    info["id"] = u.id
    info["username"] = u.username or ""
    info["first_name"] = u.first_name or ""
    info["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "group" not in info:
        info["group"] = None
        info["group_chosen"] = False
    users[uid] = info
    save_users()

def is_admin(message):
    return message.from_user.id in ADMIN_IDS

def get_user_group(user_id):
    uid = str(user_id)
    return users.get(uid, {}).get("group")

def get_schedule_for_user(user_id):
    group = get_user_group(user_id)
    if not group:
        return None
    return schedule.get(group)

def get_week_type(target_date=None):
    if target_date is None:
        target_date = date.today()
    delta_days = (target_date - REFERENCE_MONDAY).days
    weeks_passed = delta_days // 7
    if weeks_passed % 2 == 0:
        return REFERENCE_WEEK_TYPE
    else:
        return "знаменник" if REFERENCE_WEEK_TYPE == "чисельник" else "чисельник"

def get_day_key(target_date=None):
    if target_date is None:
        target_date = date.today()
    weekday = target_date.weekday()
    mapping = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}
    return mapping[weekday]

def get_pair_time(day_key, pair_num):
    if day_key == "monday":
        return BELL_SCHEDULE["monday"].get(pair_num)
    else:
        return BELL_SCHEDULE["other"].get(pair_num)

def get_meet_link_for_subject(subj: str):
    if not subj:
        return None
    s = subj.strip().lower()
    for key, url in meet_links.items():
        if key.strip().lower() == s:
            return url
    return None

def is_empty_pair(pair: dict) -> bool:
    subj = (pair.get("subject") or "").strip().lower()
    return subj in NO_LESSON_SUBJECTS

def get_day_struct(d, user_id=None):
    if user_id:
        user_schedule = get_schedule_for_user(user_id)
        if not user_schedule:
            return None, None, None, None
    else:
        user_schedule = schedule.get("БЦІГ-25")
    week_type = get_week_type(d)
    day_key = get_day_key(d)
    day_data = user_schedule.get(day_key, {})
    day_schedule = day_data.get(week_type, {})
    used_week_type = week_type
    if not day_schedule:
        other = "знаменник" if week_type == "чисельник" else "чисельник"
        if day_data.get(other):
            day_schedule = day_data[other]
            used_week_type = f"{week_type} (як у {other})"
    return day_key, used_week_type, day_schedule, user_schedule

def format_day_schedule(d, user_id=None):
    if user_id and not get_user_group(user_id):
        return "⚠️ Ви ще не вибрали групу! Використовуйте /start щоб вибрати групу."
    result = get_day_struct(d, user_id)
    if result[0] is None:
        return "⚠️ Помилка: не знайдено розклад для вашої групи."
    day_key, used_week_type, day_schedule, user_schedule = result
    group = get_user_group(user_id) if user_id else "БЦІГ-25"

    header = f"📚 Група: {group}\n"
    header += f"📅 {DAYS_RU[day_key]}, {d.strftime('%d.%m.%Y')}\n"
    # убираем скобки если совпадает с эталоном
    if used_week_type == REFERENCE_WEEK_TYPE:
        header += f"📋 Тиждень: {used_week_type.upper()}\n\n"
    else:
        header += f"📋 Тиждень: {used_week_type.upper()}\n\n"

    if not day_schedule and not day_schedule.get("org"):
        return header + "Пар немає ✅"

    lines = [header]

    # учебные пары
    for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        if pair_str == "org":
            continue
        pair_num = int(pair_str)
        pair = day_schedule[pair_str]
        if is_empty_pair(pair):
            continue
        time_txt = get_pair_time(day_key, pair_num) or "час ?"
        subj = pair.get("subject", "—")
        room = pair.get("room", "")
        teacher = pair.get("teacher", "")
        line = f"{pair_num}) {time_txt} — {subj}"
        if room:
            line += f" ({room})"
        if teacher:
            line += f" — {teacher}"
        lines.append(line)

    # организационный час
    org = day_schedule.get("org")
    if org:
        lines.append(f"🔸 13:20–13:50 — {org['subject']} ({org['room']}) — {org['teacher']}")

    if len(lines) == 1 + bool(org):
        lines.append("Пар немає ✅")
    return "\n".join(lines)

def build_day_markup(d, user_id=None):
    if not user_id or not get_user_group(user_id):
        return None
    result = get_day_struct(d, user_id)
    if result[0] is None:
        return None
    day_key, used_week_type, day_schedule, user_schedule = result
    markup = InlineKeyboardMarkup(row_width=1)
    has_buttons = False

    for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        if pair_str == "org":
            continue
        pair_num = int(pair_str)
        pair = day_schedule[pair_str]
        subj = pair.get("subject", "—")
        if is_empty_pair(pair):
            continue
        # обработка Захисту України
        if "захист україни" in subj.strip().lower():
            sapko_url = meet_links.get("Захист України Сапко")
            kiyashchuk_url = meet_links.get("Захист України Киящук")
            if sapko_url:
                markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Сапко", url=sapko_url))
                has_buttons = True
            if kiyashchuk_url:
                markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Киящук", url=kiyashchuk_url))
                has_buttons = True
            continue
        url = get_meet_link_for_subject(subj)
        if url:
            markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj}", url=url))
            has_buttons = True
    return markup if has_buttons else None

def format_full_schedule_for_user(user_id):
    user_schedule = get_schedule_for_user(user_id)
    if not user_schedule:
        return "⚠️ Ви ще не вибрали групу!"
    group = get_user_group(user_id)
    lines = [f"📚 Повний розклад для групи: {group}\n"]
    for day_key in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        lines.append(f"\n📅 {DAYS_RU[day_key]}")
        for wt in ["чисельник", "знаменник"]:
            lines.append(f"  🔹 {wt.upper()}:")
            day_data = user_schedule.get(day_key, {})
            day_schedule = day_data.get(wt, {})
            if not day_schedule:
                lines.append("    — немає пар")
            else:
                for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                    if pair_str == "org":
                        continue
                    pair_num = int(pair_str)
                    pair = day_schedule[pair_str]
                    if is_empty_pair(pair):
                        continue
                    time_txt = get_pair_time(day_key, pair_num) or "час ?"
                    room = pair.get("room", "")
                    teacher = pair.get("teacher", "")
                    line = f"    {pair_num}) {time_txt} — {pair.get('subject', '—')}"
                    if room:
                        line += f" ({room})"
                    if teacher:
                        line += f" — {teacher}"
                    lines.append(line)
                # орг-час в конце дня
                org = day_schedule.get("org")
                if org:
                    lines.append(f"    🔸 13:20–13:50 — {org['subject']} ({org['room']}) — {org['teacher']}")
    return "\n".join(lines)

# ================== КОМАНДЫ ДЛЯ ВСЕХ ==================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    remember_user(message)
    uid = str(message.from_user.id)
    user_info = users.get(uid, {})
    if user_info.get("group"):
        text = (
            f"Привіт! Я бот розкладу групи 📚\n"
            f"Ваша група: {user_info['group']}\n\n"
            "Команди:\n"
            "/week – яка зараз тиждень\n"
            "/today – розклад на сьогодні\n"
            "/tomorrow – розклад на завтра\n"
            "/day <день> – розклад на конкретний день\n"
            "/all – повний розклад\n"
            "/bells – розклад дзвінків\n"
            "/now – яка пара йде зараз\n"
            "/next – яка наступна пара\n"
            "/wont – повідомити, що тебе не буде\n"
            "/mygroup – показати мою групу\n"
        )
        if is_admin(message):
            text += "\n👑 Адмін-команди:\n"
            text += "/adminhelp – список адмін-команд\n"
            text += "/setgroup <id> <група> – змінити групу користувачу\n"
        bot.reply_to(message, text)
    else:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("БЦІГ-25", callback_data="choose_group_БЦІГ-25"),
            InlineKeyboardButton("БЦІСТ-25 (включая ТЕ-25)", callback_data="choose_group_БЦІСТ-25")
        )
        bot.reply_to(
            message,
            "Привіт! Я бот розкладу групи 📚\n\n"
            "Оберіть вашу групу (вибрати можна тільки один раз!):",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_group_"))
def choose_group_callback(call):
    group = call.data.split("_")[2]
    uid = str(call.from_user.id)
    if uid in users:
        if not is_admin(call) and users[uid].get("group_chosen", False):
            bot.answer_callback_query(call.id, "Ви вже вибрали групу! Зверніться до адміна для зміни.")
            return
        users[uid]["group"] = group
        users[uid]["group_chosen"] = True
        save_users()
        bot.answer_callback_query(call.id, f"Групу вибрано: {group}")
        bot.edit_message_text(
            f"✅ Ваша група: {group}\n\n"
            "Тепер ви можете використовувати всі команди бота!\n"
            "Напишіть /help для списку команд.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Помилка: спробуйте ще раз /start")

@bot.message_handler(commands=["mygroup"])
def mygroup_cmd(message):
    remember_user(message)
    uid = str(message.from_user.id)
    group = users.get(uid, {}).get("group")
    if group:
        bot.reply_to(message, f"📚 Ваша група: {group}")
    else:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("БЦІГ-25", callback_data="choose_group_БЦІГ-25"),
            InlineKeyboardButton("БЦІСТ-25 (включая ТЕ-25)", callback_data="choose_group_БЦІСТ-25")
        )
        bot.reply_to(
            message,
            "Ви ще не вибрали групу! Оберіть вашу групу (вибрати можна тільки один раз!):",
            reply_markup=markup
        )

@bot.message_handler(commands=["week"])
def week_cmd(message):
    remember_user(message)
    wt = get_week_type()
    bot.reply_to(message, f"Зараз тиждень: *{wt.upper()}*", parse_mode="Markdown")

@bot.message_handler(commands=["today"])
def today_cmd(message):
    remember_user(message)
    if holidays["is_holiday"]:
        bot.reply_to(message, "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️")
        return
    d = date.today()
    text = format_day_schedule(d, message.from_user.id)
    markup = build_day_markup(d, message.from_user.id)
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=["tomorrow"])
def tomorrow_cmd(message):
    remember_user(message)
    if holidays["is_holiday"]:
        bot.reply_to(message, "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️")
        return
    d = date.today() + timedelta(days=1)
    text = format_day_schedule(d, message.from_user.id)
    markup = build_day_markup(d, message.from_user.id)
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
    text = format_day_schedule(target_date, message.from_user.id)
    markup = build_day_markup(target_date, message.from_user.id)
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=["all"])
def all_cmd(message):
    remember_user(message)
    text = format_full_schedule_for_user(message.from_user.id)
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

@bot.message_handler(commands=["now"])
def now_cmd(message):
    remember_user(message)
    if holidays["is_holiday"]:
        bot.reply_to(message, "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️")
        return
    user_schedule = get_schedule_for_user(message.from_user.id)
    if not user_schedule:
        bot.reply_to(message, "⚠️ Ви ще не вибрали групу! Використовуйте /start щоб вибрати групу.")
        return
    now = datetime.utcnow() + timedelta(hours=2)
    d = now.date()
    day_key, used_week_type, day_schedule, _ = get_day_struct(d, message.from_user.id)
    if not day_schedule:
        bot.reply_to(message, "Сьогодні пар немає ✅")
        return
    current_pair = None
    for pair_str, pair in day_schedule.items():
        if pair_str == "org":
            continue
        try:
            pair_num = int(pair_str)
        except ValueError:
            continue
        if is_empty_pair(pair):
            continue
        time_txt = get_pair_time(day_key, pair_num)
        if not time_txt:
            continue
        try:
            start_str, end_str = time_txt.split("–")
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
        except Exception:
            continue
        start_dt = datetime(d.year, d.month, d.day, sh, sm)
        end_dt = datetime(d.year, d.month, d.day, eh, em)
        if start_dt <= now <= end_dt:
            current_pair = (pair_num, pair, time_txt)
            break
    if not current_pair:
        # проверим орг-час
        org = day_schedule.get("org")
        if org:
            start_dt = datetime(d.year, d.month, d.day, 13, 20)
            end_dt = datetime(d.year, d.month, d.day, 13, 50)
            if start_dt <= now <= end_dt:
                text = "Зараз йде організаційна година:\n13:20–13:50 — Організаційна година (205) — Крамаренко Л.О."
                bot.reply_to(message, text)
                return
        bot.reply_to(message, "Зараз пари немає ⏸")
        return
    pair_num, pair, time_txt = current_pair
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    teacher = pair.get("teacher", "")
    text = f"Зараз йде пара:\n{pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"
    subj_norm = subj.strip().lower()
    markup = None
    if "захист україни" in subj_norm:
        markup = InlineKeyboardMarkup(row_width=1)
        sapko_url = meet_links.get("Захист України Сапко")
        kiyashchuk_url = meet_links.get("Захист України Киящук")
        if sapko_url:
            markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=sapko_url))
        if kiyashchuk_url:
            markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=kiyashchuk_url))
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=["next"])
def next_cmd(message):
    remember_user(message)
    if holidays["is_holiday"]:
        bot.reply_to(message, "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️")
        return
    user_schedule = get_schedule_for_user(message.from_user.id)
    if not user_schedule:
        bot.reply_to(message, "⚠️ Ви ще не вибрали групу! Використовуйте /start щоб вибрати групу.")
        return
    now = datetime.utcnow() + timedelta(hours=2)
    d = now.date()
    day_key, used_week_type, day_schedule, _ = get_day_struct(d, message.from_user.id)
    if not day_schedule:
        bot.reply_to(message, "Сьогодні пар немає ✅")
        return
    next_pair = None
    for pair_str, pair in sorted(day_schedule.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        if pair_str == "org":
            continue
        try:
            pair_num = int(pair_str)
        except ValueError:
            continue
        if is_empty_pair(pair):
            continue
        time_txt = get_pair_time(day_key, pair_num)
        if not time_txt:
            continue
        try:
            start_str = time_txt.split("–")[0]
            sh, sm = map(int, start_str.split(":"))
        except Exception:
            continue
        start_dt = datetime(d.year, d.month, d.day, sh, sm)
        if start_dt > now:
            next_pair = (pair_num, pair, time_txt)
            break
    if not next_pair:
        # проверим орг-час
        org = day_schedule.get("org")
        if org:
            start_dt = datetime(d.year, d.month, d.day, 13, 20)
            if start_dt > now:
                text = "Наступна подія: організаційна година\n13:20–13:50 — Організаційна година (205) — Крамаренко Л.О."
                bot.reply_to(message, text)
                return
        bot.reply_to(message, "Сьогодні більше пар немає ✅")
        return
    pair_num, pair, time_txt = next_pair
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    teacher = pair.get("teacher", "")
    text = f"Наступна пара:\n{pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"
    subj_norm = subj.strip().lower()
    markup = None
    if "захист україни" in subj_norm:
        markup = InlineKeyboardMarkup(row_width=1)
        sapko_url = meet_links.get("Захист України Сапко")
        kiyashchuk_url = meet_links.get("Захист України Киящук")
        if sapko_url:
            markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=sapko_url))
        if kiyashchuk_url:
            markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=kiyashchuk_url))
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
    bot.reply_to(message, text, reply_markup=markup)

# ================== /wont (без изменений) ==================
@bot.message_handler(commands=["wont"])
def wont_cmd(message):
    remember_user(message)
    if message.text.strip() == "/wont":
        bot.reply_to(
            message,
            "Як писати /wont:\n"
            "• Спочатку ПІБ (наприклад: Давиташвили Илля)\n"
            "• Потім день: понеділок / понедельник / середу / среду / завтра / сьогодні / сегодня...\n"
            "• Потім пари: 1, 2, 3, 4, 5 (можна '1й', '2 і 3 пару' тощо)\n\n"
            "Приклади:\n"
            "/wont Давиташвили Илля мене не буде в середу на 1й і 4 парі\n"
            "/wont Давиташвили Илля завтра не буду на 2 і 3 парі бо/потому что хворію"
        )
        return
    try:
        _, rest = message.text.split(" ", 1)
    except ValueError:
        bot.reply_to(
            message,
            "Приклад:\n"
            "/wont Давиташвили Илля мене не буде в середу на 1й і 4 парі"
        )
        return
    rest = rest.strip()
    if not rest:
        bot.reply_to(
            message,
            "Приклад:\n"
            "/wont Давиташвили Илля мене не буде в середу на 1й і 4 парі"
        )
        return
    rest_lower = rest.lower()
    u = message.from_user
    # определяем день
    day_key = None
    today_words = {"сьогодні", "сегодня", "today"}
    tomorrow_words = {"завтра", "tomorrow"}
    after_tomorrow_words = {"післязавтра", "послезавтра"}
    today_date = date.today()
    if any(w in rest_lower for w in today_words):
        day_key = get_day_key(today_date)
    elif any(w in rest_lower for w in tomorrow_words):
        day_key = get_day_key(today_date + timedelta(days=1))
    elif any(w in rest_lower for w in after_tomorrow_words):
        day_key = get_day_key(today_date + timedelta(days=2))
    else:
        for raw in rest_lower.split():
            tok_clean = raw.strip(".,:;!?")
            if tok_clean in DAY_ALIASES:
                day_key = DAY_ALIASES[tok_clean]
                break
    if not day_key:
        bot.reply_to(
            message,
            "Я не зрозумів, на який день ти не прийдеш 🤔\n"
            "Додай день у текст: понеділок/понельник, в середу/в пятницу, завтра/сьогодні/сегодня."
        )
        return
    day_name_ua = DAYS_RU.get(day_key, day_key)
    # извлекаем номера пар
    pairs = []
    for m in re.findall(r"\b([1-5])\s*(?:й|я|ша|шу|та|у|ю|-й|-я|-ша|-та)?\b", rest_lower):
        try:
            num = int(m)
            if 1 <= num <= 5:
                pairs.append(num)
        except ValueError:
            continue
    word_to_pair = {
        "перша": 1, "першу": 1, "первая": 1, "первую": 1,
        "друга": 2, "другу": 2, "вторая": 2, "вторую": 2,
        "третя": 3, "третю": 3, "третья": 3, "третью": 3,
        "четверта": 4, "четверту": 4, "четвертая": 4, "четвертую": 4,
        "пʼята": 5, "п'ята": 5, "пятая": 5, "пятую": 5,
    }
    for word, num in word_to_pair.items():
        if word in rest_lower:
            pairs.append(num)
    pairs = list(set(pairs))
    if not pairs:
        bot.reply_to(
            message,
            "Я не бачу номерів пар 😅\n"
            "Напиши, на які саме: наприклад 'на 1й парі і на 4 парі' або '2 і 3 пару'."
        )
        return
    # извлекаем ФИО
    tokens = rest.split()
    tokens_lower = rest.lower().split()
    stopwords = {"меня", "мене", "мне", "мені", "я", "не", "у", "в"}
    relative_days = {"сьогодні", "сегодня", "today", "завтра", "tomorrow", "післязавтра", "послезавтра"}
    fio_end_idx = len(tokens)
    for i, tok in enumerate(tokens_lower):
        tt = tok.strip(".,:;!?")
        if tt in DAY_ALIASES or tt in relative_days or tt in stopwords:
            fio_end_idx = i
            break
    fio_tokens = tokens[:fio_end_idx]
    fio = " ".join(fio_tokens).strip(" ,.-—")
    if not fio:
        if u.first_name:
            fio = u.first_name
        elif u.username:
            fio = f"@{u.username}"
        else:
            fio = f"id {u.id}"
    # причина
    reason_markers = ["бо ", "бо,", "потому что", "потому, что", "потому ", "из-за", "через ", "because"]
    reason_idx = -1
    tail = rest[len(fio):].lstrip(" ,.-—")
    tail_lower = tail.lower()
    for kw in reason_markers:
        idx = tail_lower.find(kw)
        if idx != -1:
            reason_idx = idx
            break
    if reason_idx != -1:
        reason = tail[reason_idx:].strip()
    else:
        reason = tail.strip()
    if not reason:
        reason = "—"
    # сохраняем
    now_str = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    pairs_str = ", ".join(str(p) for p in sorted(pairs))
    for pair_num in pairs:
        record = {
            "name": fio,
            "pair_num": pair_num,
            "day_key": day_key,
            "reason": reason,
            "sender_id": u.id,
            "sender_username": u.username or "",
            "sender_first_name": u.first_name or "",
            "created_at": now_str,
        }
        absences.append(record)
    save_absences()
    # отправляем админу
    admin_text = (
        "📢 Повідомлення про відсутність студента\n\n"
        f"👤 Студент (ПІБ): {fio}\n"
        f"📅 День: {day_name_ua}\n"
        f"🔢 Пари: {pairs_str}\n"
        f"📝 Причина: {reason}\n\n"
        f"Відправник: @{u.username if u.username else u.first_name}\n"
        f"Час (UTC+2): {now_str}"
    )
    try:
        bot.send_message(MAIN_ADMIN_ID, admin_text)
    except Exception as e:
        print(f"Не зміг відправити /wont адмінину: {e}")
    bot.reply_to(
        message,
        "Ок, я передав інформацію, що тебе не буде на парі(ях) ✅"
    )

# ================== КОМАНДЫ КАНИКУЛЫ ==================
@bot.message_handler(commands=["holiday"])
def holiday_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Напиши текст объявления каникул.\nПример: /holiday С 25 декабря по 10 января - зимние каникулы! 🎄❄️")
        return
    announcement = parts[1].strip()
    holidays["is_holiday"] = True
    holidays["holiday_message"] = announcement
    holidays["holiday_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    holidays["announcer_id"] = message.from_user.id
    holidays["announcer_name"] = message.from_user.first_name or message.from_user.username or "Админ"
    save_holidays()
    broadcast_text = (
        "🎉🎉🎉 ВАЖНОЕ ОБЪЯВЛЕНИЕ 🎉🎉🎉\n\n"
        f"📢 {announcement}\n\n"
        "✅ Автонапоминания о парах отключены.\n"
        "⏸️ Команды /now, /next, /today, /tomorrow будут показывать, что сейчас каникулы.\n\n"
        "Хорошо отдохнуть! 🏖️✨"
    )
    bot.reply_to(message, f"✅ Каникулы объявлены! Сообщение отправлено {len(users)} пользователям.")
    successful = 0
    failed = 0
    for uid_str in list(users.keys()):
        try:
            uid = int(uid_str)
            bot.send_message(uid, broadcast_text)
            successful += 1
        except Exception as e:
            print(f"Не смог отправить сообщение о каникулах пользователю {uid_str}: {e}")
            failed += 1
    bot.send_message(
        message.from_user.id,
        f"📊 Статистика рассылки:\n✅ Успешно: {successful}\n❌ Не удалось: {failed}\nВсего пользователей: {len(users)}"
    )

@bot.message_handler(commands=["school_start"])
def school_start_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Напиши текст объявления начала учебы.\nПример: /school_start С 11 января начинаем учебу! 📚✨")
        return
    announcement = parts[1].strip()
    holidays["is_holiday"] = False
    holidays["school_start_message"] = announcement
    holidays["school_start_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    holidays["announcer_id"] = message.from_user.id
    holidays["announcer_name"] = message.from_user.first_name or message.from_user.username or "Админ"
    save_holidays()
    broadcast_text = (
        "📚📚📚 ВАЖНОЕ ОБЪЯВЛЕНИЕ 📚📚📚\n\n"
        f"📢 {announcement}\n\n"
        "✅ Автонапоминания о парах включены.\n"
        "🚀 Готовьтесь к учебе!\n\n"
        "Удачи в новом учебном периоде! 💪✨"
    )
    bot.reply_to(message, f"✅ Начало учебы объявлено! Сообщение отправлено {len(users)} пользователям.")
    successful = 0
    failed = 0
    for uid_str in list(users.keys()):
        try:
            uid = int(uid_str)
            bot.send_message(uid, broadcast_text)
            successful += 1
        except Exception as e:
            print(f"Не смог отправить сообщение о начале учебы пользователю {uid_str}: {e}")
            failed += 1
    bot.send_message(
        message.from_user.id,
        f"📊 Статистика рассылки:\n✅ Успешно: {successful}\n❌ Не удалось: {failed}\nВсего пользователей: {len(users)}"
    )

@bot.message_handler(commands=["holiday_status"])
def holiday_status_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    if holidays["is_holiday"]:
        status = "🎉 КАНИКУЛЫ"
        message_text = holidays.get("holiday_message", "Каникулы объявлены")
        announce_date = holidays.get("holiday_date", "Неизвестно")
        announcer = holidays.get("announcer_name", "Неизвестно")
    else:
        status = "📚 УЧЕБА"
        message_text = holidays.get("school_start_message", "Учеба идет")
        announce_date = holidays.get("school_start_date", "Неизвестно")
        announcer = holidays.get("announcer_name", "Неизвестно")
    response = (
        f"📊 Статус каникул:\n\n"
        f"🔸 Статус: {status}\n"
        f"🔸 Сообщение: {message_text}\n"
        f"🔸 Дата объявления: {announce_date}\n"
        f"🔸 Объявил: {announcer}\n\n"
        f"Команды:\n"
        f"/holiday <текст> - объявить каникулы\n"
        f"/school_start <текст> - объявить начало учебы"
    )
    bot.reply_to(message, response)

# ================== АДМИН-КОМАНДЫ ==================
@bot.message_handler(commands=["adminhelp"])
def admin_help(message):
    remember_user(message)
    if not is_admin(message):
        return
    text = (
        "👑 Адмін-команди:\n\n"
        "/setpair <група> <день> <номер> <тиждень> <предмет> ; <аудиторія> ; <викладач>\n"
        "/setlink <предмет> <посилання> – додати/змінити Meet-посилання\n"
        "/links – список усіх посилань\n"
        "/who – список користувачів\n"
        "/stats <week|month> – статистика /wont\n"
        "/absent – хто сьогодні відсутній\n"
        "/changelog – останні зміни розкладу\n"
        "/whois <@username|id> – інфа по користувачу\n"
        "/setgroup <id> <група> – змінити групу користувачу\n"
        "/holiday <текст> – оголосити канікули\n"
        "/school_start <текст> – оголосити початок навчання\n"
        "/holiday_status – статус канікул\n\n"
        "Приклади:\n"
        "/setpair БЦІГ-25 понеділок 1 чисельник Фізика ; 129 ; Гуденко І.А.\n"
        "/setlink Математика https://meet.google.com/xxx \n"
        "/setgroup 123456789 БЦІСТ-25"
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
        bot.reply_to(message, 
            "Формат: /setpair <група> <день> <номер> <тиждень> <предмет> ; <аудиторія> ; <викладач>\n"
            "Пример: /setpair БЦІГ-25 понеділок 1 чисельник Фізика ; 129 ; Гуденко І.А."
        )
        return
    parts = rest.split(maxsplit=5)
    if len(parts) < 6:
        bot.reply_to(message, "Недостатньо параметрів")
        return
    group_name, day_raw, pair_str, week_raw, subject_rest = parts[0], parts[1], parts[2], parts[3], parts[4]
    if group_name not in schedule:
        bot.reply_to(message, f"Група {group_name} не знайдена. Доступні групи: {', '.join(schedule.keys())}")
        return
    day_key = DAY_ALIASES.get(day_raw.lower())
    if not day_key:
        bot.reply_to(message, "Невірний день")
        return
    try:
        pair_num = int(pair_str)
        if pair_num < 1 or pair_num > 6:
            bot.reply_to(message, "Номер пари повинен бути від 1 до 6")
            return
    except ValueError:
        bot.reply_to(message, "Номер пари має бути числом")
        return
    w_raw = week_raw.lower()
    if w_raw.startswith("чис"):
        week_type = "чисельник"
    elif w_raw.startswith("зн"):
        week_type = "знаменник"
    else:
        bot.reply_to(message, "Невірний тип тижня")
        return
    if ";" in subject_rest:
        parts2 = subject_rest.split(";", 2)
        subject = parts2[0].strip()
        room = parts2[1].strip() if len(parts2) > 1 else ""
        teacher = parts2[2].strip() if len(parts2) > 2 else ""
    else:
        subject = subject_rest.strip()
        room = ""
        teacher = ""
    schedule[group_name].setdefault(day_key, {}).setdefault(week_type, {})
    schedule[group_name][day_key][week_type][str(pair_num)] = {
        "subject": subject,
        "room": room,
        "teacher": teacher
    }
    save_schedule(schedule)
    now_local = datetime.utcnow() + timedelta(hours=2)
    record = {
        "timestamp": now_local.strftime("%Y-%m-%d %H:%M:%S"),
        "group": group_name,
        "day_key": day_key,
        "pair_num": pair_num,
        "week_type": week_type,
        "subject": subject,
        "room": room,
        "teacher": teacher,
        "admin_id": message.from_user.id,
        "admin_username": message.from_user.username or "",
        "admin_first_name": message.from_user.first_name or "",
    }
    changelog.append(record)
    save_changelog()
    time_txt = get_pair_time(day_key, pair_num) or "час ?"
    bot.reply_to(
        message,
        f"✅ Оновлено розклад для групи {group_name}:\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type})\n"
        f"{time_txt} — {subject} {f'({room})' if room else ''} {f'— {teacher}' if teacher else ''}"
    )

@bot.message_handler(commands=["setlink"])
def setlink_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, 
            "Формат: /setlink <предмет> <посилання>\n"
            "Пример: /setlink Математика https://meet.google.com/xxx \n"
            "Или: /setlink 'Захист України Сапко' https://meet.google.com/xxx "
        )
        return
    subject = parts[1]
    link = parts[2]
    meet_links[subject] = link
    save_meet_links()
    bot.reply_to(message, f"✅ Посилання для '{subject}' встановлено:\n{link}")

@bot.message_handler(commands=["links"])
def links_cmd(message):
    remember_user(messageПродолжение (хвост файла) – тот же код, но обрезанный из-за лимита длины.  
Ниже то, что не поместилось выше (вставляйте в конец файла):

```python
    remember_user(message)
    if not is_admin(message):
        return
    text = "📎 Збережені посилання:\n\n"
    for subject, link in meet_links.items():
        text += f"• {subject}: {link}\n"
    bot.reply_to(message, text[:4000])

@bot.message_handler(commands=["setgroup"])
def setgroup_admin_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Формат: /setgroup <id> <група>\nПример: /setgroup 123456789 БЦІСТ-25")
        return
    user_id = parts[1]
    group = parts[2]
    if group not in schedule:
        bot.reply_to(message, f"Невірна група. Доступні: {', '.join(schedule.keys())}")
        return
    found = False
    for uid, info in users.items():
        if uid == user_id or (info.get("username", "").lower() == user_id.lower().lstrip("@")) or str(info.get("id")) == user_id:
            users[uid]["group"] = group
            users[uid]["group_chosen"] = True
            save_users()
            name = info.get("first_name", "Невідомий")
            bot.reply_to(message, f"✅ Групу для {name} (ID: {uid}) змінено на {group}")
            found = True
            break
    if not found:
        bot.reply_to(message, f"Користувача з ID/username '{user_id}' не знайдено")

@bot.message_handler(commands=["who"])
def who_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    if not users:
        bot.reply_to(message, "Поки що ніхто не писав боту 😅")
        return
    lines = ["👥 Користувачі, які писали боту:\n"]
    for uid, info in sorted(users.items(), key=lambda x: x[1].get("last_seen", ""), reverse=True):
        uname = info.get("username") or ""
        name = info.get("first_name") or ""
        group = info.get("group") or "Не вибрана"
        last_seen = info.get("last_seen", "")
        line = f"ID: {uid} | Група: {group}"
        if uname:
            line += f" | @{uname}"
        if name:
            line += f" | {name}"
        if last_seen:
            line += f" | Останній: {last_seen}"
        lines.append(line)
    text = "\n".join(lines[:50])
    bot.reply_to(message, text)

@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.reply_to(message, "Формат: /stats week або /stats month")
        return
    arg = parts[1].strip().lower()
    if arg in ("week", "тиждень", "w"):
        days_back = 7
        title = "за останній тиждень"
    elif arg in ("month", "місяць", "m"):
        days_back = 30
        title = "за останній місяць"
    else:
        bot.reply_to(message, "Невідомий період. Використовуй: week або month.")
        return
    now = datetime.utcnow() + timedelta(hours=2)
    threshold = now - timedelta(days=days_back)
    stats = {}
    for rec in absences:
        try:
            dt = datetime.strptime(rec.get("created_at", ""), "%Y-%m-%d %H:%M:%S")
        except:
            continue
        if dt < threshold:
            continue
        name = rec.get("name", "???")
        stats.setdefault(name, []).append((dt, rec))
    if not stats:
        bot.reply_to(message, f"Немає даних по /wont {title}.")
        return
    lines = [f"📊 Статистика /wont {title}:\n"]
    sorted_items = sorted(stats.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (name, recs) in enumerate(sorted_items, start=1):
        total = len(recs)
        lines.append(f"{i}) {name} — {total} раз(и)")
        for dt, rec in sorted(recs, key=lambda x: x[0], reverse=True)[:3]:
            date_str = dt.strftime("%Y-%m-%d")
            day_key = rec.get("day_key", "")
            day_name = DAYS_RU.get(day_key, day_key)
            pair_num = rec.get("pair_num", "?")
            reason = rec.get("reason", "—")
            lines.append(f"   • {date_str}, {day_name}, пара: {pair_num} — {reason[:50]}...")
        lines.append("")
    text = "\n".join(lines).strip()
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i + 4000])
    else:
        bot.reply_to(message, text)

@bot.message_handler(commands=["absent"])
def absent_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    if not absences:
        bot.reply_to(message, "Поки що ніхто не відмічав відсутність через /wont.")
        return
    today_key = get_day_key(date.today())
    today_name = DAYS_RU[today_key]
    now = datetime.utcnow() + timedelta(hours=2)
    threshold = now - timedelta(days=14)
    todays = []
    for rec in absences:
        if rec.get("day_key") != today_key:
            continue
        try:
            dt = datetime.strptime(rec.get("created_at", ""), "%Y-%m-%d %H:%M:%S")
        except:
            continue
        if dt < threshold:
            continue
        todays.append(rec)
    if not todays:
        bot.reply_to(message, f"Сьогодні ({today_name}) відміток про відсутність немає ✅")
        return
    lines = [f"🚷 Відсутні сьогодні ({today_name}):\n"]
    for rec in todays:
        name = rec.get("name", "???")
        pair_num = rec.get("pair_num", "?")
        reason = rec.get("reason", "—")
        lines.append(f"• {name} — {pair_num} пара — {reason}")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["changelog"])
def changelog_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    if not changelog:
        bot.reply_to(message, "Поки що змін розкладу не було.")
        return
    parts = message.text.split(maxsplit=1)
    try:
        limit = int(parts[1]) if len(parts) > 1 else 10
    except Exception:
        limit = 10
    items = changelog[-limit:]
    lines = ["📜 Останні зміни розкладу:\n"]
    for rec in reversed(items):
        ts = rec.get("timestamp", "")
        group = rec.get("group", "")
        day_key = rec.get("day_key", "")
        day_name = DAYS_RU.get(day_key, day_key)
        pair_num = rec.get("pair_num", "?")
        week_type = rec.get("week_type", "")
        subj = rec.get("subject", "—")
        room = rec.get("room", "")
        teacher = rec.get("teacher", "")
        admin_name = rec.get("admin_first_name") or ""
        admin_username = rec.get("admin_username") or ""
        who = admin_name
        if admin_username:
            who += f" (@{admin_username})"
        line = f"{ts} — {group}, {day_name}, пара {pair_num} ({week_type}): {subj}"
        if room:
            line += f" ({room})"
        if teacher:
            line += f" — {teacher}"
        line += f". Змінив: {who}"
        lines.append(line)
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["whois"])
def whois_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.reply_to(message, "Формат: /whois @username або /whois id")
        return
    query = parts[1].strip()
    if query.startswith("@"):
        query = query[1:]
    found_ids = set()
    for uid, info in users.items():
        uname = (info.get("username") or "").lower()
        if uname and uname == query.lower():
            found_ids.add(uid)
        elif uid == query:
            found_ids.add(uid)
        elif str(info.get("id")) == query:
            found_ids.add(uid)
    if not found_ids:
        bot.reply_to(message, "Не знайшов такого користувача серед тих, хто писав боту.")
        return
    lines = []
    for uid in found_ids:
        info = users.get(uid, {})
        uname = info.get("username") or ""
        name = info.get("first_name") or ""
        group = info.get("group") or "Не вибрана"
        last_seen = info.get("last_seen", "")
        user_id_int = int(uid)
        user_abs = [r for r in absences if r.get("sender_id") == user_id_int]
        total_wont = len(user_abs)
        lines.append("🕵️ Інформація про користувача:")
        lines.append(f"ID: {uid}")
        if uname:
            lines.append(f"Username: @{uname}")
        if name:
            lines.append(f"Ім'я: {name}")
        lines.append(f"Група: {group}")
        if last_seen:
            lines.append(f"Останній онлайн: {last_seen}")
        lines.append(f"Всього /wont: {total_wont}")
        if user_abs:
            user_abs_sorted = sorted(
                user_abs,
                key=lambda r: datetime.strptime(r.get("created_at", "2000-01-01"), "%Y-%m-%d %H:%M:%S")
            )
            last_rec = user_abs_sorted[-1]
            dt = datetime.strptime(last_rec.get("created_at", ""), "%Y-%m-%d %H:%M:%S")
            dt_str = dt.strftime("%Y-%m-%d %H:%M") if dt else last_rec.get("created_at", "")
            day_key = last_rec.get("day_key", "")
            day_name = DAYS_RU.get(day_key, day_key)
            pair_num = last_rec.get("pair_num", "?")
            reason = last_rec.get("reason", "—")
            lines.append(
                f"Останній /wont: {dt_str}, {day_name}, пара {pair_num}, причина: {reason}"
            )
        lines.append("")
    bot.reply_to(message, "\n".join(lines))

# ================== УВЕДОМЛЕНИЯ ЗА 5 МИНУТ ДО ПАРЫ ==================
notified_pairs = set()

def send_pair_notification(pair_key, pair_num, pair, day_key, user_id):
    if is_empty_pair(pair):
        return
    if holidays["is_holiday"]:
        return
    text = "Через ~5 хвилин пара:\n"
    time_txt = get_pair_time(day_key, pair_num) or "час ?"
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    teacher = pair.get("teacher", "")
    text += f"{pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"
    subj_norm = subj.strip().lower()
    markup = None
    if "захист україни" in subj_norm:
        markup = InlineKeyboardMarkup(row_width=1)
        sapko_url = meet_links.get("Захист України Сапко")
        kiyashchuk_url = meet_links.get("Захист України Киящук")
        if sapko_url:
            markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Сапко", url=sapko_url))
        if kiyashchuk_url:
            markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Киящук", url=kiyashchuk_url))
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
    # отправляем только тем, у кого выбрана группа
    for uid_str, user_info in users.items():
        if user_info.get("group") != get_user_group(user_id):
            continue
        uid = int(uid_str)
        try:
            bot.send_message(uid, text, reply_markup=markup)
        except Exception as e:
            print(f"Не зміг відправити нотіфікацію {uid}: {e}")

def notifications_loop():
    global notified_pairs
    while True:
        try:
            if holidays["is_holiday"]:
                time.sleep(60)
                continue
            now = datetime.utcnow() + timedelta(hours=2)
            d = now.date()
            date_key = d.isoformat()
            if now.hour == 0 and now.minute < 5:
                notified_pairs.clear()
            # для каждой группы
            for group_name, group_schedule in schedule.items():
                day_key = get_day_key(d)
                week_type = get_week_type(d)
                day_data = group_schedule.get(day_key, {})
                day_schedule = day_data.get(week_type, {})
                if not day_schedule:
                    continue
                for pair_str, pair in day_schedule.items():
                    if pair_str == "org":
                        continue
                    try:
                        pair_num = int(pair_str)
                    except ValueError:
                        continue
                    if is_empty_pair(pair):
                        continue
                    time_txt = get_pair_time(day_key, pair_num)
                    if not time_txt:
                        continue
                    start_str = time_txt.split("–")[0]
                    try:
                        hh, mm = map(int, start_str.split(":"))
                    except Exception:
                        continue
                    pair_dt = datetime(d.year, d.month, d.day, hh, mm)
                    delta_sec = (pair_dt - now).total_seconds()
                    if 240 <= delta_sec <= 360:
                        key = f"{date_key}_{group_name}_{pair_str}"
                        if key not in notified_pairs:
                            print(f"Отправляю уведомление для пары {key}")
                            for uid_str, user_info in users.items():
                                if user_info.get("group") == group_name:
                                    send_pair_notification(key, pair_num, pair, day_key, int(uid_str))
                            notified_pairs.add(key)
        except Exception as e:
            print("Ошибка в notifications_loop:", e)
        time.sleep(60)

threading.Thread(target=notifications_loop, daemon=True).start()

# ================== СТАРТ БОТА ==================
print("Бот запущен...")
if holidays["is_holiday"]:
    print("⚠️ Сейчас КАНИКУЛЫ! Автоуведомления отключены.")
else:
    print("📚 Учеба в процессе. Автоуведомления включены.")

bot.infinity_polling()
