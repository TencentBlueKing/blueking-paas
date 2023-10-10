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

from typing import List, Literal

from django.db.transaction import atomic

from paasng.accessories.bk_log.client import make_bk_log_client
from paasng.accessories.bk_log.definitions import CustomCollectorConfig
from paasng.accessories.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.platform.log.models import CustomCollectorConfig as CustomCollectorConfigModel
from paasng.platform.modules.models import Module


def get_or_create_custom_collector_config(
    module: Module, collector_config: CustomCollectorConfig, log_paths: List[str], log_type: Literal["stdout", "json"]
) -> CustomCollectorConfig:
    """调用日志平台的接口, 查询或创建自定义采集项
    :param module: module
    :param collector_config: custom collector config create params
    :param log_paths: 日志采集路径, 仅 log_type = "json" 时有效
    :param log_type: 日志类型
    :return: CustomCollectorConfigModel
    """
    monitor_space, _ = get_or_create_bk_monitor_space(module.application)
    client = make_bk_log_client()
    collector_config_in_bk_log = client.get_custom_collector_config_by_name_en(
        biz_or_space_id=monitor_space.iam_resource_id, collector_config_name_en=collector_config.name_en
    )
    if not collector_config_in_bk_log:
        return update_or_create_custom_collector_config(
            module, collector_config, log_paths, log_type, skip_query_bk_log=True
        )

    collector_config.id = collector_config_in_bk_log.id
    collector_config.index_set_id = collector_config_in_bk_log.index_set_id
    collector_config.bk_data_id = collector_config_in_bk_log.bk_data_id
    CustomCollectorConfigModel.objects.get_or_create(
        module=module,
        name_en=collector_config.name_en,
        defaults={
            "collector_config_id": collector_config.id,
            "index_set_id": collector_config.index_set_id,
            "bk_data_id": collector_config.bk_data_id,
            "log_paths": log_paths,
            "log_type": log_type,
        },
    )
    return collector_config


def update_or_create_custom_collector_config(
    module: Module,
    collector_config: CustomCollectorConfig,
    log_paths: List[str],
    log_type: Literal["stdout", "json"],
    skip_query_bk_log: bool = False,
) -> CustomCollectorConfig:
    """调用日志平台的接口, 创建或更新自定义采集项

    :param module: module
    :param collector_config: custom collector config create params
    :param log_paths: 日志采集路径, 仅 log_type = "json" 时有效
    :param log_type: 日志类型
    :param skip_query_bk_log: 跳过查询日志平台自定义采集项是否存在, 该参数仅提供给 get_or_create_custom_collector_config 使用.
    :return: CustomCollectorConfigModel
    """
    monitor_space, _ = get_or_create_bk_monitor_space(module.application)
    client = make_bk_log_client()
    if not collector_config.id and not skip_query_bk_log:
        collector_config_in_bk_log = client.get_custom_collector_config_by_name_en(
            biz_or_space_id=monitor_space.iam_resource_id, collector_config_name_en=collector_config.name_en
        )
        if collector_config_in_bk_log:
            collector_config.id = collector_config_in_bk_log.id
            collector_config.index_set_id = collector_config_in_bk_log.index_set_id
            collector_config.bk_data_id = collector_config_in_bk_log.bk_data_id

    with atomic():
        if not collector_config.id:
            collector_config = client.create_custom_collector_config(
                biz_or_space_id=monitor_space.iam_resource_id, config=collector_config
            )
        else:
            client.update_custom_collector_config(collector_config)

        CustomCollectorConfigModel.objects.update_or_create(
            module=module,
            name_en=collector_config.name_en,
            defaults={
                "collector_config_id": collector_config.id,
                "index_set_id": collector_config.index_set_id,
                "bk_data_id": collector_config.bk_data_id,
                "log_paths": log_paths,
                "log_type": log_type,
            },
        )

    return collector_config
