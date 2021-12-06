from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    message_id: int
    body: str
