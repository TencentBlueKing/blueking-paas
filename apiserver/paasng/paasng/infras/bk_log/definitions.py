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

from typing import Dict, List, Literal, Optional

from attrs import define, field

from paasng.infras.bk_log.constatns import ETLType, FieldType


@define
class ETLField:
    """日志清洗字段配置

    :param field_index: 字段顺序
    :param field_name: 字段名称
    :param field_type: 字段类型(int, long, double, string, object, nested)
    :param alias_name: 字段别名，一般清洗为json时，可配置上这个对字段重命名
    :param description: 字段描述信息
    :param is_delete: 字段是否被删除，保留为false即可
    :param is_dimension: 是否为维度字段，默认为true，代表字段是可聚合的
    :param is_time: 是否为时间字段，默认为false，如果指定的话，需要通过option参数配置时间的具体格式和时区
    :param is_analyzed: 是否为分词字段，默认为false，一般如果是文本类型的，建议设置为true
    :param is_built_in: 是否为内置字段，默认为false，一般不需要设置该字段，保留为false即可
    :param option: 字段配置，一般设置为时间字段后需要配置，例如：{"time_zone":8, "time_format":"yyyy-MM-dd HH:mm:ss"}
    """

    field_index: int
    field_name: str
    field_type: FieldType
    alias_name: Optional[str] = None
    description: Optional[str] = ""
    is_delete: bool = False
    is_dimension: bool = True
    is_time: bool = False
    is_analyzed: bool = False
    is_built_in: bool = False
    option: dict = field(factory=dict)


@define
class ETLParams:
    """日志清洗参数

    :param retain_original_text: 是否保留原始日志字段，即log字段，默认保留true设置即可
    :param separator: 分隔符，当类型为bk_log_delimiter时配置
    :param separator_regexp: 正则表达式，当类型为bk_log_regexp时配置
    :param retain_extra_json: 是否保留未定义JSON字段, 即未定义的字段会存入 __ext_json 中
    """

    retain_original_text: bool = True
    separator: Optional[str] = None
    separator_regexp: Optional[str] = None
    retain_extra_json: bool = False


@define
class ETLConfig:
    """日志清洗规则"""

    type: ETLType = ETLType.TEXT
    params: ETLParams = field(factory=ETLParams)
    fields: List[ETLField] = field(factory=list)


@define
class StorageConfig:
    """日志存储配置

    :param storage_cluster_id: 存储ES集群，默认会选择一个公共集群作为存储，如果需要指定存储，则填写为日志平台注册后的集群ID
    :param retention: 存储时间
    :param es_shards: 索引分片数
    :param storage_replicas: 存储副本数
    :param allocation_min_days: n天后的数据，转到冷节点，只在集群开启了冷热时生效
    """

    storage_cluster_id: int
    retention: int
    es_shards: int
    storage_replicas: int
    allocation_min_days: int = 0


@define
class PlainCustomCollectorConfig:
    """自定义采集项配置(精简)

    :param name_en: 采集英文名称，重要，5-50个字符，仅包含字母数字下划线
    :param name_zh_cn: 采集项中文名, 最多50个字符
    :param custom_type: 日志类型，无特殊要求一般固定为log。当前可选的值(log、otlp_trace、otlp_log)

    :param id: 采集项ID
    :param index_set_id: 索引集ID，查询时使用
    :param bk_data_id: 数据管道ID
    """

    name_en: str
    name_zh_cn: str
    custom_type: Literal["log"] = "log"

    # readonly fields
    id: Optional[int] = None
    index_set_id: Optional[int] = None
    bk_data_id: Optional[int] = None


@define
class PlatformIndexVisibility:
    """平台级采集项对其他业务的可见范围

    对应日志平台 create/update 自定义采集项接口的 platform_index_visibility 字段。

    :param type: 可见范围类型。"biz_attr" 按空间标签匹配，"multi_biz" 显式列出业务 ID。
    :param bk_biz_labels: type="biz_attr" 时使用，形如 {"space_type": ["bksaas"]}
    :param bk_biz_ids: type="multi_biz" 时使用，显式列出可见业务 ID
    """

    type: Literal["biz_attr", "multi_biz"]
    bk_biz_labels: Optional[Dict[str, List[str]]] = None
    bk_biz_ids: Optional[List[int]] = None


@define
class PlatformIndexFilter:
    """平台级采集项的隔离维度元数据 (对应日志平台 platform_index_filter 字段)

    当前仅作为标记保存, 不参与运行时过滤; PaaS 侧应用级隔离由 ElasticSearchParams.termTemplate 实现。

    :param field: 用于隔离的字段路径，如 "__ext.labels.bkapp_paas_bk_tencent_com_code"
    :param value_ref: 字段值的语义引用，仅允许 "space_id" 或 "bk_biz_id"
    """

    field: str
    value_ref: Literal["space_id", "bk_biz_id"]


@define
class CustomCollectorConfig:
    """自定采集项配置

    :param name_en: 采集英文名称，重要，5-50个字符，仅包含字母数字下划线
    :param name_zh_cn: 采集项中文名, 最多50个字符
    :param custom_type: 日志类型，无特殊要求一般固定为log。当前可选的值(log、otlp_trace、otlp_log)
    :param category_id: 数据分类, 无特殊要求可以固定为"application_check", 代表这个数据是业务的应用日志
    :param etl_config: 日志清洗配置
    :param storage_config: 日志存储配置
    :param data_link_id: 数据传输链路，不需要可以不填
    :param description: 描述信息

    :param is_platform_index: 是否为平台级采集项（多业务共享一个物理 ES 索引）
    :param platform_index_visibility: 平台级采集项对其他业务的可见范围，仅在 is_platform_index=True 时生效
    :param platform_index_filter: 平台级采集项的隔离维度元数据，仅在 is_platform_index=True 时生效

    :param id: 采集项ID
    :param index_set_id: 索引集ID，查询时使用
    :param bk_data_id: 数据管道ID
    """

    name_en: str
    name_zh_cn: str
    custom_type: Literal["log"] = "log"
    category_id: str = "application_check"
    etl_config: Optional[ETLConfig] = None
    storage_config: Optional[StorageConfig] = None
    data_link_id: Optional[int] = None
    description: str = ""

    # 平台级采集项字段, 默认关闭, 仅启用 ENABLE_SHARED_BK_LOG_INDEX 时由共享路径设置
    is_platform_index: bool = False
    platform_index_visibility: Optional[PlatformIndexVisibility] = None
    platform_index_filter: Optional[PlatformIndexFilter] = None

    # readonly fields
    id: Optional[int] = None
    index_set_id: Optional[int] = None
    bk_data_id: Optional[int] = None

    def __attrs_post_init__(self):
        # 平台级采集项必须同时声明可见范围与隔离维度, 否则日志平台创建会报错, 提前 fail fast
        if self.is_platform_index and (self.platform_index_visibility is None or self.platform_index_filter is None):
            raise ValueError(
                "platform_index_visibility and platform_index_filter are required when is_platform_index=True"
            )


@define
class AppLogCollectorConfig:
    """简化的采集项配置

    :param log_paths: 日志文件的绝对路径, 可使用通配符
    :param time_field: 时间字段, 仅 log_type = json 时必须
    :param time_format: 时间格式, 仅 log_type = json 时必须
    :param log_type: 日志类型, stdout, json
    :param etl_type: 日志(清洗)类型, text 纯文本, json 结构化日志

    :param collector_config: 日志采集项配置, 创建后再赋值
    """

    log_paths: List[str] = field(factory=list)
    time_field: Optional[str] = None
    time_format: Optional[str] = None
    log_type: Literal["stdout", "json"] = "json"
    etl_type: ETLType = ETLType.TEXT

    collector_config: Optional[CustomCollectorConfig] = None
