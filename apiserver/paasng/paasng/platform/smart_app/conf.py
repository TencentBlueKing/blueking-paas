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

from django.conf import settings
from pydantic import BaseModel, Field

from paasng.utils.moby_distribution import APIEndpoint, DockerRegistryV2Client


class RegistryConf(BaseModel):
    """S-Mart 注册表配置"""

    host: str = Field(default=settings.SMART_DOCKER_REGISTRY_HOST, description="Registry 的域名")
    namespace: str = Field(
        default=settings.SMART_DOCKER_REGISTRY_NAMESPACE,
        description="S-Mart 镜像仓库的命名空间, 即在 Registry 中的项目名",
    )
    username: str = Field(default=settings.SMART_DOCKER_REGISTRY_USERNAME, description="用于访问 Registry 的账号")
    password: str = Field(default=settings.SMART_DOCKER_REGISTRY_PASSWORD, description="用于访问 Registry 的密码")

    def get_client(self) -> DockerRegistryV2Client:
        client = DockerRegistryV2Client.from_api_endpoint(
            api_endpoint=APIEndpoint(url=self.host),
            username=self.username,
            password=self.password,
        )
        return client


class BaseImageConf(BaseModel):
    """slug S-Mart 基础镜像配置, 用于配置合并镜像层时的基础镜像"""

    name: str = Field(default=settings.SMART_IMAGE_NAME, description="基础镜像的名称")
    tag: str = Field(default=settings.SMART_IMAGE_TAG, description="基础镜像的标签")


class CNBBaseImageConf(BaseModel):
    """cloud native S-Mart 基础镜像配置, 用于配置合并镜像层时的基础镜像"""

    name: str = Field(default=settings.SMART_CNB_IMAGE_NAME, description="云原生基础镜像的名称")
    tag: str = Field(default=settings.SMART_CNB_IMAGE_TAG, description="云原生基础镜像的标签")


class Settings(BaseModel):
    registry: RegistryConf = Field(default_factory=RegistryConf)
    base_image: BaseImageConf = Field(default_factory=BaseImageConf, description="slug s-mart 基础镜像")
    cnb_base_image: CNBBaseImageConf = Field(
        default_factory=CNBBaseImageConf, description="cloud native s-mart 基础镜像"
    )

    def reload(self):
        for field_name, field in self.__fields__.items():
            if field.default_factory:
                setattr(self, field_name, field.default_factory())


bksmart_settings = Settings()
