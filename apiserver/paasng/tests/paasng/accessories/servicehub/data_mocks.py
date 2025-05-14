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

from typing import Any, Dict, List

OBJ_STORE_REMOTE_SERVICES_JSON: List[Dict[str, Any]] = [
    {
        "uuid": "3c18073c-b2b9-421a-8a67-223200e3c0dc",
        "name": "ceph",
        "category": 1,
        "display_name_zh_cn": "对象存储（Ceph）",
        "display_name_en": "Object Storage（Ceph）",
        "logo": "",
        "description_zh_cn": "对象存储，可存储图片、文件等",
        "description_en": "对象存储，可存储图片、文件等",
        "available_languages": "python",
        "is_visible": True,
        "plans": [
            {
                "uuid": "a8ad12f7-4dd5-4871-8e31-9a1f9f3795a2",
                "name": "plan-1",
                "description": "Plan 1",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "38ad12f9-4dd5-4871-8e31-9a1f9f3795a3",
                "name": "plan-2",
                "description": "Plan 2",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
        ],
    },
    {
        "uuid": "3c18074c-b2b9-421a-8a67-223200e3c1dc",
        "name": "APM",
        "category": 2,
        "display_name_zh_cn": "APM 性能监控服务",
        "display_name_en": "APM 性能监控服务",
        "logo": "",
        "description_zh_cn": "APM",
        "description_en": "APM",
        "available_languages": "python,php",
        "is_visible": True,
        "plans": [
            {
                "uuid": "a9ad13f7-4dd5-4871-8e31-9a1f9f3795a2",
                "name": "plan-1",
                "description": "Plan 1",
                "is_active": True,
                "service": "3c18074c-b2b9-421a-8a67-223200e3c1dc",
            },
            {
                "uuid": "92402ebb-4c7f-4b39-92f1-bbd676244302",
                "name": "plan-2",
                "description": "Plan 2",
                "is_active": True,
                "service": "3c18074c-b2b9-421a-8a67-223200e3c1dc",
            },
        ],
    },
]

REMOTE_INSTANCE_JSON = {
    "uuid": "493b6f67-b4fd-4739-9a27-85a9356422e6",
    "created": "2019-03-27T09:00:40.489049Z",
    "updated": "2019-03-27T09:00:40.490166Z",
    "config": {"username": "pig-bucket-2", "max_size": 1048576},
    "credentials": {
        "aws_access_key_id": "35ZQ8Q2J6C81C6B87240",
        "aws_secret_access_key": "txdM570AYr2scYADCIBLhv2GJPM2mnCZsjoeQ6fi",
        "rgw_host": "87c5004cb123:38081",
        "rgw_url": "http://87c5004cb123:38081",
        "bucket": "pig-bucket-2",
    },
    "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
    "plan": "f8ad12f2-4dd5-4871-8e31-9a1f9f3795a2",
}
