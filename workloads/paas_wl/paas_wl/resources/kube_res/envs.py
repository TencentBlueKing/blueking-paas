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


def encode_envs(envs: Dict[str, Any]) -> List:
    """Encode Dict-like envs to k8s env list"""
    return [{"name": key, "value": str(value)} for key, value in envs.items()]


def decode_envs(envs: List) -> Dict[str, Any]:
    """Decode k8s env list to Dict-like envs"""
    return {env["name"]: env["value"] for env in envs if "name" in env and "value" in env}
