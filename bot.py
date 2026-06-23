import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
TOKEN = "8014335358:AAHGoMN6zU8fCJgGhU1Y625PU3KwyAY2cAI"
ADMIN_ID = 8325726426  # O'z telegram ID'ngizni kiriting
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bazani ulash
conn = sqlite3.connect("movies.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    code TEXT,
    title TEXT,
    bio TEXT)""")
conn.commit()

# --- HOLATLAR (STATES) ---
class MovieState(StatesGroup):
    waiting_for_video = State()
    waiting_for_name = State()
    waiting_for_code = State()
    waiting_for_bio = State()

# --- MENU ---
def main_menu():
    kb = [
        [KeyboardButton(text="Kod orqali qidirish"), KeyboardButton(text="Nom orqali qidirish")],
        [KeyboardButton(text="Bizning kanal")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Xush kelibsiz! Kino botiga kiring.", reply_markup=main_menu())
    if message.from_user.id == ADMIN_ID:
        await message.answer("Siz adminsiz. Kino qo'shish uchun: /add_movie")

# --- ADMIN: KINO QO'SHISH ---
@dp.message(Command("add_movie"))
async def add_movie(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kinoni yuboring:")
        await state.set_state(MovieState.waiting_for_video)

@dp.message(MovieState.waiting_for_video, F.video)
async def get_video(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("Kino nomini kiriting:")
    await state.set_state(MovieState.waiting_for_name)

@dp.message(MovieState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Kino uchun kodni yozing:")
    await state.set_state(MovieState.waiting_for_code)

@dp.message(MovieState.waiting_for_code)
async def get_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Bio yozing (o'tkazib yuborish uchun /skip yozing):")
    await state.set_state(MovieState.waiting_for_bio)

@dp.message(MovieState.waiting_for_bio)
async def finish_add(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bio = message.text if message.text != "/skip" else "-"
    
    cursor.execute("INSERT INTO movies (file_id, code, title, bio) VALUES (?, ?, ?, ?)", 
                   (data['file_id'], data['code'], data['name'], bio))
    conn.commit()
    await message.answer("✅ Kino muvaffaqiyatli saqlandi!")
    await state.clear()

# --- QIDIRUV ---
@dp.message(F.text == "Kod orqali qidirish")
async def ask_code(message: types.Message, state: FSMContext):
    await message.answer("Kodini yuboring:")
    await state.set_state("waiting_code_search")

@dp.message(F.state == "waiting_code_search")
async def find_by_code(message: types.Message, state: FSMContext):
    cursor.execute("SELECT * FROM movies WHERE code=?", (message.text,))
    row = cursor.fetchone()
    if row:
        await bot.send_video(message.chat.id, row[1], caption=f"🎬 {row[3]}\nℹ️ {row[4]}")
    else:
        await message.answer("Bunday kodli kino topilmadi.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
