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
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.offline import OfflineOperation
from paasng.platform.modules.protections import (
    AllEnvsArchivedCondition,
    ConditionNotMatched,
    CustomDomainUnBoundCondition,
    NoPendingOperationsCondition,
)

pytestmark = pytest.mark.django_db


class TestNoPendingOperationsCondition:
    def test_match(self, bk_module):
        NoPendingOperationsCondition(bk_module).validate()

    def test_pending_deployment(self, bk_module, bk_stag_env):
        G(Deployment, status=JobStatus.PENDING.value, app_environment=bk_stag_env)
        with pytest.raises(ConditionNotMatched):
            NoPendingOperationsCondition(bk_module).validate()

    def test_pending_offline(self, bk_module, bk_stag_env):
        G(OfflineOperation, status=JobStatus.PENDING.value, app_environment=bk_stag_env)
        with pytest.raises(ConditionNotMatched):
            NoPendingOperationsCondition(bk_module).validate()


class TestAllEnvsArchivedCondition:
    def test_undeploy(self, bk_module):
        AllEnvsArchivedCondition(bk_module).validate()

    def test_deployed(self, bk_module, bk_stag_env):
        G(Deployment, status=JobStatus.SUCCESSFUL.value, app_environment=bk_stag_env)
        with pytest.raises(ConditionNotMatched):
            AllEnvsArchivedCondition(bk_module).validate()

    def test_deploy_but_archived(self, bk_module, bk_stag_env):
        G(Deployment, status=JobStatus.SUCCESSFUL.value, app_environment=bk_stag_env)
        G(OfflineOperation, status=JobStatus.SUCCESSFUL.value, app_environment=bk_stag_env)
        bk_stag_env.is_offlined = True
        bk_stag_env.save()
        AllEnvsArchivedCondition(bk_module).validate()

    def test_redeploy(self, bk_module, bk_stag_env):
        G(Deployment, status=JobStatus.SUCCESSFUL.value, app_environment=bk_stag_env)
        G(OfflineOperation, status=JobStatus.SUCCESSFUL.value, app_environment=bk_stag_env)
        G(Deployment, status=JobStatus.SUCCESSFUL.value, app_environment=bk_stag_env)
        with pytest.raises(ConditionNotMatched):
            AllEnvsArchivedCondition(bk_module).validate()


class TestCustomDomainUnBoundCondition:
    @pytest.fixture()
    def list_addrs_stub(self):
        with mock.patch("paasng.platform.modules.protections.LiveEnvAddresses.list_custom") as mocker:
            yield mocker

    def test_no_domain(self, bk_module, list_addrs_stub):
        list_addrs_stub.return_value = []
        CustomDomainUnBoundCondition(bk_module).validate()

    def test_any_domain(self, bk_module, list_addrs_stub):
        list_addrs_stub.return_value = [1]
        with pytest.raises(ConditionNotMatched):
            CustomDomainUnBoundCondition(bk_module).validate()
