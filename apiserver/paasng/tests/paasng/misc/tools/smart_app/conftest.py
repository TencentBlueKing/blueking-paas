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

from typing import Dict, Optional

import pytest

from .setup_utils import create_fake_smart_build

pytestmark = pytest.mark.django_db


@pytest.fixture()
def smart_build():
    """Create a SmartBuild instance for testing"""
    return create_fake_smart_build()


def construct_foo_pod(name: str, labels: Optional[Dict] = None, restart_policy: str = "Always") -> Dict:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name, "labels": labels or {}},
        "spec": {
            # Set "schedulerName", so the pod won't be processed by the default
            # scheduler.
            "schedulerName": "no-running-scheduler",
            "containers": [{"name": "main", "image": "busybox:latest", "imagePullPolicy": "IfNotPresent"}],
            "restartPolicy": restart_policy,
            "automountServiceAccountToken": False,
        },
    }
