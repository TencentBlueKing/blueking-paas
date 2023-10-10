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
import logging
import traceback

from paasng.platform.mgrlegacy.constants import MigrationStatus
from paasng.platform.mgrlegacy.exceptions import MigrationFailed
from paasng.platform.mgrlegacy.models import MigrationContext, MigrationRegister
from paasng.accessories.publish.sync_market.managers import AppManger

try:
    from paasng.platform.mgrlegacy.legacy_proxy_te import LegacyAppProxy
    from paasng.platform.mgrlegacy.task_data_te import MIGRATION_CLASSES_LIST, THIRD_APP_MIGRATION_CLASSES_LIST
except ImportError:
    from paasng.platform.mgrlegacy.legacy_proxy import LegacyAppProxy  # type: ignore
    from paasng.platform.mgrlegacy.task_data import MIGRATION_CLASSES_LIST, THIRD_APP_MIGRATION_CLASSES_LIST


logger = logging.getLogger(__name__)


#############
#  migrate  #
#############


def _do_migrate(migration_process, migration, context):
    if migration.should_skip():
        logger.info('Skip migration %s...', migration.get_name())
        return None
    migration_process.set_ongoing(migration)

    logger.info('Start migration %s for %s', migration.get_name(), migration.legacy_app.code)
    try:
        migration.apply_migration()
    except MigrationFailed:
        logger.exception('Error when running migration, %s', migration.get_name())
        migration_process.fail_on(migration)
        raise

    # save application as soon as possible
    if context.app is not None and migration_process.app is None:
        migration_process.set_app(context.app)

    migration_process.append_migration(migration)


def run_migration(migration_process, session):
    # set status to ON_MIGRATION
    migration_process.set_status(MigrationStatus.ON_MIGRATION.value)

    legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
    context = MigrationContext(
        legacy_app=legacy_app, owner=migration_process.owner, migration_process=migration_process, session=session
    )
    # 第三方应用与普通应用，迁移步骤不一致
    legacy_app_proxy = LegacyAppProxy(legacy_app=legacy_app, session=session)
    if legacy_app_proxy.is_third_app():
        migration_class_list = THIRD_APP_MIGRATION_CLASSES_LIST
    else:
        migration_class_list = MIGRATION_CLASSES_LIST

    for migration_class in migration_class_list:
        migration = migration_class(context)

        _do_migrate(migration_process, migration, context)

        if migration.should_skip():
            logger.info('Skip migration %s...', migration.get_name())
            continue
        # Use the new context
        context = migration.context

    # Migration successfully finished
    if context.app:
        migration_process.app = context.app
        migration_process.set_done_migrate_state()


def run_single_migration(migration_process, migration_class, session):
    legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
    context = MigrationContext(
        legacy_app=legacy_app,
        owner=migration_process.owner,
        migration_process=migration_process,
        app=migration_process.app,
        session=session,
    )
    migration = migration_class(context)
    _do_migrate(migration_process, migration, context)


##############
#  rollback  #
##############


def _do_rollback(migration_process, migration, context):
    # update ongoing
    migration_process.set_ongoing(migration)
    logger.info('Start rollback %s for %s', migration.get_name(), migration.legacy_app.code)
    try:
        migration.apply_rollback()
    except Exception:
        logger.exception("rollback fail!")
        raise
    migration_process.append_rollback(migration)


def run_rollback(migration_process, session):
    """Rollback an finished migration process

    :param migration_process: MigrationProcess instance
    """
    # set status to ON_ROLLBACK
    migration_process.set_status(MigrationStatus.ON_ROLLBACK.value)

    # FIXME: is this ok?
    # 第二次进入的时候app是None
    if migration_process.app is None:
        logger.critical('rollback app for %s is None \n %s' % (migration_process, "\n".join(traceback.format_stack())))
        raise MigrationFailed('rollback app for %s is None ' % migration_process.id)

    legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
    context = MigrationContext(
        legacy_app=legacy_app,
        app=migration_process.app,
        owner=migration_process.owner,
        migration_process=migration_process,
        session=session,
    )

    if migration_process.finished_migrations:
        for migration_info in reversed(migration_process.finished_migrations):
            migration_class = MigrationRegister.get_class(migration_info['name'])
            migration = migration_class(context)

            _do_rollback(migration_process=migration_process, migration=migration, context=context)
            # Use the new context
            context = migration.context
        else:
            migration_process.set_rollback_state()


def run_single_rollback(migration_process, migration_class, session):
    legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
    context = MigrationContext(
        legacy_app=legacy_app, owner=migration_process.owner, migration_process=migration_process, session=session
    )
    migration = migration_class(context)
    _do_rollback(migration_process, migration, context)
