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

import logging

from paasng.platform.modules.models.module import Module
from paasng.platform.modules.models.runtime import AppSlugRunner
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.utils.moby_distribution.registry.utils import NamedImage, parse_image

logger = logging.getLogger(__name__)


class SMartImageManager:
    def __init__(self, module: Module):
        self.module = module

    def get_slugrunner_image_info(self) -> NamedImage:
        """获取 slug S-Mart 基础镜像信息"""
        if bksmart_settings.base_image.name and bksmart_settings.base_image.tag:
            return NamedImage(
                domain=bksmart_settings.registry.host,
                name=bksmart_settings.base_image.name,
                tag=bksmart_settings.base_image.tag,
            )

        default_runner = AppSlugRunner.objects.filter(is_default=True).first()
        if not default_runner:
            raise ValueError("Unknown base image for S-Mart")
        named = parse_image(default_runner.image, default_registry=bksmart_settings.registry.host)
        return named

    def get_cnb_runner_image_info(self) -> NamedImage:
        """获取 cloud native S-Mart 基础镜像信息"""
        if bksmart_settings.cnb_base_image.name and bksmart_settings.cnb_base_image.tag:
            return NamedImage(
                domain=bksmart_settings.registry.host,
                name=bksmart_settings.cnb_base_image.name,
                tag=bksmart_settings.cnb_base_image.tag,
            )
        # TODO: 从 DB 读取默认的 cnb runner
        raise ValueError("Unknown base image for S-Mart")

    def get_image_info(self, tag: str = "latest") -> NamedImage:
        """获取当前 S-Mart 应用的镜像信息"""
        return NamedImage(
            domain=bksmart_settings.registry.host,
            name=f"{bksmart_settings.registry.namespace}/{self.module.application.code}/{self.module.name}",
            tag=tag,
        )
