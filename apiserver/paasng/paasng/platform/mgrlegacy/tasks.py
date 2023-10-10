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

from celery import shared_task

from paasng.core.core.storages.sqlalchemy import console_db
from paasng.platform.mgrlegacy.constants import MigrationStatus
from paasng.platform.mgrlegacy.models import MigrationProcess

logger = logging.getLogger(__name__)


#################
#  celery task  #
#################


@shared_task
def migrate_with_rollback_on_failure(migration_process_id):
    """
    根据应用编码同步应用，失败自动回滚
    """
    from paasng.platform.mgrlegacy.migrate import run_migration, run_rollback

    with console_db.session_scope() as session:
        migration_process = MigrationProcess.objects.get(id=migration_process_id)
        try:
            run_migration(migration_process=migration_process, session=session)
        except Exception:
            logger.exception("run_migration failed: migration_process_id=%s" % migration_process_id)
            logger.info("auto to rollback: migration_process_id=%s" % migration_process_id)
            try:
                run_rollback(migration_process=migration_process, session=session)
            except Exception:
                logger.exception("run_rollback failed")
                migration_process.set_status(MigrationStatus.ROLLBACK_FAILED.value)


@shared_task
def rollback_migration_process(migration_process_id):
    """
    回滚应用migration
    """
    from paasng.platform.mgrlegacy.migrate import run_rollback

    with console_db.session_scope() as session:
        migration_process = MigrationProcess.objects.get(id=migration_process_id)
        try:
            run_rollback(migration_process=migration_process, session=session)
        except Exception:
            logger.exception("run_rollback failed: migration_process_id=%s" % migration_process_id)
            migration_process.set_status(MigrationStatus.ROLLBACK_FAILED.value)


@shared_task
def confirm_with_rollback_on_failure(migration_process_id):
    from paasng.platform.mgrlegacy.app_migrations.entrance import EntranceMigration
    from paasng.platform.mgrlegacy.migrate import run_single_migration, run_single_rollback

    with console_db.session_scope() as session:
        migration_process = MigrationProcess.objects.get(id=migration_process_id)
        migration_process.set_status(MigrationStatus.ON_CONFIRMING.value)
        try:
            run_single_migration(
                migration_process=migration_process, migration_class=EntranceMigration, session=session
            )
        except Exception:
            logger.exception("run migration confirmed failed: migration_process_id=%s" % migration_process_id)
            # FIXME: this maybe fail too
            run_single_rollback(
                migration_process=migration_process, migration_class=EntranceMigration, session=session
            )
            migration_process.set_status(MigrationStatus.DONE_MIGRATION.value)
        else:
            migration_process.set_confirmed_state()
