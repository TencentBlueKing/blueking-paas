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

from unittest import mock

import pytest
from kubernetes.dynamic import ResourceField

from paas_wl.infras.resources.kube_res.base import ResourceList


@pytest.fixture()
def mock_reader():
    class setter:
        def __init__(self, list_processes, list_instances):
            self.list_processes = list_processes
            self.list_instances = list_instances

        def set_processes(self, processes):
            self.list_processes.return_value = ResourceList(
                items=processes, metadata=ResourceField({"resourceVersion": "1"})
            )

        def set_instances(self, instances):
            self.list_instances.return_value = ResourceList(
                items=instances, metadata=ResourceField({"resourceVersion": "1"})
            )

    with (
        mock.patch("paas_wl.bk_app.processes.readers.ProcessReader.list_by_app_with_meta") as list_processes,
        mock.patch("paas_wl.bk_app.processes.readers.InstanceReader.list_by_app_with_meta") as list_instances,
    ):
        yield setter(list_processes, list_instances)
