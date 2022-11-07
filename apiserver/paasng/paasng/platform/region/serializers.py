# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import typing
from collections import defaultdict
from typing import Dict, List, Union

from rest_framework import serializers

from paasng.dev_resources.templates.models import Template
from paasng.utils.i18n.serializers import TranslatedCharField

if typing.TYPE_CHECKING:
    from paasng.platform.region.models import Region


class RegionSerializer:
    """Serializer for Region object"""

    def __init__(self, region: 'Region'):
        self.region = region

    def serialize(self):
        data: Dict[str, Union[str, Dict]] = {"name": self.region.name}
        data["basic_info"] = BasicInfoSLZ(self.region.basic_info).data
        data["services"] = {"categories": ServiceCategorySLZ(self.region.service_categories, many=True).data}
        data["module_mobile_config"] = ModuleMobileConfigSLZ(self.region.module_mobile_config).data
        data["mul_modules_config"] = MulModulesConfigConfigSLZ(self.region.mul_modules_config).data

        # Patch entrance_config to provide "app_root_domain" field
        # TODO: Remove this field because it's app related instead of region
        entrance_config = self.region.entrance_config
        data["entrance_config"] = EntranceConfigSLZ(entrance_config).data
        return data


class BasicInfoSLZ(serializers.Serializer):
    description = serializers.CharField()


class ServiceCategorySLZ(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sort_priority = serializers.IntegerField()


class ModuleMobileConfigSLZ(serializers.Serializer):
    """Serializer for application mobile config"""

    enabled = serializers.BooleanField()


class MulModulesConfigConfigSLZ(serializers.Serializer):
    creation_allowed = serializers.BooleanField()


class EntranceConfigSLZ(serializers.Serializer):
    manually_upgrade_to_subdomain_allowed = serializers.BooleanField()


class TmplSLZ(serializers.Serializer):
    """创建应用/模块时，需要的模板信息"""

    name = serializers.CharField()
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    language = serializers.CharField()
    market_ready = serializers.BooleanField()


class AllSpecsSLZ:
    def __init__(self, regions: 'List[Region]'):
        self.regions = regions

    def serialize(self):
        data = {}
        for region in self.regions:
            languages = defaultdict(list)
            for tmpl in Template.objects.filter_by_region(region.name):
                languages[tmpl.language].append(TmplSLZ(tmpl).data)

            data.update(
                {
                    region.name: {
                        "display_name": region.display_name,
                        "languages": languages,
                        "description": region.basic_info.description,
                        "allow_deploy_app_by_lesscode": region.allow_deploy_app_by_lesscode,
                    }
                }
            )
        return data
