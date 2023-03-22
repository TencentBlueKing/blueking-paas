import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional

from paasng.engine.exceptions import DuplicateNameInSamePhaseError, StepNotInPresetListError
from paasng.engine.utils.output import RedisChannelStream

if TYPE_CHECKING:
    from paasng.engine.models.phases import DeployPhase

logger = logging.getLogger(__name__)


@dataclass
class ServerSendEvent:
    """SSE 事件对象"""

    id: str
    event: str
    data: dict
    __slots__ = ['id', 'event', 'data']

    INTERNAL_TERM: ClassVar[str] = "internal"

    @classmethod
    def from_raw(cls, raw_dict: dict) -> 'ServerSendEvent':
        return cls(
            id=raw_dict['id'],
            event='message' if raw_dict['event'] == 'msg' else raw_dict['event'],
            data=raw_dict['data'],
        )

    @property
    def is_internal(self) -> bool:
        return self.event == self.INTERNAL_TERM

    def to_yield_str_list(self):
        """支持 stream 返回"""
        return ['id: %s\n' % self.id, 'event: %s\n' % self.event, 'data: %s\n\n' % self.data]

    @staticmethod
    def to_eof_str_list():
        """事件流结束标志"""
        return ['id: -1\n', 'event: EOF\n', 'data: \n\n']


class MessageParser:
    @classmethod
    def parse_msg(cls, raw_event: dict) -> Optional[ServerSendEvent]:
        """从 SSE 中解析出 msg 字段"""
        if not raw_event:
            return None

        try:
            event = ServerSendEvent.from_raw(raw_event)
        except Exception:
            logger.exception("Failed to parse SSE event")
            return None

        if not event.event == "message":
            return None

        if isinstance(event.data, str):
            event.data = json.loads(event.data)
        return event


class MessageStepMatcher:
    @classmethod
    def match_and_update_step(cls, event: ServerSendEvent, pattern_maps: dict, phase: 'DeployPhase'):
        for job_status, pattern_map in pattern_maps.items():
            for pattern, step_name in pattern_map.items():
                match = re.compile(pattern).findall(event.data['line'])
                # 未能匹配上任何预设匹配集
                if not match:
                    continue

                try:
                    step_obj = phase.get_step_by_name(step_name)
                except StepNotInPresetListError as e:
                    logger.debug("%s, skip", e.message)
                    continue
                except DuplicateNameInSamePhaseError as e:
                    logger.warning("%s, skip", e.message)
                    continue

                # 由于 history events 每次都是重复拉取，所以肯定会重复判断
                if step_obj.status == job_status.value:
                    continue

                # 已经处于完结状态
                if step_obj.is_completed:
                    continue

                logger.info("[%s] going to mark & write to stream", phase.deployment.id)
                # 更新 step 状态，并写到输出流
                step_obj.mark_and_write_to_steam(
                    RedisChannelStream.from_deployment_id(phase.deployment.id), job_status
                )
