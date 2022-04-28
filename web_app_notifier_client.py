import requests


class WebAppNotifierClient:
    def __init__(self, group_name: str, server_url: str, AuthToken: str):
        self.group_name = group_name
        self.server_url = server_url
        self.AuthToken = AuthToken

    def send_alert(self, message: str, amend: dict = None) -> int:
        return requests.post(
            url=self.server_url + '/send_alert',
            headers={'AuthToken': self.AuthToken},
            json=dict(receiver_name=self.group_name, text=message, amend=amend)
        ).status_code

    def send_message(self, message: str, amend: dict = None) -> int:
        return requests.post(
            url=self.server_url + '/send_message',
            headers={'AuthToken': self.AuthToken},
            json=dict(receiver_name=self.group_name, text=message, amend=amend)
        ).status_code
