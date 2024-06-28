# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import logging
from contextlib import contextmanager
from typing import Type
from uuid import uuid4

from django.conf import settings

from paasng.accessories.publish.market.models import Tag
from paasng.accessories.publish.sync_market.models import TagMap
from paasng.core.core.storages.sqlalchemy import legacy_db
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.mgrlegacy.app_migrations.base import BaseMigration
from paasng.platform.mgrlegacy.constants import MigrationStatus
from paasng.platform.mgrlegacy.models import MigrationContext, MigrationProcess
from paasng.platform.modules.manager import EngineApp, ModuleInitializer
from tests.utils import mock
from tests.utils.auth import create_user

try:
    from paasng.infras.legacydb_te.models import LApplication
except ImportError:
    from paasng.infras.legacydb.models import LApplication

logger = logging.getLogger(__name__)


@contextmanager
def global_mock(context: MigrationContext):
    with mock.patch("paasng.platform.modules.manager.ModuleInitializer.create_engine_apps") as create_engine_apps:
        # for BaseObjectMigration
        def _create_engine_apps():
            app = context.app
            for env in ModuleInitializer.default_environments:
                uuid = str(uuid4())
                name = f"{app.name}-{uuid4()}"
                engine_app = EngineApp.objects.create(id=uuid, name=name, owner=app.owner, region=app.region)
                ModuleEnvironment.objects.create(
                    application=app, module=app.get_default_module(), engine_app_id=engine_app.id, environment=env
                )

        create_engine_apps.side_effect = _create_engine_apps
        # for ProductMigration
        if not TagMap.objects.filter(remote_id=context.legacy_app.tags_id).exists():
            tag = Tag.objects.create(name="test")
            TagMap.objects.create(remote_id=context.legacy_app.tags_id, tag=tag)
        yield


def get_legacy_app(session, code="test"):
    legacy_app = session.query(LApplication).filter_by(code=code).scalar()
    if legacy_app is None:
        raise ValueError("暂不支持mock legacy_app, 必须使用已存在的 legacy_app 进行测试")
    return legacy_app


def get_migration_instance(migration_cls: Type[BaseMigration]) -> BaseMigration:
    user = create_user()
    app_code = getattr(settings, "FOR_TESTS_LEGACY_APP_CODE", "test-app")
    # TODO: make a fake instance and fake session
    session = legacy_db.get_scoped_session()
    legacy_app = get_legacy_app(session, app_code)
    migration_process, _ = MigrationProcess.objects.get_or_create_migration_process_for_legacy(
        legacy_app.id, user.pk, session
    )
    migration_process.set_status(MigrationStatus.ON_MIGRATION.value)
    context = MigrationContext(legacy_app, session, owner=user.pk, migration_process=migration_process)
    return migration_cls(context)
