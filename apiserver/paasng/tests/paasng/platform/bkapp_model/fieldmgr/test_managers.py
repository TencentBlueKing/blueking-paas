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
from paasng.platform.bkapp_model.fieldmgr.fields import F_DOMAIN_RESOLUTION, F_SVC_DISCOVERY
from paasng.platform.bkapp_model.fieldmgr.managers import FieldManager, MultiFieldsManager

pytestmark = pytest.mark.django_db(databases=["default"])


class TestFieldManager:
    def test_integrated(self, bk_module):
        m = FieldManager(bk_module, F_SVC_DISCOVERY)
        assert m.get() is None

        m.set(FieldMgrName.WEB_FORM)
        assert m.get() == FieldMgrName.WEB_FORM
        assert m.can_be_managed_by(FieldMgrName.WEB_FORM)

        # Initialize the manager again to check the management status written before
        # is persistent.
        m2 = FieldManager(bk_module, F_SVC_DISCOVERY)
        assert m2.can_be_managed_by(FieldMgrName.WEB_FORM)

        m2.reset()
        assert m2.get() is None

    def test_init_manager_when_field_no_managed(self, bk_module):
        m = FieldManager(bk_module, F_SVC_DISCOVERY)
        assert m.get() is None

        m1 = FieldManager(bk_module, F_SVC_DISCOVERY, default_manager=FieldMgrName.APP_DESC)
        assert m1.can_be_managed_by(FieldMgrName.APP_DESC)

        m1.reset()
        assert m1.get() is None

        m2 = FieldManager(bk_module, F_SVC_DISCOVERY, default_manager=FieldMgrName.WEB_FORM)
        assert m2.can_be_managed_by(FieldMgrName.WEB_FORM)


class TestMultiFieldsManager:
    def test_integrated(self, bk_module):
        m = MultiFieldsManager(bk_module)
        m.set_many([F_SVC_DISCOVERY, F_DOMAIN_RESOLUTION], FieldMgrName.WEB_FORM)

        assert FieldManager(bk_module, F_SVC_DISCOVERY).can_be_managed_by(FieldMgrName.WEB_FORM)
        assert FieldManager(bk_module, F_DOMAIN_RESOLUTION).can_be_managed_by(FieldMgrName.WEB_FORM)
