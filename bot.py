import logging
import os
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# =============================================
#   SOZLAMALAR — bularni o'zgartiring!
# =============================================
BOT_TOKEN = "8014335358:AAHGoMN6zU8fCJgGhU1Y625PU3KwyAY2cAI"       # @BotFather dan olingan token
ADMIN_IDS = [8325726426]                  # Sizning Telegram ID (https://t.me/userinfobot)
DB_FILE = "movies.json"                  # Kinolar saqlanadigan fayl
CHANNEL_ID = "@your_channel"             # Kino yuboradigan kanal (ixtiyoriy)
# =============================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  MA'LUMOTLAR BAZASI (JSON fayl)
# ─────────────────────────────────────────────

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"movies": {}, "pending": {}}

def save_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_movie_by_code(code: str) -> dict | None:
    db = load_db()
    return db["movies"].get(code.upper())

def search_movies_by_name(query: str) -> list:
    db = load_db()
    query_lower = query.lower()
    results = []
    for code, movie in db["movies"].items():
        if query_lower in movie["title"].lower():
            results.append((code, movie))
    return results[:10]  # max 10 ta natija

def add_movie(code: str, movie_data: dict):
    db = load_db()
    db["movies"][code.upper()] = movie_data
    save_db(db)

def delete_movie(code: str) -> bool:
    db = load_db()
    if code.upper() in db["movies"]:
        del db["movies"][code.upper()]
        save_db(db)
        return True
    return False

def get_all_movies() -> dict:
    return load_db()["movies"]

def save_pending(user_id: int, data: dict):
    db = load_db()
    db["pending"][str(user_id)] = data
    save_db(db)

def get_pending(user_id: int) -> dict | None:
    db = load_db()
    return db["pending"].get(str(user_id))

def clear_pending(user_id: int):
    db = load_db()
    db["pending"].pop(str(user_id), None)
    save_db(db)


# ─────────────────────────────────────────────
#  YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_valid_code(code: str) -> bool:
    """Kod 1-5 ta son bo'lishi kerak"""
    return bool(re.match(r'^\d{1,5}$', code))

def movie_caption(code: str, movie: dict) -> str:
    stars = "⭐" * int(float(movie.get("rating", 0)))
    genres = " • ".join(movie.get("genres", []))
    text = (
        f"🎬 <b>{movie['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if movie.get("year"):
        text += f"📅 <b>Yil:</b> {movie['year']}\n"
    if movie.get("rating"):
        text += f"⭐ <b>Reyting:</b> {movie['rating']}/10\n"
    if genres:
        text += f"🎭 <b>Janr:</b> {genres}\n"
    if movie.get("language"):
        text += f"🌐 <b>Til:</b> {movie['language']}\n"
    if movie.get("description"):
        text += f"\n📝 {movie['description']}\n"
    text += f"\n🔑 <b>Kod:</b> <code>{code}</code>"
    return text


# ─────────────────────────────────────────────
#  FOYDALANUVCHI HANDLERLARI
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        f"🎬 <b>CineBot</b>ga xush kelibsiz!\n\n"
        f"<b>Qanday foydalanish:</b>\n"
        f"• Kino kodini yozing (masalan: <code>123</code>)\n"
        f"• Yoki kino nomini yozing (masalan: <code>Inception</code>)\n\n"
        f"📌 /help — yordam\n"
        f"🔍 /search — qidirish"
    )
    keyboard = [
        [InlineKeyboardButton("🔍 Qidirish", callback_data="search_mode"),
         InlineKeyboardButton("📋 Barcha kinolar", callback_data="list_movies")],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>BOT QOIDALARI</b>\n\n"
        "🔢 <b>Kod orqali:</b>\n"
        "  Kino kodini yozing → kino yuboriladi\n\n"
        "🔍 <b>Nom orqali:</b>\n"
        "  Kino nomini yozing → natijalar ro'yxati\n\n"
        "📂 /list — barcha kinolar ro'yxati\n"
        "🔍 /search [nom] — nom orqali qidirish\n\n"
    )
    if is_admin(update.effective_user.id):
        text += (
            "👑 <b>ADMIN BUYRUQLARI:</b>\n"
            "/add — yangi kino qo'shish\n"
            "/delete [kod] — kinoni o'chirish\n"
            "/stats — statistika\n"
            "/list_all — barchasi\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")

async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = get_all_movies()
    if not movies:
        await update.message.reply_text("📭 Hozircha kinolar yo'q.")
        return

    text = f"🎬 <b>Kinolar ro'yxati ({len(movies)} ta):</b>\n\n"
    for code, movie in list(movies.items())[:30]:
        year = f" ({movie.get('year', '')})" if movie.get("year") else ""
        text += f"• <code>{code}</code> — {movie['title']}{year}\n"

    if len(movies) > 30:
        text += f"\n... va yana {len(movies) - 30} ta kino"

    await update.message.reply_text(text, parse_mode="HTML")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        query = " ".join(context.args)
        await do_search(update, query)
    else:
        await update.message.reply_text(
            "🔍 Qidirish uchun kino nomini yozing:\n\n"
            "Masalan: <code>Inception</code> yoki <code>O'zbek kino</code>",
            parse_mode="HTML"
        )

async def do_search(update: Update, query: str):
    results = search_movies_by_name(query)
    if not results:
        await update.message.reply_text(
            f"😕 <b>«{query}»</b> bo'yicha hech narsa topilmadi.\n\n"
            "Boshqa nom bilan urinib ko'ring.",
            parse_mode="HTML"
        )
        return

    text = f"🔍 <b>«{query}»</b> bo'yicha natijalar ({len(results)} ta):\n\n"
    keyboard = []
    for code, movie in results:
        year = f" ({movie.get('year', '')})" if movie.get("year") else ""
        text += f"<code>{code}</code> — {movie['title']}{year}\n"
        keyboard.append([InlineKeyboardButton(
            f"🎬 {movie['title']}{year}",
            callback_data=f"get_{code}"
        )])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Admin kino yuklash jarayoni
    pending = get_pending(user_id)
    if pending and is_admin(user_id):
        await handle_admin_upload(update, context, pending, text)
        return

    # Kod (1-5 raqam) tekshirish
    if is_valid_code(text):
        movie = get_movie_by_code(text)
        if movie:
            await send_movie(update, context, text, movie)
        else:
            await update.message.reply_text(
                f"❌ <b>{text}</b> kodli kino topilmadi.\n\n"
                "🔍 Nom orqali qidirish uchun kino nomini yozing.",
                parse_mode="HTML"
            )
        return

    # Nom orqali qidirish (3+ harf bo'lsa)
    if len(text) >= 3:
        results = search_movies_by_name(text)
        if results:
            await do_search(update, text)
            return

    await update.message.reply_text(
        "🤔 Tushunmadim.\n\n"
        "• Kino <b>kodini</b> yozing (masalan: <code>42</code>)\n"
        "• Yoki kino <b>nomini</b> yozing (masalan: <code>Titanic</code>)",
        parse_mode="HTML"
    )

async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str, movie: dict):
    caption = movie_caption(code, movie)
    keyboard = [[InlineKeyboardButton("🔍 Yana qidirish", callback_data="search_mode")]]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        file_id = movie["file_id"]
        file_type = movie.get("file_type", "video")

        if file_type == "video":
            await update.message.reply_video(
                video=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        elif file_type == "document":
            await update.message.reply_document(
                document=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        elif file_type == "photo":
            await update.message.reply_photo(
                photo=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Kino yuborishda xato: {e}")
        await update.message.reply_text(
            f"❌ Kinoni yuborishda xatolik yuz berdi.\n\nAdmin bilan bog'laning.",
            parse_mode="HTML"
        )


# ─────────────────────────────────────────────
#  ADMIN HANDLERLARI
# ─────────────────────────────────────────────

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return

    save_pending(update.effective_user.id, {"step": "wait_file"})
    await update.message.reply_text(
        "📤 <b>Yangi kino qo'shish</b>\n\n"
        "1️⃣ Avval kino faylini yuboring (video yoki dokument):",
        parse_mode="HTML"
    )

async def handle_admin_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, pending: dict, text: str):
    user_id = update.effective_user.id
    step = pending.get("step")

    # 1-qadam: fayl kutilmoqda
    if step == "wait_file":
        file_id = None
        file_type = None

        if update.message.video:
            file_id = update.message.video.file_id
            file_type = "video"
        elif update.message.document:
            file_id = update.message.document.file_id
            file_type = "document"
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_type = "photo"

        if file_id:
            pending.update({"step": "wait_code", "file_id": file_id, "file_type": file_type})
            save_pending(user_id, pending)
            await update.message.reply_text(
                "✅ Fayl qabul qilindi!\n\n"
                "2️⃣ Endi kino <b>kodini</b> yozing (1-99999 orasida raqam):\n\n"
                "Masalan: <code>42</code> yoki <code>1001</code>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ Fayl yuboring (video, document yoki rasm).")
        return

    # 2-qadam: kod
    if step == "wait_code":
        if not is_valid_code(text):
            await update.message.reply_text("❌ Kod 1-5 ta raqamdan iborat bo'lishi kerak. Qayta kiriting:")
            return
        if get_movie_by_code(text):
            await update.message.reply_text(
                f"⚠️ <code>{text}</code> kodi band! Boshqa kod kiriting:",
                parse_mode="HTML"
            )
            return
        pending.update({"step": "wait_title", "code": text.upper()})
        save_pending(user_id, pending)
        await update.message.reply_text(
            f"✅ Kod: <code>{text}</code>\n\n"
            "3️⃣ Kino <b>nomini</b> kiriting:",
            parse_mode="HTML"
        )
        return

    # 3-qadam: nom
    if step == "wait_title":
        pending.update({"step": "wait_year", "title": text})
        save_pending(user_id, pending)
        await update.message.reply_text(
            f"✅ Nom: {text}\n\n"
            "4️⃣ Chiqarilgan <b>yilini</b> kiriting (yoki o'tkazib yuborish uchun <code>-</code>):",
            parse_mode="HTML"
        )
        return

    # 4-qadam: yil
    if step == "wait_year":
        year = text if text != "-" and text.isdigit() else ""
        pending.update({"step": "wait_rating", "year": year})
        save_pending(user_id, pending)
        await update.message.reply_text(
            "5️⃣ <b>Reytingini</b> kiriting (masalan: <code>8.5</code>) yoki o'tkazib yuborish uchun <code>-</code>:",
            parse_mode="HTML"
        )
        return

    # 5-qadam: reyting
    if step == "wait_rating":
        rating = ""
        if text != "-":
            try:
                r = float(text)
                if 0 <= r <= 10:
                    rating = str(r)
            except:
                pass
        pending.update({"step": "wait_genre", "rating": rating})
        save_pending(user_id, pending)
        await update.message.reply_text(
            "6️⃣ <b>Janrini</b> kiriting (masalan: <code>Jangari, Drama</code>) yoki <code>-</code>:",
            parse_mode="HTML"
        )
        return

    # 6-qadam: janr
    if step == "wait_genre":
        genres = [g.strip() for g in text.split(",")] if text != "-" else []
        pending.update({"step": "wait_lang", "genres": genres})
        save_pending(user_id, pending)
        keyboard = [
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
             InlineKeyboardButton("🇷🇺 Rus", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 Ingliz", callback_data="lang_en"),
             InlineKeyboardButton("⏭️ O'tkazib yuborish", callback_data="lang_skip")]
        ]
        await update.message.reply_text(
            "7️⃣ <b>Tilini</b> tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # 8-qadam: tavsif
    if step == "wait_desc":
        description = text if text != "-" else ""
        await finalize_movie(update, context, user_id, pending, description)
        return

async def finalize_movie(update_or_query, context, user_id: int, pending: dict, description: str):
    movie_data = {
        "title": pending["title"],
        "file_id": pending["file_id"],
        "file_type": pending.get("file_type", "video"),
        "year": pending.get("year", ""),
        "rating": pending.get("rating", ""),
        "genres": pending.get("genres", []),
        "language": pending.get("language", ""),
        "description": description,
    }
    code = pending["code"]
    add_movie(code, movie_data)
    clear_pending(user_id)

    text = (
        f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🎬 {movie_data['title']}\n"
        f"🔑 Kod: <code>{code}</code>\n"
    )
    if movie_data["year"]:
        text += f"📅 Yil: {movie_data['year']}\n"
    if movie_data["rating"]:
        text += f"⭐ Reyting: {movie_data['rating']}/10\n"

    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text(text, parse_mode="HTML")
    else:
        await update_or_query.edit_message_text(text, parse_mode="HTML")

async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return

    if not context.args:
        await update.message.reply_text(
            "Foydalanish: <code>/delete KOD</code>\n\nMasalan: <code>/delete 42</code>",
            parse_mode="HTML"
        )
        return

    code = context.args[0].upper()
    movie = get_movie_by_code(code)
    if not movie:
        await update.message.reply_text(f"❌ <code>{code}</code> kodli kino topilmadi.", parse_mode="HTML")
        return

    keyboard = [[
        InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_delete_{code}"),
        InlineKeyboardButton("❌ Yo'q", callback_data="cancel_delete")
    ]]
    await update.message.reply_text(
        f"⚠️ <b>{movie['title']}</b> kinoni o'chirishni tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return

    movies = get_all_movies()
    genre_count = {}
    for movie in movies.values():
        for g in movie.get("genres", []):
            genre_count[g] = genre_count.get(g, 0) + 1

    text = f"📊 <b>BOT STATISTIKASI</b>\n\n"
    text += f"🎬 Jami kinolar: <b>{len(movies)}</b>\n\n"

    if genre_count:
        text += "📂 Janr bo'yicha:\n"
        for genre, count in sorted(genre_count.items(), key=lambda x: -x[1]):
            text += f"  • {genre}: {count} ta\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ─────────────────────────────────────────────
#  CALLBACK HANDLER
# ─────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Kino olish
    if data.startswith("get_"):
        code = data[4:]
        movie = get_movie_by_code(code)
        if movie:
            await send_movie_from_callback(query, context, code, movie)
        else:
            await query.edit_message_text("❌ Bu kino o'chirilgan yoki topilmadi.")
        return

    # Qidirish rejimi
    if data == "search_mode":
        await query.edit_message_text(
            "🔍 Kino nomini yozing:",
            parse_mode="HTML"
        )
        return

    # Barcha kinolar
    if data == "list_movies":
        movies = get_all_movies()
        if not movies:
            await query.edit_message_text("📭 Hozircha kinolar yo'q.")
            return
        text = f"🎬 <b>Barcha kinolar ({len(movies)} ta):</b>\n\n"
        keyboard = []
        for code, movie in list(movies.items())[:20]:
            year = f" ({movie.get('year', '')})" if movie.get("year") else ""
            keyboard.append([InlineKeyboardButton(
                f"🎬 {movie['title']}{year} [{code}]",
                callback_data=f"get_{code}"
            )])
        await query.edit_message_text(
            text + "Quyidan tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Yordam
    if data == "help":
        await query.edit_message_text(
            "📖 <b>YORDAM</b>\n\n"
            "• Kino kodini yozing (1-5 raqam)\n"
            "• Kino nomini yozing (avtomatik qidiradi)\n"
            "• /list — barcha kinolar ro'yxati\n"
            "• /search nom — qidirish",
            parse_mode="HTML"
        )
        return

    # Til tanlash (admin)
    if data.startswith("lang_") and is_admin(user_id):
        pending = get_pending(user_id)
        if not pending:
            return
        lang_map = {"lang_uz": "O'zbek", "lang_ru": "Rus", "lang_en": "Ingliz", "lang_skip": ""}
        language = lang_map.get(data, "")
        pending.update({"step": "wait_desc", "language": language})
        save_pending(user_id, pending)
        await query.edit_message_text(
            "8️⃣ <b>Tavsif</b> kiriting (qisqacha) yoki <code>-</code>:",
            parse_mode="HTML"
        )
        return

    # O'chirishni tasdiqlash
    if data.startswith("confirm_delete_") and is_admin(user_id):
        code = data[len("confirm_delete_"):]
        movie = get_movie_by_code(code)
        name = movie["title"] if movie else code
        delete_movie(code)
        await query.edit_message_text(f"✅ <b>{name}</b> o'chirildi.", parse_mode="HTML")
        return

    if data == "cancel_delete":
        await query.edit_message_text("❌ O'chirish bekor qilindi.")
        return

async def send_movie_from_callback(query, context, code: str, movie: dict):
    caption = movie_caption(code, movie)
    keyboard = [[InlineKeyboardButton("🔍 Yana qidirish", callback_data="search_mode")]]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        file_id = movie["file_id"]
        file_type = movie.get("file_type", "video")

        if file_type == "video":
            await query.message.reply_video(video=file_id, caption=caption, parse_mode="HTML", reply_markup=markup)
        elif file_type == "document":
            await query.message.reply_document(document=file_id, caption=caption, parse_mode="HTML", reply_markup=markup)
        elif file_type == "photo":
            await query.message.reply_photo(photo=file_id, caption=caption, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        logger.error(f"Callback dan kino yuborishda xato: {e}")


# ─────────────────────────────────────────────
#  MEDIA HANDLER (admin fayl yuborish)
# ─────────────────────────────────────────────

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    pending = get_pending(user_id)
    if pending and pending.get("step") == "wait_file":
        await handle_admin_upload(update, context, pending, "")


# ─────────────────────────────────────────────
#  BOTNI ISHGA TUSHIRISH
# ─────────────────────────────────────────────

def main():
    print("🤖 CineBot ishga tushmoqda...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Foydalanuvchi buyruqlari
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_movies))
    app.add_handler(CommandHandler("search", search_command))

    # Admin buyruqlari
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CommandHandler("delete", admin_delete))
    app.add_handler(CommandHandler("stats", admin_stats))

    # Media (video, document, rasm)
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL | filters.PHOTO, handle_media))

    # Matn
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Callback (inline tugmalar)
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
