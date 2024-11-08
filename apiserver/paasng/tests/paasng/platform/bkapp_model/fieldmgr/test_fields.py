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

from paasng.platform.bkapp_model.fieldmgr.constants import ManagerType
from paasng.platform.bkapp_model.fieldmgr.fields import (
    F_DOMAIN_RESOLUTION,
    F_SVC_DISCOVERY,
    ManagedFields,
    ManagedFieldsRecord,
)

pytestmark = pytest.mark.django_db(databases=["default"])


class TestManagedFields:
    def test_start_from_empty(self, bk_module):
        mf = ManagedFields(bk_module, [])
        assert mf.get_manager(F_SVC_DISCOVERY) is None

        # Set the manager and check
        mf.set_manager(F_SVC_DISCOVERY, ManagerType.WEB_FORM)
        assert mf.get_manager(F_SVC_DISCOVERY) == ManagerType.WEB_FORM
        assert len(mf.get_dirty_records()) == 1

        # Change the manager and check again
        mf.set_manager(F_SVC_DISCOVERY, ManagerType.APP_DESC)
        assert mf.get_manager(F_SVC_DISCOVERY) == ManagerType.APP_DESC
        assert len(mf.get_dirty_records()) == 2

    def test_existed_records(self, bk_module):
        mf = ManagedFields(
            bk_module,
            [
                ManagedFieldsRecord(ManagerType.WEB_FORM, [F_SVC_DISCOVERY]),
                ManagedFieldsRecord(ManagerType.APP_DESC, [F_DOMAIN_RESOLUTION]),
            ],
        )
        assert mf.get_manager(F_SVC_DISCOVERY) == ManagerType.WEB_FORM
        assert len(mf.get_dirty_records()) == 0

        # Set the manager to the same value should have no effect
        mf.set_manager(F_SVC_DISCOVERY, ManagerType.WEB_FORM)
        assert len(mf.get_dirty_records()) == 0

        # Set the manager to a different value
        mf.set_manager(F_SVC_DISCOVERY, ManagerType.APP_DESC)
        assert mf.get_manager(F_SVC_DISCOVERY) == ManagerType.APP_DESC
        assert len(mf.get_dirty_records()) == 2
