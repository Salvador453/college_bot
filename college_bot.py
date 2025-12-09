import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta, datetime
from pathlib import Path
import json
import time
import re  # для парсинга пар

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

# твой Telegram ID (сюда прилетают /wont)
MAIN_ADMIN_ID = 1509389908

# список админов, которые могут юзать /setpair, /who, /stats, /absent, /changelog, /whois
ADMIN_IDS = {
    1509389908,
    1573294591,
    # если захочешь, сюда можно добавить ещё айдишки
}

# Неделя, которая начинается в ПН 01.12.2025 – це ЗНАМЕННИК
REFERENCE_MONDAY = date(2025, 12, 1)
REFERENCE_WEEK_TYPE = "знаменник"

SCHEDULE_FILE = "schedule.json"
USERS_FILE = "users.json"         # хто писав боту
ABSENCES_FILE = "absences.json"   # сюда пишем /wont
CHANGELOG_FILE = "changelog.json" # сюда пишем /setpair

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
    # понеділок / понедельник
    "понеділок": "monday",
    "понедельник": "monday",
    "пн": "monday",
    "пн.": "monday",
    "пон": "monday",
    "пон.": "monday",
    "mon": "monday",
    "monday": "monday",

    # вівторок / вторник
    "вівторок": "tuesday",
    "вторник": "tuesday",
    "вт": "tuesday",
    "вт.": "tuesday",
    "втор": "tuesday",
    "tue": "tuesday",
    "tuesday": "tuesday",

    # середа / среда
    "середа": "wednesday",
    "середу": "wednesday",
    "ср": "wednesday",
    "ср.": "wednesday",
    "среда": "wednesday",
    "среду": "wednesday",
    "wed": "wednesday",
    "wednesday": "wednesday",

    # четвер / четверг
    "четвер": "thursday",
    "четверг": "thursday",
    "чт": "thursday",
    "чт.": "thursday",
    "чтв": "thursday",
    "thu": "thursday",
    "thursday": "thursday",

    # п’ятниця / пятница
    "пʼятниця": "friday",
    "п'ятниця": "friday",
    "пʼятницю": "friday",
    "п'ятницю": "friday",
    "пятница": "friday",
    "пятницу": "friday",
    "пт": "friday",
    "пт.": "friday",
    "пят": "friday",
    "fri": "friday",
    "friday": "friday",

    # субота / суббота
    "субота": "saturday",
    "суботу": "saturday",
    "суббота": "saturday",
    "субботу": "saturday",
    "сб": "saturday",
    "сб.": "saturday",
    "sat": "saturday",
    "saturday": "saturday",

    # неділя / воскресенье
    "неділя": "sunday",
    "неділю": "sunday",
    "воскресенье": "sunday",
    "неделя": "sunday",
    "нд": "sunday",
    "нд.": "sunday",
    "вс": "sunday",
    "вс.": "sunday",
    "вск": "sunday",
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


# ================== ABSENCES (для /wont, /stats, /absent, /whois) ==================

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


def add_absence_record(name, pair_num, day_key, reason, sender_user):
    now_local = datetime.utcnow() + timedelta(hours=2)
    record = {
        "name": name,
        "pair_num": pair_num,
        "day_key": day_key,
        "reason": reason,
        "sender_id": sender_user.id,
        "sender_username": sender_user.username or "",
        "sender_first_name": sender_user.first_name or "",
        "created_at": now_local.strftime("%Y-%m-%d %H:%M:%S"),
    }
    absences.append(record)
    save_absences()


def parse_absence_dt(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


# ================== CHANGELOG (для /setpair, /changelog) ==================

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


def add_changelog_record(day_key, pair_num, week_type, subject, room, admin_user):
    now_local = datetime.utcnow() + timedelta(hours=2)
    record = {
        "timestamp": now_local.strftime("%Y-%m-%d %H:%M:%S"),
        "day_key": day_key,
        "pair_num": pair_num,
        "week_type": week_type,
        "subject": subject,
        "room": room,
        "admin_id": admin_user.id,
        "admin_username": admin_user.username or "",
        "admin_first_name": admin_user.first_name or "",
    }
    changelog.append(record)
    save_changelog()


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


# ======== ДОП. ХЕЛПЕРЫ ДЛЯ /wont ========

def detect_day_key_from_free_text(text: str):
    """
    Пытаемся понять день из произвольного текста:
    - слова типа 'понеділок', 'понедельник', 'середу', 'среду', 'пʼятницю', 'пятницу' и т.д. (из DAY_ALIASES)
    - относительные: сьогодні/сегодня, завтра, післязавтра/послезавтра
    """
    if not text:
        return None

    s = text.lower()

    # относительные дни
    today_words = {"сьогодні", "сегодня", "today"}
    tomorrow_words = {"завтра", "tomorrow"}
    after_tomorrow_words = {"післязавтра", "послезавтра"}

    today_date = date.today()

    if any(w in s for w in today_words):
        return get_day_key(today_date)

    if any(w in s for w in tomorrow_words):
        return get_day_key(today_date + timedelta(days=1))

    if any(w in s for w in after_tomorrow_words):
        return get_day_key(today_date + timedelta(days=2))

    # абсолютные дни (любая форма, которая есть в DAY_ALIASES)
    cleaned = s.replace(",", " ").replace(".", " ").replace(";", " ").replace("!", " ").replace("?", " ")
    for raw in cleaned.split():
        tok_clean = raw.strip(".,:;!?")
        if tok_clean in DAY_ALIASES:
            return DAY_ALIASES[tok_clean]

    return None


def extract_pairs_from_text(text: str):
    """
    Ищем номера пар в тексте:
    - цифры: 1, 2, 3, 4, 5
    - цифра + суффиксы: 1й, 1-я, 2-га, 3я, 4та и т.п.
    - слова типу 'первая', 'першу', 'вторую', 'друга', 'третью', 'четверту', 'пʼяту' і т.д.
    """
    if not text:
        return []

    s = text.lower()
    pairs = set()

    # 1) любые цифры 1–5 с возможными буквами
    for m in re.findall(r"\b([1-5])\s*(?:й|я|ша|шу|та|у|ю|-й|-я|-ша|-та)?\b", s):
        try:
            num = int(m)
            if 1 <= num <= 5:
                pairs.add(num)
        except ValueError:
            continue

    # 2) словесные формы
    word_to_pair = {
        # 1
        "перша": 1, "першу": 1, "первая": 1, "первую": 1, "первой": 1,
        # 2
        "друга": 2, "другу": 2, "вторая": 2, "вторую": 2, "второй": 2,
        # 3
        "третя": 3, "третю": 3, "третья": 3, "третью": 3,
        # 4
        "четверта": 4, "четверту": 4, "четвертая": 4, "четвертую": 4,
        # 5
        "пʼята": 5, "п'ята": 5, "пятая": 5, "пятую": 5, "пятой": 5,
    }

    cleaned = s.replace(",", " ").replace(".", " ").replace(";", " ").replace("!", " ").replace("?", " ")
    for raw in cleaned.split():
        tok = raw.strip(".,:;!?")
        if tok in word_to_pair:
            pairs.add(word_to_pair[tok])

    return sorted(pairs)


def extract_fio_from_text(rest: str, rest_lower: str, user):
    """
    Вытаскиваем ФИО из начала строки:
    - берём слова до дня недели или стоп-слов ('меня', 'мене', 'я', 'не')
    - максимум 3 слова
    - если ничего адекватного не получилось — подставляем имя/username юзера
    """
    tokens = rest.split()
    tokens_lower = rest_lower.split()
    if not tokens:
        return "", 0

    # стоп-слова, после которых ФИО точно закончилось
    stopwords = {
        "меня", "мене", "мне", "мені",
        "я", "я,", "я.", "я:",
        "меня,", "меня.", "меня:",
        "не", "не,", "не.", "нет",
        "у", "в",
    }

    relative_days = {
        "сьогодні", "сегодня", "today",
        "завтра", "tomorrow",
        "післязавтра", "послезавтра",
    }

    day_idx = None
    for i, tok in enumerate(tokens_lower):
        tt = tok.strip(".,:;!?")
        if tt in DAY_ALIASES or tt in relative_days:
            day_idx = i
            break

    stop_idx = None
    for i, tok in enumerate(tokens_lower):
        tt = tok.strip(".,:;!?")
        if tt in stopwords:
            stop_idx = i
            break

    fio_end_idx = None
    for idx in (day_idx, stop_idx):
        if idx is not None:
            fio_end_idx = idx if fio_end_idx is None else min(fio_end_idx, idx)

    if fio_end_idx is None or fio_end_idx == 0:
        fio_end_idx = min(len(tokens), 3)

    fio_tokens = tokens[:fio_end_idx]
    fio = " ".join(fio_tokens).strip(" ,.-—")

    if fio_tokens:
        joined = " ".join(fio_tokens)
        pos = rest.find(joined)
        fio_end_pos = pos + len(joined) if pos != -1 else 0
    else:
        fio_end_pos = 0

    if not fio:
        if user.first_name:
            fio = user.first_name
        elif user.username:
            fio = f"@{user.username}"
        else:
            fio = f"id {user.id}"

    return fio, fio_end_pos


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
        "/now – яка пара йде зараз + Meet\n"
        "/next – яка наступна пара + Meet\n"
        "/wont – повідомити, що тебе не буде на парі\n"
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


# ================== /now – текущая пара ==================

@bot.message_handler(commands=["now"])
def now_cmd(message):
    remember_user(message)
    now = datetime.utcnow() + timedelta(hours=2)
    d = now.date()
    day_key, used_week_type, day_schedule = get_day_struct(d)

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

    text = (
        f"Зараз йде пара:\n"
        f"{pair_num}) {time_txt} — {subj}"
    )
    if room:
        text += f" ({room})"

    subj_norm = subj.strip().lower()
    markup = None

    if subj_norm == "захист україни":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=DEFENCE_SAPKO_URL))
        markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=DEFENCE_KYYASHЧУК_URL))
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
            text += f"\n🔗 Meet: {url}"

    bot.reply_to(message, text, reply_markup=markup)


# ================== /next – следующая пара ==================

@bot.message_handler(commands=["next"])
def next_cmd(message):
    remember_user(message)
    now = datetime.utcnow() + timedelta(hours=2)
    d = now.date()
    day_key, used_week_type, day_schedule = get_day_struct(d)

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

    text = (
        f"Наступна пара:\n"
        f"{pair_num}) {time_txt} — {subj}"
    )
    if room:
        text += f" ({room})"

    subj_norm = subj.strip().lower()
    markup = None

    if subj_norm == "захист україни":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton(text="Захист України — Сапко", url=DEFENCE_SAPKO_URL))
        markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=DEFENCE_KYYASHЧУК_URL))
        text += (
            f"\n🔗 Meet (Сапко): {DEFENCE_SAPKO_URL}"
            f"\n🔗 Meet (Киящук): {DEFENCE_KYYASHЧУК_URL}"
        )
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))
            text += f"\n🔗 Meet: {url}"

    bot.reply_to(message, text, reply_markup=markup)


# ================== КОМАНДА /wont (відсутність студента) ==================

@bot.message_handler(commands=["wont"])
def wont_cmd(message):
    """
    Формат для студентів (можна довільно, головне щоб було ПІБ, день і пари):

    /wont Давиташвили Илля мене не буде в середу на 1й парі і на 4 парі
    /wont Давиташвили Илля завтра не буду на 2 і 3 парі бо/потому что хворію
    """
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

    # 1) День
    day_key = detect_day_key_from_free_text(rest)
    if not day_key:
        bot.reply_to(
            message,
            "Я не зрозумів, на який день ти не прийдеш 🤔\n"
            "Додай день у текст: понеділок/понедельник, в середу/в пятницу, завтра/сьогодні/сегодня."
        )
        return
    day_name_ua = DAYS_RU.get(day_key, day_key)

    # 2) ПАРИ
    pairs = extract_pairs_from_text(rest)
    if not pairs:
        bot.reply_to(
            message,
            "Я не бачу номерів пар 😅\n"
            "Напиши, на які саме: наприклад 'на 1й парі і на 4 парі' або '2 і 3 пару'."
        )
        return

    # 3) ПІБ
    fio, fio_end_pos = extract_fio_from_text(rest, rest_lower, u)

    if len(fio.split()) < 2:
        bot.reply_to(
            message,
            "Бажано писати хоча б прізвище та ім'я, наприклад:\n"
            "/wont Давиташвили Илля мене не буде в середу на 1й парі..."
        )
        return

    if len(fio.split()) > 4:
        bot.reply_to(
            message,
            "Щось я заплутався у твоєму /wont 😅\n"
            "Напиши спочатку тільки прізвище та ім'я (максимум по-батькові),\n"
            "а потім текст типу: 'мене не буде в середу на 1й і 4 парі, бо ...'."
        )
        return

    # 4) Причина
    tail = rest[fio_end_pos:].lstrip(" ,.-—")
    tail_lower = tail.lower()

    reason_markers = [
        "бо ", "бо,", "бо що",
        "потому что", "потому, что", "потому ", "поэтому ",
        "из-за", "из за", "із-за", "через ", "because",
    ]
    reason_idx = -1
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

    # 5) Хто відправив
    sender_parts = []
    if u.username:
        sender_parts.append(f"@{u.username}")
    if u.first_name:
        sender_parts.append(u.first_name)
    sender_str = " ".join(sender_parts) or f"id {u.id}"

    now_str = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    pairs_str = ", ".join(str(p) for p in pairs)

    admin_text = (
        "📢 Повідомлення про відсутність студента\n\n"
        f"👤 Студент (ПІБ): {fio}\n"
        f"📅 День: {day_name_ua}\n"
        f"🔢 Пари: {pairs_str}\n"
        f"📝 Причина: {reason}\n\n"
        f"Відправник: {sender_str}\n"
        f"Час (UTC+2): {now_str}"
    )

    for pair_num in pairs:
        add_absence_record(fio, pair_num, day_key, reason, u)

    try:
        bot.send_message(MAIN_ADMIN_ID, admin_text)
    except Exception as e:
        print(f"Не зміг відправити /wont адмінину: {e}")

    bot.reply_to(
        message,
        "Ок, я передав інформацію, що тебе не буде на парі(ях) ✅"
    )


# ================== АДМИН-КОМАНДЫ ==================

@bot.message_handler(commands=["adminhelp"])
def admin_help(message):
    remember_user(message)
    if not is_admin(message):
        return
    text = (
        "Адмін-команди:\n\n"
        "/setpair <день> <номер> <тиждень> <предмет> ; <аудиторія>\n"
        "/who – список користувачів, які писали боту\n"
        "/stats <week|month> – статистика /wont\n"
        "/absent – хто сьогодні відмічений як відсутній\n"
        "/changelog – останні зміни розкладу\n"
        "/whois <@username|id> – інфа по користувачу\n\n"
        "Приклади:\n"
        "/setpair понеділок 2 чисельник Інформатика ; 202\n"
        "/setpair середа 3 знаменник Математика ; 121\n"
        "/stats week\n"
        "/whois @nickname\n"
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

    schedule.setdefault(day_key, {}).setdefault(week_type, {})
    schedule[day_key][week_type][str(pair_num)] = {
        "subject": subject,
        "room": room,
    }
    save_schedule(schedule)

    add_changelog_record(day_key, pair_num, week_type, subject, room, message.from_user)

    time_txt = get_pair_time(day_key, pair_num) or "час ?"

    bot.reply_to(
        message,
        f"Ок, оновив:\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type})\n"
        f"{time_txt} — {subject} {f'({room})' if room else ''}"
    )

    changer = message.from_user.first_name or ""
    subj_norm = subject.strip().lower()
    meet_url = get_meet_link_for_subject(subject)

    change_text = (
        "⚠ Зміни в розкладі!\n\n"
        f"{DAYS_RU[day_key]}, пара {pair_num} ({week_type.upper()}):\n"
        f"{time_txt} — {subject}{f' ({room})' if room else ''}"
    )

    if subj_norm == "захист україни":
        change_text += (
            f"\n🔗 Meet (Сапко): {DEFENCE_SAPKO_URL}"
            f"\n🔗 Meet (Киящук): {DEFENCE_KYYASHЧУК_URL}"
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


# ================== /stats – статистика /wont ==================

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

    # name -> list[(dt, rec)]
    stats = {}

    for rec in absences:
        dt = parse_absence_dt(rec.get("created_at", ""))
        if not dt or dt < threshold:
            continue

        name = rec.get("name", "???")
        stats.setdefault(name, []).append((dt, rec))

    if not stats:
        bot.reply_to(message, f"Немає даних по /wont {title}.")
        return

    lines = [f"📊 Статистика /wont {title}:\n"]

    # сортируем по количеству /wont у студента (по убыванию)
    sorted_items = sorted(stats.items(), key=lambda x: len(x[1]), reverse=True)

    for i, (name, recs) in enumerate(sorted_items, start=1):
        total = len(recs)
        lines.append(f"{i}) {name} — {total} раз(и)")

        # для каждого /wont показываем дату, день, пары и причину
        recs_sorted = sorted(recs, key=lambda x: x[0], reverse=True)
        for dt, rec in recs_sorted:
            dt_str = dt.strftime("%Y-%m-%d %H:%M")
            day_key = rec.get("day_key", "")
            day_name = DAYS_RU.get(day_key, day_key)

            pair_val = rec.get("pair_num", "?")
            # на всякий случай: если когда-то будем хранить список пар
            if isinstance(pair_val, (list, tuple, set)):
                pair_str = ", ".join(str(p) for p in pair_val)
            else:
                pair_str = str(pair_val)

            reason = rec.get("reason", "")
            if reason:
                lines.append(f"   • {dt_str}, {day_name}, пара(и): {pair_str} — {reason}")
            else:
                lines.append(f"   • {dt_str}, {day_name}, пара(и): {pair_str}")

        lines.append("")  # пустая строка между студентами

    text = "\n".join(lines)
    # на случай если текст вдруг > 4096 символов — режем на части
    for i in range(0, len(text), 4000):
        bot.reply_to(message, text[i:i + 4000])



# ================== /absent – хто сьогодні відсутній ==================

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
        dt = parse_absence_dt(rec.get("created_at", ""))
        if not dt or dt < threshold:
            continue
        todays.append(rec)

    if not todays:
        bot.reply_to(message, f"Сьогодні ({today_name}) відміток про відсутність немає ✅")
        return

    lines = [f"🚷 Відсутні сьогодні ({today_name}):\n"]
    for rec in sorted(todays, key=lambda r: (r.get("pair_num", 0), r.get("name", ""))):
        name = rec.get("name", "???")
        pair_num = rec.get("pair_num", "?")
        reason = rec.get("reason", "")
        lines.append(f"• {name} — {pair_num} пара — {reason}")

    bot.reply_to(message, "\n".join(lines))


# ================== /changelog – останні зміни розкладу ==================

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
        day_key = rec.get("day_key", "")
        day_name = DAYS_RU.get(day_key, day_key)
        pair_num = rec.get("pair_num", "?")
        week_type = rec.get("week_type", "")
        subj = rec.get("subject", "—")
        room = rec.get("room", "")
        admin_name = rec.get("admin_first_name") or ""
        admin_username = rec.get("admin_username") or ""
        who = admin_name
        if admin_username:
            who += f" (@{admin_username})"
        line = (
            f"{ts} — {day_name}, пара {pair_num} ({week_type}): "
            f"{subj}{f' ({room})' if room else ''}. Змінив: {who}"
        )
        lines.append(line)

    bot.reply_to(message, "\n".join(lines))


# ================== /whois – інфа по користувачу ==================

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

    if query.isdigit() and query in users:
        found_ids.add(query)

    for uid, info in users.items():
        uname = (info.get("username") or "").lower()
        if uname and uname == query.lower():
            found_ids.add(uid)

    if not found_ids:
        bot.reply_to(message, "Не знайшов такого користувача серед тих, хто писав боту.")
        return

    lines = []
    for uid in found_ids:
        info = users.get(uid, {})
        uname = info.get("username") or ""
        name = info.get("first_name") or ""
        last_seen = info.get("last_seen", "")
        user_id_int = int(uid)

        user_abs = [r for r in absences if r.get("sender_id") == user_id_int]
        total_wont = len(user_abs)

        last_rec = None
        if user_abs:
            user_abs_sorted = sorted(
                user_abs,
                key=lambda r: parse_absence_dt(r.get("created_at", "")) or datetime.min,
            )
            last_rec = user_abs_sorted[-1]

        lines.append("🕵️ Інформація про користувача:")
        lines.append(f"ID: {uid}")
        if uname:
            lines.append(f"Username: @{uname}")
        if name:
            lines.append(f"Ім'я: {name}")
        if last_seen:
            lines.append(f"Останній онлайн: {last_seen}")
        lines.append(f"Всього /wont: {total_wont}")

        if last_rec:
            dt = parse_absence_dt(last_rec.get("created_at", "")) or None
            dt_str = dt.strftime("%Y-%m-%d %H:%M") if dt else last_rec.get("created_at", "")
            day_key = last_rec.get("day_key", "")
            day_name = DAYS_RU.get(day_key, day_key)
            pair_num = last_rec.get("pair_num", "?")
            reason = last_rec.get("reason", "")
            lines.append(
                f"Останній /wont: {dt_str}, {day_name}, пара {pair_num}, причина: {reason}"
            )

        lines.append("")

    bot.reply_to(message, "\n".join(lines))


# ================== ТРЕКИНГ ВСЕХ СООБЩЕНИЙ ==================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def tracking_handler(message):
    remember_user(message)


# ================== УВЕДОМЛЕНИЯ ЗА 5 МИНУТ ДО ПАРЫ ==================

notified_pairs = set()  # типа "2025-12-04_1"

def send_pair_notification(pair_key, pair_num, pair, day_key):
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
        markup.add(InlineKeyboardButton(text="Захист України — Киящук", url=DEFENCE_KYYASHЧУК_URL))
    else:
        url = get_meet_link_for_subject(subj)
        if url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="Увійти в Google Meet", url=url))

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
            now = datetime.utcnow() + timedelta(hours=2)
            d = now.date()
            day_key, used_week_type, day_schedule = get_day_struct(d)
            date_key = d.isoformat()

            if now.hour == 0 and now.minute < 5:
                notified_pairs = set()

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
