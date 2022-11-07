# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import datetime
import logging
from operator import itemgetter
from typing import Any, Dict

from django.db import models
from jsonfield import JSONField

from paasng.platform.applications.models import Application
from paasng.platform.mgrlegacy.constants import MigrationStatus
from paasng.utils.models import OwnerTimestampedModel

logger = logging.getLogger(__name__)


# Load this table explicitly or `app.app_app_appops_collection` relationship won't work


class MigrationProcessManager(models.Manager):
    def get_or_create_migration_process_for_legacy(self, legacy_app_id, owner, session):
        try:
            from paasng.platform.mgrlegacy.legacy_proxy_te import LegacyAppProxy  # type: ignore
        except ImportError:
            from paasng.platform.mgrlegacy.legacy_proxy import LegacyAppProxy  # type: ignore
        from paasng.publish.sync_market.managers import AppManger

        legacy_app = AppManger(session).get_by_app_id(legacy_app_id)
        legacy_app_proxy = LegacyAppProxy(legacy_app=legacy_app, session=session)
        assert legacy_app is not None, "can't find Legacy Application object id=%s" % legacy_app_id

        try:
            migration_process = (
                MigrationProcess.objects.filter(legacy_app_id=legacy_app_id)
                .filter(status__in=MigrationStatus.get_active_states())
                .get()
            )
            created = False
        except MigrationProcess.DoesNotExist:
            migration_process = super(MigrationProcessManager, self).create(
                legacy_app_id=legacy_app_id,
                status=MigrationStatus.DEFAULT.value,
                owner=owner,
                legacy_app_logo=legacy_app.logo,
                legacy_app_is_already_online=legacy_app.is_already_online,
                legacy_app_state=legacy_app.state,
                legacy_app_has_all_deployed=legacy_app_proxy.has_prod_deployed(),
            )
            created = True
        return migration_process, created


class MigrationProcess(OwnerTimestampedModel):
    """An migration process"""

    legacy_app_id = models.IntegerField()
    app = models.ForeignKey(Application, on_delete=models.CASCADE, null=True)

    status = models.IntegerField(choices=MigrationStatus.get_choices(), default=MigrationStatus.DEFAULT.value)

    failed_date = models.DateTimeField(null=True)
    migrated_date = models.DateTimeField(null=True)
    confirmed_date = models.DateTimeField(null=True)
    rollbacked_date = models.DateTimeField(null=True)

    # Use JSON to store migrations
    ongoing_migration = JSONField(null=True)
    finished_migrations = JSONField(null=True)
    finished_rollbacks = JSONField(null=True)

    # 旧版本开发者中心数据备份，迁移时这几个数据会被覆盖，回滚时用这几个字段
    legacy_app_logo = models.CharField(max_length=500, null=True, default=None)
    legacy_app_is_already_online = models.BooleanField(default=True)
    legacy_app_state = models.IntegerField(default=4)
    legacy_app_has_all_deployed = models.BooleanField(default=True)

    objects = MigrationProcessManager()

    @property
    def on_migration(self):
        return self.status == MigrationStatus.ON_MIGRATION.value

    @property
    def failed(self):
        return self.status == MigrationStatus.FAILED.value

    @property
    def confirmed(self):
        return self.status == MigrationStatus.CONFIRMED.value

    @property
    def rollbacked(self):
        return self.status == MigrationStatus.ROLLBACKED.value

    def is_v3_prod_available(self) -> bool:
        if not self.app:
            return False
        any_prod_deployed = any(app_env.is_running() for app_env in self.app.envs.filter(environment="prod"))
        return any_prod_deployed

    def is_v3_stag_available(self):
        if not self.app:
            return False
        any_stag_deployed = any(app_env.is_running() for app_env in self.app.envs.filter(environment="stag"))
        return any_stag_deployed

    def set_app(self, app):
        self.app = app
        self.save(update_fields=['app'])

    # on_migration and on_rollback

    def set_ongoing(self, migration):
        """Set ongoing migration

        :param migration: Migration instance.
        """
        self.ongoing_migration = migration.get_info()
        self.save(update_fields=['ongoing_migration'])

    def append_migration(self, migration):
        """Append a migration

        :param migration: Migration instance.
        """
        self.ongoing_migration = None
        self.finished_migrations = (self.finished_migrations or []) + [migration.get_info()]
        self.save(update_fields=['ongoing_migration', 'finished_migrations'])

    def append_rollback(self, migration):
        self.finished_rollbacks = (self.finished_rollbacks or []) + [migration.get_info()]
        self.save(update_fields=['finished_rollbacks'])

    # fail

    def fail_on(self, migration):
        """Failed on a migration

        :param migration: Migration instance.
        """
        self.ongoing_migration = None
        self.finished_migrations = (self.finished_migrations or []) + [migration.get_info()]

        self.status = MigrationStatus.FAILED.value
        self.failed_date = datetime.datetime.now()

        self.save(update_fields=['ongoing_migration', 'finished_migrations', 'status', 'failed_date'])

    # status

    def set_status(self, status):
        self.ongoing_migration = None
        self.status = status
        self.save(update_fields=['status', 'ongoing_migration'])

    def set_done_migrate_state(self):
        self.ongoing_migration = None
        self.migrated_date = datetime.datetime.now()
        self.status = MigrationStatus.DONE_MIGRATION.value
        self.save(update_fields=['status', 'migrated_date', 'ongoing_migration'])

    def set_rollback_state(self):
        self.ongoing_migration = None
        self.rollbacked_date = datetime.datetime.now()
        self.status = MigrationStatus.ROLLBACKED.value
        self.save(update_fields=['status', 'rollbacked_date', 'ongoing_migration'])

    def set_confirmed_state(self):
        self.ongoing_migration = None
        self.status = MigrationStatus.CONFIRMED.value
        self.confirmed_date = datetime.datetime.now()
        self.save(update_fields=['status', 'confirmed_date', 'ongoing_migration'])

    def is_active(self):
        """
        active情形：
        case1: 执行失败，但是还没有回滚完成
        case2: 还没有到达结束状态
        case3: 到达结束状态，但是还没有确认
        :return:
        """
        return self.status in MigrationStatus.get_active_states()

    # not used currently
    def run(self):
        from .tasks import migrate_with_rollback_on_failure

        migrate_with_rollback_on_failure.apply_async(args=(self.pk,))

    def rollback(self):
        from .tasks import rollback_migration_process

        rollback_migration_process(self)

    def finished_operations(self):
        # 返回之前按照 create_ts 排序
        operations = (self.finished_migrations or []) + (self.finished_rollbacks or [])
        for operation in operations:
            operation.setdefault('created_ts', 0)
        return sorted(operations, key=itemgetter('created_ts'))

    def __repr__(self):
        return "%s[%s]" % (self.__class__, self.id)

    def __str__(self):
        return "%s[%s]" % (self.__class__, self.id)


class MigrationContext(object):
    """Migration context"""

    def __init__(self, legacy_app, session, app=None, owner=None, migration_process=None):
        try:
            from paasng.platform.mgrlegacy.legacy_proxy_te import LegacyAppProxy  # type: ignore
        except ImportError:
            from paasng.platform.mgrlegacy.legacy_proxy import LegacyAppProxy  # type: ignore

        self.session = session
        self.legacy_app = legacy_app
        self.legacy_app_proxy = LegacyAppProxy(legacy_app=legacy_app, session=session)
        self.app: Application = app
        self.owner = owner
        self.migration_process = migration_process


class MigrationRegister(type):
    classes_map: Dict[str, Any] = {}

    def __new__(cls, name, parents, attrs):
        new_cls = type.__new__(cls, name, parents, attrs)
        cls.classes_map[name] = new_cls
        return new_cls

    @classmethod
    def get_class(cls, name):
        return cls.classes_map[name]
