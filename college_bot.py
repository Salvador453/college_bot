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
import requests

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
TOKEN = "8314863940:AAHqD0SRXnzAWj6DOdSUKiWHqiC7A-gyMiw"
bot = telebot.TeleBot(TOKEN)

# ================== НАСТРОЙКИ ПОВІТРЯНОЇ ТРИВОГИ ==================
# API ключ повітряних тривог (api.ukrainealarm.com)
AIRALARM_API_KEY = "14d49bd6:19c6d5a643e2fddfb2a473e9c4c08ccd"
# ID міста Запоріжжя (саме міста, не області)
AIRALARM_CITY_ID = 564
# ID телеграм-групи, куди надсилати сповіщення
ALERT_GROUP_CHAT_ID = -1003088722284

# Базовий URL API UkraineAlarm
AIRALARM_API_BASE = "https://api.ukrainealarm.com"

# поточний стан тривоги для міста (щоб не дублювати повідомлення)
airalarm_city_active = False
airalarm_last_check = None
airalarm_last_error = None

def fetch_airalarm_city_status():
    """
    Повертає (active: bool, raw: dict|list|str|None).
    Використовує endpoint /api/v3/alerts/{regionId}, де regionId може бути ID міста.
    """
    headers = {
        # За офіційною схемою авторизації: API key в HTTP header "Authorization"
        "Authorization": AIRALARM_API_KEY,
    }
    url = f"{AIRALARM_API_BASE}/api/v3/alerts/{AIRALARM_CITY_ID}"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    raw = resp.json()

    # Типові поля, які зустрічаються в різних клієнтах/моделях
    # - isAlarm / alarm / active
    # - status: "Alarm" | "NoAlarm" тощо
    active = False
    if isinstance(raw, dict):
        if raw.get("isAlarm") is True or raw.get("alarm") is True or raw.get("active") is True:
            active = True
        status = (raw.get("status") or raw.get("alarmStatus") or raw.get("state") or "").lower()
        if status in {"alarm", "air", "airalarm", "active", "on", "true"}:
            active = True
    elif isinstance(raw, list):
        # На випадок, якщо API раптом повертає масив подій/модифікацій
        active = len(raw) > 0
    return active, raw

try:
    bot.remove_webhook()
except Exception as e:
    print("Ошибка при удалении webhook:", e)

MAIN_ADMIN_ID = 1509389908
ADMIN_IDS = {1509389908, 1573294591, 5180067949}

REFERENCE_MONDAY = date(2026, 1, 12)
REFERENCE_WEEK_TYPE = "чисельник"

SCHEDULE_FILE = "schedule.json"
TEMP_CHANGES_FILE = "temp_changes.json"  # Новый файл для временных изменений
USERS_FILE = "users.json"
ABSENCES_FILE = "absences.json"
CHANGELOG_FILE = "changelog.json"
HOLIDAYS_FILE = "holidays.json"
MEET_LINKS_BCIG_FILE = "meet_links_bcig.json"
MEET_LINKS_BCIST_FILE = "meet_links_bcist.json"

# Расклад дзвінків
BELL_SCHEDULE = {
    "monday": {
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        # 4-я пара убрана – org отдельно
        4: "14:00–15:20",
        5: "15:30–16:50",
    },
    "other": {
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
    "уроку немає", "-", "", " ",
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
            },
            "знаменник": {
                "1": {"subject": "Фізика і астрономія",  "room": "129", "teacher": "Гуленко І.А."},
                "2": {"subject": "Українська література","room": "115", "teacher": "Лосєва К.С."},
                "3": {"subject": "Всесвітня історія",    "room": "114", "teacher": "Мелещук Ю.Л."},
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."},
            },
        },
        "tuesday": {
            "чисельник": {
                "2": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Багрін В.С."},
                "3": {"subject": "Математика",       "room": "121",  "teacher": "Приймак О.В."},
                "4": {"subject": "Українська мова",  "room": "307",  "teacher": "Гавриленко С.Т."},
            },
            "знаменник": {
                "2": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Багрін В.С."},
                "3": {"subject": "Математика",       "room": "121",  "teacher": "Приймак О.В."},
                "4": {"subject": "Українська мова",  "room": "307",  "teacher": "Гавриленко С.Т."},
            },
        },
        "wednesday": {
            "чисельник": {
                "2": {"subject": "Технології",          "room": "208", "teacher": "Потапова А.О."},
                "3": {"subject": "Біологія і екологія", "room": "16",  "teacher": "Золотова К.В."},
                "4": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
            },
            "знаменник": {
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
                "2": {"subject": "Іноземна мова",       "room": "224 a", "teacher": "Криваноченкова Л.І."},
                "3": {"subject": "Хімія",               "room": "16",    "teacher": "Золотова К.В."},
                "4": {"subject": "Фізика і астрономія", "room": "129",   "teacher": "Гуленко І.А."},
            },
            "знаменник": {
                "2": {"subject": "Іноземна мова",       "room": "224 a", "teacher": "Криваноченкова Л.І."},
                "3": {"subject": "Хімія",               "room": "16",    "teacher": "Золотова К.В."},
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
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."}
            },
            "знаменник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Іноземна мова",    "room": "224 а", "teacher": "Криваноченкова Л.І."},
                "3": {"subject": "Математика",       "room": "121",  "teacher": "Приймак О.В."},
                "org": {"subject": "Організаційна година","room": "205", "teacher": "Крамаренко Л.О."},
            },
        },
        "tuesday": {
            "чисельник": {
                "1": {"subject": "Біологія і екологія", "room": "16",  "teacher": "Золотова К.В."},
                "2": {"subject": "Історія України",     "room": "114", "teacher": "Меленчук Ю.Д."},
                "3": {"subject": "Інформатика",         "room": "39",  "teacher": "Короленко / Єреп"},
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
                "3": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
            },
            "знаменник": {
                "1": {"subject": "Хімія",               "room": "16",  "teacher": "Золотова К.В."},
                "2": {"subject": "Технології",          "room": "208", "teacher": "Потапова А.О."},
                "3": {"subject": "Захист України",      "room": "242 / 201", "teacher": "Санко / Киянчук"},
                "4": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
            },
        },
        "thursday": {
            "чисельник": {
                "1": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "2": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
                "3": {"subject": "Українська мова",     "room": "307", "teacher": "Гавриленко С.Т."},
                "4": {"subject": "Зарубіжна література","room": "116", "teacher": "Менцєрякова О.В."},
            },
            "знаменник": {
                "1": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "2": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуленко І.А."},
                "3": {"subject": "Українська мова",     "room": "307", "teacher": "Гавриленко С.Т."},
            },
        },
        "friday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Історія України",   "room": "114", "teacher": "Меленчук Ю.Д."},
                "3": {"subject": "Українська література","room": "115", "teacher": "Лосєва К.С."},
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

def load_temp_changes():
    """Загружает временные изменения"""
    path = Path(TEMP_CHANGES_FILE)
    if not path.exists():
        return {"БЦІГ-25": {}, "БЦІСТ-25": {}}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        if "БЦІГ-25" not in data:
            data["БЦІГ-25"] = {}
        if "БЦІСТ-25" not in data:
            data["БЦІСТ-25"] = {}
        return data

def save_temp_changes():
    """Сохраняет временные изменения"""
    path = Path(TEMP_CHANGES_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(temp_changes, f, ensure_ascii=False, indent=2)

schedule = load_schedule()
temp_changes = load_temp_changes()

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
    path_bcig = Path(MEET_LINKS_BCIG_FILE)
    if not path_bcig.exists():
        bcig_links = {
            "Організаційна година": "https://meet.google.com/hai-zbrq-pnb ",
            "Громадянська освіта": "https://meet.google.com/tih-uuai-bdj ",
            "Українська мова": "https://meet.google.com/dtg-huzd-rvb ",
            "Українська література": "https://meet.google.com/vsg-xppe-vxk ",
            "Зарубіжна література": "https://meet.google.com/jpc-amxg-yuj ",
            "Іноземна мова": "https://meet.google.com/pow-yoee-vxr ",
            "Історія України": "https://meet.google.com/mpc-znwb-gkq ",
            "Всесвітня історія": "https://meet.google.com/ejg-gvrv-iox ",
            "Математика": "https://meet.google.com/nph-xdxh-xrd ",
            "Біологія і екологія": "https://meet.google.com/vic-bqov-kmc ",
            "Географія": "https://meet.google.com/udz-tpss-ckd ",
            "Фізика і астрономія": "https://meet.google.com/erm-mumv-dyo ",
            "Хімія": "https://meet.google.com/pqg-djpj-qmr ",
            "Захист України Сапко": "https://meet.google.com/mev-azeu-tiw ",
            "Захист України Киящук": "https://meet.google.com/nrn-zapd-zfx ",
            "Фізична культура": "https://meet.google.com/uod-dtnv-gwm ",
            "Інформатика": "https://meet.google.com/rfc-txdu-edx ",
            "Технології": "https://meet.google.com/pcw-ryik-bms "
        }
        with path_bcig.open("w", encoding="utf-8") as f:
            json.dump(bcig_links, f, ensure_ascii=False, indent=2)
    else:
        with path_bcig.open("r", encoding="utf-8") as f:
            bcig_links = json.load(f)

    path_bcist = Path(MEET_LINKS_BCIST_FILE)
    if not path_bcist.exists():
        bcist_links = {
            "Фізична культура": "https://meet.google.com/swm-bpmx-dfb ",
            "Іноземна мова": "https://meet.google.com/fjb-fjbh-ytu ",
            "Математика": "https://meet.google.com/nnn-qzzy-yjf ",
            "Організаційна година": "https://meet.google.com/hai-zbrq-pnb ",
            "Біологія і екологія": "https://meet.google.com/dgr-knfu-apt ",
            "Технології": "https://meet.google.com/bjy-dedr-got ",
            "Захист України Сапко": "https://meet.google.com/gsp-zxhg-gme ",
            "Захист України Киящук": "https://meet.google.com/nmf-wxwf-ouv ",
            "Фізика і астрономія": "https://meet.google.com/yqs-gkhh-xqm ",
            "Громадянська освіта": "https://meet.google.com/zng-jhhs-cst ",
            "Українська мова": "https://meet.google.com/sit-dnty-uhm ",
            "Зарубіжна література": "https://meet.google.com/auz-vzwn-eag ",
            "Географія": "https://meet.google.com/euh-zuqa-igg ",
            "Історія України": "https://meet.google.com/qun-pysg-yqg ",
            "Всесвітня історія": "https://meet.google.com/wmx-zvqd-akp ",
            "Українська література": "https://meet.google.com/nqi-hraf-cpg ",
            "Хімія": "https://meet.google.com/nup-vusc-tgs ",
            "Інформатика": "https://meet.google.com/rfc-txdu-edx "
        }
        with path_bcist.open("w", encoding="utf-8") as f:
            json.dump(bcist_links, f, ensure_ascii=False, indent=2)
    else:
        with path_bcist.open("r", encoding="utf-8") as f:
            bcist_links = json.load(f)

    return {
        "БЦІГ-25": bcig_links,
        "БЦІСТ-25": bcist_links
    }

def save_meet_links(links_data):
    for group_name, links in links_data.items():
        filename = MEET_LINKS_BCIG_FILE if group_name == "БЦІГ-25" else MEET_LINKS_BCIST_FILE
        path = Path(filename)
        with path.open("w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=2)

meet_links = load_meet_links()

def get_meet_link_for_subject(subj: str, group_name: str = None):
    if not subj or not group_name:
        return None
    
    group_links = meet_links.get(group_name, {})
    s = subj.strip().lower()
    for key, url in group_links.items():
        if key.strip().lower() == s:
            return url
    
    for key, url in group_links.items():
        if key.split()[0].lower() in s or s in key.lower():
            return url
    
    return None

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

def is_empty_pair(pair: dict) -> bool:
    subj = (pair.get("subject") or "").strip().lower()
    return subj in NO_LESSON_SUBJECTS

def get_schedule_with_changes(group_name, day_key, week_type):
    """Получает расписание с учетом временных изменений"""
    if group_name not in schedule:
        return {}
    
    day_data = schedule[group_name].get(day_key, {})
    day_schedule = day_data.get(week_type, {}).copy()
    
    if (group_name in temp_changes and 
        day_key in temp_changes[group_name] and 
        week_type in temp_changes[group_name][day_key]):
        
        for pair_num, change in temp_changes[group_name][day_key][week_type].items():
            day_schedule[pair_num] = {
                "subject": change["subject"],
                "room": change.get("room", ""),
                "teacher": change.get("teacher", "")
            }
    
    return day_schedule

def get_day_struct(d, user_id=None):
    if user_id:
        group_name = get_user_group(user_id)
        if not group_name:
            return None, None, None, None
    else:
        group_name = "БЦІГ-25"
    
    if group_name not in schedule:
        return None, None, None, None
    
    week_type = get_week_type(d)
    day_key = get_day_key(d)
    
    day_schedule = get_schedule_with_changes(group_name, day_key, week_type)
    
    used_week_type = week_type
    if not day_schedule:
        other = "знаменник" if week_type == "чисельник" else "чисельник"
        day_schedule = get_schedule_with_changes(group_name, day_key, other)
        if day_schedule:
            used_week_type = f"{week_type} (як у {other})"
    
    return day_key, used_week_type, day_schedule, schedule.get(group_name, {})

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
    if used_week_type == REFERENCE_WEEK_TYPE:
        header += f"📋 Тиждень: {used_week_type.upper()}\n\n"
    else:
        header += f"📋 Тиждень: {used_week_type.upper()}\n\n"

    if not day_schedule:
        return header + "Пар немає ✅"

    lines = [header]

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

    org = day_schedule.get("org")
    if org:
        lines.append(f"🔸 13:20-13:50 — {org['subject']} ({org['room']}) — {org['teacher']}")

    if len(lines) == 1 + bool(org):
        lines.append("Пар немає ✅")
    return "\n".join(lines)

def build_day_markup(d, user_id=None):
    if not user_id or not get_user_group(user_id):
        return None
    group_name = get_user_group(user_id)
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
        if "захист україни" in subj.strip().lower():
            sapko_url = meet_links.get(group_name, {}).get("Захист України Сапко")
            kiyashchuk_url = meet_links.get(group_name, {}).get("Захист України Киящук")
            if sapko_url:
                markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Сапко", url=sapko_url))
                has_buttons = True
            if kiyashchuk_url:
                markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Киящук", url=kiyashchuk_url))
                has_buttons = True
            continue
        url = get_meet_link_for_subject(subj, group_name)
        if url:
            markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj}", url=url))
            has_buttons = True
    
    org = day_schedule.get("org")
    if org:
        subj = org.get("subject", "Організаційна година")
        url = get_meet_link_for_subject(subj, group_name)
        if url:
            markup.add(InlineKeyboardButton(text=f"🔸 {subj}", url=url))
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
                org = day_schedule.get("org")
                if org:
                    lines.append(f"    🔸 13:20-13:50 — {org['subject']} ({org['room']}) — {org['teacher']}")
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
    group_name = get_user_group(message.from_user.id)
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
            start_str, end_str = time_txt.split("-")
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
        org = day_schedule.get("org")
        if org:
            start_dt = datetime(d.year, d.month, d.day, 13, 20)
            end_dt = datetime(d.year, d.month, d.day, 13, 50)
            if start_dt <= now <= end_dt:
                subj = org.get('subject', 'Організаційна година')
                room = org.get('room', '')
                teacher = org.get('teacher', '')
                text = f"Зараз йде організаційна година:\n13:20-13:50 — {subj}"
                if room:
                    text += f" ({room})"
                if teacher:
                    text += f" — {teacher}"
                
                markup = None
                url = get_meet_link_for_subject(subj, group_name)
                if url:
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
                
                bot.reply_to(message, text, reply_markup=markup)
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
        sapko_url = meet_links.get(group_name, {}).get("Захист України Сапко")
        kiyashchuk_url = meet_links.get(group_name, {}).get("Захист України Киящук")
        if sapko_url:
            markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=sapko_url))
        if kiyashchuk_url:
            markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=kiyashchuk_url))
    else:
        url = get_meet_link_for_subject(subj, group_name)
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
    group_name = get_user_group(message.from_user.id)
    day_key, used_week_type, day_schedule, _ = get_day_struct(d, message.from_user.id)
    if not day_schedule:
        bot.reply_to(message, "Сьогодні пар немає ✅")
        return
    next_pair = None
    for pair_str, pair in sorted(day_schedule.items(), key=lambda x: int(x) if x.isdigit() else 0):
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
            start_str = time_txt.split("-")[0]
            sh, sm = map(int, start_str.split(":"))
        except Exception:
            continue
        start_dt = datetime(d.year, d.month, d.day, sh, sm)
        if start_dt > now:
            next_pair = (pair_num, pair, time_txt)
            break
    if not next_pair:
        org = day_schedule.get("org")
        if org:
            start_dt = datetime(d.year, d.month, d.day, 13, 20)
            if start_dt > now:
                subj = org.get('subject', 'Організаційна година')
                room = org.get('room', '')
                teacher = org.get('teacher', '')
                text = f"Наступна подія: організаційна година\n13:20-13:50 — {subj}"
                if room:
                    text += f" ({room})"
                if teacher:
                    text += f" — {teacher}"
                
                markup = None
                url = get_meet_link_for_subject(subj, group_name)
                if url:
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
                
                bot.reply_to(message, text, reply_markup=markup)
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
        sapko_url = meet_links.get(group_name, {}).get("Захист України Сапко")
        kiyashchuk_url = meet_links.get(group_name, {}).get("Захист України Киящук")
        if sapko_url:
            markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=sapko_url))
        if kiyashchuk_url:
            markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=kiyashchuk_url))
    else:
        url = get_meet_link_for_subject(subj, group_name)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
    bot.reply_to(message, text, reply_markup=markup)

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

# ================== НОВАЯ СИСТЕМА ВРЕМЕННЫХ ИЗМЕНЕНИЙ ==================
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
            "Примеры:\n"
            "/setpair БЦІГ-25 понеділок 1 чисельник Фізика ; 129 ; Гуденко І.А.\n"
            "/setpair БЦІСТ-25 середа 2 знаменник Математика ; 121 ; Приймак О.В.\n"
            "📝 Изменение действует до конца недели (воскресенья)"
        )
        return
    
    parts = rest.split(maxsplit=5)
    if len(parts) < 6:
        bot.reply_to(message, "Недостатньо параметрів")
        return
    
    group_name, day_raw, pair_str, week_raw, subject_rest = parts[0], parts[1], parts[2], parts[3], parts[4]
    
    if group_name not in ["БЦІГ-25", "БЦІСТ-25"]:
        bot.reply_to(message, 
            f"Невірна група. Доступні групи:\n"
            f"• БЦІГ-25\n"
            f"• БЦІСТ-25 (включая ТЕ-25)"
        )
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
    
    if group_name not in temp_changes:
        temp_changes[group_name] = {}
    
    if day_key not in temp_changes[group_name]:
        temp_changes[group_name][day_key] = {}
    
    if week_type not in temp_changes[group_name][day_key]:
        temp_changes[group_name][day_key][week_type] = {}
    
    temp_changes[group_name][day_key][week_type][str(pair_num)] = {
        "subject": subject,
        "room": room,
        "teacher": teacher,
        "changed_at": (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "changed_by": message.from_user.id,
        "original_subject": schedule[group_name].get(day_key, {}).get(week_type, {}).get(str(pair_num), {}).get("subject", "")
    }
    
    save_temp_changes()
    
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
        "change_type": "temporary"
    }
    changelog.append(record)
    save_changelog()
    
    time_txt = get_pair_time(day_key, pair_num) or "час ?"
    bot.reply_to(
        message,
        f"✅ Встановлено тимчасову заміну для групи {group_name} (діє до неділі):\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type})\n"
        f"{time_txt} — {subject} {f'({room})' if room else ''} {f'— {teacher}' if teacher else ''}"
    )

@bot.message_handler(commands=["resetpair"])
def resetpair_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    try:
        _, rest = message.text.split(" ", 1)
    except ValueError:
        bot.reply_to(message,
            "Формат: /resetpair <група> <день> <номер> <тиждень>\n"
            "Примеры:\n"
            "/resetpair БЦІГ-25 понеділок 1 чисельник\n"
            "/resetpair БЦІСТ-25 середа 2 знаменник\n"
            "Скине тимчасову заміну для вказаної пари"
        )
        return
    
    parts = rest.split(maxsplit=4)
    if len(parts) < 4:
        bot.reply_to(message, "Недостатньо параметрів")
        return
    
    group_name, day_raw, pair_str, week_raw = parts[0], parts[1], parts[2], parts[3]
    
    if group_name not in ["БЦІГ-25", "БЦІСТ-25"]:
        bot.reply_to(message, f"Невірна група. Використовуйте: БЦІГ-25 або БЦІСТ-25")
        return
    
    day_key = DAY_ALIASES.get(day_raw.lower())
    if not day_key:
        bot.reply_to(message, "Невірний день")
        return
    
    try:
        pair_num = int(pair_str)
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
    
    if (group_name in temp_changes and 
        day_key in temp_changes[group_name] and 
        week_type in temp_changes[group_name][day_key] and
        str(pair_num) in temp_changes[group_name][day_key][week_type]):
        
        del temp_changes[group_name][day_key][week_type][str(pair_num)]
        
        if not temp_changes[group_name][day_key][week_type]:
            del temp_changes[group_name][day_key][week_type]
        if not temp_changes[group_name][day_key]:
            del temp_changes[group_name][day_key]
        if not temp_changes[group_name]:
            del temp_changes[group_name]
        
        save_temp_changes()
        
        now_local = datetime.utcnow() + timedelta(hours=2)
        record = {
            "timestamp": now_local.strftime("%Y-%m-%d %H:%M:%S"),
            "group": group_name,
            "day_key": day_key,
            "pair_num": pair_num,
            "week_type": week_type,
            "action": "reset_temporary_change",
            "admin_id": message.from_user.id,
            "admin_username": message.from_user.username or "",
            "admin_first_name": message.from_user.first_name or "",
        }
        changelog.append(record)
        save_changelog()
        
        bot.reply_to(message, f"✅ Тимчасову заміну для групи {group_name}, {DAYS_RU[day_key]}, пара {pair_num} ({week_type}) скинуто")
    else:
        bot.reply_to(message, f"Тимчасової заміни для вказаної пари не знайдено")

@bot.message_handler(commands=["resetall"])
def resetall_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Так, скинути", callback_data="reset_all_confirm"),
        InlineKeyboardButton("❌ Ні, скасувати", callback_data="reset_all_cancel")
    )
    
    bot.reply_to(message, 
        "⚠️ Ви впевнені, що хочете скинути ВСІ тимчасові заміни?\n"
        "Ця дія видалить всі зміни, внесені через /setpair.\n"
        "Після скидання розклад повернеться до стандартного.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["reset_all_confirm", "reset_all_cancel"])
def reset_all_callback(call):
    if call.data == "reset_all_confirm":
        for group_name in ["БЦІГ-25", "БЦІСТ-25"]:
            if group_name in temp_changes:
                temp_changes[group_name] = {}
        
        save_temp_changes()
        
        now_local = datetime.utcnow() + timedelta(hours=2)
        record = {
            "timestamp": now_local.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "reset_all_temporary_changes",
            "admin_id": call.from_user.id,
            "admin_username": call.from_user.username or "",
            "admin_first_name": call.from_user.first_name or "",
            "groups": ["БЦІГ-25", "БЦІСТ-25"]
        }
        changelog.append(record)
        save_changelog()
        
        bot.answer_callback_query(call.id, "✅ Всі тимчасові заміни скинуті!")
        bot.edit_message_text(
            "✅ Всі тимчасові заміни для обох груп успішно скинуті!\n"
            "Розклад повернуто до стандартного для:\n"
            "• БЦІГ-25\n"
            "• БЦІСТ-25",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ Скидання скасовано")
        bot.edit_message_text(
            "❌ Скидання тимчасових замін скасовано.",
            call.message.chat.id,
            call.message.message_id
        )

@bot.message_handler(commands=["changes"])
def changes_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    has_changes_bcig = any(temp_changes.get("БЦІГ-25", {}).values())
    has_changes_bcist = any(temp_changes.get("БЦІСТ-25", {}).values())
    
    if not has_changes_bcig and not has_changes_bcist:
        bot.reply_to(message, "📋 Активних тимчасових замін немає для жодної групи.")
        return
    
    lines = ["📋 Активні тимчасові заміни (діють до неділі):\n"]
    
    for group_name in ["БЦІГ-25", "БЦІСТ-25"]:
        if group_name in temp_changes and temp_changes[group_name]:
            lines.append(f"\n👥 Група: {group_name}")
            for day_key, day_data in temp_changes[group_name].items():
                lines.append(f"  📅 {DAYS_RU.get(day_key, day_key)}")
                for week_type, week_data in day_data.items():
                    if week_data:
                        lines.append(f"    🔹 {week_type.upper()}:")
                        for pair_num, change in week_data.items():
                            subject = change.get("subject", "—")
                            room = change.get("room", "")
                            teacher = change.get("teacher", "")
                            changed_at = change.get("changed_at", "")
                            
                            original = change.get("original_subject", "")
                            original_info = f" (було: {original})" if original else ""
                            
                            line = f"      {pair_num}) {subject}{original_info}"
                            if room:
                                line += f" ({room})"
                            if teacher:
                                line += f" — {teacher}"
                            if changed_at:
                                try:
                                    dt = datetime.strptime(changed_at, "%Y-%m-%d %H:%M:%S")
                                    line += f" | змінено: {dt.strftime('%d.%m %H:%M')}"
                                except:
                                    pass
                            
                            lines.append(line)
    
    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i + 4000])
    else:
        bot.reply_to(message, text)

@bot.message_handler(commands=["tempstatus"])
def tempstatus_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    lines = ["📊 Статус тимчасових замін:\n"]
    
    for group_name in ["БЦІГ-25", "БЦІСТ-25"]:
        lines.append(f"\n👥 Група: {group_name}")
        
        if group_name in temp_changes and temp_changes[group_name]:
            total_changes = 0
            for day_data in temp_changes[group_name].values():
                for week_data in day_data.values():
                    total_changes += len(week_data)
            
            lines.append(f"  ✅ Активних змін: {total_changes}")
            
            for day_key, day_data in temp_changes[group_name].items():
                day_changes = 0
                for week_data in day_data.values():
                    day_changes += len(week_data)
                
                if day_changes > 0:
                    lines.append(f"  📅 {DAYS_RU.get(day_key, day_key)}: {day_changes} змін")
        else:
            lines.append(f"  ❌ Немає активних змін")
    
    now = datetime.utcnow() + timedelta(hours=2)
    days_to_sunday = (6 - now.weekday()) % 7
    next_sunday = now + timedelta(days=days_to_sunday)
    next_reset = next_sunday.replace(hour=23, minute=0, second=0)
    
    lines.append(f"\n⏰ Наступний автоматичний скид: {next_reset.strftime('%d.%m.%Y %H:%M')}")
    lines.append(f"📅 Через {days_to_sunday} днів")
    
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["viewtemp"])
def viewtemp_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Формат: /viewtemp <група>\nПример: /viewtemp БЦІГ-25")
        return
    
    group_name = parts[1].strip()
    
    if group_name not in ["БЦІГ-25", "БЦІСТ-25"]:
        bot.reply_to(message, "Невірна група. Використовуйте: БЦІГ-25 або БЦІСТ-25")
        return
    
    if group_name not in temp_changes or not temp_changes[group_name]:
        bot.reply_to(message, f"⚠️ Для групи {group_name} немає активних тимчасових змін.")
        return
    
    lines = [f"📋 Тимчасові заміни для групи {group_name}:\n"]
    
    for day_key, day_data in temp_changes[group_name].items():
        day_name = DAYS_RU.get(day_key, day_key)
        lines.append(f"\n📅 {day_name}:")
        
        for week_type, week_data in day_data.items():
            if week_data:
                lines.append(f"  🔹 {week_type.upper()}:")
                for pair_num, change in sorted(week_data.items(), key=lambda x: int(x[0])):
                    subject = change.get("subject", "—")
                    room = change.get("room", "")
                    teacher = change.get("teacher", "")
                    original = change.get("original_subject", "")
                    
                    line = f"    {pair_num}) {subject}"
                    if original:
                        line += f" (замість: {original})"
                    if room:
                        line += f" ({room})"
                    if teacher:
                        line += f" — {teacher}"
                    
                    lines.append(line)
    
    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i + 4000])
    else:
        bot.reply_to(message, text)

@bot.message_handler(commands=["resetday"])
def resetday_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    try:
        _, rest = message.text.split(" ", 1)
    except ValueError:
        bot.reply_to(message, "Формат: /resetday <група> <день>\nПример: /resetday БЦІГ-25 понеділок")
        return
    
    parts = rest.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "Недостатньо параметрів")
        return
    
    group_name, day_raw = parts[0], parts[1]
    
    if group_name not in ["БЦІГ-25", "БЦІСТ-25"]:
        bot.reply_to(message, "Невірна група. Використовуйте: БЦІГ-25 або БЦІСТ-25")
        return
    
    day_key = DAY_ALIASES.get(day_raw.lower())
    if not day_key:
        bot.reply_to(message, "Невірний день")
        return
    
    if (group_name in temp_changes and 
        day_key in temp_changes[group_name] and 
        temp_changes[group_name][day_key]):
        
        total_changes = 0
        for week_data in temp_changes[group_name][day_key].values():
            total_changes += len(week_data)
        
        del temp_changes[group_name][day_key]
        
        if not temp_changes[group_name]:
            del temp_changes[group_name]
        
        save_temp_changes()
        
        now_local = datetime.utcnow() + timedelta(hours=2)
        record = {
            "timestamp": now_local.strftime("%Y-%m-%d %H:%M:%S"),
            "group": group_name,
            "day_key": day_key,
            "action": "reset_day_changes",
            "changes_count": total_changes,
            "admin_id": message.from_user.id,
            "admin_username": message.from_user.username or "",
            "admin_first_name": message.from_user.first_name or "",
        }
        changelog.append(record)
        save_changelog()
        
        bot.reply_to(message, 
            f"✅ Скинуто {total_changes} тимчасових замін для групи {group_name}, {DAYS_RU[day_key]}")
    else:
        bot.reply_to(message, 
            f"Для групи {group_name}, {DAYS_RU[day_key]} немає активних тимчасових змін")

@bot.message_handler(commands=["clearold"])
def clearold_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    
    now_local = datetime.utcnow() + timedelta(hours=2)
    cutoff_date = now_local - timedelta(days=7)
    
    removed_count = 0
    groups_affected = []
    
    for group_name in list(temp_changes.keys()):
        for day_key in list(temp_changes[group_name].keys()):
            for week_type in list(temp_changes[group_name][day_key].keys()):
                for pair_num in list(temp_changes[group_name][day_key][week_type].keys()):
                    change = temp_changes[group_name][day_key][week_type][pair_num]
                    changed_at_str = change.get("changed_at", "")
                    
                    try:
                        changed_at = datetime.strptime(changed_at_str, "%Y-%m-%d %H:%M:%S")
                        if changed_at < cutoff_date:
                            del temp_changes[group_name][day_key][week_type][pair_num]
                            removed_count += 1
                            if group_name not in groups_affected:
                                groups_affected.append(group_name)
                    except:
                        continue
    
    if removed_count > 0:
        save_temp_changes()
        bot.reply_to(message, f"✅ Видалено {removed_count} застарілих тимчасових змін (старше 7 днів). Групи: {', '.join(groups_affected)}")
    else:
        bot.reply_to(message, "⚠️ Застарілих тимчасових змін не знайдено")

# ================== ОСТАЛЬНЫЕ АДМИН-КОМАНДЫ ==================
@bot.message_handler(commands=["adminhelp"])
def admin_help(message):
    remember_user(message)
    if not is_admin(message):
        return
    text = (
        "👑 Адмін-команди:\n\n"
        "📋 Управління тимчасовими замінами:\n"
        "/setpair <група> <день> <номер> <тиждень> <предмет> ; <аудиторія> ; <викладач>\n"
        "   ↳ встановити тимчасову заміну (скидається в неділю)\n"
        "/resetpair <група> <день> <номер> <тиждень> – скинути тимчасову заміну\n"
        "/resetall – скинути ВСІ тимчасові заміни\n"
        "/changes – показати активні тимчасові заміни\n"
        "/tempstatus – статус тимчасових замін для всіх груп\n"
        "/viewtemp <група> – детальний перегляд змін для групи\n"
        "/resetday <група> <день> – скинути всі зміни для дня\n"
        "/clearold – видалити застарілі зміни (старше 7 днів)\n"
        "\n📎 Посилання Meet:\n"
        "/setlink <група> <предмет> <посилання>\n"
        "/links <група> – список посилань\n"
        "\n👥 Користувачі:\n"
        "/who – список користувачів\n"
        "/whois <@username|id> – інфа по користувачу\n"
        "/setgroup <id> <група> – змінити групу\n"
        "\n📊 Статистика:\n"
        "/stats <week|month> – статистика /wont\n"
        "/absent – хто сьогодні відсутній\n"
        "/changelog – останні зміни\n"
        "\n🎉 Канікули:\n"
        "/holiday <текст> – оголосити канікули\n"
        "/school_start <текст> – початок навчання\n"
        "/holiday_status – статус канікул\n"
        "\nℹ️ Примітка: зміни через /setpair діють лише до неділі, потім автоматично скидаються."
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=["setlink"])
def setlink_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        bot.reply_to(message, 
            "Формат: /setlink <група> <предмет> <посилання>\n"
            "Пример: /setlink БЦІГ-25 Математика https://meet.google.com/xxx  \n"
            "Или: /setlink БЦІГ-25 'Захист України Сапко' https://meet.google.com/xxx  "
        )
        return
    group_name = parts[1]
    subject = parts[2]
    link = parts[3]
    
    if group_name not in meet_links:
        bot.reply_to(message, f"Група {group_name} не знайдена. Доступні групи: {', '.join(meet_links.keys())}")
        return
    
    meet_links[group_name][subject] = link
    save_meet_links(meet_links)
    bot.reply_to(message, f"✅ Посилання для групи {group_name}, предмет '{subject}' встановлено:\n{link}")

@bot.message_handler(commands=["links"])
def links_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Формат: /links <група>\nПример: /links БЦІГ-25")
        return
    group_name = parts[1].strip()
    if group_name not in meet_links:
        bot.reply_to(message, f"Група {group_name} не знайдена. Доступні групи: {', '.join(meet_links.keys())}")
        return
    
    text = f"📎 Збережені посилання для групи {group_name}:\n\n"
    for subject, link in meet_links[group_name].items():
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
            lines.append(f"   • {date_str}, {day_name}, пара {pair_num} — {reason[:50]}...")
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


# ================== ПЕРЕВІРКА ПОВІТРЯНОЇ ТРИВОГИ (ДІАГНОСТИКА) ==================
@bot.message_handler(commands=["aircheck"])
def aircheck_cmd(message):
    remember_user(message)
    if not is_admin(message):
        return
    lines = ["🧪 Перевірка системи повітряної тривоги (Запоріжжя, місто)"]
    lines.append(f"cityId/regionId: {AIRALARM_CITY_ID}")
    lines.append(f"chatId: {ALERT_GROUP_CHAT_ID}")
    lines.append(f"Останній фон.чек: {airalarm_last_check or 'ще не було'}")
    if airalarm_last_error:
        lines.append(f"Остання помилка: {airalarm_last_error}")

    # 1) Перевірка API (разовий запит)
    try:
        active_now, raw = fetch_airalarm_city_status()
        lines.append(f"API: ✅ OK, тривога зараз: {'🚨 ТАК' if active_now else '✅ НІ'}")
        if isinstance(raw, dict):
            keys_preview = ", ".join(sorted(list(raw.keys()))[:15])
            lines.append(f"Поля відповіді: {keys_preview}{' ...' if len(raw.keys()) > 15 else ''}")
        elif isinstance(raw, list):
            lines.append(f"Відповідь: list, len={len(raw)}")
        else:
            lines.append(f"Відповідь: {type(raw)}")
    except Exception as e:
        lines.append(f"API: ❌ помилка: {e}")

    # 2) Перевірка відправки в групу (тестове повідомлення)
    try:
        bot.send_message(
            ALERT_GROUP_CHAT_ID,
            "🧪 Тест: бот може надсилати повідомлення в цю групу. (команда /aircheck)",
        )
        lines.append("SendMessage в групу: ✅ OK")
    except Exception as e:
        lines.append("SendMessage в групу: ❌ помилка")
        lines.append(str(e))

    bot.reply_to(message, "\n".join(lines)[:4000])

# ================== АВТОМАТИЧЕСКИЙ СБРОС В ВОСКРЕСЕНЬЕ ==================
def auto_reset_temp_changes():
    """Автоматически сбрасывает временные изменения в воскресенье в 23:00"""
    while True:
        try:
            now = datetime.utcnow() + timedelta(hours=2)
            if now.weekday() == 6 and now.hour == 23 and now.minute == 0:
                print(f"[{now.strftime('%Y-%m-%d %H:%M')}] Автоматичне скидання тимчасових замін...")
                
                changed_groups = []
                for group_name in ["БЦІГ-25", "БЦІСТ-25"]:
                    if group_name in temp_changes and temp_changes[group_name]:
                        temp_changes[group_name] = {}
                        changed_groups.append(group_name)
                        print(f"✅ Скинуті тимчасові заміни для {group_name}")
                
                if changed_groups:
                    save_temp_changes()
                    
                    for admin_id in ADMIN_IDS:
                        try:
                            bot.send_message(
                                admin_id,
                                "🔄 Автоматичне оновлення розкладу:\n"
                                "✅ Всі тимчасові заміни скинуті.\n"
                                f"Групи: {', '.join(changed_groups)}\n"
                                "Розклад на наступний тиждень повернуто до стандартного."
                            )
                        except Exception as e:
                            print(f"Не вдалося відправити сповіщення адміну {admin_id}: {e}")
                else:
                    print("Немає тимчасових замін для скидання")
                
                time.sleep(24 * 3600)
            else:
                time.sleep(60)
        except Exception as e:
            print(f"Помилка в auto_reset_temp_changes: {e}")
            time.sleep(300)

threading.Thread(target=auto_reset_temp_changes, daemon=True).start()

# ================== МОНІТОРИНГ ПОВІТРЯНОЇ ТРИВОГИ ДЛЯ ЗАПОРІЖЖЯ (МІСТО) ==================

def check_airalarm_for_city():
    """
    Періодично опитує API повітряних тривог по місту Запоріжжя (cityId=564)
    і надсилає повідомлення в групу про початок/відбій тривоги.
    """
    global airalarm_city_active, airalarm_last_check, airalarm_last_error
    while True:
        try:
            airalarm_last_check = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
            active_now, raw = fetch_airalarm_city_status()
            airalarm_last_error = None

            # Перехід стану: з спокійно -> тривога
            if active_now and not airalarm_city_active:
                airalarm_city_active = True
                try:
                    bot.send_message(
                        ALERT_GROUP_CHAT_ID,
                        "🚨 *Повітряна тривога в місті Запоріжжя!*\n"
                        "Негайно перейдіть до укриття.",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    print(f"[AirAlarm] Не вдалося надіслати повідомлення про початок тривоги: {e}")

            # Перехід стану: з тривоги -> відбій
            if not active_now and airalarm_city_active:
                airalarm_city_active = False
                try:
                    bot.send_message(
                        ALERT_GROUP_CHAT_ID,
                        "✅ *Відбій повітряної тривоги в місті Запоріжжя.*\n"
                        "Можна виходити з укриття, дотримуючись офіційних інструкцій.",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    print(f"[AirAlarm] Не вдалося надіслати повідомлення про відбій тривоги: {e}")

        except Exception as e:
            airalarm_last_error = str(e)
            print(f"[AirAlarm] Помилка при опитуванні API: {e}")

        # Інтервал опитування (в секундах). Не ставимо дуже часто, щоб не перевищувати ліміти.
        time.sleep(30)

threading.Thread(target=check_airalarm_for_city, daemon=True).start()

# ================== УВЕДОМЛЕНИЯ ЗА 5 МИНУТ ДО ПАРЫ ==================
notified_pairs = set()

def send_pair_notification(pair_key, pair_num, pair, day_key, user_id):
    if is_empty_pair(pair):
        return
    if holidays["is_holiday"]:
        return
    group_name = get_user_group(user_id)
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
        sapko_url = meet_links.get(group_name, {}).get("Захист України Сапко")
        kiyashchuk_url = meet_links.get(group_name, {}).get("Захист України Киящук")
        if sapko_url:
            markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Сапко", url=sapko_url))
        if kiyashchuk_url:
            markup.add(InlineKeyboardButton(text=f"{pair_num}) {subj} — Киящук", url=kiyashchuk_url))
    else:
        url = get_meet_link_for_subject(subj, group_name)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
    
    try:
        bot.send_message(user_id, text, reply_markup=markup)
    except Exception as e:
        print(f"Не зміг відправити нотіфікацію {user_id}: {e}")

def send_org_notification(org_key, org, day_key, user_id):
    group_name = get_user_group(user_id)
    subj = org.get("subject", "Організаційна година")
    room = org.get("room", "")
    teacher = org.get("teacher", "")
    
    text = "Через ~5 хвилин організаційна година:\n"
    text += f"13:20-13:50 — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"
    
    markup = None
    url = get_meet_link_for_subject(subj, group_name)
    if url:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
    
    try:
        bot.send_message(user_id, text, reply_markup=markup)
    except Exception as e:
        print(f"Не зміг відправити нотіфікацію орг.години {user_id}: {e}")

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
                    start_str = time_txt.split("-")[0]
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
                
                org = day_schedule.get("org")
                if org:
                    start_dt = datetime(d.year, d.month, d.day, 13, 20)
                    delta_sec = (start_dt - now).total_seconds()
                    if 240 <= delta_sec <= 360:
                        org_key = f"{date_key}_{group_name}_org"
                        if org_key not in notified_pairs:
                            print(f"Отправляю уведомление для организационной {org_key}")
                            for uid_str, user_info in users.items():
                                if user_info.get("group") == group_name:
                                    send_org_notification(org_key, org, day_key, int(uid_str))
                            notified_pairs.add(org_key)
        except Exception as e:
            print("Ошибка в notifications_loop:", e)
        time.sleep(60)

threading.Thread(target=notifications_loop, daemon=True).start()

# ================== СТАРТ БОТА ==================
print("Бот запущен...")
print("✅ Система тимчасових замін активна")
print("👥 Підтримка груп: БЦІГ-25, БЦІСТ-25")
print("🔄 Автоматичне скидання: щонеділі о 23:00")
if holidays["is_holiday"]:
    print("⚠️ Зараз КАНІКУЛИ! Автосповіщення вимкнено.")
else:
    print("📚 Навчання в процесі. Автосповіщення ввімкнено.")

bot.infinity_polling()
