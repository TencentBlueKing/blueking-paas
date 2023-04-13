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
import cattr
from django.conf import settings

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.shim import EnvClusterService
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log.constants import DEFAULT_LOG_CONFIG_PLACEHOLDER, LogCollectorType
from paasng.platform.log.models import (
    ElasticSearchConfig,
    ElasticSearchHost,
    ElasticSearchParams,
    ProcessLogQueryConfig,
)

ELK_STDOUT_COLLECTOR_CONFIG_ID = "elk-stdout"
ELK_STRUCTURED_COLLECTOR_CONFIG_ID = "elk-structured"
ELK_INGRESS_COLLECTOR_CONFIG_ID = "elk-ingress"


def setup_platform_elk_model():
    """初始化 ELK 日志方案的数据库模型 - 平台维度"""
    host = cattr.structure(settings.ELASTICSEARCH_HOSTS[0], ElasticSearchHost)
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
    ElasticSearchConfig.objects.update_or_create(
        collector_config_id=ELK_STDOUT_COLLECTOR_CONFIG_ID,
        backend_type="es",
        defaults={
            "elastic_search_host": host,
            "search_params": stdout_search_params,
        },
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
    ElasticSearchConfig.objects.update_or_create(
        collector_config_id=ELK_STRUCTURED_COLLECTOR_CONFIG_ID,
        backend_type="es",
        defaults={
            "elastic_search_host": host,
            "search_params": structured_search_params,
        },
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
            r"client_ip|bytes_sent|user_agent|http_version|environment|process_id|stream|method|path|status_code"
        ),
    )
    ElasticSearchConfig.objects.update_or_create(
        collector_config_id=ELK_INGRESS_COLLECTOR_CONFIG_ID,
        backend_type="es",
        defaults={
            "elastic_search_host": host,
            "search_params": ingress_search_params,
        },
    )


def setup_saas_elk_model(env: ModuleEnvironment):
    """初始化 ELK 日志方案的数据库模型 - SaaS 维度"""
    setup_platform_elk_model()
    stdout_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_STDOUT_COLLECTOR_CONFIG_ID)
    structured_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_STRUCTURED_COLLECTOR_CONFIG_ID)
    ingress_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_INGRESS_COLLECTOR_CONFIG_ID)

    ProcessLogQueryConfig.objects.update_or_create(
        env=env,
        process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER,
        defaults={"stdout": stdout_config, "json": structured_config, "ingress": ingress_config},
    )


def setup_default_bk_log_model(env: ModuleEnvironment):
    """初始化蓝鲸日志平台采集方案的数据库模型"""
    raise NotImplementedError

    # TODO: 完成内置采集项的初始化
    # 1. python 语言的程序使用独特的采集项, 以 json.asctime 作为时间字段
    # 2. 其他语言共用另一份采集项配置
    # 3. 所有应用的标准输出共用一份采集项配置
    # 4. 所有应用的访问日志共用一份采集项配置


def setup_env_log_model(env: ModuleEnvironment):
    cluster = EnvClusterService(env).get_cluster()
    if cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR):
        return setup_default_bk_log_model(env)
    if settings.LOG_COLLECTOR_TYPE != LogCollectorType.ELK:
        raise ValueError("ELK is not supported")
    return setup_saas_elk_model(env)
