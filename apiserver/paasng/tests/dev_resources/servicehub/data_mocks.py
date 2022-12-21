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
        "specifications": [
            {"name": "version", "display_name_zh_cn": "version", "display_name_en": "version", "description": ""},
            {"name": "engine", "display_name_zh_cn": "engine", "display_name_en": "engine", "description": ""},
            {"name": "app_zone", "display_name_zh_cn": "app_zone", "display_name_en": "app_zone", "description": ""},
        ],
        "plans": [
            {
                "uuid": "a8ad12f7-4dd5-4871-8e31-9a1f9f3795a2",
                "name": "r1-default",
                "properties": {"region": "r1"},
                "specifications": {"app_zone": "universal"},
                "description": "专门为 r1 版本服务",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "38ad12f9-4dd5-4871-8e31-9a1f9f3795a3",
                "name": "r2-default",
                "properties": {"region": "r2"},
                "specifications": {"app_zone": "universal"},
                "description": "专门为 r2 版本服务",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "fbbf7ae9-e7db-497b-ad6b-97d315afcfbc",
                "name": "r2-for-stag-only",
                "properties": {"region": "r2", "restricted_envs": ["stag"]},
                "specifications": {"app_zone": "universal"},
                "description": "专门为 r2 版本服务(stag only)",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "c382148c-01ba-42c9-9fbe-d8de1fe2aade",
                "name": "r2-v1-x1",
                "properties": {"region": "r2"},
                "specifications": {"version": "1", "engine": "x1", "app_zone": "universal"},
                "description": "专门为 r2 版本服务",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "f0673704-c172-413d-a6b2-ca6e8392261f",
                "name": "r2-v1-x1",
                "properties": {"region": "r2"},
                "specifications": {"version": "1", "engine": "x1", "app_zone": "qzone"},
                "description": "专门为 r2 版本服务",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "aa8ed040-3d5b-4235-b70d-36c855fc567f",
                "name": "r2-v2-x2",
                "properties": {"region": "r2"},
                "specifications": {"version": "2", "engine": "x1", "app_zone": "universal"},
                "description": "专门为 r2 版本服务",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "92402ebb-4c7f-4b39-92f1-bbd676244302",
                "name": "r2-v2-x2",
                "properties": {"region": "r2"},
                "specifications": {"version": "2", "engine": "x2", "app_zone": "universal"},
                "description": "专门为 r2 版本服务",
                "is_active": True,
                "service": "4c17073c-b2b9-421a-8a67-223200e3c0dc",
            },
            {
                "uuid": "adeba975-80c0-4fd0-bece-293ae1add313",
                "name": "r3-default",
                "properties": {"region": "r3", "restricted_envs": ["prod"]},
                "specifications": {"app_zone": "universal"},
                "description": "专门为 r3 版本服务",
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
        "specifications": [
            {"name": "version", "display_name_zh_cn": "version", "display_name_en": "version", "description": ""},
        ],
        "plans": [
            {
                "uuid": "a9ad13f7-4dd5-4871-8e31-9a1f9f3795a2",
                "name": "ieod-default",
                "properties": {"region": "r1"},
                "description": "专门为 r1 版本服务",
                "is_active": True,
                "service": "3c18074c-b2b9-421a-8a67-223200e3c1dc",
            },
            {
                "uuid": "92402ebb-4c7f-4b39-92f1-bbd676244302",
                "name": "r3-v2",
                "properties": {"region": "r3"},
                "specifications": {"version": "2"},
                "description": "专门为 r3 版本服务",
                "is_active": True,
                "service": "3c18074c-b2b9-421a-8a67-223200e3c1dc",
            },
            {
                "uuid": "6ad2442a-3433-487b-8193-47c7bf186cd1",
                "name": "r3-v3",
                "properties": {"region": "r3"},
                "specifications": {"version": "3"},
                "description": "专门为 r3 版本服务",
                "is_active": True,
                "service": "3c18074c-b2b9-421a-8a67-223200e3c1dc",
            },
        ],
    },
    {
        "uuid": "4d8d62b3-8f1e-4c6d-9e28-31974380b1ba",
        "name": "legacy",
        "category": 1,
        "display_name_zh_cn": "2",
        "display_name_en": "2",
        "logo": "http://x.com/x.jpg",
        "description_zh_cn": "4",
        "description_en": "4",
        "available_languages": "7",
        "is_visible": True,
        "plans": [
            {
                "uuid": "170fc9a7-cc57-4cfc-a748-e22e78210f0d",
                "name": "r1-default",
                "properties": {"region": "rr1"},
                "description": "专门为 rr1 版本服务",
                "is_active": True,
                "service": "4d8d62b3-8f1e-4c6d-9e28-31974380b1ba",
            },
            {
                "uuid": "b5b883d6-86bc-4c94-9c37-6b11d4db3c5e",
                "name": "r2-for-stag-only",
                "properties": {"region": "rr2", "restricted_envs": ["stag"]},
                "description": "专门为 rr2 版本服务",
                "is_active": True,
                "service": "4d8d62b3-8f1e-4c6d-9e28-31974380b1ba",
            },
            {
                "uuid": "c8df17da-a190-435e-b0bd-9f31310f79e3",
                "name": "r2-default",
                "properties": {"region": "rr2", "restricted_envs": ["prod"]},
                "description": "专门为 rr2 版本服务",
                "is_active": True,
                "service": "4d8d62b3-8f1e-4c6d-9e28-31974380b1ba",
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
