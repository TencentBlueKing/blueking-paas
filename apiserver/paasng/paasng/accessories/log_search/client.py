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
from typing import Any, Dict, Optional, Protocol

import cattr
from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings

from paasng.accessories.log_search.backend.apigw import Client as APIGWClient
from paasng.accessories.log_search.backend.esb import get_client_by_username
from paasng.accessories.log_search.definitions import CustomCollectorConfig
from paasng.accessories.log_search.exceptions import (
    BkLogApiError,
    BkLogGatewayServiceError,
    CollectorConfigNotPersisted,
)


class _APIGWOperationStub(Protocol):
    """apigw operation method stub"""

    def __call__(
        self,
        data: Optional[Any] = None,
        path_params: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        proxies: Optional[Dict[str, Any]] = None,
        verify: Optional[bool] = None,
        **kwargs
    ) -> Dict:
        ...


class BKLogAPIProtocol(Protocol):
    """bk-log api protocol"""

    databus_custom_create: _APIGWOperationStub
    databus_custom_update: _APIGWOperationStub


class BkLogClient:
    def __init__(self, client: BKLogAPIProtocol):
        self.client = client

    def create_custom_collector_config(self, bk_biz_id: int, config: CustomCollectorConfig):
        """创建自定义采集项, 如果创建成功, 会给 config.id, config.index_set_id, config.bk_data_id 赋值

        :param int bk_biz_id: 业务ID，或空间ID
        :param config: 自定采集项配置
        :return: 创建的自定采集项配置
        """
        data: Dict[str, Any] = {
            "bk_biz_id": bk_biz_id,
            "collector_config_name_en": config.name_en,
            "collector_config_name": config.name_zh_cn,
            "custom_type": config.custom_type,
            "category_id": config.category_id,
            "description": config.description,
        }
        if config.data_link_id:
            data["data_link_id"] = config.data_link_id
        if config.etl_config:
            data.update(
                {
                    "etl_config": config.etl_config.type,
                    "etl_params": cattr.unstructure(config.etl_config.params),
                    "fields": cattr.unstructure(config.etl_config.fields),
                }
            )
        if config.storage_config:
            data.update(
                {
                    "storage_cluster_id": config.storage_config.storage_cluster_id,
                    "retention": config.storage_config.retention,
                    "es_shards": config.storage_config.es_shards,
                    "storage_replies": config.storage_config.storage_replies,
                    "allocation_min_days": config.storage_config.allocation_min_days,
                }
            )
        try:
            resp = self.client.databus_custom_create(data=data)
        except APIGatewayResponseError:
            raise BkLogGatewayServiceError("Failed to create custom collector config")

        if not resp["result"]:
            raise BkLogApiError(resp["message"])

        config.id = resp["data"]["collector_config_id"]
        config.index_set_id = resp["data"]["index_set_id"]
        config.bk_data_id = resp["data"]["bk_data_id"]
        return config

    def update_custom_collector_config(self, config: CustomCollectorConfig):
        """更新自定义采集项"""
        if config.id is None:
            raise CollectorConfigNotPersisted

        data: Dict[str, Any] = {
            "collector_config_name": config.name_zh_cn,
            "custom_type": config.custom_type,
            "category_id": config.category_id,
            "description": config.description,
        }
        if config.etl_config:
            data.update(
                {
                    "etl_config": config.etl_config.type,
                    "etl_params": cattr.unstructure(config.etl_config.params),
                    "fields": cattr.unstructure(config.etl_config.fields),
                }
            )
        if config.storage_config:
            data.update(
                {
                    "storage_cluster_id": config.storage_config.storage_cluster_id,
                    "retention": config.storage_config.retention,
                    "es_shards": config.storage_config.es_shards,
                    "storage_replies": config.storage_config.storage_replies,
                    "allocation_min_days": config.storage_config.allocation_min_days,
                }
            )
        try:
            resp = self.client.databus_custom_update(data=data, path_params={"collector_config_id": config.id})
        except APIGatewayResponseError:
            raise BkLogGatewayServiceError("Failed to update custom collector config")

        if not resp["result"]:
            raise BkLogApiError(resp["message"])


def make_bk_log_client() -> BkLogClient:
    if settings.ENABLE_BK_LOG_APIGW:
        apigw_client = APIGWClient(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_LOG_APIGW_SERVICE_STAGE)
        apigw_client.update_bkapi_authorization(
            # 日志平台必须要 bk_username 这个参数
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
            bk_username="admin",
        )
        return BkLogClient(apigw_client.api)

    # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
    esb_client = get_client_by_username("admin")
    return BkLogClient(esb_client.api)
