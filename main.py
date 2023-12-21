import logging
import os
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext

# Устанавливаем уровень логгирования
logging.basicConfig(level=logging.INFO)

# Замените 'YOUR_BOT_TOKEN' на реальный токен вашего бота
API_TOKEN = '6436810765:AAGNGi5z6WSMa9Jxl5jq0ihQAZSzrCz0NZ8'

# Замените 'YOUR_YANDEX_API_KEY' на ваш реальный ключ
api_key = 'YOUR_YANDEX_API_KEY'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Словарь для хранения данных о маршрутах
# Здесь нужно будет добавить реальные данные о маршрутах
routes_data = {
    '22': {'name': 'Маршрут 22', 'coordinates': [[55.752, 37.616], [55.754, 37.620], [55.756, 37.622]]},
    # Добавьте другие маршруты по аналогии
}


# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Просмотр списка маршрутов", "Выбрать маршрут", "Отправить местоположение", "Указать место назначения"]
    keyboard.add(*buttons)
    await message.answer("Выберите действие:", reply_markup=keyboard)

    # Сброс состояния пользователя при начале разговора
    await state.finish()


# Обработчик для кнопки "Просмотр списка маршрутов"
@dp.message_handler(lambda message: message.text == "Просмотр списка маршрутов")
async def show_routes_list(message: types.Message, state: FSMContext):
    await state.update_data(current_step="show_routes_list")

    routes_list_text = "Список маршрутов:\n"
    for route_number, route_data in routes_data.items():
        routes_list_text += f"{route_number}. {route_data['name']}\n"

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)
    await message.answer(routes_list_text, reply_markup=keyboard)


# Обработчик для кнопки "Выбрать маршрут"
@dp.message_handler(lambda message: message.text == "Выбрать маршрут")
async def choose_route(message: types.Message, state: FSMContext):
    await state.update_data(current_step="choose_route")

    await message.answer("Введите номер маршрута (например, 22):")


# Обработчик для кнопки "Назад" на шаге выбора маршрута
@dp.message_handler(lambda message: message.text == "Назад", state='*')
async def back_to_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_step = data.get("current_step")

    # Пока пусть возвращаются на начальное меню
    return await start(message, state)
    # В зависимости от текущего шага, выполните соответствующее действие
    if current_step == "show_routes_list":
        return await start(message, state)
    elif current_step == "choose_route":
        return await start(message, state)


# Обработчик команды /show_route
@dp.message_handler(commands=['show_route'])
async def show_route(message: types.Message, state: FSMContext):
    await state.update_data(current_step="show_route")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)

    # Проверяем, что пользователь указал номер маршрута
    if not message.get_args():
        await message.answer('Пожалуйста, укажите номер маршрута.')
        return

    route_number = message.get_args()

    try:
        # Выполняем запрос к Yandex Maps API для получения данных о маршруте
        response = requests.get(
            f'https://api-maps.yandex.ru/services/route/2.0/?apikey={api_key}&from=место_отправления'
            f'&to={route_number}&format=json')
        data = response.json()

        # Получаем координаты маршрута (предполагаем, что они в формате [широта, долгота])
        route_coordinates = data['features'][0]['geometry']['coordinates']

        # Создаем изображение карты с маршрутом
        map_image = create_route_image(route_coordinates)

        # Отправляем изображение пользователю
        with BytesIO() as bio:
            map_image.save(bio, format='PNG')
            bio.seek(0)
            await message.answer_photo(bio, reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Error fetching or processing route: {e}")
        await message.answer('Произошла ошибка при построении маршрута.', reply_markup=keyboard)


@dp.message_handler(regexp=r'^\d+$')
async def process_route_choice(message: types.Message, state: FSMContext):
    await state.update_data(current_step="process_route_choice")
    route_number = message.text

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)

    if route_number in routes_data:
        route_coordinates = routes_data[route_number]['coordinates']
        map_image = Image.open('bot.jpg')
        # map_image = create_route_image(route_coordinates)
        await send_image(message.chat.id, map_image, keyboard)
    else:
        await message.answer("Маршрут не найден. Введите корректный номер маршрута.", reply_markup=keyboard)


# Функция для отправки изображения
async def send_image(chat_id, image, keyboard):
    with BytesIO() as bio:
        image.save(bio, format='PNG')
        bio.seek(0)
        await bot.send_photo(chat_id, bio, reply_markup=keyboard)


# Обработчик для кнопки "Отправить местоположение"
@dp.message_handler(lambda message: message.text == "Отправить местоположение")
async def request_location(message: types.Message, state: FSMContext):
    await state.update_data(current_step="request_location")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("Отправить местоположение", request_location=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(button)
    keyboard.add(back_button)

    await message.answer("Отправьте ваше текущее местоположение:", reply_markup=keyboard)


@dp.message_handler(content_types=types.ContentType.LOCATION)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(current_step="process_location")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)

    # Здесь вы можете обработать полученные координаты и отправить список маршрутов рядом
    await message.answer("Список маршрутов в вашем районе:", reply_markup=keyboard)


# Обработчик для кнопки "Указать место назначения"
@dp.message_handler(lambda message: message.text == "Указать место назначения")
async def request_destination(message: types.Message, state: FSMContext):
    await state.update_data(current_step="request_destination")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)

    await message.answer("Введите место назначения (например, улица Языкова):", reply_markup=keyboard)


@dp.message_handler(lambda message: True)
async def process_destination(message: types.Message, state: FSMContext):
    await state.update_data(current_step="process_destination")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)

    destination = message.text
    # Здесь вы можете обработать место назначения и отправить список транспорта
    await message.answer("Список транспорта и места пересадок:", reply_markup=keyboard)


# Функция для создания изображения карты с маршрутом
def create_route_image(route_coordinates):
    # Здесь вам нужно реализовать логику создания изображения с маршрутом
    # Пример использования Pillow:
    image = Image.new('RGB', (500, 500), color='white')
    draw = ImageDraw.Draw(image)

    # Пример: рисование линии маршрута
    draw.line(route_coordinates, fill='blue', width=3)

    return image


# Запуск бота
if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
