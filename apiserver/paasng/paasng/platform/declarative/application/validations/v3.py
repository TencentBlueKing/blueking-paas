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
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.accessories.publish.market.serializers import ProductTagByNameField
from paasng.core.region.states import get_region
from paasng.platform.applications.serializers import AppIDField, AppIDUniqueValidator, AppNameField
from paasng.platform.declarative.application.resources import (
    ApplicationDesc,
    DisplayOptions,
    MarketDesc,
    ModuleDesc,
)
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.modules.serializers import ModuleNameField
from paasng.utils.i18n.serializers import I18NExtend, i18n
from paasng.utils.serializers import Base64FileField
from paasng.utils.validators import ReservedWordValidator

module_name_field = ModuleNameField()


class DisplayOptionsSLZ(serializers.Serializer):
    """Serializer for describing application's market.display_options properties"""

    width = serializers.IntegerField(required=False, default=1280, help_text="窗口宽度")
    height = serializers.IntegerField(required=False, default=600, help_text="窗口高度")
    isMaximized = serializers.BooleanField(
        required=False, default=False, source="is_win_maximize", help_text="窗口是否最大化"
    )
    isVisible = serializers.BooleanField(required=False, default=True, source="visible", help_text="是否展示")
    openMode = serializers.CharField(required=False, help_text="打开方式")

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
    introduction = I18NExtend(serializers.CharField(required=True, help_text="简介"))
    description = I18NExtend(serializers.CharField(required=False, default="", help_text="描述"))
    displayOptions = DisplayOptionsSLZ(required=False, default=DisplayOptionsSLZ.gen_default_value)
    logoB64ata = Base64FileField(required=False, help_text="应用logo", source="logo")

    def to_internal_value(self, data) -> MarketDesc:
        attrs = super().to_internal_value(data)
        tag = attrs.pop("tag", None)
        if tag:
            attrs["tag_id"] = tag.pk
        return MarketDesc(**attrs)


class ModuleSpecField(serializers.DictField):
    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        return bk_app.BkAppSpec(**attrs)

    def to_representation(self, value):
        if isinstance(value, bk_app.BkAppSpec):
            return value.dict(exclude_none=True, exclude_unset=True)
        return super().to_representation(value)


class ModuleDescriptionSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="模块名称", required=True)
    isDefault = serializers.BooleanField(default=False, help_text="是否为主模块")
    spec = ModuleSpecField(required=True)

    def to_internal_value(self, data) -> ModuleDesc:
        attrs = super().to_internal_value(data)
        return ModuleDesc(**attrs)


class AppDescriptionSLZ(serializers.Serializer):
    # S-mart 专用字段(region, bkAppCode, bkAppName)
    region = serializers.ChoiceField(required=False, allow_null=True, choices=get_region().get_choices())
    bkAppCode = AppIDField(
        # DNS safe(prefix)
        # S-mart 应用ID 长度限制为 20 个字符
        max_length=20,
        regex="^(?![0-9]+.*$)(?!-)[a-zA-Z0-9-_]{,63}(?<!-)$",
        validators=[ReservedWordValidator("应用 ID"), AppIDUniqueValidator()],
        error_messages={"invalid": _("格式错误，只能包含小写字母(a-z)、数字(0-9)和半角连接符(-)和下划线(_)")},
        source="code",
    )
    bkAppName = AppNameField(source="name_zh_cn")
    bkAppNameEn = AppNameField(source="name_en", required=False)
    market = MarketSLZ(required=False, default=None)
    modules = serializers.ListField(child=ModuleDescriptionSLZ())

    def validate_modules(self, modules: List[ModuleDesc]):
        for module_desc in modules:
            module_name_field.run_validation(module_desc.name)
        return modules

    def to_internal_value(self, data: Dict) -> ApplicationDesc:
        attrs = super().to_internal_value(data)
        attrs["name_en"] = attrs.get("name_en") or attrs["name_zh_cn"]

        modules_list = attrs.pop("modules")
        # 调整 modules 字段格式从 list 到 dict
        attrs["modules"] = {module_desc.name: module_desc for module_desc in modules_list}
        # 验证至少有一个主模块
        has_default = False
        for module_desc in modules_list:
            if module_desc.isDefault:
                if has_default:
                    raise serializers.ValidationError({"modules": _("一个应用只能有一个主模块")})
                has_default = True
        if not has_default:
            raise serializers.ValidationError({"modules": _("一个应用必须有一个主模块")})

        # 校验 shared_from 的模块是否存在
        for idx, module_desc in enumerate(modules_list):
            for addon in module_desc.spec.addons:
                if addon.moduleRef and addon.moduleRef.moduleName not in attrs["modules"]:
                    raise serializers.ValidationError(
                        {f"modules[{idx}].spec.addons": _("提供共享增强服务的模块不存在")}
                    )

        # 处理额外字段
        attrs.setdefault("plugins", [])
        if self.context.get("app_version"):
            attrs["plugins"].append({"type": AppDescPluginType.APP_VERSION, "data": self.context.get("app_version")})

        if self.context.get("spec_version"):
            attrs["spec_version"] = self.context["spec_version"]

        return ApplicationDesc(instance_existed=bool(self.instance), **attrs)
