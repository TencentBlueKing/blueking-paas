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

"""SaaS 共享索引/采集项链路

设计要点:
  - 采集项: 同一租户下所有 SaaS 共用一份 json / stdout 采集项 (name_en 后缀 tenant_id)
  - 索引: 同租户共用同一份 ES 索引, 跨租户隔离, 跨 App 隔离靠查询侧 termTemplate 注入
    `__ext.labels.bkapp_paas_bk_tencent_com_code` (源于 Pod label `bkapp.paas.bk.tencent.com/code`)
"""

import logging
from typing import Literal

from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.log.constants import (
    BK_LOG_PLATFORM_INDEX_FILTER,
    BK_LOG_SHARED_INDEX_VISIBILITY,
    DEFAULT_LOG_CONFIG_PLACEHOLDER,
)
from paasng.accessories.log.models import CustomCollectorConfig as CustomCollectorConfigModel
from paasng.accessories.log.models import (
    ElasticSearchConfig,
    ElasticSearchParams,
    ProcessLogQueryConfig,
)
from paasng.accessories.log.shim.setup_bklog import (
    BKLogConfigProvider,
    build_normal_json_collector_config,
    build_python_json_collector_config,
    to_custom_collector_config,
)
from paasng.accessories.log.shim.setup_elk import ELK_INGRESS_COLLECTOR_CONFIG_ID_TMPL, setup_platform_elk_config
from paasng.infras.bk_log.client import make_bk_log_management_client
from paasng.infras.bk_log.constatns import (
    PLATFORM_INDEX_NAME_JSON_TEMPLATE,
    PLATFORM_INDEX_NAME_STDOUT_TEMPLATE,
    ETLType,
)
from paasng.infras.bk_log.definitions import (
    AppLogCollectorConfig,
    CustomCollectorConfig,
)
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.platform.modules.models import Module
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


def setup_shared_bk_log_custom_collector(module: Module):
    """共享版 setup_bk_log_custom_collector: 创建/复用租户级共享的 json / stdout 采集项

    创建走幂等路径 (client 根据 is_platform_index 自动注入 ignore_exists)
    """
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

    for app_cfg in (json_config, stdout_config):
        app_cfg.collector_config = _upsert_shared_custom_collector_config(module, app_cfg)
    return json_config, stdout_config


def setup_shared_bk_log_model(env: ModuleEnvironment):
    """共享版 setup_default_bk_log_model: 仅 json / stdout 走共享, ingress 仍用 ELK

    与独立路径的差异集中在 ElasticSearchParams (索引前缀 + termTemplate), 见 _build_es_search_params
    """
    json_config, stdout_config = setup_shared_bk_log_custom_collector(env.module)

    shared_bk_biz_id = BKLogConfigProvider(env.module).shared_bk_biz_id
    _update_or_create_es_search_config(env, json_config, shared_bk_biz_id, message_field="message")
    _update_or_create_es_search_config(env, stdout_config, shared_bk_biz_id)

    cluster_uuid = EnvClusterService(env).get_cluster().uuid
    setup_platform_elk_config(cluster_uuid, env.tenant_id)
    try:
        ingress_config = ElasticSearchConfig.objects.get(
            collector_config_id=ELK_INGRESS_COLLECTOR_CONFIG_ID_TMPL.format(cluster_uuid=cluster_uuid)
        )
    except ElasticSearchConfig.DoesNotExist:
        # 未配置时，需要记录异常日志方便排查
        logger.exception("The elk ingress log is not configured with the corresponding Elasticsearch.")
        raise error_codes.ES_NOT_CONFIGURED.f(_("日志存储的 Elasticsearch 配置尚未完成，请稍后再试。"))

    config = ProcessLogQueryConfig.objects.get(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER)
    config.ingress = ingress_config
    config.save()


def _upsert_shared_custom_collector_config(module: Module, app_cfg: AppLogCollectorConfig) -> CustomCollectorConfig:
    """调用日志平台创建/更新共享采集项, 并把结果同步到 PaaS 侧 DB"""
    cfg = _build_shared_custom_collector_config(module, app_cfg)
    tenant_id = get_tenant_id_for_app(module.application.code)
    client = make_bk_log_management_client(tenant_id)
    shared_bk_biz_id = BKLogConfigProvider(module).shared_bk_biz_id

    with atomic():
        if cfg.id:
            client.update_custom_collector_config(cfg)
        else:
            cfg = client.create_custom_collector_config(biz_or_space_id=shared_bk_biz_id, config=cfg)

        CustomCollectorConfigModel.objects.update_or_create(
            module=module,
            name_en=cfg.name_en,
            defaults={
                "collector_config_id": cfg.id,
                "index_set_id": cfg.index_set_id,
                "bk_data_id": cfg.bk_data_id,
                "log_paths": app_cfg.log_paths,
                "log_type": app_cfg.log_type,
                "is_builtin": True,
                "is_enabled": True,
                "tenant_id": module.tenant_id,
            },
        )
    return cfg


def _build_shared_custom_collector_config(module: Module, app_cfg: AppLogCollectorConfig) -> CustomCollectorConfig:
    """构造共享采集项的 CustomCollectorConfig: 复用独立路径的 etl/storage 配置, 仅覆盖 name 和平台级字段"""
    cfg = to_custom_collector_config(module, app_cfg)
    shared_name = _resolve_shared_name_en(module.tenant_id, app_cfg.log_type)
    cfg.name_en = shared_name
    cfg.name_zh_cn = shared_name
    cfg.is_platform_index = True
    cfg.platform_index_visibility = BK_LOG_SHARED_INDEX_VISIBILITY
    cfg.platform_index_filter = BK_LOG_PLATFORM_INDEX_FILTER
    return cfg


def _update_or_create_es_search_config(
    env: ModuleEnvironment,
    app_cfg: AppLogCollectorConfig,
    shared_bk_biz_id: int,
    message_field: str = "log",
):
    """共享版 update_or_create_es_search_config: 写入指向共享索引的 ES 查询配置

    :param int shared_bk_biz_id: 共享采集项所属的 CMDB 业务 ID, 用于构造 ES 索引前缀
    :param str message_field: 日志查询字段, 默认值 log 是日志平台原始日志字段
    """
    assert app_cfg.collector_config

    search_params = _build_es_search_params(
        name_en=app_cfg.collector_config.name_en,
        shared_bk_biz_id=shared_bk_biz_id,
        message_field=message_field,
    )
    defaults = {
        "backend_type": "bkLog",
        "bk_log_config": {"scenarioID": "log"},
        "search_params": search_params,
        "tenant_id": env.tenant_id,
    }

    search_config, _ = ElasticSearchConfig.objects.update_or_create(
        collector_config_id=app_cfg.collector_config.id,
        defaults=defaults,
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


def _build_es_search_params(name_en: str, shared_bk_biz_id: int, message_field: str) -> ElasticSearchParams:
    """构造共享索引的 ES 查询参数

    共享索引模式下采集项挂在 shared_bk_biz_id 业务下, 索引为 `${shared_bk_biz_id}_bklog_{name_en}_*`,
    termTemplate 注入 `__ext.labels.bkapp_paas_bk_tencent_com_code` 来区分不同的 application
    """
    index_prefix = f"{shared_bk_biz_id}_bklog_"
    return ElasticSearchParams(
        indexPattern=f"{index_prefix}{name_en}_*",
        # time 是日志平台默认的时间字段
        timeField="time",
        timeFormat="timestamp[ns]",
        messageField=message_field,
        termTemplate={"__ext.labels.bkapp_paas_bk_tencent_com_code": "{{ app_code }}"},
        builtinFilters={},
        builtinExcludes={},
        filedMatcher="message|levelname|pathname|funcName|otelSpanID"
        r"|otelServiceName|otelTraceID|requestID|environment|process_id|stream|__ext_json\..*",
    )


def _resolve_shared_name_en(tenant_id: str, log_type: Literal["json", "stdout"]) -> str:
    """按租户渲染共享采集项的 name_en, 不同租户落到不同 ES 索引"""
    if log_type == "json":
        return PLATFORM_INDEX_NAME_JSON_TEMPLATE.format(tenant_id=tenant_id)
    if log_type == "stdout":
        return PLATFORM_INDEX_NAME_STDOUT_TEMPLATE.format(tenant_id=tenant_id)
    raise ValueError(f"unsupported log_type for shared collector: {log_type}")
