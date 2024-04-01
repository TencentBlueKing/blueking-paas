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
from contextlib import suppress
from typing import List, Type

from paasng.accessories.publish.sync_market.managers import AppManger
from paasng.platform.mgrlegacy.cnative_migrations.base import CNativeBaseMigrator
from paasng.platform.mgrlegacy.constants import MigrationStatus
from paasng.platform.mgrlegacy.entities import MigrationResult, RollbackResult
from paasng.platform.mgrlegacy.exceptions import (
    BackupLegacyDataFailed,
    MigrationFailed,
    PreCheckMigrationFailed,
    RollbackFailed,
)
from paasng.platform.mgrlegacy.models import CNativeMigrationProcess, MigrationContext, MigrationRegister
from paasng.platform.mgrlegacy.task_data import MIGRATE_TO_CNATIVE_CLASSES_LIST

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
        logger.info("Skip migration %s...", migration.get_name())
        return
    migration_process.set_ongoing(migration)

    logger.info("Start migration %s for %s", migration.get_name(), migration.legacy_app.code)
    try:
        migration.apply_migration()
    except MigrationFailed:
        logger.exception("Error when running migration, %s", migration.get_name())
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
            logger.info("Skip migration %s...", migration.get_name())
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
    logger.info("Start rollback %s for %s", migration.get_name(), migration.legacy_app.code)
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
        logger.critical("rollback app for %s is None \n %s", migration_process, "\n".join(traceback.format_stack()))
        raise MigrationFailed("rollback app for %s is None " % migration_process.id)

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
            migration_class = MigrationRegister.get_class(migration_info["name"])
            migration = migration_class(context)

            _do_rollback(migration_process=migration_process, migration=migration, context=context)
            # Use the new context
            context = migration.context
        migration_process.set_rollback_state()


def run_single_rollback(migration_process, migration_class, session):
    legacy_app = AppManger(session).get_by_app_id(migration_process.legacy_app_id)
    context = MigrationContext(
        legacy_app=legacy_app, owner=migration_process.owner, migration_process=migration_process, session=session
    )
    migration = migration_class(context)
    _do_rollback(migration_process, migration, context)


def migrate_default_to_cnative(migration_process: CNativeMigrationProcess):
    """
    migrate default app to cloud-native app. auto rollback if migrate failed
    """
    migrate_succeeded = True

    for migrator_cls in MIGRATE_TO_CNATIVE_CLASSES_LIST:
        migrator_name = migrator_cls.get_name()
        try:
            migrator_cls(migration_process).migrate()
        except (PreCheckMigrationFailed, BackupLegacyDataFailed) as e:
            migrate_succeeded = False
            # 没有实际开始迁移, 设置 is_finished=False
            migration_process.append_migration(
                MigrationResult(migrator_name=migrator_name, is_succeeded=False, is_finished=False, error_msg=str(e))
            )
            break
        except MigrationFailed as e:
            migrate_succeeded = False
            # 开始迁移, 但迁移失败
            migration_process.append_migration(
                MigrationResult(migrator_name=migrator_name, is_succeeded=False, error_msg=str(e))
            )
            break
        else:
            migration_process.append_migration(MigrationResult(migrator_name=migrator_name, is_succeeded=True))

    if not migrate_succeeded:
        with suppress(RollbackFailed):
            _rollback_cnative(migration_process, migration_process)

    migration_process.finish_migration(migrate_succeeded)


def rollback_cnative_to_default(
    rollback_process: CNativeMigrationProcess, last_migration_process: CNativeMigrationProcess
):
    """rollback cloud-native app to default app

    :param rollback_process: 当前的回滚过程
    :param last_migration_process: 最近一次迁移过程, 用于回滚
    """

    try:
        _rollback_cnative(rollback_process, last_migration_process)
    except MigrationFailed:
        rollback_process.finish_rollback(False)
    else:
        rollback_process.finish_rollback(True)


def _rollback_cnative(process: CNativeMigrationProcess, last_migration_process: CNativeMigrationProcess):
    """
    actual rollback cloud-native app to default

    :param process: 用于记录当前的回滚过程详情
    :param last_migration_process: 最近一次迁移过程, 其中的 legacy_data 和 details.migrations 用于回滚
    """

    performed_migrations = last_migration_process.details.migrations
    performed_migrator_classes: List[Type[CNativeBaseMigrator]] = [
        CNativeBaseMigrator.get_class(result.migrator_name) for result in performed_migrations if result.is_finished
    ]

    for migrator_cls in performed_migrator_classes:
        try:
            migrator_cls(last_migration_process).rollback()
        except RollbackFailed as e:
            process.append_rollback(
                RollbackResult(migrator_name=migrator_cls.get_name(), is_succeeded=False, error_msg=str(e))
            )
            raise
        else:
            process.append_rollback(RollbackResult(migrator_name=migrator_cls.get_name(), is_succeeded=True))
