# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import pickle
from typing import List, Optional, Set, Tuple, TypeVar

from paasng.engine.processes.models import PlainProcess
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.core.storages.redisdb import get_default_redis

T = TypeVar("T")


def diff_list(l_before: List[T], l_after: List[T]) -> Tuple[Set[T], Set[T], Set[T]]:
    """Returns (added, removed, both_exists)"""
    return (set(l_after) - set(l_before), set(l_before) - set(l_after), set(l_after) & set(l_before))


class ProcessesSnapshotStore:
    """Stores snapshot of application's processes data, use redis as backend."""

    # processes will expire after 1 day to save space
    data_expires_in = 3600 * 24

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.redis_db = get_default_redis()
        self.rkey = f'procs::snapshot::app:{env.engine_app.name}'

    def save(self, processes: List[PlainProcess]):
        """Save processes"""
        self.redis_db.setex(self.rkey, value=pickle.dumps(processes), time=self.data_expires_in)

    def get(self) -> Optional[List[PlainProcess]]:
        """Get processes"""
        val = self.redis_db.get(self.rkey)
        if val is None:
            return None
        return pickle.loads(val)
