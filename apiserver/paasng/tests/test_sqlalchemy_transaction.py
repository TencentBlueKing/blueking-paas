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

import pytest

from paasng.platform.core.storages.sqlalchemy import legacy_db
from tests.conftest import check_legacy_enabled
from tests.utils.helpers import adaptive_lapplication_fields, configure_regions

try:
    from paasng.platform.legacydb_te.models import LApplication
except ImportError:
    from paasng.platform.legacydb.models import LApplication


@pytest.fixture
def legacy_app():
    if not check_legacy_enabled():
        raise pytest.skip("Legacy db engine is not initialized")
    values = dict(
        code="test_rollback",
        name="test_rollback",
        from_paasv3=1,
        logo='',
        introduction='',
        creater='',
        created_date=datetime.datetime.now(),
        created_state=0,
        app_type=1,
        state=1,  # 开发中
        width=890,
        height=550,
        deploy_env=102,
        init_svn_version=0,
        is_already_online=1,
        is_already_test=1,
        is_code_private=1,
        first_test_time=datetime.datetime.now(),
        first_online_time=datetime.datetime.now(),
        dev_time=0,
        app_cate=0,
        is_offical=0,
        is_base=0,
        audit_state=0,
        isneed_reaudit=1,
        svn_domain="",  # SVN域名, 真正注册的时候完善
        use_celery=0,  # app是否使用celery，确定一下是否需要
        use_celery_beat=0,  # app是否使用celery beat，确定一下是否需要
        usecount_ied=0,
        is_select_svn_dir=1,
        is_lapp=0,  # 是否是轻应用
        use_mobile_test=0,
        use_mobile_online=0,
        is_display=1,
        is_mapp=0,
        is_default=0,
        is_open=0,
        is_max=0,
        display_type='app',
        issetbar=1,
        isflash=0,
        isresize=1,
        usecount=0,
        starnum=0,  # 星级评分
        starnum_ied=0,  # 星级评分
        deploy_ver="default",  # 部署的版本
        cpu_limit=1024,  # 上线或提测CPU限制
        mem_limit=512,  # 上线或提测内存限制
        open_mode="desktop",
    )
    return LApplication(**adaptive_lapplication_fields(values))


def test_create_legacy_app_1(legacy_app):
    # if run this test twice, this test will raise exception when transaction rollback fail
    with configure_regions(["ieod"]):
        session = legacy_db.get_scoped_session()
        session.add(legacy_app)
        session.commit()


def test_create_legacy_app_2(legacy_app):
    # if run this test twice, this test will raise exception when transaction rollback fail
    with configure_regions(["ieod"]):
        session = legacy_db.get_scoped_session()
        session.add(legacy_app)
        session.commit()
