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

"""
被 paasng/infras/legacydb_te/adaptors.py 引用
"""
from paasng.utils.basic import ChoicesEnum


class LegacyAppState(ChoicesEnum):
    """命名保持跟 PaaS2.0 一致，方便核对"""

    OUTLINE = 0
    DEVELOPMENT = 1
    TEST = 3
    ONLINE = 4
    IN_TEST = 8
    IN_ONLINE = 9
    IN_OUTLINE = 10

    _choices_labels = (
        (OUTLINE, '已下架'),
        (DEVELOPMENT, '开发中'),
        (TEST, '测试中'),
        (ONLINE, '已上线'),
        (IN_TEST, '正在提测'),
        (IN_ONLINE, '正在上线'),
        (IN_OUTLINE, '正在下架'),
    )
