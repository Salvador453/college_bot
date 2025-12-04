import telebot
from datetime import date, timedelta
from pathlib import Path
import json
import threading
import os

# ===== Flask для Render =====
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()
# ===========================

# ========= НАСТРОЙКИ =========

TOKEN = "7762300503:AAFEGU-fuw6fk7cJR0spchDDHFUyzxj-4WE"
bot = telebot.TeleBot(TOKEN)

ADMIN_IDS = {1509389908}

REFERENCE_MONDAY = date(2025, 12, 1)
REFERENCE_WEEK_TYPE = "знаменник"

SCHEDULE_FILE = "schedule.json"

# ========= ВРЕМЯ ПАР =========

BELL_SCHEDULE = {
    "monday": {
        1: "08:30–09:50",
        2: "10:00–11:20",
        3: "11:50–13:10",
        4: "13:20–13:50",
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
    "понеділок": "monday", "пн": "monday",
    "вівторок": "tuesday", "вт": "tuesday",
    "середа": "wednesday", "ср": "wednesday",
    "четвер": "thursday", "чт": "thursday",
    "пʼятниця": "friday", "п'ятниця": "friday", "пт": "friday",
    "субота": "saturday", "сб": "saturday",
    "неділя": "sunday", "нд": "sunday",
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


# ========= GOOGLE MEET ССЫЛКИ =========

LINKS = {
    "Фізика": "https://meet.google.com/yqs-gkhh-xqm",
    "Всесвітня історія": "https://meet.google.com/ejg-gvrv-iox",
    "Історія України": "https://meet.google.com/mpc-znwb-gkq",
    "Іноземна мова": "https://meet.google.com/xfq-qeab-vis",
    "Інформатика": "https://meet.google.com/qhx-qkcv-sds",
    "Математика": "https://meet.google.com/nnn-qzzy-yjf",
    "Фізична культура": "https://meet.google.com/swm-bpmx-dfb",
    "Географія": "https://meet.google.com/euh-zuqa-igg",
    "Організаційна година": "https://meet.google.com/hai-zbrq-pnb",
    "Зарубіжна література": "https://meet.google.com/hug-ddec-mop",
    "Українська література": "https://meet.google.com/ogm-ssbj-jzd",
    "Громадянська освіта": "https://meet.google.com/mzw-uedt-fzf",
    "Технології": "https://meet.google.com/oap-sefr-fgc",
    "Українська мова": "https://meet.google.com/wof-fggd-pet",
    "Захист України": "https://meet.google.com/mev-azeu-tiw",
    "Хімія": "https://meet.google.com/nup-vusc-tgs",
    "Біологія": "https://meet.google.com/dgr-knfu-apt",
}


# ========= БАЗОВОЕ РАСПИСАНИЕ =========

def default_schedule():
    return {
        "monday": {
            "чисельник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2"},
                "2": {"subject": "Інформатика", "room": "202"},
                "3": {"subject": "Фізика", "room": "129"},
                "4": {"subject": "Організаційна година", "room": "205"},
            },
            "знаменник": {
                "1": {"subject": "Фізична культура", "room": "с/з №2"},
                "2": {"subject": "Інформатика", "room": "202"},
                "3": {"subject": "Математика", "room": "121"},
                "4": {"subject": "Організаційна година", "room": "205"},
            }
        },

        "tuesday":
        {
            "чисельник": {
                "2": {"subject": "Хімія", "room": "16"},
                "3": {"subject": "Біологія", "room": "16"},
                "4": {"subject": "Громадянська освіта", "room": "114"},
            },
            "знаменник": {
                "1": {"subject": "Інформатика", "room": "239"},
                "2": {"subject": "Хімія", "room": "16"},
                "3": {"subject": "Біологія", "room": "16"},
                "4": {"subject": "Громадянська освіта", "room": "114"},
            }
        },

        "wednesday":
        {
            "чисельник": {
                "1": {"subject": "Іноземна мова", "room": "224а"},
                "2": {"subject": "Всесвітня історія", "room": "114"},
                "3": {"subject": "Математика", "room": "121"},
                "4": {"subject": "Географія", "room": "123"},
            },
            "знаменник": {
                "1": {"subject": "Іноземна мова", "room": "224а"},
                "2": {"subject": "Історія України", "room": "114"},
                "3": {"subject": "Математика", "room": "121"},
                "4": {"subject": "Географія", "room": "123"},
            }
        },

        "thursday":
        {
            "чисельник": {
                "2": {"subject": "Українська мова", "room": "307"},
                "3": {"subject": "Фізика", "room": "129"},
            },
            "знаменник": {
                "1": {"subject": "Технології", "room": "207"},
                "2": {"subject": "Українська мова", "room": "307"},
                "3": {"subject": "Фізика", "room": "129"},
            }
        },

        "friday":
        {
            "чисельник": {
                "1": {"subject": "Українська література", "room": "209"},
                "2": {"subject": "Фізична культура", "room": "с/з №2"},
                "3": {"subject": "Захист України", "room": "242 / 201"},
            },
            "знаменник": {
                "1": {"subject": "Українська література", "room": "209"},
                "2": {"subject": "Зарубіжна література", "room": "116"},
                "3": {"subject": "Захист України", "room": "242 / 201"},
            }
        },

        "saturday": {"чисельник": {}, "знаменник": {}},
        "sunday": {"чисельник": {}, "знаменник": {}},
    }


def load_schedule():
    if not Path(SCHEDULE_FILE).exists():
        return default_schedule()
    return json.loads(Path(SCHEDULE_FILE).read_text(encoding="utf-8"))


def save_schedule(data):
    Path(SCHEDULE_FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


schedule = load_schedule()


# ========= ВСПОМОГАТЕЛЬНЫЕ =========

def get_week_type(d=None):
    if d is None:
        d = date.today()
    diff = (d - REFERENCE_MONDAY).days // 7
    return REFERENCE_WEEK_TYPE if diff % 2 == 0 else ("чисельник" if REFERENCE_WEEK_TYPE == "знаменник" else "знаменник")


def get_day_key(d=None):
    if d is None:
        d = date.today()
    return ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]


def get_pair_time(day, num):
    return BELL_SCHEDULE["monday" if day == "monday" else "other"].get(num)


# ========= КНОПКИ GOOGLE MEET =========

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def send_day_with_buttons(message, d):
    day_key = get_day_key(d)
    week = get_week_type(d)
    day = schedule.get(day_key, {}).get(week, {})

    header = f"{DAYS_RU[day_key]}, {d.strftime('%d.%m.%Y')}\nТиждень: {week.upper()}\n"
    bot.send_message(message.chat.id, header)

    if not day:
        bot.send_message(message.chat.id, "Пар немає")
        return

    for pair_str in sorted(day.keys(), key=lambda x: int(x)):
        pair = day[pair_str]
        subj = pair["subject"]
        room = pair.get("room", "")
        time_txt = get_pair_time(day_key, int(pair_str)) or "?"
        link = LINKS.get(subj, "")

        text = f"{pair_str}) {time_txt} — {subj}"
        if room:
            text += f" ({room})"

        markup = None
        if link:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("💻 Приєднатися до уроку", url=link))

        bot.send_message(message.chat.id, text, reply_markup=markup)


# ========= КОМАНДЫ =========

@bot.message_handler(commands=["start", "help"])
def welcome(message):
    bot.reply_to(message,
                 "Привіт! Я бот розкладу 📚\n\n"
                 "/week — яка тиждень\n"
                 "/today — сьогоднішні пари\n"
                 "/tomorrow — завтрашні\n"
                 "/day <день>\n"
                 "/all — весь розклад\n")


@bot.message_handler(commands=["week"])
def week(message):
    bot.reply_to(message, f"Зараз: *{get_week_type().upper()}*", parse_mode="Markdown")


@bot.message_handler(commands=["today"])
def today_cmd(message):
    send_day_with_buttons(message, date.today())


@bot.message_handler(commands=["tomorrow"])
def tomorrow_cmd(message):
    send_day_with_buttons(message, date.today() + timedelta(days=1))


@bot.message_handler(commands=["day"])
def day_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.reply_to(message, "Приклад: /day середа")
        return
    key = DAY_ALIASES.get(parts[1].lower())
    if not key:
        bot.reply_to(message, "Невідомий день")
        return
    today = date.today()
    weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    target = weekday.index(key)
    shift = (target - weekday.index(get_day_key(today))) % 7
    d = today + timedelta(days=shift)
    send_day_with_buttons(message, d)


# ========= ADMIN /setpair =========

def is_admin(msg):
    return msg.from_user.id in ADMIN_IDS

@bot.message_handler(commands=["setpair"])
def setpair(message):
    if not is_admin(message):
        return

    try:
        _, rest = message.text.split(" ", 1)
        day_raw, num, week_raw, subj_room = rest.split(maxsplit=3)
    except:
        bot.reply_to(message, "Формат:\n/setpair день номер тиждень предмет ; аудиторія")
        return

    day_key = DAY_ALIASES.get(day_raw.lower())
    if not day_key:
        bot.reply_to(message, "День некоректний")
        return

    week_type = "чисельник" if week_raw.startswith("чис") else "знаменник"

    if ";" in subj_room:
        subject, room = [x.strip() for x in subj_room.split(";", 1)]
    else:
        subject, room = subj_room, ""

    schedule[day_key][week_type][str(num)] = {"subject": subject, "room": room}
    save_schedule(schedule)

    bot.reply_to(message, "Готово. Оновлено.")


# ========= START =========

print("BOT started.")
bot.infinity_polling()
