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

import pytest
from sqlalchemy.exc import IntegrityError

from paasng.accessories.publish.sync_market.managers import AppManger
from paasng.accessories.publish.sync_market.utils import cascade_delete_legacy_app
from paasng.core.core.storages.sqlalchemy import console_db
from tests.conftest import mark_skip_if_console_not_configured
from tests.utils.helpers import create_app

pytestmark = [
    mark_skip_if_console_not_configured(),
    pytest.mark.django_db,
    pytest.mark.xdist_group(name="legacy-db"),
    pytest.mark.usefixtures("_register_app_core_data"),
]


def test_cascade_delete_legacy_app(bk_app_full):
    new_app = create_app()
    session = console_db.get_scoped_session()
    app = AppManger(session).get(new_app.code)
    with pytest.raises(IntegrityError):
        AppManger(session).delete_by_code(app.code)
    assert cascade_delete_legacy_app("code", app.code, False) is not None
    app = AppManger(session).get(new_app.code)
    assert app is None
