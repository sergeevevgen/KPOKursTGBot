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
    # '22': {'name': 'Маршрут №22', 'file': '22marsh.txt'},
    # '42': {'name': 'Маршрут №42', 'file': '42marsh.txt'},
    '78': {'name': 'Маршрут №78', 'file': '78marsh.txt'},
    '84': {'name': 'Маршрут №84', 'file': '84marsh.txt'},
    '82': {'name': 'Маршрут №82', 'file': '82marsh.txt'},
    # Другие маршруты
}

# координаты в яндекс.картах менять местами необходимо
base_url = 'https://static-maps.yandex.ru/v1?lang=ru_RU&pl='


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
            file_c = routes_data[route_number]['file']

            with open(file_c, 'r') as file:
                # Читаем содержимое файла и записываем его в переменную
                file_content = file.read()

            # Разделяем строки по символу новой строки и удаляем пробелы
            lines_without_whitespace = [line.strip() for line in file_content.split('\n')]

            # Объединяем строки обратно в одну строку
            coordinates = ''.join(lines_without_whitespace)

            url_for_marsh = base_url + coordinates + f'&apikey={api_key}'
            # Выполняем запрос к Yandex Maps API для получения данных о маршруте
            response = requests.get(url_for_marsh)

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

    # Получаем широту и долготу из объекта message.location
    latitude = message.location.latitude
    longitude = message.location.longitude

    # Порог для сравнения координат
    # threshold = 0.02
    #
    # # Перебираем маршруты и проверяем, находится ли пользователь вблизи какой-либо точки маршрута
    # for route_id, route_data in routes_data.items():
    #     file_path = route_data['file']
    #     route_coordinates = read_coordinates_from_file(file_path)
    #
    #     # Проверяем, находится ли пользователь вблизи какой-либо координаты маршрута
    #     for coord in route_coordinates:
    #         if abs(coord[0] - latitude) < threshold and abs(coord[1] - longitude) < threshold:
    #             await message.answer(f"Ваше местоположение близко к маршруту {route_id}: {route_data['name']}")
    #             break
    #     else:
    #         continue  # Продолжаем поиск в других маршрутах
    #     break  # Выход из внешнего цикла, если найдено совпадение
    #
    # else:
    #     await message.answer("Ваше местоположение не близко ни к одному из маршрутов.")

    # Здесь вы можете обработать полученные координаты и отправить список маршрутов рядом
    routes_list_text = "Список маршрутов, близких к вам:\n"
    for route_number, route_data in routes_data.items():
        routes_list_text += f"{route_number}. {route_data['name']}\n"

    await message.answer(routes_list_text, reply_markup=create_back_button())


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

    destination = message.text.split(':')
    path_to = f'Чтобы добраться от места {destination[0]} до места {destination[1]}, вам необходимо:\n' \
              'Дойти до остановки Деева, направленной в сторону Верхней Террасы (500м).' \
              'Сесть на маршрутное такси № 78. Ехать до остановки УлГТУ (ул. Докучаева).\n ' \
              'Альтернативный путь: Дойти до остановки ТЦ Мегастрой, направленной в сторону Верхней Террасы (500м).' \
              'Сесть на маршрутное такси № 82. Ехать до остановки Маяковского. Пройти до места назначения (1.3км)'
    # Здесь вы можете обработать место назначения и отправить список транспорта
    await message.answer(path_to, reply_markup=create_back_button())


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


def read_coordinates_from_file(file_path):
    with open(file_path, 'r') as file:
        coordinates = [tuple(map(float, line.strip().split(','))) for line in file]
    return coordinates


def coordinates_in_range(coord, range_min, range_max):
    return range_min[0] <= coord[0] <= range_max[0] and range_min[1] <= coord[1] <= range_max[1]


# Запуск бота
if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
