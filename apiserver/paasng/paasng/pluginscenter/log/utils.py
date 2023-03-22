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
from typing import Dict, List

from elasticsearch_dsl.response import Hit
from rest_framework.fields import get_attribute

from paasng.pluginscenter.definitions import ElasticSearchParams
from paasng.utils.es_log.misc import flatten_structure, format_timestamp


def clean_logs(
    logs: List[Hit],
    search_params: ElasticSearchParams,
) -> List[Dict]:
    """从 ES 日志中提取 PaaS 的字段"""
    cleaned = []
    for log in logs:
        cleaned.append(
            {
                "timestamp": format_timestamp(
                    get_attribute(log, search_params.timeField.split(".")), search_params.timeFormat
                ),
                "message": get_attribute(log, search_params.messageField.split(".")),
                "raw": flatten_structure(log.to_dict(), None),
            }
        )
    return cleaned
