from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import sqlite3
import threading
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "xxx"
BOT_USERNAME = "xxx"
ADMIN_CHAT_ID = "xxx"

# ================= DATABASE (FAST + SAFE) =================

DB_NAME = "bot.db"
db_lock = threading.RLock()

conn = sqlite3.connect(DB_NAME, check_same_thread=False, isolation_level=None)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=20000")
conn.execute("PRAGMA temp_store=MEMORY")
conn.execute("PRAGMA busy_timeout=5000")

cur = conn.cursor()

def db_execute(query, params=(), fetch=False, fetchone=False):
    with db_lock:
        try:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            if fetchone:
                return cur.fetchone()
            return None
        except sqlite3.OperationalError:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            if fetchone:
                return cur.fetchone()

def db_write(query, params=()):
    with db_lock:
        cur.execute(query, params)

# ================= TABLES =================

db_write("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    score INTEGER DEFAULT 0,
    inviter INTEGER
)""")

db_write("""CREATE TABLE IF NOT EXISTS referrals (
    inviter INTEGER,
    invited INTEGER UNIQUE
)""")

db_write("""CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)""")

db_write("""CREATE TABLE IF NOT EXISTS configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price INTEGER,
    volume INTEGER,
    link TEXT
)""")

db_write("""CREATE TABLE IF NOT EXISTS lang (
    user_id INTEGER PRIMARY KEY,
    language TEXT
)""")

# ================= TRANSLATIONS =================

TRANSLATIONS = {
    "fa": {
        "buy_service": "🚀 خرید سرویس",
        "test": "🧪 اتصال تستی (رایگان)",
        "renew": "🔗 تمدید سرویس",
        "profile": "💰 حساب کاربری",
        "my_services": "📋 سرویس‌های من",
        "my_factors": "🧾 فاکتورهای من",
        "invite": "🎁 دعوت از دوستان",
        "support": "📞 پشتیبانی",
        "admin_panel": "👑 پنل مدیریت",
        "back": "🔙 بازگشت",
        "welcome": "سلام کاربر عزیز!\nموجودی: 0",
        "choose_lang": "Choose language / انتخاب زبان",
        "menu": "منو اصلی",
        "admin_real": "👑 پنل واقعی ادمین",
        "users": "👤 کاربران",
        "refs": "🎁 ریفرال‌ها",
        "services": "📦 سرویس‌ها"
    },
    "en": {
        "buy_service": "🚀 Buy Service",
        "test": "🧪 Free Trial",
        "renew": "🔗 Renew Service",
        "profile": "💰 Profile",
        "my_services": "📋 My Services",
        "my_factors": "🧾 My Invoices",
        "invite": "🎁 Invite Friends",
        "support": "📞 Support",
        "admin_panel": "👑 Admin Panel",
        "back": "🔙 Back",
        "welcome": "Hello dear user!\nBalance: 0",
        "choose_lang": "Choose language / انتخاب زبان",
        "menu": "Main Menu",
        "admin_real": "👑 Real Admin Panel",
        "users": "👤 Users",
        "refs": "🎁 Referrals",
        "services": "📦 Services"
    }
}

# ================= LANGUAGE =================

def set_lang(user_id, lang):
    db_write(
        "INSERT OR REPLACE INTO lang (user_id, language) VALUES (?,?)",
        (user_id, lang)
    )

def get_lang(user_id):
    row = db_execute(
        "SELECT language FROM lang WHERE user_id=?",
        (user_id,),
        fetchone=True
    )
    return row[0] if row else None

def get_translation(user_id, key):
    lang = get_lang(user_id) or "fa"
    return TRANSLATIONS.get(lang, TRANSLATIONS["fa"]).get(key, key)

# ================= CORE =================

def get_admin():
    row = db_execute("SELECT value FROM settings WHERE key='admin'", fetchone=True)
    return row[0] if row else None

def set_admin(user_id):
    db_write("INSERT OR REPLACE INTO settings (key,value) VALUES ('admin',?)", (str(user_id),))

def add_user(user_id):
    row = db_execute("SELECT user_id FROM users WHERE user_id=?", (user_id,), fetchone=True)
    if not row:
        db_write("INSERT INTO users (user_id) VALUES (?)", (user_id,))

def add_score(user_id, amount=1):
    db_write("UPDATE users SET score = score + ? WHERE user_id=?", (amount, user_id))

def use_score(user_id, amount):
    db_write("UPDATE users SET score = score - ? WHERE user_id=?", (amount, user_id))

# ================= MENU (WITH COLORS PRESERVED) =================

def menu(is_admin=False, user_id=None):
    buttons = [
        [
            InlineKeyboardButton(
                get_translation(user_id, "buy_service"),
                callback_data="buy_service",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                get_translation(user_id, "test"),
                callback_data="test",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                get_translation(user_id, "renew"),
                callback_data="renew",
                style="success"
            ),
            InlineKeyboardButton(
                get_translation(user_id, "profile"),
                callback_data="profile",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                get_translation(user_id, "my_services"),
                callback_data="my_services",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                get_translation(user_id, "my_factors"),
                callback_data="my_factors",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                get_translation(user_id, "invite"),
                callback_data="invite",
                style="success"
            ),
            InlineKeyboardButton(
                get_translation(user_id, "support"),
                callback_data="support",
                style="success"
            )
        ]
    ]

    if is_admin:
        buttons.append([
            InlineKeyboardButton(
                get_translation(user_id, "admin_panel"),
                callback_data="admin_users",
                style="danger"
            )
        ])

    return InlineKeyboardMarkup(buttons)

def back_button(user_id=None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            get_translation(user_id, "back"),
            callback_data="back",
            style="danger"
        )]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if not get_lang(user_id):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ])
        await update.message.reply_text(
            get_translation(user_id, "choose_lang"),
            reply_markup=kb
        )
        return

    admin = get_admin()
    if not admin:
        set_admin(user_id)

    is_admin = (str(user_id) == str(get_admin()))

    await update.message.reply_text(
        get_translation(user_id, "welcome"),
        reply_markup=menu(is_admin, user_id)
    )

# ================= ADMIN PANEL =================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != str(get_admin()):
        return

    users = db_execute("SELECT COUNT(*) FROM users", fetchone=True)[0]
    refs = db_execute("SELECT COUNT(*) FROM referrals", fetchone=True)[0]
    configs = db_execute("SELECT COUNT(*) FROM configs", fetchone=True)[0]

    await update.message.reply_text(
        f"{get_translation(user_id, 'admin_real')}\n"
        f"{get_translation(user_id, 'users')}: {users}\n"
        f"{get_translation(user_id, 'refs')}: {refs}\n"
        f"{get_translation(user_id, 'services')}: {configs}"
    )

# ================= BUTTONS =================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_admin = (str(user_id) == str(get_admin()))
    data = query.data

    # -------- LANGUAGE --------
    if data == "lang_fa":
        set_lang(user_id, "fa")
        await query.edit_message_text("زبان: فارسی")
        await query.message.reply_text(
            get_translation(user_id, "menu"),
            reply_markup=menu(is_admin, user_id)
        )
        return

    if data == "lang_en":
        set_lang(user_id, "en")
        await query.edit_message_text("Language: English")
        await query.message.reply_text(
            get_translation(user_id, "menu"),
            reply_markup=menu(is_admin, user_id)
        )
        return

    # -------- ADMIN PANEL --------
    if data == "admin_users" and is_admin:
        await query.edit_message_text(get_translation(user_id, "admin_real"))
        await admin_panel(query, context)
        return

    # -------- BACK --------
    if data == "back":
        await query.edit_message_text(
            get_translation(user_id, "menu"),
            reply_markup=menu(is_admin, user_id)
        )
        return

# ================= MAIN =================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
