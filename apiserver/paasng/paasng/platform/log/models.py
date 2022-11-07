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
import logging
from operator import itemgetter
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from django.core.exceptions import ObjectDoesNotExist
from elasticsearch import Elasticsearch
from elasticsearch_dsl import AttrDict, Index
from elasticsearch_dsl.response import Response
from pydantic import BaseModel, Field, parse_obj_as, root_validator, validator

from paasng.engine.models import EngineApp
from paasng.platform.log.constants import LOG_QUERY_FIELDS, ESField
from paasng.platform.log.exceptions import LogLineInfoBrokenError, UnknownEngineAppNameError
from paasng.utils.datetime import trans_ts_to_local

logger = logging.getLogger(__name__)


class ResponseWrapper(BaseModel):
    # TODO: 目前整个 PaaS 项目大多数接口都没有嵌套类似的 Wrapper, 因此计划是下个迭代里 **直接去掉**
    code: int
    data: Union[List[BaseModel], BaseModel, None]


class FieldFilter(BaseModel):
    name: str = Field(..., description="查询字段的title")
    chinese_name: Optional[str] = Field(..., description="展示用名称")
    key: str = Field(..., description="query_term: get参数中的key")
    options: List[Tuple[str, str]] = Field(..., description="该field的可选项")


class LogLine(BaseModel):
    region: str
    app_code: str
    environment: str
    process_id: Optional[str]
    stream: str
    message: str
    # key: json.*
    # e.g. json.funcName
    detail: Dict[str, Any]
    ts: str

    @staticmethod
    def _get_message(log) -> str:
        # 替换高亮文案
        if hasattr(log.meta, "highlight"):
            for attrs in log.meta.highlight:
                highlighted = "".join(log.meta.highlight[attrs])
                attrs = attrs.split(".")
                # 不带 .
                if len(attrs) <= 1:
                    log[attrs[0]] = highlighted
                    continue
                # 带 . 要按层级进去赋值
                container = log
                for attr in attrs:
                    if isinstance(container, AttrDict) and isinstance(container[attr], AttrDict):
                        container = container[attr]
                    else:
                        container[attr] = highlighted
                        break

        try:
            message = log["json"]["message"]
        except KeyError:
            logger.warning("log <%s> is not json format(filebeat did not fullfill json field)", log)
            message = "<日志解析异常，请以 JSON 格式输出>"

        return message

    @classmethod
    def _get_detail(cls, log, message: str):
        try:
            fields = log.json.to_dict()
        except AttributeError:
            fields = {"message": message}

        return dict(
            sorted(
                cls.parse_structured_properties(parent="json", structured_fields=fields).items(),
                key=itemgetter(0),
            )
        )

    @classmethod
    def check_key_field_exist(cls, log: dict, key_fields: List[str]):
        for k in key_fields:
            if k not in log:
                raise LogLineInfoBrokenError(k)

    @classmethod
    def get_app_identifiers(cls, log) -> dict:
        cls.check_key_field_exist(log, ["app_code", "environment"])

        return {
            "app_code": log["app_code"],
            "environment": log["environment"],
        }

    @classmethod
    def parse_from_es_log(cls, log) -> 'LogLine':
        message = cls._get_message(log)
        detail = cls._get_detail(log, message)

        if "process_id" not in log and "process_type" not in log:
            # process_type 作为兼容字段，并不需要显式抛出
            raise LogLineInfoBrokenError("process_id")

        cls.check_key_field_exist(log, ["region", "stream", "@timestamp"])
        obj = {
            "region": log["region"],
            "process_id": log["process_id"] if "process_id" in log else log["process_type"],
            "stream": log["stream"],
            "message": message,
            "detail": detail,
            "ts": trans_ts_to_local(log["@timestamp"]),
        }
        obj.update(cls.get_app_identifiers(log))
        return cls.parse_obj(obj)

    @classmethod
    def parse_structured_properties(cls, parent, structured_fields):
        """将结构化的属性铺平展开, 方便前端取值"""
        ret = dict()
        for sub_field, value in structured_fields.items():
            key = f"{parent}.{sub_field}"
            if isinstance(value, Mapping):
                sub = cls.parse_structured_properties(key, value)
                ret.update(sub)
                continue
            ret[key] = value
        return ret


class IngressLogLine(LogLine):
    """Ingress 日志行"""

    AVAILABLE_FIELDS: ClassVar[List] = [
        "method",
        "path",
        "status_code",
        "response_time",
        "client_ip",
        "bytes_sent",
        "user_agent",
        "http_version",
    ]

    @classmethod
    def _get_detail(cls, log, message: str):
        return {x: log[x] for x in cls.AVAILABLE_FIELDS}

    @classmethod
    def get_app_identifiers(cls, log) -> dict:
        cls.check_key_field_exist(log, ["engine_app_name"])

        try:
            # ingress 日志是从 serviceName 解析的 engine_app_name，默认已经被 engine 将下划线转换了
            engine_app = EngineApp.objects.get(name=log["engine_app_name"].replace("0us0", "_"))
            return {
                "app_code": engine_app.env.module.application.code,
                "environment": engine_app.env.environment,
            }
        except ObjectDoesNotExist:
            logger.exception("engine app <%s> does not exist, please check", log["engine_app_name"])
            # 当无法从 engine_app_name 中解析出 app_code & env 抛出异常
            raise UnknownEngineAppNameError(f"Unknown engine_app_name: {log['engine_app_name']}")


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int


class LogPage(BaseModel):
    page: Pagination
    logs: List[LogLine]

    line_class: ClassVar[Type[LogLine]] = LogLine

    @validator("logs", pre=True)
    @classmethod
    def cast_logs(cls, value) -> List[LogLine]:
        if isinstance(value, Response):
            log_lines = []
            for es_log in value:
                try:
                    log_lines.append(cls.line_class.parse_from_es_log(es_log))
                except LogLineInfoBrokenError as e:
                    logger.warning("log line<%s>: %s", es_log, e)
                    continue

            return log_lines
        else:
            return parse_obj_as(List[LogLine], value)

    @staticmethod
    def get_field_parent() -> str:
        return "json"

    @staticmethod
    def get_es_dict(mapping: dict) -> dict:
        return mapping["mappings"]["properties"]["json"]

    @staticmethod
    def parse_structured_properties(es_dict, parent: Optional[str] = "") -> Dict[str, ESField]:
        fields = {}
        for field, detail in es_dict["properties"].items():
            if parent:
                key = f"{parent}.{field}"
            else:
                key = field

            if "properties" in detail:
                # NOTE: 先不允许过滤多层结构
                # fields.update(self.parse_structured_properties(key, es_dict=detail))
                continue

            fields[key] = ESField.parse_obj({"query_term": key, "title": key, "chinese_name": key})
        return fields

    @classmethod
    def filter_fields(cls, client: Elasticsearch, es_index: Index):
        """查询 _mapping, 获取日志 `json.*` 下的所有 `properties`"""
        fields: Dict[str, ESField] = {}
        dirty_field = set()
        # 遍历所有 indexes, 获取 json.* 里记录的字段名
        for mapping in es_index.get_mapping().values():
            for field_name, es_field in cls.parse_structured_properties(
                cls.get_es_dict(mapping), cls.get_field_parent()
            ).items():
                if field_name in fields and fields[field_name] != es_field:
                    logger.warning("字段 %s 在不同 index 中的类型不一致", field_name)
                    dirty_field.add(field_name)
                    continue
                fields[field_name] = es_field

        for field in dirty_field:
            del fields[field]
        return fields


class IngressLogPage(LogPage):
    line_class = IngressLogLine

    @staticmethod
    def get_field_parent() -> str:
        return ""

    @staticmethod
    def get_es_dict(mapping: dict) -> dict:
        return mapping["mappings"]


class StandardOutputLogLine(BaseModel):
    environment: str = Field(..., description="部署环境")
    process_id: str = Field(..., description="应用进程")
    pod_name: str = Field(..., description="实例名")
    message: str
    timestamp: str

    @classmethod
    def parse_from_es_log(cls, log) -> 'StandardOutputLogLine':
        if hasattr(log.meta, "highlight") and "json.message" in log.meta.highlight:
            message = "".join(log.meta.highlight["json.message"])
        else:
            message = log.json.message

        return cls(
            environment=log.environment,
            process_id=log.process_id,
            pod_name=log.pod_name,
            message=message,
            timestamp=trans_ts_to_local(log["@timestamp"]),
        )


class StandardOutputLogScroll(BaseModel):
    scroll_id: str
    logs: List[StandardOutputLogLine]
    total: int = 0

    @validator("logs", pre=True)
    @classmethod
    def cast_logs(cls, value):
        if isinstance(value, Response):
            return [StandardOutputLogLine.parse_from_es_log(es_log) for es_log in value]
        else:
            return parse_obj_as(List[StandardOutputLogLine], value)


class LogCountTimeHistogram(BaseModel):
    """日志数量 x 时间 直方图"""

    series: List[int] = Field(..., description="按时间排序的值")
    timeline: List[str] = Field(..., description="Series 中对应位置记录的时间点")


# DSL 建模
class DSLQueryItem(BaseModel):
    """简化的 dsl-query 结构
    目前只支持: query_string/terms 两种查询方式
    query_string: 使用 ES 的 query_string 搜索
    terms: 精准匹配(根据 field 过滤 的场景)
    """

    query_string: str = Field(None, description="使用 `query_string` 语法进行搜索")
    terms: Dict[str, List[str]] = Field({}, description="多值精准匹配")
    exclude: Dict[str, List[str]] = Field({}, description="terms取反, 非标准 DSL")

    @root_validator(pre=True)
    @classmethod
    def transfer_query_term_to_es_term(cls, values: Dict):
        # 将 query_term 转换成 es_term
        terms = values.get("terms", {})
        exclude = values.get("exclude", {})

        for container in [terms, exclude]:
            for regular_field in LOG_QUERY_FIELDS:
                if regular_field.query_term in container:
                    v = container.pop(regular_field.query_term)
                    container[regular_field.query_term] = v
        return values


class SimpleDomainSpecialLanguage(BaseModel):
    """简化的 dsl 结构"""

    query: DSLQueryItem
    sort: Optional[Dict] = Field({}, description='排序，e.g. {"response_time": "desc", "other": "asc"}')

    def add_terms_conditions(self, **kwargs):
        kwargs = self.query.parse_obj(dict(terms=kwargs)).dict()
        self.query.terms.update(kwargs["terms"])
        return self

    def add_exclude_conditions(self, **kwargs):
        kwargs = self.query.parse_obj(dict(exclude=kwargs)).dict()
        self.query.exclude.update(kwargs["exclude"])
        return self

    def remove_terms_condition(self, key):
        return self.remove_conditions_core("terms", key)

    def remove_exclude_conditions(self, key):
        return self.remove_conditions_core("exclude", key)

    def remove_conditions_core(self, cond_type: str, key):
        if cond_type not in ["terms", "exclude"]:
            raise NotImplementedError

        if key in getattr(self.query, cond_type):
            getattr(self.query, cond_type).pop(key, None)

        return self

    def remove_regular_conditions(self, mappings: dict):
        for regular_field in LOG_QUERY_FIELDS:
            self.remove_terms_condition(regular_field.get_es_term(mappings))
            self.remove_terms_condition(regular_field.query_term)
        return self
