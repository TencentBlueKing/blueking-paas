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

from typing import Any, Dict, List, Optional, Protocol, Union

import cattr
from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.infras.bk_log.backend.apigw import Client as APIGWClient
from paasng.infras.bk_log.backend.esb import get_client_by_username
from paasng.infras.bk_log.definitions import CustomCollectorConfig, PlainCustomCollectorConfig
from paasng.infras.bk_log.exceptions import BkLogApiError, BkLogGatewayServiceError, CollectorConfigNotPersisted


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
        **kwargs,
    ) -> Dict: ...


class BKLogQueryAPIProtocol(Protocol):
    esquery_dsl: _APIGWOperationStub
    esquery_scroll: _APIGWOperationStub
    esquery_mapping: _APIGWOperationStub


class BkLogManagementAPIProtocol(Protocol):
    """bk-log api protocol"""

    databus_custom_create: _APIGWOperationStub
    databus_custom_update: _APIGWOperationStub
    databus_list_collectors: _APIGWOperationStub


class BkLogManagementClient:
    def __init__(self, client: BkLogManagementAPIProtocol):
        self.client = client

    def list_custom_collector_config(
        self,
        biz_or_space_id: Union[int, str],
    ) -> List[PlainCustomCollectorConfig]:
        """列举所有自定义采集项"""
        try:
            resp = self.client.databus_list_collectors(params={"bk_biz_id": biz_or_space_id})
        except APIGatewayResponseError:
            raise BkLogGatewayServiceError("Failed to list custom collector config")

        if not resp["result"]:
            raise BkLogApiError(resp["message"])

        data = resp["data"]
        return [
            PlainCustomCollectorConfig(
                name_en=item["collector_config_name_en"],
                name_zh_cn=item["collector_config_name"],
                custom_type=item["custom_type"],
                id=item["collector_config_id"],
                index_set_id=item["index_set_id"],
                bk_data_id=item["bk_data_id"],
            )
            for item in data
        ]

    def get_custom_collector_config_by_name_en(
        self, biz_or_space_id: Union[int, str], collector_config_name_en: str
    ) -> Optional[PlainCustomCollectorConfig]:
        """根据名字查询自定义采集项"""
        try:
            resp = self.client.databus_list_collectors(params={"bk_biz_id": biz_or_space_id})
        except APIGatewayResponseError:
            raise BkLogGatewayServiceError("Failed to list custom collector config")

        if not resp["result"]:
            raise BkLogApiError(resp["message"])

        data = resp["data"]
        for item in data:
            if item["collector_config_name_en"] == collector_config_name_en:
                return PlainCustomCollectorConfig(
                    name_en=item["collector_config_name_en"],
                    name_zh_cn=item["collector_config_name"],
                    custom_type=item["custom_type"],
                    id=item["collector_config_id"],
                    index_set_id=item["index_set_id"],
                    bk_data_id=item["bk_data_id"],
                )
        return None

    def create_custom_collector_config(self, biz_or_space_id: Union[int, str], config: CustomCollectorConfig):
        """创建自定义采集项, 如果创建成功, 会给 config.id, config.index_set_id, config.bk_data_id 赋值

        :param int/str biz_or_space_id: 业务ID(bkcmdb)，或空间ID(space_id)
        :param config: 自定采集项配置
        :return: 创建的自定采集项配置
        """
        data: Dict[str, Any] = {
            # 日志侧的接口参数未调整, 虽然参数名是 bk_biz_id, 实际上空间ID也通过这个参数传递
            "bk_biz_id": biz_or_space_id,
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
                    # log-search API 参数为 storage_replies
                    "storage_replies": config.storage_config.storage_replicas,
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
                    # log-search API 参数为 storage_replies
                    "storage_replies": config.storage_config.storage_replicas,
                    "allocation_min_days": config.storage_config.allocation_min_days,
                }
            )
        try:
            resp = self.client.databus_custom_update(data=data, path_params={"collector_config_id": config.id})
        except APIGatewayResponseError:
            raise BkLogGatewayServiceError("Failed to update custom collector config")

        if not resp["result"]:
            raise BkLogApiError(resp["message"])


def make_bk_log_management_client(tenant_id: str) -> BkLogManagementClient:
    if settings.ENABLE_BK_LOG_APIGW:
        apigw_client = APIGWClient(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_LOG_APIGW_SERVICE_STAGE)
        apigw_client.update_bkapi_authorization(
            # 日志平台必须要 bk_username 这个参数
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
            bk_username="admin",
        )
        apigw_client.update_headers(
            {
                API_HERDER_TENANT_ID: tenant_id,
            }
        )
        return BkLogManagementClient(apigw_client.api)

    # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
    esb_client = get_client_by_username("admin")
    return BkLogManagementClient(esb_client.api)


def make_bk_log_esquery_client(tenant_id: str) -> BKLogQueryAPIProtocol:
    if settings.ENABLE_BK_LOG_APIGW:
        apigw_client = APIGWClient(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_LOG_APIGW_SERVICE_STAGE)
        apigw_client.update_bkapi_authorization(
            # 日志平台必须要 bk_username 这个参数
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
            bk_username="admin",
        )
        apigw_client.update_headers(
            {
                API_HERDER_TENANT_ID: tenant_id,
            }
        )
        return apigw_client.api

    # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
    esb_client = get_client_by_username("admin")
    return esb_client.api
