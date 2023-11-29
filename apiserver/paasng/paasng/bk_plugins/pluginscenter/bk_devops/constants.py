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
from blue_krill.data_types.enum import EnumField, StructuredEnum


class PipelineBuildStatus(str, StructuredEnum):
    """蓝盾流水线构建状态"""

    # 由于蓝盾接口文档未提供所有枚举值, 因此这里只列举目前已知的状态

    SUCCEED = EnumField("SUCCEED", label="成功")
    FAILED = EnumField("FAILED", label="失败")
    CANCELED = EnumField("CANCELED", label="已取消")
