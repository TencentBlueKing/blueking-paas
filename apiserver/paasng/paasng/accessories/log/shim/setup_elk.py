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
from typing import Optional

import cattr
from attr import define
from django.conf import settings
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _

from paasng.accessories.log.constants import DEFAULT_LOG_CONFIG_PLACEHOLDER
from paasng.accessories.log.models import (
    ElasticSearchConfig,
    ElasticSearchHost,
    ElasticSearchParams,
    ProcessLogQueryConfig,
)
from paasng.platform.applications.models import ModuleEnvironment
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)
ELK_STDOUT_COLLECTOR_CONFIG_ID = "elk-stdout"
ELK_STRUCTURED_COLLECTOR_CONFIG_ID = "elk-structured"
ELK_INGRESS_COLLECTOR_CONFIG_ID = "elk-ingress"


@define
class ESParamsConfig:
    stdout: ElasticSearchParams
    structured: ElasticSearchParams
    ingress: ElasticSearchParams


def construct_platform_es_params() -> ESParamsConfig:
    """构造平台的 ES 查询参数，如果参数有修改需要执行 python manage.py update_es_params 来更新数据库的配置。"""
    # 标准输出日志
    # paas 的标准输出日志过滤条件
    # termTemplate = {'app_code.keyword': '{{ app_code }}'}
    # builtinFilters = {"stream.keyword": ["stderr", "stdout"]}
    stdout_search_params = ElasticSearchParams(
        indexPattern=settings.ES_K8S_LOG_INDEX_PATTERNS.replace("(?P<date>.+)", "*"),
        timeField="@timestamp",
        timeFormat="datetime",
        messageField="json.message",
        termTemplate={"app_code": "{{ app_code }}", "module_name": "{{ module_name }}"},
        # 结构化日志与标准输出日志共用 index, 通过 stream.keyword 来区分日志类型
        builtinFilters={"stream": ["stderr", "stdout"]},
        builtinExcludes={},
    )
    # 结构化日志
    # paas 的结构化日志过滤条件
    # termTemplate = {'app_code.keyword': '{{ app_code }}'}
    # builtinExcludes = {"stream.keyword": ["stderr", "stdout"]}
    structured_search_params = ElasticSearchParams(
        indexPattern=settings.ES_K8S_LOG_INDEX_PATTERNS.replace("(?P<date>.+)", "*"),
        timeField="@timestamp",
        timeFormat="datetime",
        messageField="json.message",
        termTemplate={"app_code": "{{ app_code }}", "module_name": "{{ module_name }}"},
        builtinFilters={},
        # 结构化日志与标准输出日志共用 index, 通过 stream.keyword 来区分日志类型
        builtinExcludes={"stream": ["stderr", "stdout"]},
        filedMatcher=r"json\..*|environment|process_id|stream",
    )
    # Ingress 日志
    ingress_search_params = ElasticSearchParams(
        indexPattern=settings.ES_K8S_LOG_INDEX_NGINX_PATTERNS.replace("(?P<date>.+)", "*"),
        timeField="@timestamp",
        timeFormat="datetime",
        messageField="json.message",
        # ingress 日志是从 serviceName 解析的 engine_app_name，下划线已经转换成 0us0
        # 因此查日志时需要将下划线转换成 0us0 才能搜索到
        termTemplate={"engine_app_name": "{{ engine_app_names | tojson }}"},
        builtinFilters={"stream": ["stdout"]},
        builtinExcludes={},
        filedMatcher=(
            # 字段需要与模型 IngressLogLine 保持一致
            r"method|path|status_code|response_time"
            r"|client_ip|bytes_sent|user_agent|http_version"
            r"|environment|process_id|stream"
        ),
    )
    return ESParamsConfig(
        stdout=stdout_search_params,
        structured=structured_search_params,
        ingress=ingress_search_params,
    )


def setup_platform_elk_config(es_host: Optional[ElasticSearchHost] = None):
    """
    按租户初始化/更新平台 ELK 日志方案的数据库配置，在新增租户时执行。
    """
    # 未指定 Host 则使用 settings 中的配置
    if es_host is None:
        es_host = cattr.structure(settings.ELASTICSEARCH_HOSTS[0], ElasticSearchHost)

    # 获取构造的 Elasticsearch 查询参数
    search_params = construct_platform_es_params()

    # 定义 index 和 ES 查询参数的对应关系
    collector_configs = [
        (ELK_STDOUT_COLLECTOR_CONFIG_ID, search_params.stdout),
        (ELK_STRUCTURED_COLLECTOR_CONFIG_ID, search_params.structured),
        (ELK_INGRESS_COLLECTOR_CONFIG_ID, search_params.ingress),
    ]

    for config_id, params in collector_configs:
        elastic_search_config, created = ElasticSearchConfig.objects.update_or_create(
            collector_config_id=config_id,
            backend_type="es",
            defaults={
                "elastic_search_host": es_host,
                "search_params": params,
            },
        )
        if created:
            logger.info(f"Created new Elasticsearch configuration: {config_id}")
        else:
            logger.info(f"Updated Elasticsearch configuration: {config_id}")


def setup_saas_elk_model(env: ModuleEnvironment):
    """初始化 ELK 日志方案的数据库模型 - SaaS 维度"""
    try:
        stdout_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_STDOUT_COLLECTOR_CONFIG_ID)
        structured_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_STRUCTURED_COLLECTOR_CONFIG_ID)
        ingress_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_INGRESS_COLLECTOR_CONFIG_ID)
    except ElasticSearchConfig.DoesNotExist:
        # 未配置时，需要记录异常日志方便排查
        logger.exception("The elk logs are not configured with the corresponding Elasticsearch.")
        raise error_codes.ES_NOT_CONFIGURED.f(_("日志存储的 Elasticsearch 配置尚未完成，请稍后再试。"))

    if ProcessLogQueryConfig.objects.filter(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER).exists():
        return

    try:
        ProcessLogQueryConfig.objects.update_or_create(
            env=env,
            process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER,
            defaults={"stdout": stdout_config, "json": structured_config, "ingress": ingress_config},
        )
    except IntegrityError:
        logger.info("unique constraint conflict in the database when creating ProcessLogQueryConfig, can be ignored.")
