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
from typing import Union

import cattr
from django.conf import settings
from django.utils.timezone import get_default_timezone

from paasng.accessories.log.constants import DEFAULT_LOG_CONFIG_PLACEHOLDER
from paasng.accessories.log.models import CustomCollectorConfig as CustomCollectorConfigModel
from paasng.accessories.log.models import (
    ElasticSearchConfig,
    ElasticSearchHost,
    ElasticSearchParams,
    ProcessLogQueryConfig,
)
from paasng.accessories.log.shim.bklog_custom_collector_config import get_or_create_custom_collector_config
from paasng.accessories.log.shim.setup_elk import ELK_INGRESS_COLLECTOR_CONFIG_ID, setup_platform_elk_model
from paasng.infras.bk_log.constatns import ETLType, FieldType
from paasng.infras.bk_log.definitions import (
    AppLogCollectorConfig,
    CustomCollectorConfig,
    ETLConfig,
    ETLField,
    ETLParams,
    StorageConfig,
)
from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class BKLogConfigProvider:
    def __init__(self, module: Module):
        self.module = module

    @property
    def timezone(self) -> int:
        if timezone := settings.BKLOG_CONFIG.get("TIME_ZONE"):
            return timezone
        tz = get_default_timezone()
        return int(tz.utcoffset(datetime.datetime.now()).total_seconds() // 60 // 60)

    @property
    def storage_cluster_id(self) -> int:
        return settings.BKLOG_CONFIG["STORAGE_CLUSTER_ID"]


def _add_wildcard_suffix(path: str) -> str:
    """add '/*' suffix to path

    >>> _add_wildcard_suffix("/app/v3logs")
    "/app/v3logs/*"

    >>> _add_wildcard_suffix("/app/v3logs/")
    "/app/v3logs/*"
    """
    if not path.endswith("/") and not path.endswith("/*"):
        path += "/"
    if not path.endswith("*"):
        path += "*"
    return path


def build_python_json_collector_config():
    """构建 python 类型的日志采集项 - 时间字段的清洗格式为 logging 标准库的时间格式"""
    return AppLogCollectorConfig(
        # 平台配置的采集项是采集目录的所有日志文件, 需要添加通配符 '*' 才能在日志平台使用
        log_paths=[
            _add_wildcard_suffix(settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR),
            _add_wildcard_suffix(settings.VOLUME_MOUNT_APP_LOGGING_DIR),
        ],
        log_type="json",
        etl_type=ETLType.JSON,
        time_field="asctime",
        # time_format for python logging library
        # ref: https://docs.python.org/3/library/logging.html#logging.Formatter.formatTime
        time_format="yyyy-MM-dd HH:mm:ss,SSS",
    )


def build_normal_json_collector_config():
    """构建 json 类型的日志采集项 - 未指定时间字段, 以采集时间作为日志时间"""
    return AppLogCollectorConfig(
        log_paths=[
            _add_wildcard_suffix(settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR),
            _add_wildcard_suffix(settings.VOLUME_MOUNT_APP_LOGGING_DIR),
        ],
        log_type="json",
        etl_type=ETLType.JSON,
    )


def update_or_create_es_search_config(
    env: ModuleEnvironment, collector_config: AppLogCollectorConfig, message_field: str = "log"
):
    """初始化日志查询相关的数据库模型

    :param str message_field: 日志查询字段, 默认值 log 是日志平台的原始日志字段
    """
    module = env.module
    assert collector_config.collector_config
    # 与 ELK 方案共用 ES 存储, 需要预先在日志平台配置
    host = cattr.structure(settings.ELASTICSEARCH_HOSTS[0], ElasticSearchHost)

    monitor_space, _ = get_or_create_bk_monitor_space(module.application)
    # 日志平台的索引规则:
    # 对于 biz_id 是 业务ID 的采集项: ${biz_id}_bklog_${name_en}_*
    # 对于 biz_id 是 空间ID 的采集项: space_${id}_bklog_${name_en}_*
    index_prefix = f"space_{monitor_space.id}_bklog_"
    search_params = ElasticSearchParams(
        indexPattern=f"{index_prefix}{collector_config.collector_config.name_en}_*",
        # time 是日志平台默认的时间字段
        timeField="time",
        timeFormat="timestamp[ns]",
        messageField=message_field,
        # 已根据 index 区分不同应用-模块的日志, 无需额外的搜索条件
        termTemplate={},
        builtinFilters={},
        builtinExcludes={},
        filedMatcher="message|levelname|pathname|funcName|otelSpanID"
        r"|otelServiceName|otelTraceID|environment|process_id|stream|__ext_json\..*",
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


def setup_bk_log_custom_collector(module: Module):
    """初始化内置的日志采集项(JSON日志采集和标准输出日志采集)"""
    language: Union[AppLanguage, str]
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

    # 创建 json/stdout 的自定义采集项
    # Note: 由于用户可在日志平台编辑自定义采集项, 目前策略以日志平台为准, 因此 json/stdout 的自定义采集项 只创建不更新
    json_config.collector_config = get_or_create_custom_collector_config(
        module,
        to_custom_collector_config(module, json_config),
        log_paths=json_config.log_paths,
        log_type=json_config.log_type,
    )
    stdout_config.collector_config = get_or_create_custom_collector_config(
        module,
        to_custom_collector_config(module, stdout_config),
        log_paths=stdout_config.log_paths,
        log_type=stdout_config.log_type,
    )
    return json_config, stdout_config


def setup_default_bk_log_model(env: ModuleEnvironment):
    """初始化蓝鲸日志平台采集方案的数据库模型

    - 创建内置的日志采集项(JSON日志采集和标准输出日志采集)
    - 初始化日志查询配置
        - 结构化日志查询 JSON日志采集项
        - 标准输出日志查询 标准输出日志采集项
        - 访问日志查询 ELK
    """
    json_config, stdout_config = setup_bk_log_custom_collector(env.module)

    # 绑定日志查询的配置
    # TODO: 日志平台支持存储将日志内容本身存储为 json 后, 修改成类似于 json.message 的字段
    update_or_create_es_search_config(env, json_config, message_field="message")
    update_or_create_es_search_config(env, stdout_config)

    # Ingress 仍然使用 elk 的采集方案
    setup_platform_elk_model()
    ingress_config = ElasticSearchConfig.objects.get(collector_config_id=ELK_INGRESS_COLLECTOR_CONFIG_ID)
    config = ProcessLogQueryConfig.objects.get(env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER)
    config.ingress = ingress_config
    config.save()


def build_custom_collector_config_name(module: Module, type: str) -> str:
    """构造应用唯一的自定义采集项英文名称，重要，5-50 个字符，仅包含字母数字下划线"""
    # app_code max_length 20 字符
    app_code = module.application.code
    # module_name max_length 20 字符
    module_name = module.name
    return f"bkapp__{app_code}__{module_name}__{type}".replace("-", "_")


def to_custom_collector_config(module: Module, collector_config: AppLogCollectorConfig) -> CustomCollectorConfig:
    """将 AppLogCollectorConfig 转换成 CustomCollectorConfig

    仅用于系统内置的自定义采集项
    """

    if collector_config.etl_type == ETLType.TEXT:
        etl_config = ETLConfig(
            type=collector_config.etl_type,
        )
    elif collector_config.etl_type == ETLType.JSON:

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

        time_filed = None
        if collector_config.time_field:
            time_filed = ETLField(
                field_index=1,
                field_name=collector_config.time_field,
                field_type=FieldType.STRING,
                is_time=True,
                is_dimension=False,
                option={
                    "time_zone": BKLogConfigProvider(module).timezone,
                    "time_format": collector_config.time_format,
                },
            )

        fields = [
            *([time_filed] if time_filed is not None else []),
            make_string_field(2, "message"),
            make_string_field(3, "levelname"),
            make_string_field(4, "pathname"),
            make_string_field(5, "funcName"),
            make_string_field(6, "otelSpanID"),
            make_string_field(7, "otelServiceName"),
            make_string_field(8, "otelTraceID"),
        ]

        etl_config = ETLConfig(
            type=collector_config.etl_type,
            params=ETLParams(retain_extra_json=True),
            fields=fields,
        )
    else:
        raise NotImplementedError

    name = build_custom_collector_config_name(module, type=collector_config.log_type)
    cfg = CustomCollectorConfig(
        name_en=name,
        name_zh_cn=name,
        etl_config=etl_config,
        storage_config=StorageConfig(
            storage_cluster_id=BKLogConfigProvider(module).storage_cluster_id,
        ),
    )
    # fill persistence fields from db
    try:
        db_obj = CustomCollectorConfigModel.objects.get(module=module, name_en=cfg.name_en)
    except CustomCollectorConfigModel.DoesNotExist:
        logger.debug("CustomCollectorConfig dones not exits, skip fill persistence fields")
        return cfg

    cfg.id = db_obj.collector_config_id
    cfg.index_set_id = db_obj.index_set_id
    cfg.bk_data_id = db_obj.bk_data_id
    return cfg
