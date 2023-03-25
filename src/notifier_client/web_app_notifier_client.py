import logging
from typing import Tuple, Optional

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
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend)
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
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend)
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
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend)
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
            )
        ).status_code


class SendNotification:
    def __init__(
            self,
            receiver_id: int,
            server_url: str,
            auth_token: str,
            retrying_number: int = 5,
            telegram_bot_token=None
    ):
        """

        :param receiver_id:
        :param server_url:
        :param auth_token:
        :param retrying_number:
        :param telegram_bot_token:
        """
        self.receiver_id = receiver_id
        self.server_url = server_url
        self.retiring_number = retrying_number
        self.telegram_bot_token = telegram_bot_token
        self.notifier_client = WebAppNotifierClient(self.receiver_id, server_url, auth_token)

    def send_alert(self, message: str, amend: dict = None) -> Optional[int]:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        try:
            for i in range(self.retiring_number):
                status = self.notifier_client.send_alert(message, amend)
                if status == 200:
                    return status
        except Exception as e:
            print(e.__str__())
        self.__send_emergency_message(message, self.receiver_id, amend)

    def send_message(self, message: str, amend: dict = None) -> Optional[int]:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        try:
            for i in range(self.retiring_number):
                status = self.notifier_client.send_message(message, amend)
                if status == 200:
                    return status
        except Exception as e:
            print(e.__str__())
        self.__send_emergency_message(message, self.receiver_id, amend)

    def send_message_by_threshold(self, message: str, amend: dict = None) -> Optional[Tuple[int, bool]]:
        """

        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response and that the message was added to queue for sending or not
        """
        try:
            for i in range(self.retiring_number):
                status, sending = self.notifier_client.send_message_by_threshold(message, amend)
                if status == 200:
                    return status, sending
        except Exception as e:
            print(e.__str__())
        self.__send_emergency_message(message + 'failed to send by th:', self.receiver_id, amend)

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

    def __send_emergency_message(self, message: str, receiver_id: int, amend: dict = None, retrying=5):
        for _ in range(retrying):
            logger.info(f'{message}, {receiver_id}')
            url = f'https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage'
            data = {
                'chat_id': receiver_id,
                'text': f"message: {message} amend: {amend}",
                'disable_web_page_preview': True
            }
            if requests.post(url=url, data=data, timeout=5).status_code == 200:
                break
