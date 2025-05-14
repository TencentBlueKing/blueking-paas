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

from typing import Dict, List, Union

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.templates.models import Template


class TemplateSLZ(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = "__all__"

    def validate_preset_services_config(self, conf: Dict) -> Dict:
        if not isinstance(conf, dict):
            raise ValidationError(_("预设增强服务配置必须为 Dict 格式"))
        return conf

    def validate_required_buildpacks(self, required_buildpacks: Union[List, Dict]) -> Union[List, Dict]:
        if isinstance(required_buildpacks, list):
            if any(not isinstance(bp, str) for bp in required_buildpacks):
                raise ValidationError(_("构建工具配置必须为 List[str] 格式"))
        elif isinstance(required_buildpacks, dict):
            if "__default__" not in required_buildpacks:
                raise ValidationError(_("针对不同镜像配置 required_buildpacks 时必须配置默认值 __default__"))
            for required_buildpacks_for_image in required_buildpacks.values():
                if any(not isinstance(bp, str) for bp in required_buildpacks_for_image):
                    raise ValidationError(_("构建工具配置必须为 Dict[str, List[str]] 格式"))
        else:
            raise ValidationError(_("构建工具必须为 List[str] 或 Dict[str, List[str]] 格式"))
        return required_buildpacks

    def validate_processes(self, processes: Dict) -> Dict:
        if not isinstance(processes, dict):
            raise ValidationError(_("进程配置必须为 Dict 格式"))
        return processes

    def validate_tags(self, tags: List) -> List:
        if not isinstance(tags, list):
            raise ValidationError(_("标签必须为 List 格式"))
        return tags

    def validate_blob_url(self, value: str) -> str:
        if not value:
            raise ValidationError(_("二进制包存储配置必须为有效的地址字符串"))
        return value
