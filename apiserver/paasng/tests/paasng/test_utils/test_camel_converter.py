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

from paasng.utils.camel_converter import dict_to_camel


@pytest.mark.parametrize(
    ("snake_case_dict", "camel_case_dict"),
    [
        ({"foo_bar": "cc"}, {"fooBar": "cc"}),
        (
            {"liveness": {"initial_delay_seconds": 0, "timeout_seconds": 1}},
            {"liveness": {"initialDelaySeconds": 0, "timeoutSeconds": 1}},
        ),
        (
            {
                "clusters": [
                    {"c_name": "BCS-01", "server_port": "443"},
                    {"c_name": "BCS-02", "server_port": "80"},
                ]
            },
            {
                "clusters": [
                    {"cName": "BCS-01", "serverPort": "443"},
                    {"cName": "BCS-02", "serverPort": "80"},
                ]
            },
        ),
        (
            {
                "monitoring": {
                    "metrics": [
                        {"process": "web1", "service_name": "metric"},
                        {"process": "web2", "service_name": "metric"},
                    ]
                }
            },
            {
                "monitoring": {
                    "metrics": [
                        {"process": "web1", "serviceName": "metric"},
                        {"process": "web2", "serviceName": "metric"},
                    ]
                }
            },
        ),
    ],
)
def test_dict_to_camel(snake_case_dict, camel_case_dict):
    assert dict_to_camel(snake_case_dict) == camel_case_dict
