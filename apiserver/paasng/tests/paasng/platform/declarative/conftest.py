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

from tests.utils.mocks.cluster import cluster_ingress_config


@pytest.fixture(autouse=True)
def _setup_mocks():
    """Setup mocks for current testing module

    - Mock cluster ingress config with fixed domains
    - Mock ProcessManager which depends on `workloads` module
    """
    with cluster_ingress_config(
        {
            "sub_path_domains": [],
            "app_root_domains": [{"name": "bkapps.example.com"}],
        }
    ), mock.patch("paas_wl.bk_app.processes.processes.ProcessManager.sync_processes_specs"):
        yield


@pytest.fixture()
def one_px_png():
    """The binary content of an one pixel png format picture"""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00%\xdbV\xca\x00\x00"
        b"\x00\x01sRGB\x01\xd9\xc9,\x7f\x00\x00\x00\tpHYs\x00\x00\x00'\x00\x00\x00'\x01*\t\x91O\x00\x00\x00\x03PLTE"
        b"\x00\x00\x00\xa7z=\xda\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H"
        b"\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
