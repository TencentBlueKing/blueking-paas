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
from dataclasses import dataclass

from paasng.anti_contracts.platform.mgrlegacy import constants
from paasng.utils.basic import ChoicesEnum


class MigrationStatus(ChoicesEnum):
    """
    new status flow
    start -> ON_MIGRATION -> fail to FAILED
                 |->  success to     DONE_MIGRATION -> rollback ->  ON_ROLLBACK  -> fail to ? 找管理员/回滚代码需保证最高健壮性
                                          |                              |->        success to ROLLBACKED
                                          |->  ON_CONFIRMING -> fail to ? (rollback entracnemigration)
                                                     |->        success to CONFIRMED

    0 -> 1(ON_MIGRATION)
        1 -> 2 (FAILED) - fail
        1 -> 3 (DONE_MIGRATION) - success
            3 -> 4 (ON_ROLLBACK)                - to rollback
                 4 -> 8 (ROLLBACK_FAILED) - fail
                 4 -> 5 (ROLLBACKED) - success
            3 -> 6 (ON_CONFIRMING)              - to confirmed
                 6 -> 3 (DONE_MIGRATION) - fail
                 6 -> 7 (CONFIRMED) - success
    """

    DEFAULT = 0
    ON_MIGRATION = 1
    FAILED = 2
    DONE_MIGRATION = 3
    ON_ROLLBACK = 4
    ROLLBACKED = 5
    ON_CONFIRMING = 6
    CONFIRMED = 7

    # 回滚失败, 需要人工介入
    ROLLBACK_FAILED = 8

    _choices_labels = (
        (DEFAULT, u'默认'),
        (ON_MIGRATION, u'正在迁移'),
        (FAILED, u'已失败'),
        (DONE_MIGRATION, u'完成迁移'),
        (ON_ROLLBACK, u'正在回滚'),
        (ROLLBACKED, u'已回滚'),
        (ON_CONFIRMING, u'正在确认'),
        (CONFIRMED, u'已确认'),
        (ROLLBACK_FAILED, u'回滚失败'),
    )

    _active_states = (ON_MIGRATION, DONE_MIGRATION, ON_ROLLBACK, ON_CONFIRMING)

    @classmethod
    def get_active_states(cls):
        return cls._active_states.value

    @classmethod
    def check_active(cls, choice):
        if isinstance(choice, cls):
            choice = choice.value
        return choice in cls._active_states.value


class LegacyAppTag(ChoicesEnum):
    SUPPORT = 'SUPPORT'
    NOT_SUPPORT = 'NOT_SUPPORT'
    ON_MIGRATION = 'ON_MIGRATION'
    FINISHED_MIGRATION = 'FINISHED_MIGRATION'

    _choices_labels = ((SUPPORT, u'支持'), (NOT_SUPPORT, u'不支持'), (ON_MIGRATION, u'迁移中'), (FINISHED_MIGRATION, u'迁移完成'))


LegacyAppState = constants.LegacyAppState


@dataclass
class AppMember:
    username: str
    role: int


try:
    # Load external constants
    from . import constants_ext  # type: ignore  # noqa
except ImportError:
    pass
