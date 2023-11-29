import logging
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class ServerSendEvent:
    """SSE 事件对象"""

    id: str
    event: str
    data: dict
    __slots__ = ["id", "event", "data"]

    INTERNAL_TERM: ClassVar[str] = "internal"

    @classmethod
    def from_raw(cls, raw_dict: dict) -> "ServerSendEvent":
        return cls(
            id=raw_dict["id"],
            event="message" if raw_dict["event"] == "msg" else raw_dict["event"],
            data=raw_dict["data"],
        )

    @property
    def is_internal(self) -> bool:
        return self.event == self.INTERNAL_TERM

    def to_yield_str_list(self):
        """支持 stream 返回"""
        return ["id: %s\n" % self.id, "event: %s\n" % self.event, "data: %s\n\n" % self.data]

    @staticmethod
    def to_eof_str_list():
        """事件流结束标志"""
        return ["id: -1\n", "event: EOF\n", "data: \n\n"]
