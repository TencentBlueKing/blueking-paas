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
from functools import partial
from typing import Dict, List, Literal, Optional, Type, Union

import cattr
from django.db import models
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field

from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.log.constants import DEFAULT_LOG_CONFIG_PLACEHOLDER
from paasng.utils.models import AuditedModel, UuidAuditedModel, make_json_field


def registry(pydantic_model: Type[BaseModel]):
    cattr.register_structure_hook(pydantic_model, lambda obj, cl: pydantic_model.parse_obj(obj))
    cattr.register_unstructure_hook(pydantic_model, partial(pydantic_model.dict, by_alias=True))
    return pydantic_model


@registry
class ElasticSearchHost(BaseModel):
    """ES 配置, 字段命名保持 elasticsearch 的格式"""

    host: str
    port: int
    http_auth: str = Field(..., description="形如 username:password 的凭证对")
    url_prefix: str = ""
    use_ssl: bool = Field(False)


@registry
class ElasticSearchParams(BaseModel):
    """ES 搜索相关配置"""

    indexPattern: str = Field(description="索引模板")
    timeField: str = Field(default="@timestamp", description="时间字段")
    timeFormat: Literal["timestamp[s]", "timestamp[ns]", "datetime"] = Field(default="timestamp[s]")
    messageField: str = Field(default="json.message", description="消息字段")
    termTemplate: Dict[str, str] = Field(description="搜索语句模板, 例如 {'app_code.keyword': '{{ app_code }}'};")
    builtinFilters: Dict[str, Union[str, List[str]]] = Field(default_factory=dict, description="内置的过滤条件")
    builtinExcludes: Dict[str, Union[str, List[str]]] = Field(default_factory=dict, description="内置的排除条件")


@registry
class BKLogConfig(BaseModel):
    """日志平台的查询配置"""

    scenarioID: Literal["log", "bkdata"] = Field(default="log", description="接入场景")
    bkdataDataToken: Optional[str] = Field(description="数据平台认证Token")
    bkdataAuthenticationMethod: Optional[Literal["token", "user"]] = Field(description="数据平台认证方式")


@registry
class ContainerLogCollectorConfig(BaseModel):
    """容器日志采集配置"""

    paths: List[str] = Field(default_factory=list, min_items=1, description="日志路径")
    data_encoding: Optional[str] = Field(..., description="日志字符集")


ElasticSearchHostField = make_json_field("ElasticSearchHostField", ElasticSearchHost)
BKLogConfigField = make_json_field("BKLogConfigField", BKLogConfig)
ElasticSearchParamsField = make_json_field("ElasticSearchParamsField", ElasticSearchParams)
ContainerLogCollectorConfigField = make_json_field("ContainerLogCollectorConfigField", ContainerLogCollectorConfig)


class ProcessStructureLogCollectorConfig(AuditedModel):
    """进程结构化日志采集配置"""

    collector_config_id = models.BigAutoField(_("采集配置ID"), primary_key=True)

    # TODO: 二期功能, 支持管理日志采集规则
    application = models.ForeignKey(Application, on_delete=models.CASCADE, db_constraint=False)
    env = models.ForeignKey(ModuleEnvironment, on_delete=models.CASCADE, db_constraint=False)
    process_type = models.CharField(help_text="进程类型(名称)", max_length=16)

    config = ContainerLogCollectorConfigField(null=True)


class ElasticSearchConfig(UuidAuditedModel):
    """ES查询配置"""

    # TODO: 支持云原生应用
    collector_config_id = models.CharField(_("采集配置ID"), unique=True, help_text="采集配置ID", max_length=64)
    backend_type = models.CharField(help_text="日志后端类型, 可选 'es', 'bkLog' ", max_length=16)
    elastic_search_host: Optional[ElasticSearchHost] = ElasticSearchHostField(
        null=True, help_text="required when backend_type is 'es'"
    )
    bk_log_config: Optional[BKLogConfig] = BKLogConfigField(
        null=True, help_text="required when backend_type is 'bkLog'"
    )
    search_params: ElasticSearchParams = ElasticSearchParamsField(help_text="ES 搜索相关配置")


class ProcessLogQueryConfigManager(models.Manager):
    def select_process_irrelevant(self, env: Optional[ModuleEnvironment] = None):
        # 兼容关联查询(RelatedManager)的接口
        if env is None:
            if hasattr(self, "instance"):
                env = self.instance
            else:
                raise TypeError("select_process_irrelevant() 1 required positional argument: 'env'")
        return self.filter(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER).get()

    def get_by_process_type(self, process_type: Optional[str], env: Optional[ModuleEnvironment] = None):
        # 兼容关联查询(RelatedManager)的接口
        if env is None:
            if hasattr(self, "instance"):
                env = self.instance
            else:
                raise TypeError("select_process_irrelevant() 1 required positional argument: 'env'")
        try:
            self.filter(env=env, process_type=process_type).get()
        except ProcessLogQueryConfig.DoesNotExist:
            # get all process placeholder as fallback
            return self.filter(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER).get()


class ProcessLogQueryConfig(UuidAuditedModel):
    """进程日志查询配置"""

    env = models.ForeignKey(ModuleEnvironment, on_delete=models.CASCADE, db_constraint=False)
    process_type = models.CharField(_("进程类型(名称)"), max_length=16, blank=True, null=True, help_text="默认配置使用 ")

    stdout = models.ForeignKey(
        ElasticSearchConfig,
        on_delete=models.SET_NULL,
        db_constraint=False,
        help_text="标准输出日志配置",
        null=True,
        related_name="related_stdout",
    )
    json = models.ForeignKey(
        ElasticSearchConfig,
        on_delete=models.SET_NULL,
        db_constraint=False,
        help_text="结构化日志配置",
        null=True,
        related_name="related_json",
    )
    ingress = models.ForeignKey(
        ElasticSearchConfig,
        on_delete=models.SET_NULL,
        db_constraint=False,
        help_text="接入层日志配置",
        null=True,
        related_name="related_ingress",
    )

    objects = ProcessLogQueryConfigManager()
