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

from paasng.platform.bkapp_model.fieldmgr.constants import FieldMgrName
from paasng.platform.bkapp_model.fieldmgr.fields import (
    F_DOMAIN_RESOLUTION,
    F_SVC_DISCOVERY,
    ManagerFieldsRow,
    ManagerFieldsRowGroup,
)

pytestmark = pytest.mark.django_db(databases=["default"])


class TestManagedFields:
    def test_start_from_empty(self):
        mf = ManagerFieldsRowGroup([])
        assert mf.get_manager(F_SVC_DISCOVERY) is None

        # Set the manager and check
        mf.set_manager(F_SVC_DISCOVERY, FieldMgrName.WEB_FORM)
        assert mf.get_manager(F_SVC_DISCOVERY) == FieldMgrName.WEB_FORM
        assert len(mf.get_updated_rows()) == 1

        # Change the manager and check again
        mf.set_manager(F_SVC_DISCOVERY, FieldMgrName.APP_DESC)
        assert mf.get_manager(F_SVC_DISCOVERY) == FieldMgrName.APP_DESC
        assert len(mf.get_updated_rows()) == 2

    # The order of the rows should not matter
    @pytest.mark.parametrize("reverse_rows", [False, True])
    def test_existed_rows(self, reverse_rows):
        rows = [
            ManagerFieldsRow(FieldMgrName.WEB_FORM, [F_SVC_DISCOVERY]),
            ManagerFieldsRow(FieldMgrName.APP_DESC, [F_DOMAIN_RESOLUTION]),
        ]
        mf = ManagerFieldsRowGroup(
            rows if not reverse_rows else list(reversed(rows)),
        )
        assert mf.get_manager(F_SVC_DISCOVERY) == FieldMgrName.WEB_FORM
        assert len(mf.get_updated_rows()) == 0

        # Set the manager to the same value should have no effect
        mf.set_manager(F_SVC_DISCOVERY, FieldMgrName.WEB_FORM)
        assert len(mf.get_updated_rows()) == 0

        # Set the manager to a different value
        mf.set_manager(F_SVC_DISCOVERY, FieldMgrName.APP_DESC)
        assert mf.get_manager(F_SVC_DISCOVERY) == FieldMgrName.APP_DESC
        assert len(mf.get_updated_rows()) == 2

    def test_reset_manager(self):
        rows = [
            ManagerFieldsRow(FieldMgrName.WEB_FORM, [F_SVC_DISCOVERY]),
            ManagerFieldsRow(FieldMgrName.APP_DESC, [F_DOMAIN_RESOLUTION]),
        ]
        mf = ManagerFieldsRowGroup(rows)
        assert mf.get_manager(F_DOMAIN_RESOLUTION) == FieldMgrName.APP_DESC

        mf.reset_manager(F_DOMAIN_RESOLUTION)
        assert mf.get_manager(F_DOMAIN_RESOLUTION) is None
