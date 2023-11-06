import logging
from logging import Logger
from typing import Tuple, Optional, Union, List

import requests

logger = logging.getLogger('telegram')


class WebAppNotifierClient:
    def __init__(self, receiver_id: int, server_url: str, auth_token: str):
        """
        :param receiver_id: the id of the group in the telegram that wants to send a message to
        :param server_url: the base URL of the sending server
        :param auth_token: the Token to access the APIs
        """
        self.receiver_id = receiver_id
        self.server_url = server_url
        self.auth_token = auth_token

    def send_alert(self, message: str, amend: dict = None) -> int:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        return requests.post(
            url=self.server_url + '/send_alert',
            headers={'AuthToken': self.auth_token},
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend),
            timeout=5
        ).status_code

    def send_message(self, message: str, amend: dict = None) -> int:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        return requests.post(
            url=self.server_url + '/send_message',
            headers={'AuthToken': self.auth_token},
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend),
            timeout=5
        ).status_code

    def send_message_by_threshold(self, message: str, amend: dict = None) -> Tuple[int, bool]:
        """

        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response and that the message was added to queue for sending or not
        """
        response = requests.post(
            url=self.server_url + '/send_message_threshold',
            headers={'AuthToken': self.auth_token},
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend),
            timeout=5
        )
        if response.status_code != 200:
            return response.status_code, False
        return response.status_code, response.json()['sending']

    def set_threshold_setting(self,
                              message: str,
                              sending_threshold_number: int,
                              sending_threshold_time: int
                              ) -> int:
        """

        :param message: the message want to set a sending thresh hole to
        :param sending_threshold_number: the number of the message that need to be added to send one
                    of them (threshold value)
        :param sending_threshold_time: the threshold boundary
        :return:
        """
        return requests.post(
            url=self.server_url + '/set_sending_threshold',
            headers={'AuthToken': self.auth_token},
            json=dict(
                message=message,
                sending_threshold_number=sending_threshold_number,
                sending_threshold_time=sending_threshold_time
            ),
            timeout=5
        ).status_code


class SendNotification:
    def __init__(
            self,
            receiver_id: int,
            server_url: str,
            auth_token: str,
            retrying_number: int = 5,
            telegram_bot_token=None,
            test_env=False,
            test_env_logger: Optional[Logger] = None,
            max_msg_size: int = 3000
    ):
        """

        :param receiver_id:
        :param server_url:
        :param auth_token:
        :param retrying_number:
        :param telegram_bot_token:
        :param test_env_logger:
        :param max_msg_size:
        """
        self.receiver_id = receiver_id
        self.server_url = server_url
        self.retiring_number = retrying_number
        self.telegram_bot_token = telegram_bot_token
        self.notifier_client = WebAppNotifierClient(self.receiver_id, server_url, auth_token)
        self.test_env = test_env
        self.max_msg_size = max_msg_size
        if self.test_env:
            if test_env_logger:
                self.test_env_logger = test_env_logger
            else:
                logging.basicConfig()
                logging.getLogger().setLevel(logging.DEBUG)
                self.test_env_logger = logging

    def send_alert(self, message: str, amend: dict = None, emergency_msg: str = None) -> Optional[int]:
        """
        :param message: the message to send
        :param amend: to amend the message
        :param emergency_msg: emergency message like mentioning someone
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        if self.test_env:
            self.test_env_logger.info(message)
            return
        msg_list = self.__split_msg(message, amend, emergency_msg)
        status, __, page = self.__send_multiple_msg(msg_list, self.notifier_client.send_alert)
        if len(msg_list[page:]) == 0:
            return status
        self.__send_emergency_message(msg_list[page:], self.receiver_id)

    def send_message(self, message: str, amend: dict = None, emergency_msg: str = None) -> Optional[int]:
        """
        :param message: the message to send
        :param amend: to amend the message
        :param emergency_msg: emergency message like mentioning someone
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        if self.test_env:
            self.test_env_logger.info(message)
            return

        msg_list = self.__split_msg(message, amend, emergency_msg)
        status, __, page = self.__send_multiple_msg(msg_list, self.notifier_client.send_message)
        if len(msg_list[page:]) == 0:
            return status
        self.__send_emergency_message(msg_list[page:], self.receiver_id)

    def send_message_by_threshold(self, message: str, amend: dict = None,
                                  emergency_msg: str = None) -> Optional[Tuple[int, bool]]:
        """

        :param message: the message to send
        :param amend: to amend the message
        :param emergency_msg: emergency message like mentioning someone
        :return: the status code of the response and that the message was added to queue for sending or not
        """
        if self.test_env:
            self.test_env_logger.info(message)
            return
        msg_list = self.__split_msg(message, amend, emergency_msg)
        status, sending, page = self.__send_multiple_msg(msg_list, self.notifier_client.send_message_by_threshold)
        if len(msg_list[page:]) == 0:
            return status, sending
        msg_list = msg_list[page:]
        self.__send_emergency_message([msg_list[0] + 'failed to send by th:'] + msg_list[1:], self.receiver_id)

    def set_threshold_setting(self,
                              message: str,
                              sending_threshold_number: int,
                              sending_threshold_time: int
                              ) -> int:
        """

        :param message: the message want to set a sending thresh hole to
        :param sending_threshold_number: the number of the message that need to be added to send one
                    of them (threshold value)
        :param sending_threshold_time: the threshold boundary
        :return: the status code
        """
        return self.notifier_client.set_threshold_setting(
            message,
            sending_threshold_number,
            sending_threshold_time
        )

    def __send_emergency_message(self, msg_list: List[str], receiver_id: int, retrying=5):
        for msg in msg_list:
            for _ in range(retrying):
                logger.info(f'{msg}, {receiver_id}')
                url = f'https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage'
                data = {
                    'chat_id': receiver_id,
                    'text': f"message: {msg} amend: {None}",
                    'disable_web_page_preview': True
                }
                if requests.post(url=url, data=data, timeout=15).status_code == 200:
                    break

    def __split_msg(self, message: str, amend: dict = None, emergency_msg: str = None) -> List[str]:
        mandatory_msg = f"\nemergency_msg: {emergency_msg}\namend: {amend}"
        first_message_size = self.max_msg_size - len(mandatory_msg)
        if first_message_size < 0:
            raise Exception("Max size is to low")
        first_message = message[:first_message_size]
        rest_of_message = message[first_message_size:]
        return [f'{first_message}\n#{0}'] + [
                f"{rest_of_message[i:i + self.max_msg_size]}\n#{page + 1}\n"
                for page, i in enumerate(range(0, len(rest_of_message), self.max_msg_size))
            ]

    def __send_multiple_msg(self, msg_list: List[str], send_func: callable) -> Tuple[int, bool, int]:
        page = 0
        res = None
        try:
            for msg in msg_list:
                for _ in range(self.retiring_number):
                    res = send_func(msg)
                    if self.__check_status(res):
                        page += 1
                        break
                else:
                    raise Exception(f"status code: {res}\n"
                                    f"Couldn't send message: {msg}")
        except Exception as e:
            print(e.__str__())

        return (res, False, page) if not isinstance(res, tuple) else res + (page,)

    @staticmethod
    def __check_status(result: Union[int, Tuple[int, bool]]):
        if type(result) == Tuple:
            return result[0] == 200
        return result == 200
