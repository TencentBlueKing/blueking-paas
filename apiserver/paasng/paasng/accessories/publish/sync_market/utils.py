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
from functools import partial, wraps

from django.conf import settings

from paasng.accessories.publish.sync_market.managers import AppManger
from paasng.core.core.storages.sqlalchemy import console_db

logger = logging.getLogger(__name__)


def run_required_db_console_config(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # BK_CONSOLE_DBCONF has a default value of None
        if not getattr(settings, "BK_CONSOLE_DBCONF", None):
            func_name = func.func.__name__ if isinstance(func, partial) else func.__name__
            logger.warning("BK_CONSOLE_DB_CONF not provided, skip running %s", func_name)
            return
        else:
            return func(*args, **kwargs)

    return wrapper


@run_required_db_console_config
def set_migrated_state(code, is_migrated):
    """this is a tool function for legacy migration"""
    with console_db.session_scope() as session:
        count = AppManger(session).update(code, {"migrated_to_paasv3": is_migrated})
        logger.info("成功更新应用%s的迁移状态为: %s, 影响记录%s条" % (code, is_migrated, count))
