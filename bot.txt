import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import re
import time
import os
from flask import Flask
from threading import Thread


VK_TOKEN = os.environ.get("VK_TOKEN")       
ADMIN_ID = int(os.environ.get("ADMIN_ID"))  


app = Flask(__name__)

@app.route('/')
def home():
    
    return "Бот VK успешно запущен и работает!"

def run_web_server():
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))


def send_message(vk, peer_id, text):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=0)
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def run_bot():
    while True:
        try:
            vk_session = vk_api.VkApi(token=VK_TOKEN)
            vk = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            print("Бот VK запущен и слушает сообщения...")

            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    msg = event.text.strip()
                    user_id = event.user_id
                    if not msg: continue

                    if not msg.startswith("/anon"):
                        try:
                            user_info = vk.users.get(user_ids=user_id, fields="first_name,last_name")
                            name = f"{user_info[0]['first_name']} {user_info[0]['last_name']} (id{user_id})"
                        except:
                            name = f"Пользователь {user_id}"
                        send_message(vk, ADMIN_ID, f"📝 От {name}:\n{msg}")
                        send_message(vk, user_id, "✅ Отправлено (не анонимно).")
                    else:
                        anon_text = re.sub(r'^/anon\s*', '', msg).strip()
                        if not anon_text:
                            send_message(vk, user_id, "⚠️ Напишите: /anon ваш текст")
                            continue
                        send_message(vk, ADMIN_ID, f"🕊️ Анонимно:\n{anon_text}")
                        send_message(vk, user_id, "✅ Анонимно отправлено.")
        except Exception as e:
            print(f"Критическая ошибка в боте: {e}. Перезапуск через 10 секунд...")
            time.sleep(10)


if __name__ == "__main__":
    # Запускаем веб-сервер в фоновом потоке
    web_thread = Thread(target=run_web_server)
    web_thread.start()
    # Запускаем основного бота
    run_bot()