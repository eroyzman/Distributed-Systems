import logging
from itertools import pairwise

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageStorage:
    messages_with_id = []

    @classmethod
    def insert_message(cls, message: str, message_id: int) -> None:
        # Messages deduplication
        if message_id in {item[1] for item in cls.messages_with_id}:
            logger.info(
                "Message has been discarded, as it's a duplicate",
            )
            return
        cls.messages_with_id.insert(message_id, (message, message_id))
        logger.info("Message with ID:%d has been saved", message_id)
        # Sort messages by timestamp
        cls.messages_with_id.sort(key=lambda x: x[1])

    @classmethod
    def messages(cls):
        if cls.messages_with_id:
            item = cls.messages_with_id[0]
            if item[1] != 0:
                messages_list = ", ".join(
                    map(str, [item[1] for item in cls.messages_with_id])
                )
                logger.info(
                    "Waiting for delayed message | " + messages_list,
                )
                return ""
            elif len(cls.messages_with_id) > 1:
                message_id_diff = [
                    y - x
                    for (x, y) in pairwise(
                        [item[1] for item in cls.messages_with_id]
                    )
                ]
                if not all(flag == 1 for flag in message_id_diff):
                    messages_list = ", ".join(
                        map(str, [item[1] for item in cls.messages_with_id])
                    )
                    logger.info(
                        "Waiting for delayed message | " + messages_list,
                    )
                    return ""
        return ", ".join(message[0] for message in cls.messages_with_id)
