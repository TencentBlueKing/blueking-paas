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
from kubernetes.client.apis import VersionApi

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING
from tests.utils.helpers import kube_ver_lt


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock(), get_client_by_cluster_name(CLUSTER_NAME_FOR_TESTING) as k8s_client:
        k8s_version = VersionApi(k8s_client).get_code()

    if kube_ver_lt(k8s_version, (1, 20)):
        pytest.skip("Skip tests because current k8s version less than 1.20")
