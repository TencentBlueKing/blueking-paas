# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from paasng.platform.engine.constants import KMSCleanupStatus, KMSConfigVersionStatus
from paasng.platform.engine.models import Deployment, KMSConfigVersion

pytestmark = pytest.mark.django_db


def _create_version(**overrides) -> KMSConfigVersion:
    kwargs = {
        "app_code": "demo",
        "module_name": "web",
        "env_name": "prod",
        "module_environment_id": "6a2e0d4c1b3f4e5a8c7d9e0f1a2b3c4d",
        "envelope": "ZW52ZWxvcGU=",
        "credential_name": "demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d",
        "openbao_key": "default/scope/blueking/secret/demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d",
        "kms_role": "default.scope.blueking.secret.demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d",
        "cluster_name": "test-cluster",
        "namespace": "bkapp-demo-prod",
        "service_account_name": "demo-web-prod-kms",
        "cluster_secret_store_name": "kms-default-demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d",
        "resource_name": "kms-demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d",
    }
    kwargs.update(overrides)
    return KMSConfigVersion.objects.create(**kwargs)


class TestKMSConfigVersion:
    def test_defaults_to_pending_and_not_requested(self):
        version = _create_version()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.PENDING.value
        assert version.cleanup_status == KMSCleanupStatus.NOT_REQUESTED.value
        assert version.credential_id is None
        assert version.tenant_id == "default"

    def test_deleting_deployment_keeps_version(self, bk_deployment):
        version = _create_version()
        bk_deployment.kms_config_version = version
        bk_deployment.save(update_fields=["kms_config_version"])

        Deployment.objects.filter(pk=bk_deployment.pk).delete()

        assert KMSConfigVersion.objects.filter(pk=version.pk).exists()

    def test_deleting_version_only_unlinks_deployment(self, bk_deployment):
        version = _create_version()
        bk_deployment.kms_config_version = version
        bk_deployment.save(update_fields=["kms_config_version"])

        version.delete()

        bk_deployment.refresh_from_db()
        assert bk_deployment.kms_config_version is None
        assert Deployment.objects.filter(pk=bk_deployment.pk).exists()
