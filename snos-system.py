import os
import random
import re
import smtplib
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Путь к базе данных bot_data.db в той же папке
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "bot_data.db")

# 1. Список из 8 адресов получателей
RECIPIENT_EMAILS = [
    "support@telegram.org",
    "abuse@telegram.org",
    "recover@telegram.org",
    "security@telegram.org",
    "dmca@telegram.org",
    "sms@telegram.org",
    "stopca@telegram.org",
    "sticker@telegram.org",
]

# 2. Список аккаунтов отправителей
ACCOUNTS = [
    {"email": "artemshyshkin456@gmail.com", "password": "onrf tikg zdnm dtuv"},
    {"email": "artemshyshkin146@gmail.com", "password": "ygfn nund ukha oslr"},
    {"email": "ulvyy096@gmail.com", "password": "ooqb xrzb tjhr ozes"},
    {"email": "ssj629787@gmail.com", "password": "clas oosn tsla xwwh"},
]

# 3. Пронумерованные шаблоны сообщений
MESSAGE_TEMPLATES = {
    1: "Добрый день, я стал жертвой мошенничества от аккаунта {username},{telegram_id} который продает несуществующие товары. Он требует предоплату, но не выполняет обещания. Прошу принять меры по блокировке и расследованию этого аккаунта.",
    2: "Добрый день, аккаунт {username},{telegram_id} активно занимается мошенничеством. Он обещает услуги и товары, но в итоге ничего не предоставляет. Прошу принять меры по блокировке данного пользователя.",
    3: "Добрый день, аккаунт {username},{telegram_id} занимается обманом пользователей, предлагая товары и услуги, которые не существуют. Прошу принять меры и заблокировать данного пользователя за нарушение правил Telegram.",
    4: "Здравствуйте, аккаунт {username},{telegram_id} распространяет ложные предложения, обещая услуги или товары, которые не соответствуют действительности. Он обманывает пользователей и заставляет их платить за несуществующие вещи. Прошу заблокировать аккаунт и провести расследование.",
    5: "Добрый день, аккаунт {username},{telegram_id} использует Telegram для мошенничества. Он продает несуществующие товары и просит оплату за них. Пожалуйста, примите меры по блокировке данного аккаунта и расследованию ситуации.",
    6: "Добрый день, аккаунт {username},{telegram_id} нарушает политику безопасности Telegram, распространяет экстремистские материалы и агитирует к насилию. Это поведение создаёт опасность для других пользователей. Прошу заблокировать данный аккаунт и предпринять все необходимые меры по предотвращению распространения насилия.",
    7: "Здравствуйте, аккаунт {username},{telegram_id} активно призывает к насилию и распространению экстремистских идей, что нарушает политику Telegram. Эти действия могут серьёзно угрожать безопасности пользователей. Прошу срочно заблокировать аккаунт и принять меры по предотвращению подобных публикаций.",
    8: "Добрый день, аккаунт {username},{telegram_id} нарушает правила Telegram, распространяя экстремистские материалы и призывы к насилию. Это крайне опасное поведение, которое угрожает безопасности и спокойствию пользователей. Прошу заблокировать аккаунт и принять меры для предотвращения распространения экстремизма.",
}

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def fetch_latest_transfer():
    """Извлекает последнюю запись из таблицы transfers в bot_data.db"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, sender_id, sender_username, target_input, timestamp 
            FROM transfers 
            ORDER BY id DESC 
            LIMIT 1
        """
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "sender_id": row[1],
                "sender_username": row[2],
                "target_input": row[3],
                "timestamp": row[4],
            }
        return None
    except Exception as e:
        print(f"[-] Ошибка при чтении базы данных: {e}")
        return None


def parse_target_input(target_input):
    """Извлекает отдельно @username и цифровой ID из строки target_input"""
    username_match = re.search(r"@[a-zA-Z0-9_]{4,}", target_input)
    id_match = re.search(r"\b\d{6,12}\b", target_input)

    username = username_match.group(0) if username_match else target_input
    telegram_id = id_match.group(0) if id_match else "Не указан"

    return username, telegram_id


def delete_transfer_record(record_id):
    """Удаляет из базы данных строго ту запись, с которой работал скрипт"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transfers WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        print(f"[+] Запись ID {record_id} успешно удалена из базы данных.")
    except Exception as e:
        print(f"[-] Ошибка при удалении записи ID {record_id}: {e}")


def send_all_messages(username, telegram_id):
    """Каждая почта-отправитель посылает по 1 случайному письму на ВСЕ 8 почт-получателей"""
    template_numbers = list(MESSAGE_TEMPLATES.keys())

    for acc in ACCOUNTS:
        sender_email = acc["email"]
        password = acc["password"]

        print(f"\n--- Запуск отправки с аккаунта: {sender_email} ---")

        for recipient in RECIPIENT_EMAILS:
            # Для КАЖДОЙ из 8 почт выбирается свой случайный номер шаблона
            chosen_number = random.choice(template_numbers)

            selected_template = MESSAGE_TEMPLATES[chosen_number]
            body_text = selected_template.format(
                username=username, telegram_id=telegram_id
            )

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient

            # Уникальные заголовки против склеивания писем в цепочки
            unique_key = str(uuid.uuid4())[:8]
            time_stamp = datetime.now().strftime("%H:%M:%S")

            msg["Subject"] = f"Уведомление №{chosen_number} - {time_stamp} [{unique_key}]"
            msg["Message-ID"] = (
                f"<{unique_key}.{time.time()}@{sender_email.split('@')[1]}>"
            )
            msg["X-Entity-Ref-ID"] = unique_key

            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            try:
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
                server.quit()

                print(
                    f"[+] {sender_email} -> {recipient} | Отправлен шаблон №{chosen_number}"
                )
            except Exception as e:
                print(f"[-] Ошибка отправки с {sender_email} на {recipient}: {e}")

            time.sleep(0.1)


def main():
    print("[*] Чтение записи из базы данных...")
    record = fetch_latest_transfer()

    if not record:
        print("[-] Записей в БД не найдено.")
        sys.exit(0)

    target_record_id = record["id"]
    target_input = record["target_input"]

    username, telegram_id = parse_target_input(target_input)
    print(
        f"[+] Взята запись #{target_record_id}: username='{username}', telegram_id='{telegram_id}'"
    )

    # 1. Отправляем письма по схеме "1 отправитель -> 8 получателей (по 1 случайному шаблону каждому)"
    send_all_messages(username, telegram_id)

    # 2. Удаляем обработанную запись из БД
    delete_transfer_record(target_record_id)

    # 3. Завершаем работу
    print("\n[+] Скрипт успешно завершил работу.")
    sys.exit(0)


if __name__ == "__main__":
    main()