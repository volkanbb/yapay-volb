from enum import StrEnum


class AssistantState(StrEnum):
    """Visual / behavioural state of VOLB. Mirrored 1:1 by the QML character."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    WORKING = "working"
    ERROR = "error"
