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

# API-ключ для Telegram Bot API
API_TOKEN = '6436810765:AAGNGi5z6WSMa9Jxl5jq0ihQAZSzrCz0NZ8'

# API-ключ для Static API Yandex
api_key = '3936e5b7-220c-49f2-9715-f926cd686b84'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Словарь для хранения данных о маршрутах
# Здесь нужно будет добавить реальные данные о маршрутах
routes_data = {
    '22': {'name': 'Маршрут 22', 'coordinates': [[18.560364, 40.354126], [55.754, 37.620], [55.756, 37.622]]},
    # Добавьте другие маршруты по аналогии
}

# координаты в яндекс.картах менять местами необходимо
url_for_test = 'https://static-maps.yandex.ru/v1?lang=ru_RU&pl=48.55439632694345,54.35608323640922,' \
               '48.55622050135121,54.35750023872133,' \
               '48.55889198153004,54.35846523427855,48.56087681620108,54.358578024480806,' \
               '48.56346155352407,54.35758170026521,' \
               '48.564727556179115,54.35753783637713,48.56598051991628,54.35787676005814,' \
               '48.574066877540865,54.36146463563228,' \
               '48.57705910451171,54.36269462763428,48.58258125031516,54.365154317694476,' \
               '48.590735795658105,54.36872067244739,48.610957727662566,54.37769882245048' \
               '&apikey=3936e5b7-220c-49f2-9715-f926cd686b84'


# Обработчик команды /start. Также сбрасывает состояние пользователя
@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Просмотр списка маршрутов", "Выбрать маршрут", "Отправить местоположение", "Указать место назначения"]
    keyboard.add(*buttons)
    await message.answer("Выберите действие:", reply_markup=keyboard)

    # Сброс состояния пользователя при начале разговора
    await state.finish()


# Обработчик для кнопки "Просмотр списка маршрутов". Выполняется, когда пользователь также написал
# "Просмотр списка маршрутов"
@dp.message_handler(lambda message: message.text == "Просмотр списка маршрутов")
async def show_routes_list(message: types.Message, state: FSMContext):
    await state.update_data(current_step="show_routes_list")

    routes_list_text = "Список маршрутов:\n"
    for route_number, route_data in routes_data.items():
        routes_list_text += f"{route_number}. {route_data['name']}\n"

    await message.answer(routes_list_text, reply_markup=create_back_button())


# Обработчик для кнопки "Выбрать маршрут". Выполняется, когда пользователь также написал
# "Выбрать маршрут"
@dp.message_handler(lambda message: message.text == "Выбрать маршрут")
async def choose_route(message: types.Message, state: FSMContext):
    await state.update_data(current_step="choose_route")

    # Создаем кнопку "Назад"
    keyboard = create_back_button()

    await message.answer("Введите номер маршрута (например, 22):", reply_markup=keyboard)


# Обработчик для ввода номера маршрута при вызове функции choose_route
@dp.message_handler(lambda message: message.text.isdigit())
async def handle_route_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_step = data.get("current_step")

    if current_step != 'choose_route':
        await message.answer("Неверная команда", reply_markup=create_back_button())
        return

    # Получаем номер маршрута из сообщения
    route_number = message.text

    # Вызываем вторую функцию для отображения маршрута
    await show_route(message, state, route_number)


# Обработчик команды /show_route + номер маршрута. Срабатывает только на эту команду
@dp.message_handler(commands=['show_route'])
async def show_route(message: types.Message, state: FSMContext, route_number=None):
    await state.update_data(current_step="show_route")

    # Создаем кнопку "Назад"
    keyboard = create_back_button()

    # Проверяем, что пользователь указал номер маршрута
    if route_number is None and not message.get_args():
        route_number = message.get_args()

    if route_number in routes_data:
        try:
            # Тут надо вытаскивать массив координат и по ним строить путь
            route_coordinates = routes_data[route_number]['coordinates'][0]
            # Выполняем запрос к Yandex Maps API для получения данных о маршруте
            response = requests.get(
                f'https://static-maps.yandex.ru/v1?apikey={api_key}&ll={route_coordinates[0]},{route_coordinates[1]}'
                f'&spn=1,1')
            data = response.content

            await message.answer_photo(data, reply_markup=keyboard)

        except Exception as e:
            logging.error(f"Error fetching or processing route: {e}")
            await message.answer('Произошла ошибка при построении маршрута', reply_markup=keyboard)
    else:
        await message.answer("Маршрут не найден. Введите корректный номер маршрута", reply_markup=keyboard)


# Обработчик для кнопки "Отправить местоположение". Пользователь отправляет своё местоположение
@dp.message_handler(lambda message: message.text == "Отправить местоположение")
async def request_location(message: types.Message, state: FSMContext):
    await state.update_data(current_step="request_location")

    keyboard = create_back_button()
    button = types.KeyboardButton("Отправить местоположение", request_location=True)
    keyboard.add(button)

    await message.answer("Отправьте ваше текущее местоположение:", reply_markup=keyboard)


# Обработчик для кнопки "Отправить местоположение". Пользователь отправляет своё местоположение.
# В данной функции мы получаем местоположение пользователя. Надо из него вытаскивать его координаты
# и на их основе предлагать ему проезжающий транспорт
@dp.message_handler(content_types=types.ContentType.LOCATION)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(current_step="process_location")

    # Здесь вы можете обработать полученные координаты и отправить список маршрутов рядом
    await message.answer("Список маршрутов в вашем районе:", reply_markup=create_back_button())


# Выводит кнопку "Указать место назначения". В текстовом формате спрашивает у пользователя место назначения.
# Мы должны строить путь между его местоположением - поэтому надо хранить его последнее местоположение, если его нет, то
# выводить ошибку.
@dp.message_handler(lambda message: message.text == "Указать место назначения")
async def request_destination(message: types.Message, state: FSMContext):
    await state.update_data(current_step="request_destination")

    await message.answer("Введите место назначения (например, улица Языкова):", reply_markup=create_back_button())


# Обработчик для кнопки "Назад" на шаге выбора маршрута. Пока что возвращает на команду /start
@dp.message_handler(lambda message: message.text == "Назад", state='*')
async def back_to_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_step = data.get("current_step")

    # В зависимости от текущего шага, выполните соответствующее действие
    if current_step == "process_destination":
        return await start(message, state)

    # Пока пусть возвращаются на начальное меню
    return await start(message, state)


# Обработчик для кнопки "Указать место назначения". В текстовом формате спрашивает у пользователя место назначения.
# Мы должны строить путь между его местоположением и отдавать ему план поездки
# - поэтому надо хранить его последнее местоположение, если его нет, то выводить ошибку
@dp.message_handler(lambda message: True)
async def process_destination(message: types.Message, state: FSMContext):
    await state.update_data(current_step="process_destination")

    destination = message.text
    # Здесь вы можете обработать место назначения и отправить список транспорта
    await message.answer("Список транспорта и места пересадок:", reply_markup=create_back_button())


# Функция для создания изображения карты с маршрутом
def create_route_image(route_coordinates):
    # Здесь вам нужно реализовать логику создания изображения с маршрутом
    # Пример использования Pillow:
    image = Image.new('RGB', (500, 500), color='white')
    draw = ImageDraw.Draw(image)

    # Пример: рисование линии маршрута
    draw.line(route_coordinates, fill='blue', width=3)

    return image


# Функция для отправки изображения. Принимает номер чата, картинку (в виде набора байтов), а также клавиватуру
async def send_image(chat_id, image, keyboard):
    with BytesIO() as bio:
        image.save(bio, format='PNG')
        bio.seek(0)
        await bot.send_photo(chat_id, bio, reply_markup=keyboard)


# Добавление кнопки "Назад"
def create_back_button():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton("Назад")
    keyboard.add(back_button)
    return keyboard


# Запуск бота
if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
