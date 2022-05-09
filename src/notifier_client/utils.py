import datetime
import hashlib
import json
import logging
import uuid
from typing import Optional

import requests


class GlobalVariables:
    redis_server1 = None
    redis_server2 = None
    telegram_bot_token = None
    alter_delay = None

    @classmethod
    def set_redis_servers(cls, redis_server1, redis_server2):
        cls.redis_server1 = redis_server1
        cls.redis_server2 = redis_server2

    @classmethod
    def set_alter_delay(cls, alter_delay):
        cls.alter_delay = alter_delay

    @classmethod
    def set_telegram_bot_token(cls, telegram_bot_token):
        cls.telegram_bot_token = telegram_bot_token

    @classmethod
    def get_telegram_bot_token(cls):
        return cls.telegram_bot_token

    @classmethod
    def get_alter_delay(cls):
        return cls.alter_delay

    @classmethod
    def get_redis_server1(cls):
        return cls.redis_server1

    @classmethod
    def get_redis_server2(cls):
        return cls.redis_server2


def get_now_epoch() -> int:
    return round(
        datetime.datetime.now().timestamp()
    )


def normalize_group_name(group_name: str):
    return group_name.strip().lower().replace(' ', '')


def process_telegram_info(telegram_info: dict, group_name) -> Optional[int]:
    for update in telegram_info["result"]:
        data = update.get('my_chat_member') or update.get('message')
        data = data.get('chat')
        REDIS_SERVER = GlobalVariables.get_redis_server1()
        if data:
            if normalize_group_name(data['title']) == group_name:
                REDIS_SERVER.set(group_name, data['id'])
                return data['id']
    return


def get_set_telegram_group_id(group_name: str) -> Optional[int]:
    group_name = normalize_group_name(group_name.strip().lower().replace(' ', ''))
    REDIS_SERVER = GlobalVariables.get_redis_server1()
    redis_data = REDIS_SERVER.get(group_name)
    TELEGRAM_BOT_TOKEN = GlobalVariables.get_telegram_bot_token()
    if redis_data is not None:
        return redis_data
    try:
        telegram_info = requests.get(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates'
        ).json()
    except Exception:
        raise Exception
    if not telegram_info['ok']:
        raise Exception
    chat_id = process_telegram_info(telegram_info, group_name)
    if chat_id is None:
        raise Exception
    return chat_id


def set_threshold_setting(
        message: str,
        sending_threshold_number: int,
        sending_threshold_time: int
) -> None:
    key = f'{message}_setting'
    REDIS_SERVER_THRESHOLD = GlobalVariables.get_redis_server2()
    REDIS_SERVER_THRESHOLD.set(
        f'{hashlib.sha256(key.encode()).hexdigest()}',
        json.dumps(
            dict(
                sending_threshold_number=sending_threshold_number,
                sending_threshold_time=sending_threshold_time
            )
        )
    )


def get_threshold_setting(
        message: str
) -> dict:
    key = f'{message}_setting'
    REDIS_SERVER_THRESHOLD = GlobalVariables.get_redis_server2()
    redis_data = REDIS_SERVER_THRESHOLD.get(f'{hashlib.sha256(key.encode()).hexdigest()}')
    if redis_data:
        return json.loads(
            redis_data
        )


def set_message_data(
        message: str,
        receiver_id: int
):
    key = f'{message}_{receiver_id}'
    alert_key = f'{hashlib.sha256(key.encode()).hexdigest()}'
    setting = get_threshold_setting(message)
    unique_id = str(uuid.uuid4())
    REDIS_SERVER_THRESHOLD = GlobalVariables.get_redis_server2()
    REDIS_SERVER_THRESHOLD.set(f'{alert_key}-{unique_id}', 1, ex=setting['sending_threshold_time'])


def check_condition_send_message(
        message: str,
        receiver_id: int,
        amend: dict,
) -> bool:
    key = f'{message}_{receiver_id}'
    alert_key = f'{hashlib.sha256(key.encode()).hexdigest()}'
    REDIS_SERVER = GlobalVariables.get_redis_server1()
    keys = REDIS_SERVER.keys(f'{alert_key}-*')
    message_setting = get_threshold_setting(message)
    if not message_setting:
        send_message(message, receiver_id, amend)
        return True
    if len(keys) >= message_setting['sending_threshold_number']:
        message += f'\n count: {len(keys)}'
        send_message(message, receiver_id, amend)
        REDIS_SERVER.delete(*keys)
        return True
    return False


logger = logging.getLogger('telegram')


def send_alert(text: str, receiver_id: int, amend: dict = None):
    alert_key = f'{hashlib.sha256(text.encode()).hexdigest()}-{receiver_id}'
    REDIS_SERVER = GlobalVariables.get_redis_server1()
    alert_count = REDIS_SERVER.incr(alert_key)
    logger.error(f'send alert: {text} to {receiver_id}')
    ALERT_DELAY = GlobalVariables.get_alter_delay()
    if REDIS_SERVER.get(f'{alert_key}-expire') is None:
        send_message(
            text + f'\n count: {alert_count}',
            receiver_id,
            amend

        )
        REDIS_SERVER.set(f'{alert_key}-expire', 'true', ex=ALERT_DELAY)
        REDIS_SERVER.set(alert_key, 0)


def send_message(message: str, receiver_id: int, amend: dict = None, retrying=5):
    TELEGRAM_BOT_TOKEN = GlobalVariables.get_telegram_bot_token()
    for i in range(retrying):
        logger.info(f'{message}, {receiver_id}')
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        data = {
            'chat_id': receiver_id,
            'text': f"message: {message} amend: {amend}",
            'disable_web_page_preview': True
        }
        if requests.post(url=url, data=data, timeout=5).status_code == '200':
            break
