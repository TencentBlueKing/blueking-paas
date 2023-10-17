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
from dataclasses import dataclass
from typing import List

from paasng.utils.basic import ChoicesEnum


class RegionConverter:
    _data = {
        "ieod": "ied",
    }
    _data_reverse = {v: k for k, v in list(_data.items())}

    @classmethod
    def to_old(cls, region):
        return cls._data.get(region, region)

    @classmethod
    def to_new(cls, region):
        return cls._data_reverse.get(region, region)


class PVTimeType(ChoicesEnum):
    """
    应用访问量-日期范围类型
    """

    TYPE_15m = "15m"
    TYPE_30m = "30m"
    TYPE_1h = "1h"
    TYPE_4h = "4h"
    TYPE_12h = "12h"
    TYPE_1d = "1d"
    TYPE_3d = "3d"
    TYPE_7d = "7d"
    TYPE_CUSTOMIZED = "customized"

    _choices_labels = (
        (TYPE_15m, u"15分钟"),
        (TYPE_30m, u"30钟"),
        (TYPE_1h, u"1小时"),
        (TYPE_4h, u"4小时"),
        (TYPE_12h, u"12小时"),
        (TYPE_1d, u"1天"),
        (TYPE_3d, u"3天"),
        (TYPE_7d, u"7天"),
        (TYPE_CUSTOMIZED, u"自定义"),
    )


@dataclass
class SaaSPackageInfo:
    version: str
    url: str
    name: str


# 蓝鲸桌面中应用国际化相关的字段 Fields
I18N_FIELDS_IN_CONSOLE: List[str] = ["introduction_en", "name_en"]
