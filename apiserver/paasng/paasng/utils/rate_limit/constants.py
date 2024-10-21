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

from blue_krill.data_types.enum import IntStructuredEnum


class UserAction(IntStructuredEnum):
    """
    用于频率限制的用户操作

    Q: 为什么需要有 UserAction 这个枚举类，而不是根据需要传入操作名称，或者直接使用函数名作为标识？
    A: 传入操作名称或使用函数名作为标识，都可能出现重名的情况，这时它们将共享频率限制配额，可能埋下隐患
       使用枚举类则可以避免这个问题，新增限制时需要先检查是否有重名的 Action，避免共享配额
       反之亦然，如果希望共享频率限制配额，则可以使用相同的枚举值
    Q：为什么使用整数作为枚举值，生成的 redis key 可读性不佳？
    A：讨论参见：https://github.com/TencentBlueKing/blueking-paas/pull/271#discussion_r1139562569
    """

    FETCH_DEPLOY_LOG = 1
    WATCH_PROCESS = 2
