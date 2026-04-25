import socket
import threading
import json
import os

# Настройки для Railway
# 0.0.0.0 позволяет принимать соединения извне
HOST = '0.0.0.0'
# Railway сам назначит порт, если его нет — юзаем 5577
PORT = int(os.environ.get("PORT", 5577))

# Словарь для хранения активных юзеров: {username: socket}
online_users = {}


def handle_client(client_socket, addr):
    print(f"[+] Новое подключение: {addr}")
    username = None

    while True:
        try:
            raw_data = client_socket.recv(4096).decode('utf-8')
            if not raw_data:
                break

            data = json.loads(raw_data)
            m_type = data.get("type")

            # 1. Авторизация (когда юзер ввел код и ник в приложении)
            if m_type == "auth":
                username = data.get("username")
                online_users[username] = client_socket
                print(f"[AUTH] {username} теперь в сети")

            # 2. Поиск пользователя
            elif m_type == "search":
                target = data.get("target")
                found = target in online_users
                response = {"type": "search_res", "found": found, "user": target}
                client_socket.send(json.dumps(response).encode('utf-8'))

            # 3. Пересылка приватного сообщения
            elif m_type == "private_msg":
                to_user = data.get("to")
                text = data.get("text")
                if to_user in online_users:
                    try:
                        online_users[to_user].send(json.dumps({
                            "type": "new_msg",
                            "from": username,
                            "text": text
                        }).encode('utf-8'))
                    except:
                        del online_users[to_user]

        except Exception as e:
            print(f"[!] Ошибка с клиентом {username}: {e}")
            break

    # Удаление при отключении
    if username and username in online_users:
        del online_users[username]
        print(f"[-] {username} отключился")
    client_socket.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Позволяет повторно использовать порт сразу после перезапуска
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
        server.listen()
        print(f"[*] СЕРВЕР ЗАПУЩЕН")
        print(f"[*] Адрес: {HOST}, Порт: {PORT}")
    except Exception as e:
        print(f"[!] Ошибка запуска: {e}")
        return

    while True:
        client, addr = server.accept()
        # Запускаем отдельный поток для каждого юзера
        thread = threading.Thread(target=handle_client, args=(client, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    start_server()