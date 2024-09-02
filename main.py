import ast
import asyncio
import os
import shutil
import ssl
import zipfile
import settings
import aiohttp
import certifi
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform

ssl.default_ca_certs = certifi.where()

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.button import Button


async def request_perms(app):
    if platform == "android":
        from android.permissions import request_permissions, Permission, check_permission
        request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
        await asyncio.sleep(1)
        read_permission = check_permission(Permission.READ_EXTERNAL_STORAGE)
        write_permission = check_permission(Permission.WRITE_EXTERNAL_STORAGE)

        if read_permission and write_permission:
            await app.on_success()
    else:
        await app.on_win()


async def mainloop(app):
    ssl._create_default_https_context = ssl._create_unverified_context
    await request_perms(app)


async def download_files(app):
    url = "https://github.com/maxximgb/HamsterKombatBot/archive/refs/heads/main.zip"
    version_url = "https://raw.githubusercontent.com/maxximgb/HamsterKombatBot/main/version.txt"

    async with aiohttp.ClientSession() as session:
        async with session.get(version_url, ssl=False) as version_response:
            remote_version = await version_response.text()
            app.version_label.text = f"Remote version: {remote_version.strip()}"

        local_version_path = "version.txt"
        if os.path.exists(local_version_path):
            with open(local_version_path, "r") as file:
                local_version = file.read().strip()
            if local_version == remote_version.strip():
                app.label.text = "No update needed."
                for i in range(1, 101):
                    await asyncio.sleep(0.03)
                    app.progress_bar.value = i
                await check_and_run_script(app)
                return
            else:
                app.label.text = "Update needed. Downloading new version..."
        else:
            app.label.text = "First run. Downloading files..."

        async with session.get(url, ssl=False) as response:
            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0:
                app.label.text = "Failed to get the file size."
                app.add_retry_button()
                return

            block_size = 1024
            progress = 0
            with open("main.zip", "wb") as file:
                async for data in response.content.iter_chunked(block_size):
                    file.write(data)
                    progress += len(data)
                    app.progress_bar.value = (progress / total_size) * 100

            extract_path = "HamsterKombatBot"
            with zipfile.ZipFile("main.zip", "r") as zip_ref:
                zip_ref.extractall(extract_path)
            os.remove("main.zip")
            app.label.text = "Download and extraction complete! "
            await asyncio.sleep(2)
            app.label.text = f"Files extracted to: {os.path.abspath(extract_path)}"

            # Copy files to current directory
            source_dir = os.path.join(extract_path, "HamsterKombatBot-main")
            for item in os.listdir(source_dir):
                s = os.path.join(source_dir, item)
                d = os.path.join(".", item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

            # Remove the extracted folder
            shutil.rmtree(extract_path)

            await check_and_run_script(app)


async def check_and_run_script(app):
    env_path = ".env"
    example_env_path = ".env-example"
    api_id = None
    api_hash = None
    env_lines = []
    example_lines = []

    if not os.path.exists(env_path) or os.path.getsize(env_path) == 0:
        if os.path.exists(example_env_path):
            with open(example_env_path, "r") as example_file:
                example_lines = example_file.readlines()
            with open(env_path, "w") as env_file:
                env_file.writelines(example_lines)
            env_lines = example_lines
        else:
            print(f"{example_env_path} not found.")
            return
    else:
        with open(env_path, "r") as file:
            env_lines = file.readlines()
        if os.path.exists(example_env_path):
            with open(example_env_path, "r") as example_file:
                example_lines = example_file.readlines()

    env_dict = {line.split("=")[0]: line for line in env_lines if "=" in line}
    example_dict = {line.split("=")[0]: line for line in example_lines if "=" in line}

    # Add missing lines from example to env
    for key, value in example_dict.items():
        if key not in env_dict:
            env_dict[key] = value

    # Remove lines from env that are not in example
    for key in list(env_dict.keys()):
        if key not in example_dict:
            del env_dict[key]

    # Write updated env_dict back to .env file
    with open(env_path, "w") as env_file:
        env_file.writelines(env_dict.values())

    for line in env_dict.values():
        if line.startswith("API_ID="):
            api_id = line.split("=")[1].strip()
        elif line.startswith("API_HASH="):
            api_hash = line.split("=")[1].strip()

    if api_id and api_hash:
        await run_script()
    else:
        await show_api_dialog(app, env_dict.values())


async def show_api_dialog(app, lines):
    await asyncio.sleep(2)
    layout = BoxLayout(orientation='vertical')
    layout.add_widget(Label(text='Для работы бота нужно ввести API_ID и API_HASH'))
    layout.add_widget(Label(text='Ссылка на YouTube: youtu.be'))

    api_id_layout = BoxLayout(orientation='horizontal')
    api_id_input = TextInput(hint_text='API_ID')
    api_id_layout.add_widget(api_id_input)
    paste_button_id = Button(text='Вставить', size_hint=(None, None), size=(80, 40))
    paste_button_id.bind(on_press=lambda instance: api_id_input.insert_text(Clipboard.paste()))
    api_id_layout.add_widget(paste_button_id)
    layout.add_widget(api_id_layout)

    api_hash_layout = BoxLayout(orientation='horizontal')
    api_hash_input = TextInput(hint_text='API_HASH')
    api_hash_layout.add_widget(api_hash_input)
    paste_button_hash = Button(text='Вставить', size_hint=(None, None), size=(80, 40))
    paste_button_hash.bind(on_press=lambda instance: api_hash_input.insert_text(Clipboard.paste()))
    api_hash_layout.add_widget(paste_button_hash)
    layout.add_widget(api_hash_layout)

    def save_and_run(instance):
        api_id = api_id_input.text
        api_hash = api_hash_input.text
        with open(".env", "w") as file:
            for line in lines:
                if line.startswith("API_ID="):
                    file.write(f"API_ID={api_id}\n")
                elif line.startswith("API_HASH="):
                    file.write(f"API_HASH={api_hash}\n")
                else:
                    file.write(line)
        popup.dismiss()
        asyncio.ensure_future(run_script())

    submit_button = Button(text='Ввести', on_press=save_and_run)
    layout.add_widget(submit_button)

    popup = Popup(title='Введите API_ID и API_HASH', content=layout, size_hint=(0.8, 0.8))
    popup.open()


async def parse_settings(file_path):
    settings = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = ast.literal_eval(value.strip())
                settings[key] = value
    return settings


def save_settings(filename):
    with open(filename, "w", encoding='utf-8') as f:
        for key, value in widget_references.items():
            a = getattr(settings, key)

            if isinstance(value, TextInput):
                try:
                    # Попробуем преобразовать строку в список
                    value_list = ast.literal_eval(value.text)
                    if isinstance(value_list, list):
                        a[0] = [int(v) for v in value_list if isinstance(v, (int, str)) and str(v).isdigit()]
                    else:
                        a[0] = int(value.text)
                except (ValueError, SyntaxError):
                    a[0] = int(value.text) if value.text.isdigit() else value.text
            elif isinstance(value, Switch):
                a[0] = value.active  # Сохраняем булевое значение как есть
            elif isinstance(value, str):
                try:
                    # Попробуем преобразовать строку в список
                    value_list = ast.literal_eval(value)
                    if isinstance(value_list, list):
                        a[0] = [int(v) for v in value_list if isinstance(v, (int, str)) and str(v).isdigit()]
                    else:
                        a[0] = int(value)
                except (ValueError, SyntaxError):
                    a[0] = int(value) if value.isdigit() else value
            elif isinstance(value, list):
                a[0] = [int(v) for v in value if isinstance(v, (int, str)) and str(v).isdigit()]
            elif isinstance(value, bool):
                a[0] = value  # Сохраняем булевое значение как есть
            else:
                a[0] = value

            setattr(settings, key, a)
            f.write(f"{key} = {a}\n")
    update_env_from_settings(filename, ".env")
    show_restart_popup()


def update_env_from_settings(settings_file, env_file):
    # Чтение файла settings.py
    with open(settings_file, 'r', encoding='utf-8') as f:
        settings_content = f.read()

    # Парсинг содержимого файла settings.py
    settings_dict = {}
    for line in settings_content.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = ast.literal_eval(value.strip())
            if isinstance(value, list) and len(value) > 0:
                settings_dict[key] = value[0]

    # Чтение существующего содержимого файла .env
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.readlines()

    # Сохранение первых двух строк
    new_env_content = env_content[:2]

    # Добавление новых значений из settings.py
    for key, value in settings_dict.items():
        new_env_content.append(f'{key}={value}\n')

    # Запись обновленного содержимого в .env
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_env_content)

def show_restart_popup():
    layout = BoxLayout(orientation='vertical')
    label = Label(text="Перезапустите приложение для применения настроек")
    button = Button(text="OK", size_hint=(1, 0.25))

    layout.add_widget(label)
    layout.add_widget(button)

    popup = Popup(title="Settings Saved",
                  content=layout,
                  size_hint=(None, None), size=(400, 200),
                  auto_dismiss=False)

    button.bind(on_release=App.get_running_app().stop)
    popup.open()

widget_references = {}

async def run_script():
    from bot.utils.new_launcher import get_tg_clients, run_tasks
    app = App.get_running_app()
    layout = app.root

    create_session_btn = Button(text='Создать сессию')
    start_bot_btn = Button(text='Запустить бот')
    settings_btn = Button(text='Настроить бот')
    create_session_btn.bind(on_press=lambda instance: asyncio.ensure_future(run_bot('1')))
    start_bot_btn.bind(on_press=lambda instance: asyncio.ensure_future(run_bot('2')))
    settings_btn.bind(on_press=lambda instance: asyncio.ensure_future(run_bot('3')))
    layout.clear_widgets()
    layout.add_widget(create_session_btn)
    layout.add_widget(settings_btn)
    layout.add_widget(start_bot_btn)

    async def run_bot(args):
        app = App.get_running_app()
        layout = app.root
        saved_layout = layout.children[:]  # Сохраняем текущие виджеты

        if args == '1':
            from bot.core.new_registrator import register_sessions
            layout.clear_widgets()
            if await register_sessions(app) == 1:
                asyncio.ensure_future(run_script())

        elif args == '2':
            layout.clear_widgets()
            try:
                tg_clients = await get_tg_clients()
            except FileNotFoundError:
                error_label = Label(text="Перезапустите приложение и создайте сессии перед запуском",
                                    color=(1, 0, 0, 1))
                layout.add_widget(error_label)
                return
            await run_tasks(tg_clients=tg_clients, app=app, saved_layout=saved_layout)

        elif args == '3':

            layout.clear_widgets()

            scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height))

            layouty = GridLayout(cols=2, padding=10, spacing=10, size_hint_y=None)

            layouty.bind(minimum_height=layouty.setter('height'))

            scroll_view.add_widget(layouty)

            layout.add_widget(scroll_view)

            # Load settings

            settings = await parse_settings("settings.py")

            for key, value in settings.items():

                box = BoxLayout(orientation='vertical', size_hint_y=None, height=60)

                label = Label(text=f"{key}\n{value[1]}", halign='left', valign='middle', text_size=(None, None))

                label.bind(size=lambda s, w: setattr(s, 'text_size', (s.width, None)))

                box.add_widget(label)

                layouty.add_widget(box)

                if isinstance(value[0], bool):

                    switch = Switch(active=value[0], size_hint=(None, None), size=(100, 44))

                    layouty.add_widget(switch)

                    widget_references[key] = switch


                elif isinstance(value[0], list) and len(value[0]) == 2:

                    text_input = TextInput(text=str(value[0]), size_hint=(None, None), size=(100, 44))

                    layouty.add_widget(text_input)

                    widget_references[key] = text_input


                elif isinstance(value[0], int):

                    text_input = TextInput(text=str(value[0]), size_hint=(None, None), size=(100, 44))

                    layouty.add_widget(text_input)

                    widget_references[key] = text_input

            # Add save button

            save_button = Button(text="Save", size_hint=(1, None), size=(100, 44))

            save_button.bind(on_press=lambda x: save_settings("settings.py"))

            layouty.add_widget(save_button)


class MainApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        button = Button(text='Старт', size_hint=(1, 1))
        button.bind(on_press=self.on_start_press)
        layout.add_widget(button)
        return layout

    def on_start_press(self, instance):
        layout = self.root
        layout.clear_widgets()
        asyncio.ensure_future(self.pre_install(layout))

    def on_button_press(self, instance):
        asyncio.ensure_future(mainloop(self))

    async def on_success(self):
        self.label.text = 'Granted!'
        self.create_download_coroutine(None)

    async def on_win(self):
        self.label.text = 'Используется Windows'
        self.create_download_coroutine(None)

    def initialize(self, layout):
        self.progress_bar = ProgressBar(max=100)
        self.version_label = Label(text='Remote version: ')
        layout.add_widget(self.version_label)
        layout.add_widget(self.progress_bar)
        return layout

    def create_download_coroutine(self, instance):
        layout = self.root
        layout.clear_widgets()
        layout.add_widget(self.label)
        self.initialize(layout)
        asyncio.ensure_future(download_files(self))

    async def clear_widgets(self):
        layout = self.root
        layout.clear_widgets()

    def add_retry_button(self):
        self.retry_button = Button(text='Retry', on_press=self.create_download_coroutine)
        self.root.add_widget(self.retry_button)

    async def pre_install(self, layout):
        self.label = Label(text='Инициализировано')
        layout.add_widget(self.label)
        button = Button(text='Запуск', on_press=self.on_button_press)
        layout.add_widget(button)

    async def get_input(self, popup_title, input_text, popup_text):
        self.input_text = None
        layout = BoxLayout(orientation='horizontal')
        text_input = TextInput(hint_text=input_text, size_hint=(0.85, None), height=30)
        insert_button = Button(text='Вставить', size_hint=(0.15, None), height=30,
                               on_press=lambda x: self.insert_text_from_clipboard(text_input))
        layout.add_widget(text_input)
        layout.add_widget(insert_button)
        popup_content = BoxLayout(orientation='vertical')
        popup_content.add_widget(Label(text=popup_text))
        popup_content.add_widget(layout)
        enter_button = Button(text='Ввести', size_hint=(1, None), height=30,
                              on_press=lambda x: self.return_text(text_input.text))
        popup_content.add_widget(enter_button)
        self.popup = Popup(title=popup_title, content=popup_content, size_hint=(0.8, 0.4))
        self.popup.open()
        while self.input_text is None:
            await asyncio.sleep(0.1)
        return self.input_text

    def insert_text_from_clipboard(self, text_input):
        text_input.text = Clipboard.paste()

    def return_text(self, text):
        self.input_text = text
        self.popup.dismiss()


async def main():
    await MainApp().async_run(async_lib='asyncio')


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
