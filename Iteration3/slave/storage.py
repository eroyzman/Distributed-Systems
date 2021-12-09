import heapq
import itertools
import logging
from dataclasses import dataclass, field

logging.basicConfig(
    format="time: %(asctime)s - message: %(message)s - line: %(lineno)d",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True, order=True)
class Message:
    id: int
    body: str = field(compare=False)


class MessageStorage:
    messages: list[Message] = []

    @classmethod
    def insert_message(cls, message: str, message_id: int) -> None:
        # Messages deduplication
        if message_id in {message.id for message in cls.messages}:
            logger.info(
                "Message has been discarded, as it's a duplicate",
            )
            return

        heapq.heappush(cls.messages, Message(message_id, message))
        logger.info("Message with ID:%d has been saved", message_id)

    @classmethod
    def get_missing_messages(cls):
        missing_messages: list[int] = []
        if cls.messages:
            fist_message = cls.messages[0]
            if fist_message.id != 0:
                missing_messages = list(range(fist_message.id))

            if len(cls.messages) > 1:
                for (curr_id, next_id) in itertools.pairwise(
                    [message.id for message in cls.messages]
                ):
                    if next_id - curr_id != 1:
                        missing_messages += list(range(curr_id, next_id))

            if missing_messages:
                logger.info(
                    "Waiting for delayed messages | "
                    + ", ".join(map(str, missing_messages))
                )

        return missing_messages

    @classmethod
    def get_messages(cls):
        if cls.get_missing_messages():
            return "Waiting for the delayed messages"

        return ", ".join(message.body for message in cls.messages)
