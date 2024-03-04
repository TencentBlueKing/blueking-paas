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
import logging
from itertools import chain, product
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar, Union, cast

from django.core.files.base import ContentFile
from django.utils.functional import Promise
from django.utils.translation import gettext as _
from pydantic import BaseModel, Field

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.accessories.publish.market.constant import OpenMode
from paasng.accessories.servicehub.manager import ServiceObj, mixed_service_mgr
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
from paasng.platform.modules.models import Module

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
    specs: Dict = Field(default_factory=dict, description="限定规格")
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
    spec: bk_app.BkAppSpec


class ApplicationDesc(BaseModel):
    spec_version: AppSpecVersion = AppSpecVersion.VER_2
    code: str
    name_zh_cn: str
    name_en: str
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


class ApplicationDescDiffDog:
    """deprecated: TODO: 前端重构后未再使用 `diffs` 字段展示差异, 是否可以移除相关实现？"""

    def __init__(self, application: Application, desc: ApplicationDesc):
        self.application = application
        self.desc = desc

    def diff(self) -> Dict[str, ModuleDiffResult]:
        diffs = {}
        for module in self.application.modules.all():
            try:
                diffs[module.name] = self._diff_module(module)
            except ValueError:
                logger.warning("Module<%s> of the application<%s> is removed.", module.name, self.application.code)

        # 生成未创建的模块的差异
        for module_name, module_desc in self.desc.modules.items():
            if module_name not in diffs:
                diffs[module_name] = ModuleDiffResult(
                    services=self._diff_services(
                        current_services=set(), expected_services={item.name for item in module_desc.spec.addons}
                    )
                )
        return diffs

    def _diff_module(self, module: "Module") -> ModuleDiffResult:
        """对比模块与模块定义之间的差异

        :param module: 需要与 ModuleSpec 做对比的模块
        :return: DescDiffResult
        :raise ValueError: 如果提供的模块未在 ApplicationDesc 中定义, 那么将抛出 ValueError 异常.
        """
        if module.name not in self.desc.modules:
            raise ValueError(f"Module<{module.name}> not found!")

        current_services = {service.name for service in mixed_service_mgr.list_binded(module)}  # type: ignore
        expected_services = {item.name for item in self.desc.modules[module.name].spec.addons}

        return ModuleDiffResult(services=self._diff_services(current_services, expected_services))

    def _diff_services(self, current_services: Set[str], expected_services: Set[str]) -> List[DiffItem]:
        """根据支持的增强服务列表, 目前的增强服务列表, 期望的增强服务列表计算差异

        :param current_services: 目前已绑定的增强服务名称集合
        :param expected_services: 期望绑定的增强服务名称集合
        :return:
        """
        supported_services = list(mixed_service_mgr.list_by_region(self.application.region))
        supported_services = cast(List[ServiceObj], supported_services)
        not_modified_services = sorted(current_services & expected_services)
        added_services = sorted(expected_services - current_services)
        deleted_services = sorted(current_services - expected_services)

        def make_service_spec(service: str) -> ServiceSpec:
            spec = ServiceSpec(name=service)
            try:
                spec.display_name = next(item.display_name for item in supported_services if item.name == spec.name)
            except StopIteration:
                spec.display_name = spec.name
            return spec

        return [
            DiffItem(
                resource=make_service_spec(service=service),
                diff_type=diff_type,
            )
            for service, diff_type in chain(
                product(deleted_services, [DiffType.DELETED]),
                product(not_modified_services, [DiffType.NOT_MODIFIED]),
                product(added_services, [DiffType.ADDED]),
            )
        ]
