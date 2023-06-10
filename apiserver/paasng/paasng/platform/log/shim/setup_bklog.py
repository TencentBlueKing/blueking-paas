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
import datetime
import logging
from typing import Optional, Tuple

import cattr
from django.conf import settings
from django.db.transaction import atomic
from django.utils.timezone import get_default_timezone

from paasng.accessories.log_search.client import make_bk_log_client
from paasng.accessories.log_search.constatns import ETLType, FieldType
from paasng.accessories.log_search.definitions import (
    AppLogCollectorConfig,
    CustomCollectorConfig,
    ETLConfig,
    ETLField,
    StorageConfig,
)
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log.constants import DEFAULT_LOG_CONFIG_PLACEHOLDER
from paasng.platform.log.models import CustomCollectorConfig as CustomCollectorConfigModel
from paasng.platform.log.models import (
    ElasticSearchConfig,
    ElasticSearchHost,
    ElasticSearchParams,
    ProcessLogQueryConfig,
)
from paasng.platform.modules.models import Module

from .setup_elk import ELK_INGRESS_COLLECTOR_CONFIG_ID, setup_platform_elk_model

logger = logging.getLogger(__name__)


class BKLogConfigProvider:
    @property
    def timezone(self) -> int:
        if timezone := settings.BKLOG_CONFIG.get("TIME_ZONE"):
            return timezone
        tz = get_default_timezone()
        return tz.utcoffset(datetime.datetime.now()).total_seconds() // 60 // 60

    @property
    def storage_cluster_id(self) -> int:
        return settings.BKLOG_CONFIG["STORAGE_CLUSTER_ID"]

    @property
    def bk_biz_id(self) -> int:
        return settings.BKLOG_CONFIG["BK_BIZ_ID"]


def build_python_json_collector_config():
    return AppLogCollectorConfig(
        log_paths=[
            settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
            settings.VOLUME_MOUNT_APP_LOGGING_DIR,
        ],
        log_type="json",
        etl_type=ETLType.JSON,
        time_field="asctime",
        # time_format for python logging library
        # ref: https://docs.python.org/3/library/logging.html#logging.Formatter.formatTime
        time_format="yyyy-MM-dd HH:mm:ss,SSS",
    )


def build_normal_json_collector_config():
    return AppLogCollectorConfig(
        log_paths=[
            settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
            settings.VOLUME_MOUNT_APP_LOGGING_DIR,
        ],
        log_type="json",
        etl_type=ETLType.JSON,
    )


def build_custom_collector_config_name(module: Module, type: str) -> str:
    """构造应用唯一的自定义采集项英文名称，重要，5-50 个字符，仅包含字母数字下划线"""
    # app_code max_length 20 字符
    app_code = module.application.code
    # module_name max_length 20 字符
    module_name = module.name
    return f"bkapp__{app_code}__{module_name}__{type}".replace("-", "_")


def to_custom_collector_config(
    module: Module, collector_config: AppLogCollectorConfig
) -> Tuple[CustomCollectorConfig, Optional[CustomCollectorConfigModel]]:
    """Transform AppLogCollectorConfig to CustomCollectorConfig"""

    if collector_config.etl_type == ETLType.TEXT:
        etl_config = ETLConfig(
            type=collector_config.etl_type,
        )
    elif collector_config.etl_type == ETLType.JSON:
        assert collector_config.time_field

        def make_string_field(index: int, field_name: str) -> ETLField:
            return ETLField(
                field_index=index,
                field_name=field_name,
                field_type=FieldType.STRING,
                is_time=False,
                is_dimension=False,
                is_analyzed=True,
                option={},
            )

        etl_config = ETLConfig(
            type=collector_config.etl_type,
            fields=[
                ETLField(
                    field_index=1,
                    field_name=collector_config.time_field,
                    field_type=FieldType.STRING,
                    is_time=True,
                    is_dimension=False,
                    option={
                        "time_zone": BKLogConfigProvider().timezone,
                        "time_format": collector_config.time_format,
                    },
                ),
                # NOTE: bklog 目前不支持将日志内容本身存储为 json, 所以只能逐个字段定义
                # TODO: 日志平台支持存储将日志内容本身存储为 json 后, 修改这里的字段定义
                make_string_field(2, "message"),
                make_string_field(3, "levelname"),
                make_string_field(4, "pathname"),
                make_string_field(5, "funcName"),
                make_string_field(6, "otelSpanID"),
                make_string_field(7, "otelServiceName"),
                make_string_field(8, "otelTraceID"),
            ],
        )
    else:
        raise NotImplementedError

    name = build_custom_collector_config_name(module, type=collector_config.log_type)
    cfg = CustomCollectorConfig(
        name_en=name,
        name_zh_cn=name,
        etl_config=etl_config,
        storage_config=StorageConfig(
            storage_cluster_id=BKLogConfigProvider().storage_cluster_id,
        ),
    )
    # fill persistence fields from db
    try:
        db_obj = CustomCollectorConfigModel.objects.get(module=module, name_en=cfg.name_en)
    except CustomCollectorConfigModel.DoesNotExist:
        logger.debug("CustomCollectorConfig dones not exits, skip fill persistence fields")
        return cfg, None

    cfg.id = db_obj.collector_config_id
    cfg.index_set_id = db_obj.index_set_id
    cfg.bk_data_id = db_obj.bk_data_id
    return cfg, db_obj


def update_or_create_custom_collector_config(
    env: ModuleEnvironment, collector_config: AppLogCollectorConfig, skip_update: bool = False
):
    """调用日志平台的接口, 创建或更新自定义采集项"""
    module: Module = env.module
    custom_collector_config, db_obj = to_custom_collector_config(module, collector_config)
    client = make_bk_log_client()
    with atomic():
        if db_obj is not None:
            if not skip_update:
                client.update_custom_collector_config(custom_collector_config)
                db_obj.log_paths = collector_config.log_paths
                db_obj.log_type = collector_config.log_type
                db_obj.save(update_fields=["log_paths", "log_type", "updated"])
        else:
            # create_custom_collector_config will fill `id`, `index_set_id`, `bk_data_id` fields
            custom_collector_config = client.create_custom_collector_config(
                bk_biz_id=BKLogConfigProvider().bk_biz_id, config=custom_collector_config
            )
            CustomCollectorConfigModel.objects.update_or_create(
                module=module,
                name_en=custom_collector_config.name_en,
                defaults={
                    "collector_config_id": custom_collector_config.id,
                    "index_set_id": custom_collector_config.index_set_id,
                    "bk_data_id": custom_collector_config.bk_data_id,
                    "log_paths": collector_config.log_paths,
                    "log_type": collector_config.log_type,
                },
            )
    collector_config.collector_config = custom_collector_config


def update_or_create_es_search_config(env: ModuleEnvironment, collector_config: AppLogCollectorConfig):
    """初始化日志查询相关的数据库模型"""
    assert collector_config.collector_config
    # 与 ELK 方案共用 ES 存储, 需要预先在日志平台配置
    host = cattr.structure(settings.ELASTICSEARCH_HOSTS[0], ElasticSearchHost)
    search_params = ElasticSearchParams(
        # 日志平台的索引规则: ${biz_id}_bklog_${name_en}_*
        indexPattern=f"{BKLogConfigProvider().bk_biz_id}_bklog_{collector_config.collector_config.name_en}_*",
        # time 是日志平台默认的时间字段
        timeField="time",
        timeFormat="timestamp[ns]",
        # log 是日志平台的原始日志字段
        messageField="log",
        # 已根据 index 区分日志, 无需额外的搜索条件
        termTemplate={},
        builtinFilters={},
        builtinExcludes={},
    )
    search_config, _ = ElasticSearchConfig.objects.update_or_create(
        collector_config_id=collector_config.collector_config.id,
        backend_type="es",
        defaults={
            "elastic_search_host": host,
            "search_params": search_params,
        },
    )

    config, _ = ProcessLogQueryConfig.objects.get_or_create(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER)
    if collector_config.log_type == "stdout":
        config.stdout = search_config
    elif collector_config.log_type == "json":
        config.json = search_config
    else:
        raise NotImplementedError
    config.save()


def setup_default_bk_log_model(env: ModuleEnvironment):
    """初始化蓝鲸日志平台采集方案的数据库模型"""
    module = env.module
    if module.language == AppLanguage.PYTHON:
        json_config = build_python_json_collector_config()
    else:
        json_config = build_normal_json_collector_config()
    stdout_config = AppLogCollectorConfig(log_type="stdout", etl_type=ETLType.TEXT)

    # 创建 json/stdout 的自定义采集项
    update_or_create_custom_collector_config(env, json_config, skip_update=True)
    update_or_create_custom_collector_config(env, stdout_config, skip_update=True)
    # 绑定日志查询的配置
    update_or_create_es_search_config(env, json_config)
    update_or_create_es_search_config(env, stdout_config)

    # Ingress 仍然使用 elk 的采集方案
    setup_platform_elk_model()
    ingress_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_INGRESS_COLLECTOR_CONFIG_ID)
    config = ProcessLogQueryConfig.objects.get(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER)
    config.ingress = ingress_config
    config.save()
