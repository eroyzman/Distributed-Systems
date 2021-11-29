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
        # Sort messages by message id
        cls.messages_with_id.sort(key=lambda x: x[1])

    @classmethod
    def get_suspected_messages(cls):
        suspected_messages = []
        if cls.messages_with_id:
            item = cls.messages_with_id[0]
            if item[1] != 0:
                suspected_messages = list(range(item[1]))

            if len(cls.messages_with_id) > 1:
                for (curr_id, next_id) in pairwise(
                    [item[1] for item in cls.messages_with_id]
                ):
                    if next_id - curr_id != 1:
                        suspected_messages += list(range(curr_id, next_id))

            if suspected_messages:
                messages_list = ", ".join(map(str, suspected_messages))

                logger.info(
                    "Waiting for delayed message | " + messages_list,
                )

        return suspected_messages

    @classmethod
    def messages(cls):
        if cls.get_suspected_messages():
            return ""

        return ", ".join(message[0] for message in cls.messages_with_id)
