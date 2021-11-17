import logging

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageStorage:
    messages_with_timestamps = []

    @classmethod
    def insert_message(cls, message: str, timestamp: float) -> None:
        # Messages deduplication
        if timestamp in {item[1] for item in cls.messages_with_timestamps}:
            logger.info(
                "Message has been discarded, as it's a duplicate",
            )
            return

        cls.messages_with_timestamps.append((message, timestamp))
        logger.info("Message has been saved")
        # Sort messages by timestamp
        cls.messages_with_timestamps.sort(key=lambda x: x[1])

    @classmethod
    def messages(cls):
        return ", ".join(
            message[0] for message in cls.messages_with_timestamps
        )
