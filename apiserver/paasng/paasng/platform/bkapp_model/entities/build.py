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

from typing import Dict, Optional

from pydantic import BaseModel

from paasng.platform.bkapp_model.constants import ImagePullPolicy


class AppBuildConfig(BaseModel):
    """
    构建配置

    :param image: 镜像名称
    :param image_pull_policy: 镜像拉取策略
    :param image_credentials_name: 镜像凭证名称
    :param dockerfile: Dockerfile 路径
    :param build_target: 当 Dockerfile 中启用了"多阶段构建"时，可用本字段指定阶段名
    :param args: 执行构建命令时所需要传入的额外参数
    """

    image: Optional[str] = None
    image_pull_policy: str = ImagePullPolicy.IF_NOT_PRESENT.value
    image_credentials_name: Optional[str] = None
    dockerfile: Optional[str] = None
    build_target: Optional[str] = None
    args: Optional[Dict[str, str]] = None
