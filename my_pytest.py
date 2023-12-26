import unittest
from unittest.mock import patch, MagicMock
from aiogram import types
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

from main import start

API_TOKEN = '6436810765:AAGNGi5z6WSMa9Jxl5jq0ihQAZSzrCz0NZ8'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# Mock объект для эмуляции сообщения от пользователя
class MockMessage(types.Message):
    def __init__(self, text, chat_id):
        super().__init__(text=text, chat=types.Chat(id=chat_id), from_user=types.User(id=1))


class TestYourBot(unittest.TestCase):
    @patch('aiogram.Bot', autospec=True)
    @patch('aiogram.contrib.fsm_storage.memory.MemoryStorage', autospec=True)
    def setUp(self, mock_bot, mock_memory_storage):
        self.bot = mock_bot.return_value
        self.storage = mock_memory_storage.return_value
        self.dp = dp

    @patch('aiogram.dispatcher.FSMContext', autospec=True)
    async def test_start_command(self, mock_fsm_context):
        # Создаем объект состояния
        state = mock_fsm_context.return_value

        # Эмулируем команду /start
        message = MockMessage(text='/start', chat_id=123)

        with patch('aiogram.types.ReplyKeyboardMarkup', autospec=True) as mock_reply_keyboard:
            with patch('aiogram.types.KeyboardButton', autospec=True):
                expected_keyboard = mock_reply_keyboard.return_value
                await start(message, state)

                # Проверяем, что бот отправил ожидаемое сообщение
                self.bot.send_message.assert_called_once_with(
                    chat_id=message.chat.id,
                    text="Выберите действие:",
                    reply_markup=expected_keyboard
                )

                # Проверяем, что клавиатура была создана и добавлена к сообщению
                mock_reply_keyboard.assert_called_once_with(resize_keyboard=True)
                mock_reply_keyboard.return_value.add.assert_called_once_with(
                    "Просмотр списка маршрутов", "Выбрать маршрут", "Отправить местоположение",
                    "Указать место назначения"
                )


if __name__ == '__main__':
    unittest.main()
