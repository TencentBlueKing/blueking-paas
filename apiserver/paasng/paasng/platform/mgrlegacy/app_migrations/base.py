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
import time
import traceback

import six

from paasng.platform.mgrlegacy.exceptions import MigrationFailed
from paasng.platform.mgrlegacy.models import MigrationContext, MigrationRegister

logger = logging.getLogger(__name__)


class BaseMigration(six.with_metaclass(MigrationRegister)):
    """Base class for application migration"""

    def get_description(self):
        return "BaseMigration"

    def __init__(self, context: MigrationContext):
        self.context = context
        self.legacy_app = self.context.legacy_app

        self.apply_type = "migrate"
        self.finished = False
        self.successful = False
        self.failed_reason = ""
        self.msecs_cost = 0
        self.log = None
        self.created_ts = time.time()

    def set_log(self, log):
        if not log:
            return

        self.log = log
        self.update_ongoing()

    def append_log(self, log):
        if not self.log:
            self.log = log
        else:
            self.log += log
        self.update_ongoing()

    def add_log(self, log):
        if not log:
            return

        if self.log:
            self.log = "%s\n%s" % (self.log, log)
        else:
            self.log = log
        self.update_ongoing()

    def update_ongoing(self):
        self.context.migration_process.set_ongoing(self)

    def apply_migration(self):
        """Apply this migration"""
        st = time.time()
        self.apply_type = "migrate"
        try:
            self.migrate()
            self.successful = True
        except Exception as e:
            self.failed_reason = str(e)
            self.successful = False
            logger.exception("Apply %s failed: %s" % (self.get_name(), e))
            raise MigrationFailed("Apply %s failed: %s" % (self.get_name(), e))
        finally:
            self.finished = True
            self.msecs_cost = int((time.time() - st) * 1000)

    def apply_rollback(self):
        """Apply rollback"""
        if self.context.app is None:
            logger.critical(
                "rollback app for LApplication[%s] is None \n %s"
                % (self.context.legacy_app.id, "\n".join(traceback.format_stack()))
            )

        st = time.time()
        self.apply_type = "rollback"
        try:
            self.rollback()
            self.successful = True
        except Exception as e:
            self.failed_reason = str(e)
            self.successful = False
            logger.exception("Apply %s %s failed: %s" % (self.get_name(), self.apply_type, e))
        finally:
            self.finished = True
            self.msecs_cost = int((time.time() - st) * 1000)

    def get_info(self):
        """Get current info of this migration instance"""
        return {
            "apply_type": self.apply_type,
            "name": self.get_name(),
            "description": self.get_description(),
            "finished": self.finished,
            "successful": self.successful,
            "failed_reason": self.failed_reason,
            "msecs_cost": self.msecs_cost,
            "log": self.log,
            "created_ts": self.created_ts,
        }

    def migrate(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError

    def get_name(self):
        return self.__class__.__name__

    def should_skip(self):
        return False
