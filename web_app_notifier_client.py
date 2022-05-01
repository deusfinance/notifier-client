import requests
from typing import Tuple


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
