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
from typing import Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paasng.platform.declarative.application.resources import (
    ApplicationDesc,
    DisplayOptions,
    MarketDesc,
    ModuleDesc,
    ServiceSpec,
)
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.serializers import validate_language
from paasng.platform.applications.serializers import AppIDField, AppIDUniqueValidator, AppNameField
from paasng.platform.modules.serializers import ModuleNameField
from paasng.core.region.states import get_region
from paasng.accessories.publish.market.serializers import ProductTagByNameField
from paasng.utils.i18n.serializers import I18NExtend, i18n
from paasng.utils.serializers import Base64FileField
from paasng.utils.validators import ReservedWordValidator

module_name_field = ModuleNameField()


class DisplayOptionsSLZ(serializers.Serializer):
    """Serializer for describing application's market.display_options properties"""

    width = serializers.IntegerField(required=False, default=1280, help_text='窗口宽度')
    height = serializers.IntegerField(required=False, default=600, help_text='窗口高度')
    is_maximized = serializers.BooleanField(
        required=False, default=False, source='is_win_maximize', help_text='窗口是否最大化'
    )
    is_visible = serializers.BooleanField(required=False, default=True, source='visible', help_text='是否展示')
    open_mode = serializers.CharField(required=False, help_text="打开方式")

    @classmethod
    def gen_default_value(cls) -> DisplayOptions:
        """Generate default `DisplayOptions` object"""
        attrs = serializers.Serializer.to_internal_value(cls(), {})
        return DisplayOptions(**attrs)

    def to_internal_value(self, data) -> DisplayOptions:
        attrs = super().to_internal_value(data)
        return DisplayOptions(**attrs)


@i18n
class MarketSLZ(serializers.Serializer):
    """Serializer for describing application's market properties"""

    category = ProductTagByNameField(required=False, source="tag")
    introduction = I18NExtend(serializers.CharField(required=True, help_text='简介'))
    description = I18NExtend(serializers.CharField(required=False, default='', help_text='描述'))
    display_options = DisplayOptionsSLZ(required=False, default=DisplayOptionsSLZ.gen_default_value)
    logo_b64data = Base64FileField(required=False, help_text="应用logo", source="logo")

    def to_internal_value(self, data) -> MarketDesc:
        attrs = super().to_internal_value(data)
        tag = attrs.pop('tag', None)
        if tag:
            attrs['tag_id'] = tag.pk
        return MarketDesc(**attrs)


class ServiceSLZ(serializers.Serializer):
    """Describes a service object, plan & detailed specs requirements are not supported yet"""

    name = serializers.CharField(required=True, help_text='增强服务名称')
    shared_from = serializers.CharField(required=False, allow_null=True, help_text="从哪个模块共享该增强服务")
    specs = serializers.DictField(required=False, allow_null=True, default=dict, help_text="声明的增强服务规格")

    def to_internal_value(self, data) -> ServiceSpec:
        attrs = super().to_internal_value(data)
        return ServiceSpec(**attrs)


class ModuleDescriptionSLZ(serializers.Serializer):
    is_default = serializers.BooleanField(default=False, help_text="是否为主模块")
    language = serializers.CharField(help_text="模块开发语言", validators=[validate_language])
    services = serializers.ListField(child=ServiceSLZ(), required=False, default=[])
    source_dir = serializers.CharField(help_text="源码目录", required=False, default="")

    def to_internal_value(self, data) -> ModuleDesc:
        attrs = super().to_internal_value(data)
        return ModuleDesc(**attrs)


class AppDescriptionSLZ(serializers.Serializer):
    # S-mart 专用字段(region, bk_app_code, bk_app_name)
    region = serializers.ChoiceField(required=False, allow_null=True, choices=get_region().get_choices())
    bk_app_code = AppIDField(
        # DNS safe(prefix)
        regex="^(?![0-9]+.*$)(?!-)[a-zA-Z0-9-_]{,63}(?<!-)$",
        validators=[ReservedWordValidator("应用 ID"), AppIDUniqueValidator()],
        error_messages={'invalid': _('格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)和下划线(_)')},
        source='code',
    )
    bk_app_name = AppNameField(source='name_zh_cn')
    bk_app_name_en = AppNameField(source='name_en', required=False)
    market = MarketSLZ(required=False, default=None)
    modules = serializers.DictField(child=ModuleDescriptionSLZ())

    def validate_modules(self, modules: Dict[str, ModuleDesc]):
        for module_name in modules.keys():
            module_name_field.run_validation(module_name)
        return modules

    def to_internal_value(self, data: Dict) -> ApplicationDesc:
        attrs = super().to_internal_value(data)
        attrs["name_en"] = attrs.get("name_en") or attrs["name_zh_cn"]
        # 验证至少有一个主模块
        has_default = False
        for module_desc in attrs["modules"].values():
            if module_desc.is_default:
                if has_default:
                    raise serializers.ValidationError({"modules": _("一个应用只能有一个主模块")})
                has_default = True
        if not has_default:
            raise serializers.ValidationError({"modules": _("一个应用必须有一个主模块")})

        # 校验 shared_from 的模块是否存在
        for module_desc in attrs["modules"].values():
            for svc in module_desc.services:
                if svc.shared_from and svc.shared_from not in attrs["modules"]:
                    raise serializers.ValidationError({"modules.services": _("提供共享增强服务的模块不存在")})

        attrs.setdefault("plugins", [])
        if self.context.get("app_version"):
            attrs["plugins"].append({'type': AppDescPluginType.APP_VERSION, 'data': self.context.get("app_version")})

        if self.context.get("spec_version"):
            attrs["spec_version"] = self.context["spec_version"]

        return ApplicationDesc(instance_existed=bool(self.instance), **attrs)
