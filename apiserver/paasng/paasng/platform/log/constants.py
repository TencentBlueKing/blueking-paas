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

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.conf import settings
from pydantic import BaseModel, Field, parse_obj_as, validator

from paasng.platform.log.utils import get_es_term
from paasng.utils.basic import ChoicesEnum


class ESField(BaseModel):
    title: str = Field("", description="字段的标题")
    chinese_name: str = Field("", description="字段的中文名称")
    query_term: str = Field(..., description="query_term: get参数中的key")
    is_multiple: bool = Field(False, description="是否多值过滤")
    is_filter: bool = Field(True, description="是否可以进行过滤")

    @validator("is_filter", always=True)
    @classmethod
    def json_field_blacklist(cls, value, values):
        # 根据黑名单限制某些字段不能开启搜索
        if values["query_term"] in settings.ES_JSON_FIELD_BLACKLIST:
            return False
        return value

    def get_es_term(self, mappings: dict) -> str:
        return get_es_term(self.query_term, mappings)


LOG_QUERY_FIELDS: List[ESField] = parse_obj_as(
    List[ESField],
    [
        {
            "title": "Env",
            "chinese_name": "部署环境",
            "query_term": "environment",
            "is_filter": True,
        },
        {
            "title": "Process",
            "chinese_name": "应用进程",
            "query_term": "process_id",
            "is_filter": True,
        },
        {
            "title": "Stream",
            "chinese_name": "日志输出流",
            "query_term": "stream",
            "is_filter": True,
        },
        {
            "title": "InstanceName",
            "chinese_name": "实例名称",
            "query_term": "pod_name",
            "is_filter": False,
        },
    ],
)

# queryField.title to queryField map
LOG_FILTER_FIELD_MAPS: Dict[str, ESField] = {f.title: f for f in LOG_QUERY_FIELDS if f.is_filter}


class LogTimeType(ChoicesEnum):
    """
    日志搜索-日期范围类型
    """

    TYPE_5m = "5m"
    TYPE_1h = "1h"
    TYPE_3h = "3h"
    TYPE_6h = "6h"
    TYPE_12h = "12h"
    TYPE_1d = "1d"
    TYPE_3d = "3d"
    TYPE_7d = "7d"
    TYPE_CUSTOMIZED = "customized"

    _choices_labels = (
        (TYPE_5m, "5分钟"),
        (TYPE_1h, "1小时"),
        (TYPE_3h, "3小时"),
        (TYPE_6h, "6小时"),
        (TYPE_12h, "12小时"),
        (TYPE_1d, "1天"),
        (TYPE_3d, "3天"),
        (TYPE_7d, "7天"),
        (TYPE_CUSTOMIZED, "自定义"),
    )


class LogType(StructuredEnum):
    """
    日志类型
    """

    STRUCTURED = EnumField("STRUCTURED", label="结构化日志")
    STANDARD_OUTPUT = EnumField("STANDARD_OUTPUT", label="标准输出日志")
    INGRESS = EnumField("INGRESS", label="接入层日志")
