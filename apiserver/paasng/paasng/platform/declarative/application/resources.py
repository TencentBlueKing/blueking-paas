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
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from django.core.files.base import ContentFile
from django.utils.functional import Promise
from django.utils.translation import gettext as _
from pydantic import BaseModel, Field

from paasng.accessories.publish.market.constant import OpenMode
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.platform.declarative.basic import AllowOmittedModel
from paasng.platform.declarative.constants import (
    OMITTED_VALUE,
    AppDescPluginType,
    AppSpecVersion,
    DiffType,
    OmittedType,
)
from paasng.platform.declarative.exceptions import DescriptionValidationError

M = TypeVar("M")
logger = logging.getLogger(__name__)


def get_application(json_data: Dict, field_name: str) -> Optional[Application]:
    """Try to get an application from JSON data"""
    try:
        return Application.default_objects.get(code=json_data[field_name])
    except Application.DoesNotExist:
        return None
    except KeyError:
        raise DescriptionValidationError({field_name: "内容不能为空"})


class DisplayOptions(AllowOmittedModel):
    # Optional fields
    width: Union[int, OmittedType] = Field(OMITTED_VALUE, description="窗口宽度")
    height: Union[int, OmittedType] = Field(OMITTED_VALUE, description="窗口高度")
    is_win_maximize: Union[bool, OmittedType] = Field(OMITTED_VALUE, description="是否最大化显示")
    visible: Union[bool, OmittedType] = Field(OMITTED_VALUE, description="是否展示")
    open_mode: Union[OpenMode, OmittedType] = Field(OMITTED_VALUE, description="打开方式")


class MarketDesc(AllowOmittedModel):
    introduction_en: Union[str, Promise] = Field(..., description="简介(英文)")
    introduction_zh_cn: Union[str, Promise] = Field(..., description="简介(中文)")

    # Optional fields
    description_en: Union[str, OmittedType, Promise] = Field(OMITTED_VALUE, description="描述(英文)")
    description_zh_cn: Union[str, OmittedType, Promise] = Field(OMITTED_VALUE, description="描述(中文)")
    tag_id: Union[str, OmittedType] = Field(OMITTED_VALUE, description="市场标签id")
    display_options: Union[DisplayOptions, OmittedType] = Field(OMITTED_VALUE)
    logo: Union[ContentFile, OmittedType] = Field(OMITTED_VALUE, description="logo 内容")


class ServiceSpec(BaseModel):
    name: str
    # specs 字段已弃用，不再接收描述文件通过 specs 定义任何规则
    specs: Dict = Field(default_factory=dict, description="限定规格，已弃用")
    display_name: Optional[str] = None
    shared_from: Optional[str] = None

    def __init__(__pydantic_self__, **data: Any) -> None:  # noqa: N805
        super().__init__(**data)
        if __pydantic_self__.display_name is None:
            __pydantic_self__.display_name = __pydantic_self__.name


class DiffItem(BaseModel, Generic[M]):
    resource: M
    diff_type: DiffType


class ModuleDiffResult(BaseModel):
    services: List[DiffItem[ServiceSpec]]


class ModuleDesc(BaseModel):
    name: Optional[str] = Field(..., description="模块名")
    language: AppLanguage = Field(AppLanguage.PYTHON, description="模块开发语言")
    is_default: bool = Field(False, description="是否为主模块?")
    source_dir: str = Field("", description="源码目录")
    services: List[ServiceSpec] = Field(default_factory=list)


class ApplicationDesc(BaseModel):
    spec_version: AppSpecVersion = AppSpecVersion.VER_2
    code: str
    name_zh_cn: str
    name_en: str
    # The region field is deprecated and does not have any real effect. Its value must be the
    # default region if it is set.
    region: Optional[str] = None
    market: Optional[MarketDesc] = None
    modules: Dict[str, ModuleDesc] = Field(default_factory=dict, description="该应用的模块")

    # Store extra plugins, such as version number of S-Mart application
    plugins: List[Dict] = Field(default_factory=list)
    # whether the application instance exists
    instance_existed: bool = False

    @property
    def default_module(self):
        try:
            return next(filter(lambda m: m.is_default, self.modules.values()))
        except StopIteration:
            raise RuntimeError(_("当前应用未定义主模块"))

    def get_plugin(self, plugin_type: AppDescPluginType) -> Optional[Dict]:
        """Return the first plugin in given type"""
        for plugin in self.plugins:
            if plugin["type"] == plugin_type:
                return plugin
        return None


class AppTenantConf(BaseModel):
    """应用租户相关的配置，参数的详细说明可参考：paasng/platform/applications/models.py 中 Application 的定义

    :param app_tenant_mode: 应用在租户层面的可用范围，可选值：全租户、指定租户
    :param app_tenant_id: 应用租户 ID
    :param tenant_id: 应用所属租户
    """

    app_tenant_mode: str
    app_tenant_id: str
    tenant_id: str
