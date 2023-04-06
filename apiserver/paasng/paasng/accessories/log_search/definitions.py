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
from typing import List, Literal, Optional

from attrs import define


@define
class StorageConfig:
    """日志存储配置

    :param storage_cluster_id: 存储ES集群，默认会选择一个公共集群作为存储，如果需要指定存储，则填写为日志平台注册后的集群ID
    :param retention: 存储时间
    :param es_shards: 索引分片数
    :param storage_replies: 存储副本数
    :param allocation_min_days: n天后的数据，转到冷节点，只在集群开启了冷热时生效
    """

    storage_cluster_id: int
    retention: int = 14
    es_shards: int = 3
    storage_replies: int = 1
    allocation_min_days: int = 14


@define
class CustomCollectorMetaData:
    """自定采集项元信息

    :param name_en: 采集英文名称，重要，5-50个字符，仅包含字母数字下划线
    :param name_zh_cn: 采集项中文名, 最多50个字符
    :param custom_type: 日志类型，无特殊要求一般固定为log。当前可选的值(log、otlp_trace、otlp_log)
    :param category_id: 数据分类, 无特殊要求可以固定为"application_check", 代表这个数据是业务的应用日志
    :param storage_config: 日志存储配置
    :param data_link_id: 数据传输链路，不需要可以不填
    :param description: 描述信息

    :param id: 采集项ID
    :param index_set_id: 索引集ID，查询时使用
    :param bk_data_id: 数据管道ID
    """

    name_en: str
    name_zh_cn: str
    custom_type: Literal["log"] = "log"
    category_id: str = "application_check"
    storage_config: Optional[StorageConfig] = None
    data_link_id: Optional[int] = None
    description: str = ""

    id: Optional[int] = None
    index_set_id: Optional[int] = None
    bk_data_id: Optional[int] = None


@define
class CollectorConfig:
    """采集项配置

    :param log_path: 日志文件的绝对路径, 可使用通配符
    """

    log_path: List[str]
    encoding: Literal["UTF-8"] = "UTF-8"
    # TODO: 清洗规则
