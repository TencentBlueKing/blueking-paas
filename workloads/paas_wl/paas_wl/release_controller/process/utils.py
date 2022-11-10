# -*- coding: utf-8 -*-
import pickle
from typing import List, Optional, Set, Tuple, TypeVar

from paas_wl.platform.applications.models import EngineApp
from paas_wl.release_controller.process.models import PlainProcess
from paas_wl.utils.redisdb import get_default_redis

T = TypeVar("T")


def diff_list(l_before: List[T], l_after: List[T]) -> Tuple[Set[T], Set[T], Set[T]]:
    """Returns (added, removed, both_exists)"""
    return (set(l_after) - set(l_before), set(l_before) - set(l_after), set(l_after) & set(l_before))


class ProcessesSnapshotStore:
    """Stores snapshot of application's processes data, use redis as backend."""

    # processes will expire after 1 day to save space
    data_expires_in = 3600 * 24

    def __init__(self, engine_app: EngineApp):
        self.engine_app = engine_app
        self.redis_db = get_default_redis()
        self.rkey = f'procs::snapshot::app:{engine_app.name}'

    def save(self, processes: List[PlainProcess]):
        """Save processes"""
        self.redis_db.setex(self.rkey, value=pickle.dumps(processes), time=self.data_expires_in)

    def get(self) -> Optional[List[PlainProcess]]:
        """Get processes"""
        val = self.redis_db.get(self.rkey)
        if val is None:
            return None
        return pickle.loads(val)
