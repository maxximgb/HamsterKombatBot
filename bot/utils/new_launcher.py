import asyncio
import argparse
from contextlib import redirect_stdout
from io import StringIO
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from pyrogram import Client
from kivy.uix.button import Button
from bot.config import settings
from bot.utils import logger
from bot.utils.proxy import get_proxy_string
from bot.utils.scripts import get_session_names
from bot.core.tapper import run_tapper
from bot.core.new_registrator import register_sessions


banner = """

▒█ ▒█ █▀▀█ █▀▄▀█ █▀▀ ▀▀█▀▀ █▀▀ █▀▀█ ▒█ ▄▀ █▀▀█ █▀▄▀█ █▀▀▄ █▀▀█ ▀▀█▀▀ ▒█▀▀█ █▀▀█ ▀▀█▀▀ 
▒█▀▀█ █▄▄█ █ ▀ █ ▀▀█   █   █▀▀ █▄▄▀ ▒█▀▄  █  █ █ ▀ █ █▀▀▄ █▄▄█   █   ▒█▀▀▄ █  █   █   
▒█ ▒█ ▀  ▀ ▀   ▀ ▀▀▀   ▀   ▀▀▀ ▀ ▀▀ ▒█ ▒█ ▀▀▀▀ ▀   ▀ ▀▀▀  ▀  ▀   ▀   ▒█▄▄█ ▀▀▀▀   ▀  

"""
options = """
Select an action:

    1. Create session
    2. Run clicker
"""


async def get_tg_clients() -> list[Client]:
    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [Client(
        name=session_name,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        workdir='sessions/',
    ) for session_name in session_names]

    return tg_clients


async def process(args) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', type=int, help='Action to perform')

    print(banner)

    logger.info(f"Detected {len(get_session_names())} sessions")

    action = args

    if not action:
        print(options)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ['1', '2']:
                logger.warning("Action must be 1 or 2")
            else:
                action = int(action)
                break

    if action == 1:
        await register_sessions()
    elif action == 2:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)


async def run_tasks(tg_clients: list[Client], app, saved_layout):
    f = StringIO()
    label = Label(size_hint_y=None, text_size=(app.root.width, None), markup=True)
    new_layout = BoxLayout(orientation='vertical')
    new_layout.add_widget(label)

    # Create a back button
    back_button = Button(text='Back', size_hint=(None, None), size=(100, 50), pos_hint={'right': 1, 'top': 1})
    new_layout.add_widget(back_button)

    # Function to go back to the previous layout
    def go_back(instance):
        app.root.clear_widgets()
        for widget in saved_layout:
            app.root.add_widget(widget)
        for task in tasks:
            task.cancel()

    back_button.bind(on_press=go_back)

    app.root.add_widget(new_layout)

    async def update_text():
        while True:
            label.text = f.getvalue().replace('\n', '[color=000000]\n[/color]')
            label.height = label.texture_size[1]
            await asyncio.sleep(1)

    with redirect_stdout(f):
        print('bot work started')
        logger.add(f, format="<green>{time}</green> <level>{message}</level>")
        tasks = [asyncio.create_task(run_tapper(tg_client=tg_client, proxy=get_proxy_string(tg_client.name)))
                 for tg_client in tg_clients]
        tasks.append(asyncio.create_task(update_text()))
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print('Tasks cancelled')
