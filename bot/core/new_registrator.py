import asyncio

from bot.config import settings
from bot.utils import logger
from bot.utils.default import DEFAULT_HEADERS, DEFAULT_FINGERPRINT
from bot.utils.json_db import JsonDB
from bot.utils.proxy import get_proxy_dict
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PasswordHashInvalid, PhoneCodeInvalid


async def register_sessions(app) -> int:
    API_ID = settings.API_ID
    API_HASH = settings.API_HASH

    if not API_ID or not API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    session_name = await app.get_input('Ввод имени сессии', 'Назовите сессию', 'Название сессии')

    if not session_name:
        return 0

    proxy = ''

    proxy_dict = get_proxy_dict(proxy)
    phone_number = await app.get_input('Ввод номера телефона', 'Номер телефона',
                                       'Введите номер телефона на который зарегистрирован аккаунт телеграм')
    session = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir="sessions/",
        proxy=proxy_dict,
    )
    l = Label(text='Подключение к серверам телеграм')
    app.root.add_widget(l)
    pb = ProgressBar(max=100)
    app.root.add_widget(pb)
    app.progress_bar.value = 50
    await session.connect()
    app.progress_bar.value = 100
    await asyncio.sleep(1)
    app.root.clear_widgets()
    l = Label(text='Отправка кода')
    app.root.add_widget(l)
    pb = ProgressBar(max=100)
    app.root.add_widget(pb)
    app.progress_bar.value = 50
    sent_code_info = await session.send_code(phone_number)
    app.progress_bar.value = 100

    try:
        phone_code = await app.get_input('Ввод кода', 'Код', 'Введите код полученный из телеграм')
        await session.sign_in(phone_number, sent_code_info.phone_code_hash, phone_code)
    except SessionPasswordNeeded:
        password = await app.get_input('Ввод пароля', 'Пароль', 'Введите ваш пароль от телеграм аккаунта')
        try:
            await session.check_password(password)
        except PasswordHashInvalid:
            exit(1)
    except PhoneCodeInvalid:
        exit(1)
    user_data = await session.get_me()

    app.root.text = f'Session added successfully @{user_data.username} | {user_data.first_name} {user_data.last_name}'

    db = JsonDB("profiles")

    data = db.get_data()

    data[session_name] = {
        "proxy": proxy,
        "headers": DEFAULT_HEADERS,
        "fingerprint": DEFAULT_FINGERPRINT,
    }

    db.save_data(data)
    await session.disconnect()
    return 1
