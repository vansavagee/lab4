import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import asyncio
from aiogram.filters import Command
from dotenv import load_dotenv
import openai

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токены из переменных окружения
API_TOKEN = os.getenv('BOT_API_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not API_TOKEN:
    raise ValueError("API_TOKEN не найден в файле .env")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в файле .env")

# Включаем логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)

dp = Dispatcher()

# Инициализация OpenAI API
openai.api_key = OPENAI_API_KEY

# Глобальная переменная для хранения данных пользователя
user_data = {}

@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать", callback_data="start")],
            [InlineKeyboardButton(text="Помощь", callback_data="help")]
        ]
    )
    await message.answer("Добро пожаловать в бота-диетолога!", reply_markup=keyboard)

@dp.callback_query()
async def handle_callbacks(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if callback_query.data == "help":
        await callback_query.message.edit_text("Это бот диетолог")
    elif callback_query.data == "start":
        await callback_query.message.edit_text(
            "Какова ваша цель? Поддержание веса, похудение, набор массы или просто здоровое питание?"
        )
        user_data[user_id] = {"step": "aim"}

@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_data and user_data[user_id].get("step") == "aim":
        user_data[user_id]["aim"] = message.text
        user_data[user_id]["step"] = "details"
        await message.answer(
            "Укажите через пробел ваш возраст (лет), рост (см) и вес (кг), чтобы рассчитать вашу дневную норму калорий."
        )
    elif user_id in user_data and user_data[user_id].get("step") == "details":
        user_data[user_id]["params"] = message.text
        user_data[user_id]["step"] = "activity"
        await message.answer(
            "Какой у вас уровень физической активности? Низкий, умеренный или высокий?"
        )
    elif user_id in user_data and user_data[user_id].get("step") == "activity":
        user_data[user_id]["activity"] = message.text
        user_data[user_id]["step"] = "budget"
        await message.answer(
            "Какой бюджет (руб) вы планируете на неделю (приблизительно)?"
        )
    elif user_id in user_data and user_data[user_id].get("step") == "budget":
        user_data[user_id]["budget"] = message.text
        user_data[user_id]["step"] = "preferences"
        await message.answer(
            "Напишите про ваши какие-либо ограничения или предпочтения по питанию."
        )
    elif user_id in user_data and user_data[user_id].get("step") == "preferences":
        user_data[user_id]["preferences"] = message.text

        # Формирование промпта для OpenAI API
        prompt = (f"Составь недельное меню, которое включает сбалансированный рацион питания.\n"
                  f"Цель питания: {user_data[user_id]['aim']}.\n"
                  f"Возраст (лет), Рост (см) , Вес (кг): {user_data[user_id]['params']}.\n"
                  f"Уровень физической активности: {user_data[user_id]['activity']}.\n"
                  f"Ограничения или предпочтения: {user_data[user_id]['preferences']}.\n"
                  f"Бюджет на неделю: {user_data[user_id]['budget']} рублей.\n\n"
                  "Меню должно быть разнообразным, учитывать указанные ограничения. Укажи калорийность каждого блюда. Пиши кратко и структурированно.")

        # Логируем промпт
        logging.info(f"Generated prompt for OpenAI: {prompt}")

        # Отправка запроса в OpenAI API
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful diet assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            menu = response['choices'][0]['message']['content']
            await message.answer(f"Вот ваше меню на неделю:\n{menu}"
                                 "Помните, что данная информация явлеятся лишь рекомандацией и перед следванием данной рекомандации стоит проконсультироваться со специалистом.")
        except Exception as e:
            logging.error(f"Error while generating menu: {e}")
            await message.answer("Произошла ошибка при составлении меню. Попробуйте позже.")

async def delete_webhook():
    await bot.delete_webhook()

async def on_start():
    await delete_webhook()
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(on_start())
