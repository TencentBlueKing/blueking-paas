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

import datetime
import logging
from typing import Union

from django.conf import settings
from django.utils.timezone import get_default_timezone
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.log.constants import DEFAULT_LOG_CONFIG_PLACEHOLDER
from paasng.accessories.log.models import CustomCollectorConfig as CustomCollectorConfigModel
from paasng.accessories.log.models import (
    ElasticSearchConfig,
    ElasticSearchParams,
    ProcessLogQueryConfig,
)
from paasng.accessories.log.shim.bklog_custom_collector_config import get_or_create_custom_collector_config
from paasng.accessories.log.shim.setup_elk import ELK_INGRESS_COLLECTOR_CONFIG_ID_TMPL, setup_platform_elk_config
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
from paasng.utils.error_codes import error_codes

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

    @property
    def retention(self) -> int:
        """获取日志存储时间(天)"""
        return settings.BKLOG_CONFIG["RETENTION"]

    @property
    def es_shards(self) -> int:
        """获取ES索引分片数"""
        return settings.BKLOG_CONFIG["ES_SHARDS"]

    @property
    def storage_replicas(self) -> int:
        """获取存储副本数"""
        return settings.BKLOG_CONFIG["STORAGE_REPLICAS"]


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
    """初始化日志平台采集链路日志查询相关的数据库模型

    :param str message_field: 日志查询字段, 默认值 log 是日志平台的原始日志字段
    """
    application = env.application
    assert collector_config.collector_config

    monitor_space, _ = get_or_create_bk_monitor_space(application)
    # Note: 修改以下的 ElasticSearchParams 只对新创建的查询配置生效
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
        r"|otelServiceName|otelTraceID|requestID|environment|process_id|stream|__ext_json\..*",
    )

    # 日志平台查询 API 参数配置
    defaults = {
        "backend_type": "bkLog",
        "bk_log_config": {
            "scenarioID": "log",
        },
        "search_params": search_params,
        "tenant_id": env.tenant_id,
    }

    search_config, _ = ElasticSearchConfig.objects.update_or_create(
        collector_config_id=collector_config.collector_config.id,
        defaults=defaults,
    )

    config, _ = ProcessLogQueryConfig.objects.get_or_create(
        env=env, process_type=DEFAULT_LOG_CONFIG_PLACEHOLDER, defaults={"tenant_id": env.tenant_id}
    )
    config.tenant_id = env.tenant_id
    if collector_config.log_type == "stdout":
        config.stdout = search_config
    elif collector_config.log_type == "json":
        config.json = search_config
    else:
        raise NotImplementedError
    config.save()


def setup_bk_log_custom_collector(module: Module):
    """初始化日志平台内置的日志采集项(JSON日志采集和标准输出日志采集)"""
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
    update_or_create_es_search_config(env, json_config, message_field="message")
    update_or_create_es_search_config(env, stdout_config)

    # Ingress 仍然使用 elk 的采集方案
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


def build_custom_collector_config_name(module: Module, type: str) -> str:
    """构造应用唯一的自定义采集项英文名称，重要，5-50 个字符，仅包含字母数字下划线

    保险起见, type 只能在 6 个字符以内(含6个字符)
    """
    # app_code max_length 20 字符
    app_code = module.application.code
    # module_name max_length 20 字符
    module_name = module.name
    # 使用 "__" 分割 app_code/module_name 是为了保证从自定义采集项名称可以逆推出应用信息(这个名称会作为 ES index 的组成部分)
    # 原理: 目前的逻辑保证 app_code 与 module_name 均不能有连续的连字符 "--"
    return f"{app_code}__{module_name}__{type}".replace("-", "_")


def to_custom_collector_config(module: Module, collector_config: AppLogCollectorConfig) -> CustomCollectorConfig:
    """将 AppLogCollectorConfig 转换成 CustomCollectorConfig

    仅用于系统内置的自定义采集项
    """

    if collector_config.etl_type == ETLType.TEXT:
        etl_config = ETLConfig(
            type=collector_config.etl_type,
        )
    elif collector_config.etl_type == ETLType.JSON:

        def make_string_field(index: int, field_name: str, is_analyzed: bool) -> ETLField:
            return ETLField(
                field_index=index,
                field_name=field_name,
                field_type=FieldType.STRING,
                is_time=False,
                is_dimension=False,
                is_analyzed=is_analyzed,
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
            # 只对 message 字段做分词处理，其他字段不分词
            # 对字段分词后无法使用 term 查询做精确查询
            # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-term-query.html
            make_string_field(2, "message", is_analyzed=True),
            make_string_field(3, "levelname", is_analyzed=False),
            make_string_field(4, "pathname", is_analyzed=False),
            make_string_field(5, "funcName", is_analyzed=False),
            make_string_field(6, "otelSpanID", is_analyzed=False),
            make_string_field(7, "otelServiceName", is_analyzed=False),
            make_string_field(8, "otelTraceID", is_analyzed=False),
            make_string_field(9, "requestID", is_analyzed=False),
        ]

        etl_config = ETLConfig(
            type=collector_config.etl_type,
            params=ETLParams(retain_extra_json=True),
            fields=fields,
        )
    else:
        raise NotImplementedError

    db_obj = None
    try:
        # 当内置采集项已创建, 则采集项名称不可修改(只能用数据库中存储的名称)
        db_obj = CustomCollectorConfigModel.objects.get(
            module=module, log_type=collector_config.log_type, is_builtin=True
        )
        name = db_obj.name_en
    except CustomCollectorConfigModel.DoesNotExist:
        logger.debug("CustomCollectorConfig does not exits, skip fill persistence fields")
        name = build_custom_collector_config_name(module, type=collector_config.log_type)

    bklog_provider = BKLogConfigProvider(module)
    cfg = CustomCollectorConfig(
        name_en=name,
        name_zh_cn=name,
        etl_config=etl_config,
        storage_config=StorageConfig(
            storage_cluster_id=bklog_provider.storage_cluster_id,
            retention=bklog_provider.retention,
            es_shards=bklog_provider.es_shards,
            storage_replicas=bklog_provider.storage_replicas,
        ),
    )
    # fill persistence fields from db
    if db_obj:
        cfg.id = db_obj.collector_config_id
        cfg.index_set_id = db_obj.index_set_id
        cfg.bk_data_id = db_obj.bk_data_id
    return cfg
