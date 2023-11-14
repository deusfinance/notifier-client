from dataclasses import dataclass
import logging
from logging import Logger
from typing import Tuple, Optional, Union, List

import requests

logger = logging.getLogger('telegram')


@dataclass
class Message:
    page: int
    content: str
    emergency: str = ''
    amend: dict = None

    def message(self) -> str:
        return f"{self.content}\n#{self.page}\n" if len(self.emergency) == 0 \
            else f"{self.content}\nemergency_msg: {self.emergency}\n#{self.page}\n"


class WebAppNotifierClient:
    def __init__(self, receiver_id: int, server_url: str, auth_token: str):
        """
        Initializes a new instance of the WebAppNotifierClient.
        Parameters:
            - receiver_id (int): The ID of the Telegram group to which messages are to be sent.
            - server_url (str): The base URL of the server to send requests to.
            - auth_token (str): The authentication token used to access the server APIs.
        """
        self.receiver_id = receiver_id
        self.server_url = server_url
        self.auth_token = auth_token

    def send_alert(self, message: str, amend: dict = None) -> int:
        """
        Sends an alert message to the configured receiver.
        Parameters:
            - message (str): The alert message to be sent.
            - amend (dict, optional): Additional data to amend the alert message.
        Returns:
            - int: The HTTP status code of the response (200 indicates that the message has been queued).
        """
        return requests.post(
            url=self.server_url + '/send_alert',
            headers={'AuthToken': self.auth_token},
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend),
            timeout=5
        ).status_code

    def send_message(self, message: str, amend: dict = None) -> int:
        """
        Sends a regular message to the configured receiver.

        Parameters:
            - message (str): The message to be sent.
            - amend (dict, optional): Additional data to amend the message.

        Returns:
            - int: The HTTP status code of the response (200 indicates that the message has been queued).
        """
        return requests.post(
            url=self.server_url + '/send_message',
            headers={'AuthToken': self.auth_token},
            json=dict(receiver_id=self.receiver_id, text=message, amend=amend),
            timeout=5
        ).status_code

    def send_message_by_threshold(self, message: str, amend: dict = None) -> Tuple[int, bool]:
        """
        Sends a message to the configured receiver with threshold checks.

        Parameters:
            - message (str): The message to be sent.
            - amend (dict, optional): Additional data to amend the message.

        Returns:
            - Tuple[int, bool]: A tuple containing the HTTP status code and a boolean indicating whether
                                the message has been added to the queue.
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
        Sets threshold settings for sending messages.

        Parameters:
            - message (str): The message for which to set the sending threshold.
            - sending_threshold_number (int): The number of messages that trigger the threshold.
            - sending_threshold_time (int): The time boundary for the threshold.

        Returns:
            - int: The HTTP status code of the response.
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
           Initializes a new instance of the SendNotification.

           Parameters:
               - receiver_id (int): The receiver ID for sending notifications.
               - server_url (str): The server URL for the WebAppNotifierClient.
               - auth_token (str): The authentication token for the WebAppNotifierClient.
               - retrying_number (int): The number of times to retry sending a notification upon failure.
               - telegram_bot_token (str, optional): The bot token for the Telegram bot.
               - test_env (bool): Flag indicating if the notification is being sent in a test environment.
               - test_env_logger (logging.Logger, optional): The logger to use in the test environment.
               - max_msg_size (int): The maximum allowed size for a message to be sent.
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

    def send_alert(self, message: str, amend: dict = None, emergency_msg: str = '') -> Optional[int]:
        """
        Sends an alert notification with optional message amendment and emergency message.

        Parameters:
            - message (str): The alert message to be sent.
            - amend (dict, optional): Additional data to amend the alert message.
            - emergency_msg (str, optional): An emergency message to include, such as mentioning a user.

        Returns:
            - Optional[int]: The HTTP status code of the response (200 indicates that the message has been queued).
                              Returns None if in test environment.
        """
        if self.test_env:
            self.test_env_logger.info(message)
            return
        return self.__send_message_pagination(message, self.notifier_client.send_alert, amend, emergency_msg)

    def send_message(self, message: str, amend: dict = None, emergency_msg: str = None) -> Optional[int]:
        """
        Parameters:
            -message: the message to send
            -amend: to amend the message
            -emergency_msg: emergency message like mentioning someone
        Returns:
            -the status code of the response (200 means the message added to
                                                  the queue for sending not the message sent)
        """
        if self.test_env:
            self.test_env_logger.info(message)
            return
        return self.__send_message_pagination(message, self.notifier_client.send_message, amend, emergency_msg)

    def send_message_by_threshold(self, message: str, amend: dict = None,
                                  emergency_msg: str = '') -> Optional[Tuple[int, bool]]:
        """
        Parameters:
            -message: the message to send
            -amend: to amend the message
            -emergency_msg: emergency message like mentioning someone
        Returns:
            -the status code of the response and that the message was added to queue for sending or not
        """
        if self.test_env:
            self.test_env_logger.info(message)
            return
        return self.__send_message_pagination(message, self.notifier_client.send_message_by_threshold, amend,
                                              emergency_msg)

    def set_threshold_setting(self,
                              message: str,
                              sending_threshold_number: int,
                              sending_threshold_time: int
                              ) -> int:
        """
        Parameters:
            -message: the message want to set a sending thresh hole to
            -sending_threshold_number: the number of the message that need to be added to send one
                        of them (threshold value)
            -sending_threshold_time: the threshold boundary
        Returns:
             the status code
        """
        return self.notifier_client.set_threshold_setting(
            message,
            sending_threshold_number,
            sending_threshold_time
        )

    def __split_msg(self, message: str, amend: dict = None, emergency_msg: str = '') -> List[Message]:
        """
        Splits a given message into multiple parts if it exceeds a predefined size.
        The method ensures that the split messages include the emergency message and amendments, if provided.
        Parameters:
            - message (str): The original message to be split.
            - amend (dict, optional): A dictionary of amendments to be appended to each message part.
            - emergency_msg (str, optional): An emergency message to be included in each message part.

        Returns:
            - List[str]: A list of message strings, each not exceeding the predefined size limit.
        """
        mandatory_msg = f"\nemergency_msg: {emergency_msg}\namend: {amend}"
        first_message_size = self.max_msg_size - len(mandatory_msg)
        if first_message_size < 0:
            raise Exception("Max size is to low")
        first_message = message[:first_message_size]
        rest_of_message = message[first_message_size:]

        return [Message(1, first_message, emergency_msg, amend)] + [
            Message(page+2, rest_of_message[i:i + self.max_msg_size])
            for page, i in enumerate(range(0, len(rest_of_message), self.max_msg_size))
        ]

    def __send_message_pagination(
            self, message: str, send_func: callable, amend: dict = None, emergency_msg: str = ''
    ) -> Union[int, Optional[Tuple[int, bool]]]:
        """
        Sends a message in paginated form and attempts retries if necessary.
        This method handles the sending of large messages that need to be split into multiple parts.
        It also manages the retry mechanism by checking the status of each sent message.

        Parameters:
            - message (str): The message to be sent.
            - send_func (callable): The function to be used to send the message.
            - amend (dict, optional): A dictionary of amendments to be included in the message.
            - emergency_msg (str, optional): An emergency message to be appended to each message part.
        Returns:
            - Union[int, Optional[Tuple[int, bool]]]: The result of the last message attempt to send.
        """
        msg_list = self.__split_msg(message, amend, emergency_msg)
        res = 0
        for msg in msg_list:
            break_flag = False
            try:
                for _ in range(self.retiring_number):
                    res = send_func(msg.message(), msg.amend)
                    if self.__check_status(res):
                        break_flag = True
                        break
                if break_flag:
                    continue
            except Exception as e:
                logger.exception(f'exception:{e}')
            self.__send_emergency_message(msg.message(), self.receiver_id, msg.amend)
        return res

    @staticmethod
    def __check_status(result: Union[int, Tuple[int, bool]]):
        """
        Checks the status of a sent message.
        Determines if the message was sent successfully based on the status code or the tuple received.
        Parameters:
            - result (Union[int, Tuple[int, bool]]): The result returned by the message sending function.
        Returns:
            - bool: True if the message was sent successfully, False otherwise.
        """
        if type(result) == Tuple:
            return result[0] == 200
        return result == 200

    def __send_emergency_message(self, message: str, receiver_id: int, amend: dict = None, retrying=5):
        """
        Sends an emergency message to a specified receiver, with optional retries.
        If the message fails to send, the function retries the sending up to a specified number of times.
        Parameters:
            - message (str): The emergency message to be sent.
            - receiver_id (int): The ID of the receiver to whom the message should be sent.
            - amend (dict, optional): A dictionary of amendments to be appended to the message.
            - emergency_msg (str, optional): An additional emergency message to be included.
            - retrying (int): The number of times to retry sending the message.
        Returns:
            - None
        """
        for _ in range(retrying):
            logger.info(f'{message}, {receiver_id}')
            url = f'https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage'
            data = {
                'chat_id': receiver_id,
                'text': f"message: {message} amend: {amend}",
                'disable_web_page_preview': True
            }
            if requests.post(url=url, data=data, timeout=15).status_code == 200:
                break
