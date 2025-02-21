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

from rest_framework.exceptions import ValidationError

from paasng.platform.sourcectl.source_types import docker_registry_config


def validate_image_url(url: str) -> str:
    """检查镜像地址(判断是否支持第三方镜像)"""
    default_registry = docker_registry_config.default_registry
    allow_third_party_registry = docker_registry_config.allow_third_party_registry
    if not allow_third_party_registry and not url.startswith(default_registry):
        raise ValidationError(f"`{url}` is not supported, please use image of `{default_registry}`")
    return url
