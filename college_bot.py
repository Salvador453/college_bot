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
import openai

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

# OpenAI API ключ
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

try:
    bot.remove_webhook()
except Exception as e:
    print("Ошибка при удалении webhook:", e)

MAIN_ADMIN_ID = 1509389908
ADMIN_IDS = {1509389908, 1573294591, 5180067949}

# Неделя, которая начинается в ПН 01.12.2025 – це ЗНАМЕННИК
REFERENCE_MONDAY = date(2025, 12, 1)
REFERENCE_WEEK_TYPE = "знаменник"

SCHEDULE_FILE = "schedule.json"
USERS_FILE = "users.json"
ABSENCES_FILE = "absences.json"
CHANGELOG_FILE = "changelog.json"
HOLIDAYS_FILE = "holidays.json"
MEET_LINKS_FILE = "meet_links.json"
AI_CONTEXT_FILE = "ai_context.json"

# Расклад дзвінків
BELL_SCHEDULE = {
    "monday": {
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "13:20–13:50",
        5: "14:00–15:20",
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

# Предметы, которые считаем "немає пари"
NO_LESSON_SUBJECTS = {
    "немає пари", "нема пари", "нет пары", "немає уроку", "нема уроку", 
    "уроку немає", "-", "—", "", " ",
}

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def is_private_chat(message_or_call):
    """Проверяем, что сообщение или callback из приватного чата"""
    if hasattr(message_or_call, 'message'):
        # Это callback
        return message_or_call.message.chat.type == 'private'
    else:
        # Это обычное сообщение
        return message_or_call.chat.type == 'private'

def is_group_chat(message):
    """Проверяем, что сообщение из группы"""
    return message.chat.type in ['group', 'supergroup']

def remember_user(message):
    # Запоминаем пользователя всегда (и в группах тоже)
    u = message.from_user
    uid = str(u.id)
    info = users.get(uid, {})
    info["id"] = u.id
    info["username"] = u.username or ""
    info["first_name"] = u.first_name or ""
    info["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Группу устанавливаем только в приватных сообщениях
    if is_private_chat(message):
        if "group" not in info:
            info["group"] = None
            info["group_chosen"] = False
    
    users[uid] = info
    save_users()

def is_admin(message):
    return message.from_user.id in ADMIN_IDS

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
            "Захист України": "https://meet.google.com/mev-azeu-tiw?authuser=0&hs=179",
            "Хімія": "https://meet.google.com/nup-vusc-tgs?authuser=0&hs=179",
            "Біологія і екологія": "https://meet.google.com/dgr-knfu-apt?authuser=0&hs=179",
            "Полезна мова": "https://meet.google.com/xfq-qeab-vis?authuser=0&hs=179",
            "Захист України Сапко": "https://meet.google.com/mev-azeu-tiw?authuser=0&hs=179",
            "Захист України Киящук": "https://meet.google.com/nmf-wxwf-ouv",
        }
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_meet_links():
    path = Path(MEET_LINKS_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(meet_links, f, ensure_ascii=False, indent=2)

meet_links = load_meet_links()

def load_ai_context():
    path = Path(AI_CONTEXT_FILE)
    if not path.exists():
        context = {
            "system_prompt": """Ты - полезный бот-помощник для студентов. Ты помогаешь с расписанием занятий, отвечаешь на вопросы о парах, времени, преподавателях и т.д.
Доступные команды:
1. Расписание на сегодня (/today)
2. Расписание на завтра (/tomorrow)
3. Расписание на конкретный день (/day <день>)
4. Текущая пара (/now)
5. Следующая пара (/next)
6. Какая неделя (/week)
7. Полное расписание (/all)
8. Звонки (/bells)
9. Отметить отсутствие (/wont)

Отвечай кратко, информативно и дружелюбно. Если вопрос не по теме расписания, вежливо скажи, что можешь помочь только с расписанием."""
        }
        save_ai_context(context)
        return context
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_ai_context(context):
    path = Path(AI_CONTEXT_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

ai_context = load_ai_context()

# ================== РАСПИСАНИЯ ==================
def create_schedule_bcig():
    """БЦІГ-25 - первое фото"""
    return {
        "monday": {
            "чисельник": {
                "1": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуденко І.А."},
                "2": {"subject": "Українська література", "room": "115", "teacher": "Лосєва К.С."},
                "3": {"subject": "Історія України", "room": "114", "teacher": "Мелєщук Ю.Д."},
                "4": {"subject": "Всесвітня історія", "room": "114", "teacher": "Мелєщук Ю.Д."},
                "5": {"subject": "Організаційна година", "room": "205", "teacher": "Крамаренко Л.О."},
                "6": {"subject": "Зарубіжна література", "room": "116", "teacher": "Мендеркова О.В."}
            },
            "знаменник": {
                "1": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуденко І.А."},
                "2": {"subject": "Українська література", "room": "115", "teacher": "Лосєва К.С."},
                "3": {"subject": "Всесвітня історія", "room": "114", "teacher": "Мелєщук Ю.Д."},
                "4": {"subject": "Всесвітня історія", "room": "114", "teacher": "Мелєщук Ю.Д."},
                "5": {"subject": "Організаційна година", "room": "205", "teacher": "Крамаренко Л.О."},
                "6": {"subject": "Зарубіжна література", "room": "116", "teacher": "Мендеркова О.В."}
            }
        },
        "tuesday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Багрін В.С."},
                "2": {"subject": "Математика", "room": "121", "teacher": "Приймик О.В."},
                "3": {"subject": "Українська мова", "room": "307", "teacher": "Гавриленко С.Т."}
            },
            "знаменник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Багрін В.С."},
                "2": {"subject": "Математика", "room": "121", "teacher": "Приймик О.В."},
                "3": {"subject": "Українська мова", "room": "307", "teacher": "Гавриленко С.Т."}
            }
        },
        "wednesday": {
            "чисельник": {
                "1": {"subject": "Технології", "room": "208", "teacher": "Потапова А.О."},
                "2": {"subject": "Математика", "room": "121", "teacher": "Приймик О.В."},
                "3": {"subject": "Біологія і екологія", "room": "16", "teacher": "Золотова К.В."},
                "4": {"subject": "Захист України", "room": "242 / 201", "teacher": "Салко / Киличук"}
            },
            "знаменник": {
                "1": {"subject": "Технології", "room": "208", "teacher": "Потапова А.О."},
                "2": {"subject": "Математика", "room": "121", "teacher": "Приймик О.В."},
                "3": {"subject": "Біологія і екологія", "room": "16", "teacher": "Золотова К.В."},
                "4": {"subject": "Захист України", "room": "242 / 201", "teacher": "Салко / Киличук"}
            }
        },
        "thursday": {
            "чисельник": {
                "1": {"subject": "Історія України", "room": "114", "teacher": "Мелєщук Ю.Д."},
                "2": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "3": {"subject": "Інформатика", "room": "39", "teacher": "Короленко / Єреп"},
                "4": {"subject": "Географія", "room": "123", "teacher": "Баранець Т.О."}
            },
            "знаменник": {
                "1": {"subject": "Історія України", "room": "114", "teacher": "Мелєщук Ю.Д."},
                "2": {"subject": "Громадянська освіта", "room": "142", "teacher": "Зубко Г.М."},
                "3": {"subject": "Інформатика", "room": "39", "teacher": "Короленко / Єреп"},
                "4": {"subject": "Географія", "room": "123", "teacher": "Баранець Т.О."}
            }
        },
        "friday": {
            "чисельник": {
                "1": {"subject": "Полезна мова", "room": "224 a", "teacher": "Кривалівченкова Л.І."},
                "2": {"subject": "Хімія", "room": "16", "teacher": "Золотова К.В."},
                "3": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуденко І.А."},
                "4": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Багрін В.С."}
            },
            "знаменник": {
                "1": {"subject": "Полезна мова", "room": "224 a", "teacher": "Кривалівченкова Л.І."},
                "2": {"subject": "Хімія", "room": "16", "teacher": "Золотова К.В."},
                "3": {"subject": "Фізика і астрономія", "room": "129", "teacher": "Гуденко І.А."},
                "4": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Багрін В.С."}
            }
        },
        "saturday": {"чисельник": {}, "знаменник": {}},
        "sunday": {"чисельник": {}, "знаменник": {}}
    }

def create_schedule_bcis():
    """БЦІСТ-25 (включая ТЕ-25) - второе фото"""
    return {
        "monday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Іноземна мова", "room": "224 а", "teacher": "Криваночешкова Л.І."},
                "3": {"subject": "Математика", "room": "121", "teacher": "Приймак О.В."},
                "4": {"subject": "Організаційна година", "room": "205", "teacher": "Крамаренко Л.О."}
            },
            "знаменник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Іноземна мова", "room": "224 а", "teacher": "Криваночешкова Л.І."},
                "3": {"subject": "Математика", "room": "121", "teacher": "Приймак О.В."},
                "4": {"subject": "Організаційна година", "room": "205", "teacher": "Крамаренко Л.О."}
            }
        },
        "tuesday": {
            "чисельник": {
                "1": {"subject": "Біологія і екологія", "room": "16", "teacher": "Золотова К.В."},
                "2": {"subject": "Історія України", "room": "114", "teacher": "Меленчук Ю.Л."},
                "3": {"subject": "Всесвітня історія", "room": "114", "teacher": "Меленчук Ю.Л."},
                "4": {"subject": "Інформатика", "room": "39", "teacher": "Короленко / Єреп"}
            },
            "знаменник": {
                "1": {"subject": "Біологія і екологія", "room": "16", "teacher": "Золотова К.В."},
                "2": {"subject": "Всесвітня історія", "room": "114", "teacher": "Меленчук Ю.Л."},
                "3": {"subject": "Інформатика", "room": "39", "teacher": "Короленко / Єреп"},
                "4": {"subject": "немає пари", "room": "", "teacher": ""}
            }
        },
        "wednesday": {
            "чисельник": {
                "1": {"subject": "Хімія", "room": "16", "teacher": "Золотова К.В."},
                "2": {"subject": "Математика", "room": "121", "teacher": "Приймак О.В."},
                "3": {"subject": "Технології", "room": "208", "teacher": "Потапова А.О."},
                "4": {"subject": "Захист України", "room": "242 / 201", "teacher": "Санко / Киянчук"}
            },
            "знаменник": {
                "1": {"subject": "Хімія", "room": "16", "teacher": "Золотова К.В."},
                "2": {"subject": "Технології", "room": "208", "teacher": "Потапова А.О."},
                "3": {"subject": "Захист України", "room": "242 / 201", "teacher": "Санко / Киянчук"},
                "4": {"subject": "немає пари", "room": "", "teacher": ""}
            }
        },
        "thursday": {
            "чисельник": {
                "1": {"subject": "Громадянська освіта", "room": "129", "teacher": "Гуленко І.А."},
                "2": {"subject": "Фізика і астрономія", "room": "142", "teacher": "Зубко Г.М."},
                "3": {"subject": "Українська мова", "room": "129", "teacher": "Гуленко І.А."},
                "4": {"subject": "Зарубіжна література", "room": "116", "teacher": "Мендерякова О.В."}
            },
            "знаменник": {
                "1": {"subject": "Фізика і астрономія", "room": "142", "teacher": "Зубко Г.М."},
                "2": {"subject": "Українська мова", "room": "307", "teacher": "Гавриленко С.Т."},
                "3": {"subject": "Зарубіжна література", "room": "116", "teacher": "Мендерякова О.В."},
                "4": {"subject": "немає пари", "room": "", "teacher": ""}
            }
        },
        "friday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Історія України", "room": "123", "teacher": "Бераненко Т.О."},
                "3": {"subject": "Українська література", "room": "115", "teacher": "Лосєва К.С."},
                "4": {"subject": "немає пари", "room": "", "teacher": ""}
            },
            "знаменник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2", "teacher": "Свиридов А.П."},
                "2": {"subject": "Історія України", "room": "114", "teacher": "Меленчук Ю.Л."},
                "3": {"subject": "Українська література", "room": "115", "teacher": "Лосєва К.С."},
                "4": {"subject": "немає пари", "room": "", "teacher": ""}
            }
        },
        "saturday": {"чисельник": {}, "знаменник": {}},
        "sunday": {"чисельник": {}, "знаменник": {}}
    }

# ================== ОСНОВНЫЕ ФУНКЦИИ ==================
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
        return "чисельник" if REFERENCE_WEEK_TYPE == "знаменник" else "знаменник"

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
    header += f"📋 Тиждень: {used_week_type.upper()}\n\n"

    if not day_schedule:
        return header + "Пар немає ✅"

    lines = [header]
    for pair_str in sorted(day_schedule.keys(), key=lambda x: int(x)):
        pair_num = int(pair_str)
        pair = day_schedule[pair_str]
        subj = pair.get("subject", "—")
        
        if is_empty_pair(pair):
            continue
            
        time_txt = get_pair_time(day_key, pair_num) or "час ?"
        room = pair.get("room", "")
        teacher = pair.get("teacher", "")
        
        line = f"{pair_num}) {time_txt} — {subj}"
        if room:
            line += f" ({room})"
        if teacher:
            line += f" — {teacher}"
        lines.append(line)

    if len(lines) == 1:
        lines.append("Пар немає ✅")
        
    return "\n".join(lines)

# ================== ИИ ФУНКЦИИ (ТОЛЬКО ДЛЯ ЛС) ==================
def get_next_pair_info_with_time(user_id):
    """Получает информацию о следующей паре с временем до начала"""
    now = datetime.utcnow() + timedelta(hours=2)
    d = now.date()
    
    user_schedule = get_schedule_for_user(user_id)
    if not user_schedule:
        return "⚠️ Ви ще не вибрали групу! Використовуйте /start щоб вибрати групу."
    
    day_key, used_week_type, day_schedule, _ = get_day_struct(d, user_id)
    
    if not day_schedule:
        return "Сьогодні пар немає ✅"
    
    next_pair = None
    for pair_str, pair in sorted(day_schedule.items(), key=lambda x: int(x[0])):
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
        except Exception:
            continue

        start_dt = datetime(d.year, d.month, d.day, sh, sm)
        if start_dt > now:
            next_pair = (pair_num, pair, time_txt, start_dt)
            break

    if not next_pair:
        return "Сьогодні більше пар немає ✅"

    pair_num, pair, time_txt, start_dt = next_pair
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    teacher = pair.get("teacher", "")
    
    # Вычисляем время до начала
    time_left = start_dt - now
    hours_left = time_left.seconds // 3600
    minutes_left = (time_left.seconds % 3600) // 60
    
    time_left_text = ""
    if hours_left > 0:
        time_left_text += f"{hours_left} год. "
    time_left_text += f"{minutes_left} хв."
    
    text = f"⏰ Наступна пара через {time_left_text}:\n"
    text += f"📚 {pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"
    
    return text

def get_current_pair_info(user_id):
    """Получает информацию о текущей паре"""
    now = datetime.utcnow() + timedelta(hours=2)
    d = now.date()
    
    user_schedule = get_schedule_for_user(user_id)
    if not user_schedule:
        return "⚠️ Ви ще не вибрали групу! Використовуйте /start щоб вибрати групу."
    
    day_key, used_week_type, day_schedule, _ = get_day_struct(d, user_id)
    
    if not day_schedule:
        return "Сьогодні пар немає ✅"
    
    current_pair = None
    for pair_str, pair in day_schedule.items():
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
            # Вычисляем оставшееся время
            time_left = end_dt - now
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            time_left_text = ""
            if hours_left > 0:
                time_left_text += f"{hours_left} год. "
            time_left_text += f"{minutes_left} хв."
            
            current_pair = (pair_num, pair, time_txt, time_left_text)
            break

    if not current_pair:
        return "Зараз пари немає ⏸"

    pair_num, pair, time_txt, time_left_text = current_pair
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    teacher = pair.get("teacher", "")
    
    text = f"⏳ Зараз йде пара (залишилось {time_left_text}):\n"
    text += f"📚 {pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"
    
    return text

def ask_openai(question, user_context=""):
    """Запрашивает ответ у OpenAI"""
    try:
        system_content = ai_context["system_prompt"]
        
        if user_context:
            system_content += f"\n\nКонтекст пользователя: {user_context}"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        return "⚠️ Извините, возникла ошибка при обработке запроса. Попробуйте позже."

def process_natural_language(text, user_id):
    """Обрабатывает естественный язык и возвращает ответ"""
    text_lower = text.lower().strip()
    
    if holidays["is_holiday"]:
        return "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️"
    
    # 1. Приветствия
    greetings = ["привіт", "привет", "hello", "hi", "хай", "здравствуй", "добрий день", "добрый день"]
    if any(greet in text_lower for greet in greetings):
        group = get_user_group(user_id)
        if group:
            return f"Привіт! 👋 Я бот розкладу для групи {group}. Чим можу допомогти?"
        else:
            return "Привіт! 👋 Я бот розкладу. Спочатку виберіть групу командою /start"
    
    # 2. Вопросы о следующей паре
    next_keywords = ["наступна пара", "следующая пара", "какая следующая пара", "яка наступна пара", 
                    "що далі", "что дальше", "коли наступна", "коли следующая", "через сколько пара"]
    
    if any(keyword in text_lower for keyword in next_keywords):
        return get_next_pair_info_with_time(user_id)
    
    # 3. Вопросы о текущей паре
    current_keywords = ["зараз пара", "сейчас пара", "какая сейчас пара", "яка зараз пара", 
                       "що зараз", "что сейчас", "йде пара", "идет пара"]
    
    if any(keyword in text_lower for keyword in current_keywords):
        return get_current_pair_info(user_id)
    
    # 4. Вопросы о сегодняшнем расписании
    today_keywords = ["сьогодні", "сегодня", "розклад сьогодні", "расписание сегодня", 
                     "пари сьогодні", "пары сегодня", "що сьогодні", "что сегодня"]
    
    if any(keyword in text_lower for keyword in today_keywords):
        d = date.today()
        return format_day_schedule(d, user_id)
    
    # 5. Вопросы о завтрашнем расписании
    tomorrow_keywords = ["завтра", "завтрашній", "завтрашний", "розклад завтра", "расписание завтра"]
    
    if any(keyword in text_lower for keyword in tomorrow_keywords):
        d = date.today() + timedelta(days=1)
        return format_day_schedule(d, user_id)
    
    # 6. Вопросы о неделе
    week_keywords = ["тиждень", "неделя", "чисельник", "знаменник", "какая неделя", "який тиждень"]
    
    if any(keyword in text_lower for keyword in week_keywords):
        wt = get_week_type()
        return f"Зараз тиждень: *{wt.upper()}*"
    
    # 7. Вопросы о днях недели
    day_patterns = {
        "понеділок": "понеділок", "понедельник": "понеділок",
        "вівторок": "вівторок", "вторник": "вівторок",
        "середа": "середа", "среда": "середа",
        "четвер": "четвер", "четверг": "четвер",
        "пʼятниця": "пʼятниця", "пятница": "пʼятниця"
    }
    
    for pattern, day in day_patterns.items():
        if pattern in text_lower:
            today = date.today()
            today_key = get_day_key(today)
            keys_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            
            day_key = None
            for ru_day, eng_day in DAYS_RU.items():
                if day.lower() in ru_day or day.lower() in eng_day.lower():
                    day_key = ru_day
                    break
            
            if day_key:
                idx_today = keys_order.index(today_key)
                idx_target = keys_order.index(day_key)
                shift = (idx_target - idx_today) % 7
                target_date = today + timedelta(days=shift)
                return format_day_schedule(target_date, user_id)
    
    # 8. Вопросы о времени/звонках
    time_keywords = ["дзвінки", "звонки", "коли пара", "во сколько", "о котрій", "графік пар", "график пар"]
    
    if any(keyword in text_lower for keyword in time_keywords):
        txt = "🔔 Розклад дзвінків\n\nПонеділок:\n"
        for num in sorted(BELL_SCHEDULE["monday"].keys()):
            txt += f"{num}) {BELL_SCHEDULE['monday'][num]}\n"
        txt += "\nВівторок–Пʼятниця:\n"
        for num in sorted(BELL_SCHEDULE["other"].keys()):
            txt += f"{num}) {BELL_SCHEDULE['other'][num]}\n"
        return txt
    
    # 9. Вопросы о группе
    group_keywords = ["яка група", "какая группа", "моя група", "група", "группа"]
    
    if any(keyword in text_lower for keyword in group_keywords):
        group = get_user_group(user_id)
        if group:
            return f"📚 Ваша група: {group}"
        else:
            return "⚠️ Ви ще не вибрали групу! Використовуйте /start щоб вибрати групу."
    
    # 10. Если не распознали - используем OpenAI
    group = get_user_group(user_id)
    week_type = get_week_type()
    today_schedule = format_day_schedule(date.today(), user_id)[:500]
    
    user_context = f"""
    Група пользователя: {group if group else "Не выбрана"}
    Текущая неделя: {week_type}
    Сегодняшнее расписание: {today_schedule}
    """
    
    return ask_openai(text, user_context)

# ================== КОМАНДЫ (РАБОТАЮТ ВЕЗДЕ) ==================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    remember_user(message)
    uid = str(message.from_user.id)
    user_info = users.get(uid, {})
    
    if is_private_chat(message):
        # В ЛС показываем полный функционал
        if user_info.get("group"):
            text = (
                f"Привіт! Я бот розкладу групи 📚\n"
                f"Ваша група: {user_info['group']}\n\n"
                "📌 Основні команди:\n"
                "/week – яка зараз тиждень\n"
                "/today – розклад на сьогодні\n"
                "/tomorrow – розклад на завтра\n"
                "/day <день> – розклад на конкретний день\n"
                "/all – повний розклад\n"
                "/bells – розклад дзвінків\n"
                "/now – яка пара йде зараз\n"
                "/next – яка наступна пара\n"
                "/wont – повідомити, що тебе не буде\n"
                "/mygroup – показати мою групу\n\n"
                "💬 Можете просто писати мені як:\n"
                "• «Яка наступна пара?»\n"
                "• «Через скільки починається?»\n"
                "• «Що сьогодні?»\n"
                "• «Розклад на завтра»\n"
                "• «Яка зараз пара?»\n"
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
    else:
        # В группе показываем только основные команды
        text = (
            "👋 Привіт! Я бот розкладу групи.\n\n"
            "📌 Основні команди:\n"
            "/week – яка зараз тиждень\n"
            "/today – розклад на сьогодні\n"
            "/tomorrow – розклад на завтра\n"
            "/day <день> – розклад на конкретний день\n"
            "/bells – розклад дзвінків\n"
            "/now – яка пара йде зараз\n"
            "/next – яка наступна пара\n\n"
            "⚠️ Повний функціонал доступний в приватних повідомленнях!"
        )
        bot.reply_to(message, text)

@bot.message_handler(commands=["today"])
def today_cmd(message):
    remember_user(message)
    
    if holidays["is_holiday"]:
        bot.reply_to(message, "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️")
        return
    
    d = date.today()
    text = format_day_schedule(d, message.from_user.id)
    bot.reply_to(message, text)

@bot.message_handler(commands=["tomorrow"])
def tomorrow_cmd(message):
    remember_user(message)
    
    if holidays["is_holiday"]:
        bot.reply_to(message, "🎉 Зараз канікули! Відпочивай та насолоджуйся вільним часом! 🏖️")
        return
    
    d = date.today() + timedelta(days=1)
    text = format_day_schedule(d, message.from_user.id)
    bot.reply_to(message, text)

@bot.message_handler(commands=["week"])
def week_cmd(message):
    remember_user(message)
    wt = get_week_type()
    bot.reply_to(message, f"Зараз тиждень: *{wt.upper()}*", parse_mode="Markdown")

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
    bot.reply_to(message, text)

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

    bot.reply_to(message, text)

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
    for pair_str, pair in sorted(day_schedule.items(), key=lambda x: int(x[0])):
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
        except Exception:
            continue

        start_dt = datetime(d.year, d.month, d.day, sh, sm)
        if start_dt > now:
            next_pair = (pair_num, pair, time_txt)
            break

    if not next_pair:
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

    # Определяем день
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

    # Извлекаем номера пар
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

    # Извлекаем ФИО
    tokens = rest.split()
    tokens_lower = rest_lower.split()
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

    # Извлекаем причину
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

    # Создаем запись
    now_str = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    pairs_str = ", ".join(str(p) for p in sorted(pairs))
    
    # Сохраняем
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
    
    # Отправляем админу
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

@bot.message_handler(commands=["mygroup"])
def mygroup_cmd(message):
    remember_user(message)
    uid = str(message.from_user.id)
    group = users.get(uid, {}).get("group")
    
    if group:
        bot.reply_to(message, f"📚 Ваша група: {group}")
    else:
        if is_private_chat(message):
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
        else:
            bot.reply_to(message, "⚠️ Для вибору групи напишіть /start в приватних повідомленнях з ботом.")

# ================== ОБРАБОТЧИК ЕСТЕСТВЕННОГО ЯЗЫКА (ТОЛЬКО В ЛС) ==================
@bot.message_handler(func=lambda message: is_private_chat(message) and not message.text.startswith('/'), content_types=['text'])
def handle_natural_language(message):
    """Обрабатывает все текстовые сообщения, не являющиеся командами (только в ЛС)"""
    remember_user(message)
    
    # Обрабатываем естественный язык
    response = process_natural_language(message.text, message.from_user.id)
    
    # Отправляем ответ
    bot.reply_to(message, response)

# ================== КАЛЛБЭКИ (ТОЛЬКО В ЛС) ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_group_"))
def choose_group_callback(call):
    # Только в приватных сообщениях
    if not is_private_chat(call):
        bot.answer_callback_query(call.id, "Цей бот працює тільки в приватних повідомленнях")
        return
    
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
            "Тепер ви можете спілкуватися зі мною природньою мовою! 🎉\n"
            "Наприклад:\n"
            "• «Яка наступна пара?»\n"
            "• «Що сьогодні?»\n"
            "• «Розклад на середу»\n"
            "• «Яка зараз пара?»\n\n"
            "Або використовуйте команди: /help",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Помилка: спробуйте ще раз /start")

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
        "/holiday_status – статус канікул\n"
        "/setaiprompt <текст> – налаштувати промпт для ІІ\n"
        "/aiprompt – показати поточний промпт\n\n"
        "Приклади:\n"
        "/setpair БЦІГ-25 понеділок 1 чисельник Фізика ; 129 ; Гуденко І.А.\n"
        "/setlink Математика https://meet.google.com/xxx\n"
        "/setgroup 123456789 БЦІСТ-25"
    )
    bot.reply_to(message, text)

# (Добавь остальные админ-команды как в предыдущей версии)

# ================== УВЕДОМЛЕНИЯ ==================
notified_pairs = set()

def send_pair_notification(pair_key, pair_num, pair, day_key, user_id):
    if is_empty_pair(pair):
        return

    if holidays["is_holiday"]:
        return

    text = "🔔 Через ~5 хвилин пара:\n"
    time_txt = get_pair_time(day_key, pair_num) or "час ?"
    subj = pair.get("subject", "—")
    room = pair.get("room", "")
    teacher = pair.get("teacher", "")
    text += f"{pair_num}) {time_txt} — {subj}"
    if room:
        text += f" ({room})"
    if teacher:
        text += f" — {teacher}"

    for uid_str, user_info in users.items():
        if not user_info.get("group"):
            continue
            
        uid = int(uid_str)
        try:
            bot.send_message(uid, text)
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

            for group_name, group_schedule in schedule.items():
                day_key = get_day_key(d)
                week_type = get_week_type(d)
                
                day_schedule = group_schedule.get(day_key, {}).get(week_type, {})
                if not day_schedule:
                    continue

                for pair_str, pair in day_schedule.items():
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
print("🤖 Бот запущен...")
print("⚙️ Команды работают ВЕЗДЕ (в группах и ЛС)")
print("💬 ИИ работает ТОЛЬКО в приватных сообщениях")
print(f"📚 Группы: {list(schedule.keys())}")

if holidays["is_holiday"]:
    print("⚠️ Сейчас КАНИКУЛЫ! Автоуведомления отключены.")
else:
    print("📚 Учеба в процессе. Автоуведомления включены.")

if OPENAI_API_KEY == "your-openai-api-key-here":
    print("⚠️ ВНИМАНИЕ: OpenAI API ключ не установлен!")
    print("Для работы ИИ получите ключ на platform.openai.com")
    print("Бот будет работать в режиме правил (без GPT)")
else:
    print("✅ OpenAI API ключ обнаружен. ИИ активирован в ЛС!")

bot.infinity_polling()
