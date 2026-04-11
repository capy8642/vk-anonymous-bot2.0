import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import re
import time
import os
import sys
import json
from flask import Flask
from threading import Thread

# --- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (задаются на Render) ---
VK_TOKEN = os.environ.get("VK_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except:
        sys.stderr.write(f"ОШИБКА: ADMIN_ID должен быть числом, получено: {ADMIN_ID}\n")
        ADMIN_ID = None
else:
    sys.stderr.write("ОШИБКА: переменная ADMIN_ID не задана\n")

if not VK_TOKEN:
    sys.stderr.write("ОШИБКА: переменная VK_TOKEN не задана\n")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот VK успешно запущен и работает!"

# --- КЛАВИАТУРА С ТРЕМЯ КНОПКАМИ ---
def get_start_keyboard():
    # one_time=True — клавиатура скроется после первого нажатия
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(label="📝 Анонимное сообщение", color=VkKeyboardColor.PRIMARY, payload={"command": "anon"})
    keyboard.add_line()  # перенос на новую строку
    keyboard.add_button(label="📜 Правила", color=VkKeyboardColor.SECONDARY, payload={"command": "rules"})
    keyboard.add_button(label="📞 Контакты", color=VkKeyboardColor.NEGATIVE, payload={"command": "contacts"})
    return keyboard

# --- ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ ---
def send_message(vk, peer_id, text, keyboard=None):
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=text,
            keyboard=keyboard.get_keyboard() if keyboard else None,
            random_id=0
        )
    except Exception as e:
        sys.stderr.write(f"Ошибка отправки сообщения: {e}\n")

# --- ОСНОВНАЯ ЛОГИКА БОТА ---
def run_bot():
    if not VK_TOKEN or not ADMIN_ID:
        sys.stderr.write("Бот не запущен из-за отсутствия переменных окружения\n")
        return

    while True:
        try:
            vk_session = vk_api.VkApi(token=VK_TOKEN)
            vk = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            sys.stderr.write("Бот VK запущен и слушает сообщения...\n")

            for event in longpoll.listen():
                # --- ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ (в том числе приветствия) ---
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    msg = event.text.strip()
                    user_id = event.user_id

                    # Приветствие при первом открытии диалога (флаг 65536)
                    if event.flags & 65536:
                        send_message(
                            vk, user_id,
                            "👋 Привет! Я бот сообщества. Выбери действие:",
                            keyboard=get_start_keyboard()
                        )
                        continue  # приветствие отправлено, дальше не обрабатываем

                    # Обработка обычных и анонимных сообщений (старая логика)
                    if not msg:
                        continue

                    if not msg.startswith("/anon"):
                        # Обычное сообщение – пересылаем админу с указанием автора
                        try:
                            user_info = vk.users.get(user_ids=user_id, fields="first_name,last_name")
                            name = f"{user_info[0]['first_name']} {user_info[0]['last_name']} (id{user_id})"
                        except:
                            name = f"Пользователь {user_id}"
                        send_message(vk, ADMIN_ID, f"📝 От {name}:\n{msg}")
                        send_message(vk, user_id, "✅ Отправлено (не анонимно).")
                    else:
                        # Анонимное сообщение
                        anon_text = re.sub(r'^/anon\s*', '', msg).strip()
                        if not anon_text:
                            send_message(vk, user_id, "⚠️ Напишите: /anon ваш текст")
                            continue
                        send_message(vk, ADMIN_ID, f"🕊️ Анонимно:\n{anon_text}")
                        send_message(vk, user_id, "✅ Анонимно отправлено.")

                # --- ОБРАБОТКА НАЖАТИЙ НА КНОПКИ (callback) ---
                elif event.type == VkEventType.MESSAGE_EVENT and event.to_me:
                    payload_data = json.loads(event.object.payload)
                    command = payload_data.get("command")
                    user_id = event.user_id

                    if command == "anon":
                        send_message(vk, user_id, "Чтобы отправить анонимное сообщение, напиши: `/anon твой текст`")
                        # Всплывающее уведомление о выполнении
                        vk.messages.sendMessageEventAnswer(
                            event_id=event.object.event_id,
                            user_id=user_id,
                            peer_id=event.object.peer_id,
                            event_data=json.dumps({"type": "show_snackbar", "text": "Инструкция отправлена!"})
                        )
                    elif command == "rules":
                        send_message(vk, user_id, "📜 *Правила сообщества:*\n1. Будьте вежливы.\n2. Запрещён спам.\n3. Уважайте других участников.")
                        vk.messages.sendMessageEventAnswer(
                            event_id=event.object.event_id,
                            user_id=user_id,
                            peer_id=event.object.peer_id,
                            event_data=json.dumps({"type": "show_snackbar", "text": "Правила отправлены!"})
                        )
                    elif command == "contacts":
                        send_message(vk, user_id, "📞 *Связаться с нами:*\nEmail: support@example.com\nVK: vk.com/ваше_сообщество")
                        vk.messages.sendMessageEventAnswer(
                            event_id=event.object.event_id,
                            user_id=user_id,
                            peer_id=event.object.peer_id,
                            event_data=json.dumps({"type": "show_snackbar", "text": "Контакты отправлены!"})
                        )

        except Exception as e:
            sys.stderr.write(f"Критическая ошибка в боте: {e}. Перезапуск через 10 секунд...\n")
            time.sleep(10)

# --- ЗАПУСК (Flask в главном потоке, бот в фоновом) ---
if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    # Запускаем веб-сервер (необходим для Render)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)