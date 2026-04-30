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

from typing import Literal

from django.conf import settings

from paasng.accessories.log.constants import (
    BK_LOG_PLATFORM_INDEX_FILTER,
    BK_LOG_SHARED_INDEX_VISIBILITY,
    DEFAULT_LOG_CONFIG_PLACEHOLDER,
)
from paasng.accessories.log.models import CustomCollectorConfig as CustomCollectorConfigModel
from paasng.accessories.log.models import ElasticSearchConfig, ElasticSearchParams, ProcessLogQueryConfig
from paasng.accessories.log.shim.bklog_custom_collector_config import get_or_create_custom_collector_config
from paasng.accessories.log.shim.setup_bklog import (
    BKLogConfigProvider,
    _setup_ingress_log_config,
    build_normal_json_collector_config,
    build_python_json_collector_config,
    to_custom_collector_config,
)
from paasng.infras.bk_log.constatns import (
    SHARED_INDEX_NAME_JSON_TEMPLATE,
    SHARED_INDEX_NAME_STDOUT_TEMPLATE,
    ETLType,
)
from paasng.infras.bk_log.definitions import AppLogCollectorConfig, CustomCollectorConfig
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module

SHARED_INDEX_NAME_BY_LOG_TYPE: dict[Literal["json", "stdout"], str] = {
    "json": SHARED_INDEX_NAME_JSON_TEMPLATE,
    "stdout": SHARED_INDEX_NAME_STDOUT_TEMPLATE,
}
SHARED_INDEX_NAMES = set(SHARED_INDEX_NAME_BY_LOG_TYPE.values())


def should_use_shared_bk_log_index(module: Module) -> bool:
    """判断是否使用共享索引

    对应 module 的采集项:
    - 已存在，根据 name_en 是否为共享索引的名称
    - 不存在时，根据全局开关 ENABLE_SHARED_BK_LOG_INDEX 决定是否使用共享索引
    """
    builtin_names = set(
        CustomCollectorConfigModel.objects.filter(module=module, is_builtin=True).values_list("name_en", flat=True)
    )
    if builtin_names:
        return bool(builtin_names & SHARED_INDEX_NAMES)

    return settings.ENABLE_SHARED_BK_LOG_INDEX


def setup_shared_bk_log_model(env: ModuleEnvironment):
    """初始化平台共享索引日志平台采集方案的数据库模型"""
    json_config, stdout_config = setup_shared_bk_log_custom_collector(env.module)
    shared_bk_biz_id = BKLogConfigProvider(env.module).shared_bk_biz_id

    _bind_shared_query_config(env, json_config, shared_bk_biz_id, message_field="message")
    _bind_shared_query_config(env, stdout_config, shared_bk_biz_id)
    _setup_ingress_log_config(env)


def setup_shared_bk_log_custom_collector(module: Module):
    """创建/复用租户级共享的 json/stdout 采集项"""
    json_config, stdout_config = _build_app_log_configs(module)
    for app_cfg in (json_config, stdout_config):
        app_cfg.collector_config = _upsert_shared_custom_collector_config(module, app_cfg)
    return json_config, stdout_config


def _build_app_log_configs(module: Module) -> tuple[AppLogCollectorConfig, AppLogCollectorConfig]:
    """根据模块语言构造 json/stdout 采集基础配置"""
    language: AppLanguage | str
    try:
        language = AppLanguage(module.language)
    except ValueError:
        # Dockerfile 等无语言设置的应用
        language = ""

    if language == AppLanguage.PYTHON:
        json_config = build_python_json_collector_config()
    else:
        json_config = build_normal_json_collector_config()
    stdout_config = AppLogCollectorConfig(log_type="stdout", etl_type=ETLType.TEXT)
    return json_config, stdout_config


def _upsert_shared_custom_collector_config(module: Module, app_cfg: AppLogCollectorConfig) -> CustomCollectorConfig:
    """调用日志平台创建/复用共享采集项, 并把结果同步到 PaaS 侧 DB"""
    shared_bk_biz_id = BKLogConfigProvider(module).shared_bk_biz_id
    return get_or_create_custom_collector_config(
        module=module,
        collector_config=_build_shared_collector_config(module, app_cfg),
        log_paths=app_cfg.log_paths,
        log_type=app_cfg.log_type,
        biz_or_space_id=shared_bk_biz_id,
    )


def _build_shared_collector_config(module: Module, app_cfg: AppLogCollectorConfig) -> CustomCollectorConfig:
    """构造平台级共享采集项配置"""
    cfg = to_custom_collector_config(module, app_cfg, reuse_existing=False)
    shared_name = SHARED_INDEX_NAME_BY_LOG_TYPE[app_cfg.log_type]
    cfg.name_en = shared_name
    cfg.name_zh_cn = shared_name
    cfg.is_platform_index = True
    cfg.platform_index_visibility = BK_LOG_SHARED_INDEX_VISIBILITY
    cfg.platform_index_filter = BK_LOG_PLATFORM_INDEX_FILTER
    return cfg


def _bind_shared_query_config(
    env: ModuleEnvironment,
    app_cfg: AppLogCollectorConfig,
    shared_bk_biz_id: int,
    message_field: str = "log",
):
    """写入指向共享索引的 ES 查询配置"""
    assert app_cfg.collector_config

    search_config, _ = ElasticSearchConfig.objects.update_or_create(
        collector_config_id=app_cfg.collector_config.id,
        defaults={
            "backend_type": "bkLog",
            "bk_log_config": {"scenarioID": "log"},
            "search_params": _build_shared_es_search_params(
                name_en=app_cfg.collector_config.name_en,
                shared_bk_biz_id=shared_bk_biz_id,
                message_field=message_field,
            ),
            "tenant_id": env.tenant_id,
        },
    )

    config, _ = ProcessLogQueryConfig.objects.get_or_create(
        env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER, defaults={"tenant_id": env.tenant_id}
    )
    config.tenant_id = env.tenant_id
    if app_cfg.log_type == "stdout":
        config.stdout = search_config
    elif app_cfg.log_type == "json":
        config.json = search_config
    else:
        raise NotImplementedError
    config.save()


def _build_shared_es_search_params(name_en: str, shared_bk_biz_id: int, message_field: str) -> ElasticSearchParams:
    """构造共享索引的 ES 查询参数"""
    return ElasticSearchParams(
        indexPattern=f"{shared_bk_biz_id}_bklog_{name_en}_*",
        # time 是日志平台默认的时间字段
        timeField="time",
        timeFormat="timestamp[ns]",
        messageField=message_field,
        termTemplate={
            "__ext.labels.bkapp_paas_bk_tencent_com_code": "{{ app_code }}",
        },
        builtinFilters={},
        builtinExcludes={},
        filedMatcher="message|levelname|pathname|funcName|otelSpanID"
        r"|otelServiceName|otelTraceID|requestID|environment|process_id|stream|__ext_json\..*",
    )
