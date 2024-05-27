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

from blue_krill.data_types.enum import StructuredEnum

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
        (DEFAULT, "默认"),
        (ON_MIGRATION, "正在迁移"),
        (FAILED, "已失败"),
        (DONE_MIGRATION, "完成迁移"),
        (ON_ROLLBACK, "正在回滚"),
        (ROLLBACKED, "已回滚"),
        (ON_CONFIRMING, "正在确认"),
        (CONFIRMED, "已确认"),
        (ROLLBACK_FAILED, "回滚失败"),
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
    SUPPORT = "SUPPORT"
    NOT_SUPPORT = "NOT_SUPPORT"
    ON_MIGRATION = "ON_MIGRATION"
    FINISHED_MIGRATION = "FINISHED_MIGRATION"

    _choices_labels = (
        (SUPPORT, "支持"),
        (NOT_SUPPORT, "不支持"),
        (ON_MIGRATION, "迁移中"),
        (FINISHED_MIGRATION, "迁移完成"),
    )


class LegacyAppState(ChoicesEnum):
    """命名保持跟 PaaS2.0 一致，方便核对"""

    OUTLINE = 0
    DEVELOPMENT = 1
    TEST = 3
    ONLINE = 4
    IN_TEST = 8
    IN_ONLINE = 9
    IN_OUTLINE = 10

    _choices_labels = (
        (OUTLINE, "已下架"),
        (DEVELOPMENT, "开发中"),
        (TEST, "测试中"),
        (ONLINE, "已上线"),
        (IN_TEST, "正在提测"),
        (IN_ONLINE, "正在上线"),
        (IN_OUTLINE, "正在下架"),
    )


@dataclass
class AppMember:
    username: str
    role: int


class CNativeMigrationStatus(str, StructuredEnum):
    DEFAULT = "default"
    ON_MIGRATION = "on_migration"
    MIGRATION_SUCCEEDED = "migration_succeeded"
    MIGRATION_FAILED = "migration_failed"
    CONFIRMED = "confirmed"
    ON_ROLLBACK = "on_rollback"
    ROLLBACK_SUCCEEDED = "rollback_succeeded"
    ROLLBACK_FAILED = "rollback_failed"
    NO_NEED_MIGRATION = "no_need_migration"


try:
    # Load external constants
    from . import constants_ext  # type: ignore  # noqa: F401
except ImportError:
    pass
