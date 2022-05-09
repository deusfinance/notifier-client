import requests
from typing import Tuple, Optional

from utils import GlobalVariables, get_set_telegram_group_id, send_alert, send_message


class WebAppNotifierClient:
    def __init__(self, group_name: str, server_url: str, AuthToken: str):
        """
        :param group_name: the name of the group in the telegram that wants to send a message to
        :param server_url: the base URL of the sending server
        :param AuthToken: the Token to access the APIs
        """
        self.group_name = group_name
        self.server_url = server_url
        self.AuthToken = AuthToken

    def send_alert(self, message: str, amend: dict = None) -> int:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        return requests.post(
            url=self.server_url + '/send_alert',
            headers={'AuthToken': self.AuthToken},
            json=dict(receiver_name=self.group_name, text=message, amend=amend)
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
            headers={'AuthToken': self.AuthToken},
            json=dict(receiver_name=self.group_name, text=message, amend=amend)
        ).status_code

    def send_message_by_threshold(self, message: str, amend: dict = None) -> Tuple[int, bool]:
        """

        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response and that the message was added to queue for sending or not
        """
        response = requests.post(
            url=self.server_url + '/send_message_threshold',
            headers={'AuthToken': self.AuthToken},
            json=dict(receiver_name=self.group_name, text=message, amend=amend)
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
            headers={'AuthToken': self.AuthToken},
            json=dict(
                message=message,
                sending_threshold_number=sending_threshold_number,
                sending_threshold_time=sending_threshold_time
            )
        ).status_code


class SendNotification:
    def __init__(
            self,
            group_name: str,
            server_url: str,
            AuthToken: str,
            retiring_number: int = 5,
            redis_server1=None,
            redis_server2=None,
            telegram_bot_token=None,
            alter_delay=None
    ):
        """

        :param group_name:
        :param server_url:
        :param AuthToken:
        :param retiring_number:
        :param redis_server1:
        :param redis_server2:
        :param telegram_bot_token:
        :param alter_delay:
        """
        self.group_name = group_name
        self.server_url = server_url
        self.AuthToken = AuthToken
        self.retiring_number = retiring_number
        GlobalVariables.set_redis_servers(redis_server1,
                                          redis_server2),
        GlobalVariables.set_alter_delay(alter_delay)
        GlobalVariables.set_telegram_bot_token(telegram_bot_token)
        self.notifier_client = WebAppNotifierClient(group_name, server_url, AuthToken)

    def send_alert(self, message: str, amend: dict = None) -> Optional[int]:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        for i in range(self.retiring_number):
            status = self.notifier_client.send_alert(message, amend)
            if status == 200:
                return status
        receiver_id = get_set_telegram_group_id(self.group_name)
        send_alert(message, receiver_id, amend)

    def send_message(self, message: str, amend: dict = None) -> Optional[int]:
        """
        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        for i in range(self.retiring_number):
            status = self.notifier_client.send_message(message, amend)
            if status == 200:
                return status
        receiver_id = get_set_telegram_group_id(self.group_name)
        send_message(message, receiver_id, amend)

    def send_message_by_threshold(self, message: str, amend: dict = None) -> Optional[Tuple[int, bool]]:
        """

        :param message: the message to send
        :param amend: to amend the message
        :return: the status code of the response and that the message was added to queue for sending or not
        """
        for i in range(self.retiring_number):
            status, sending = self.notifier_client.send_message_by_threshold(message, amend)
            if status == 200:
                return status, sending
        receiver_id = get_set_telegram_group_id(self.group_name)
        send_message(message + 'failed to send by th:', receiver_id, amend)


