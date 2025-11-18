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

from unittest import mock

import pytest

from paasng.infras.bk_log.client import BkLogManagementAPIProtocol, BkLogManagementClient
from paasng.infras.bk_log.constatns import ETLType, FieldType
from paasng.infras.bk_log.definitions import CustomCollectorConfig, ETLConfig, ETLField, ETLParams, StorageConfig
from paasng.infras.bk_log.exceptions import CollectorConfigNotPersisted


class TestBkLogClient:
    @pytest.fixture()
    def mocked_api(self):
        return mock.MagicMock(
            spec=type(BkLogManagementAPIProtocol.__name__, (), BkLogManagementAPIProtocol.__annotations__)
        )

    @pytest.fixture()
    def client(self, mocked_api):
        return BkLogManagementClient(mocked_api)

    @pytest.mark.parametrize(
        ("config", "expected_data"),
        [
            # 测试最简配置
            (
                CustomCollectorConfig(name_en="foo", name_zh_cn="foo", description="bar" * 10),
                {
                    "bk_biz_id": 1,
                    "collector_config_name_en": "foo",
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "bar" * 10,
                },
            ),
            # 测试配置 ES 存储
            (
                CustomCollectorConfig(
                    name_en="foo",
                    name_zh_cn="foo",
                    description="bar" * 10,
                    storage_config=StorageConfig(
                        storage_cluster_id=1008611,
                        retention=14,
                        es_shards=1,
                        storage_replicas=1,
                    ),
                ),
                {
                    "bk_biz_id": 1,
                    "collector_config_name_en": "foo",
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "barbarbarbarbarbarbarbarbarbar",
                    "storage_cluster_id": 1008611,
                    "retention": 14,
                    "es_shards": 1,
                    # log-search API 参数为 storage_replies
                    "storage_replies": 1,
                    "allocation_min_days": 0,
                },
            ),
            # 测试 JSON 类型配置
            (
                CustomCollectorConfig(
                    name_en="foo",
                    name_zh_cn="foo",
                    etl_config=ETLConfig(
                        type=ETLType.JSON,
                        fields=[
                            ETLField(
                                field_index=1,
                                field_name="custom_1",
                                field_type=FieldType.INT,
                                description="自定义字段说明1",
                            ),
                            ETLField(
                                field_index=1,
                                field_name="time",
                                field_type=FieldType.STRING,
                                description="时间字段",
                                is_time=True,
                                option={"time_zone": 8, "time_format": "yyyy-MM-dd HH:mm:ss"},
                            ),
                        ],
                        params=ETLParams(retain_original_text=False, retain_extra_json=True),
                    ),
                ),
                {
                    "bk_biz_id": 1,
                    "collector_config_name_en": "foo",
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "",
                    "etl_config": "bk_log_json",
                    "etl_params": {
                        "retain_original_text": False,
                        "separator": None,
                        "separator_regexp": None,
                        "retain_extra_json": True,
                    },
                    "fields": [
                        {
                            "field_index": 1,
                            "field_name": "custom_1",
                            "field_type": FieldType.INT,
                            "alias_name": None,
                            "description": "自定义字段说明1",
                            "is_delete": False,
                            "is_dimension": True,
                            "is_time": False,
                            "is_analyzed": False,
                            "is_built_in": False,
                            "option": {},
                        },
                        {
                            "field_index": 1,
                            "field_name": "time",
                            "field_type": FieldType.STRING,
                            "alias_name": None,
                            "description": "时间字段",
                            "is_delete": False,
                            "is_dimension": True,
                            "is_time": True,
                            "is_analyzed": False,
                            "is_built_in": False,
                            "option": {"time_zone": 8, "time_format": "yyyy-MM-dd HH:mm:ss"},
                        },
                    ],
                },
            ),
            # 测试 Text 类型配置
            (
                CustomCollectorConfig(
                    name_en="foo",
                    name_zh_cn="foo",
                    description="bar" * 10,
                    etl_config=ETLConfig(type=ETLType.TEXT, params=ETLParams(retain_original_text=True)),
                ),
                {
                    "bk_biz_id": 1,
                    "collector_config_name_en": "foo",
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "barbarbarbarbarbarbarbarbarbar",
                    "etl_config": "bk_log_text",
                    "etl_params": {
                        "retain_original_text": True,
                        "separator": None,
                        "separator_regexp": None,
                        "retain_extra_json": False,
                    },
                    "fields": [],
                },
            ),
        ],
    )
    def test_create_custom_collector_config(self, mocked_api, client, config, expected_data):
        mocked_api.databus_custom_create.return_value = {
            "result": True,
            "data": {"collector_config_id": 1026, "index_set_id": 481367, "bk_data_id": 1578495},
            "code": 0,
            "message": "",
        }
        c = client.create_custom_collector_config(1, config)
        assert mocked_api.databus_custom_create.called
        # validate data
        data = mocked_api.databus_custom_create.call_args.kwargs["data"]
        assert data == expected_data
        # validate update id, index_set_id, bk_data_id
        assert c.id == 1026
        assert c.index_set_id == 481367
        assert c.bk_data_id == 1578495

    # 测试数据和 test_create_custom_collector_config 一致, 但 expected_data 不一样
    @pytest.mark.parametrize(
        ("config", "expected_data"),
        [
            # 测试最简配置
            (
                CustomCollectorConfig(name_en="foo", name_zh_cn="foo", description="bar" * 10),
                {
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "bar" * 10,
                },
            ),
            # 测试配置 ES 存储
            (
                CustomCollectorConfig(
                    name_en="foo",
                    name_zh_cn="foo",
                    description="bar" * 10,
                    storage_config=StorageConfig(
                        storage_cluster_id=1008611,
                        retention=14,
                        es_shards=1,
                        storage_replicas=1,
                    ),
                ),
                {
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "barbarbarbarbarbarbarbarbarbar",
                    "storage_cluster_id": 1008611,
                    "retention": 14,
                    "es_shards": 1,
                    # log-search API 参数为 storage_replies
                    "storage_replies": 1,
                    "allocation_min_days": 0,
                },
            ),
            # 测试 JSON 类型配置
            (
                CustomCollectorConfig(
                    name_en="foo",
                    name_zh_cn="foo",
                    etl_config=ETLConfig(
                        type=ETLType.JSON,
                        fields=[
                            ETLField(
                                field_index=1,
                                field_name="custom_1",
                                field_type=FieldType.INT,
                                description="自定义字段说明1",
                            ),
                            ETLField(
                                field_index=1,
                                field_name="time",
                                field_type=FieldType.STRING,
                                description="时间字段",
                                is_time=True,
                                option={"time_zone": 8, "time_format": "yyyy-MM-dd HH:mm:ss"},
                            ),
                        ],
                        params=ETLParams(retain_original_text=False, retain_extra_json=True),
                    ),
                ),
                {
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "",
                    "etl_config": "bk_log_json",
                    "etl_params": {
                        "retain_original_text": False,
                        "separator": None,
                        "separator_regexp": None,
                        "retain_extra_json": True,
                    },
                    "fields": [
                        {
                            "field_index": 1,
                            "field_name": "custom_1",
                            "field_type": FieldType.INT,
                            "alias_name": None,
                            "description": "自定义字段说明1",
                            "is_delete": False,
                            "is_dimension": True,
                            "is_time": False,
                            "is_analyzed": False,
                            "is_built_in": False,
                            "option": {},
                        },
                        {
                            "field_index": 1,
                            "field_name": "time",
                            "field_type": FieldType.STRING,
                            "alias_name": None,
                            "description": "时间字段",
                            "is_delete": False,
                            "is_dimension": True,
                            "is_time": True,
                            "is_analyzed": False,
                            "is_built_in": False,
                            "option": {"time_zone": 8, "time_format": "yyyy-MM-dd HH:mm:ss"},
                        },
                    ],
                },
            ),
            # 测试 Text 类型配置
            (
                CustomCollectorConfig(
                    name_en="foo",
                    name_zh_cn="foo",
                    description="bar" * 10,
                    etl_config=ETLConfig(type=ETLType.TEXT, params=ETLParams(retain_original_text=True)),
                ),
                {
                    "collector_config_name": "foo",
                    "custom_type": "log",
                    "category_id": "application_check",
                    "description": "barbarbarbarbarbarbarbarbarbar",
                    "etl_config": "bk_log_text",
                    "etl_params": {
                        "retain_original_text": True,
                        "separator": None,
                        "separator_regexp": None,
                        "retain_extra_json": False,
                    },
                    "fields": [],
                },
            ),
        ],
    )
    def test_databus_custom_update(self, mocked_api, client, config, expected_data):
        # set id
        config.id = 1026
        mocked_api.databus_custom_update.return_value = {
            "result": True,
            "code": 0,
            "message": "",
        }
        client.update_custom_collector_config(config)
        assert mocked_api.databus_custom_update.called
        # validate data
        data = mocked_api.databus_custom_update.call_args.kwargs["data"]
        assert data == expected_data
        # validate path params
        assert mocked_api.databus_custom_update.call_args.kwargs["path_params"]["collector_config_id"] == 1026

    def test_databus_custom_update_failed(self, client):
        with pytest.raises(CollectorConfigNotPersisted):
            client.update_custom_collector_config(CustomCollectorConfig(name_en="foo", name_zh_cn="foo"))
