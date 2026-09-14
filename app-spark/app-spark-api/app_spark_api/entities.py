# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""API 层共用的 schema，放在这里而不是某个具体模块的 `entities.py` 里。

只收那些每个模块都会用到、且形状不该各自发明一遍的东西。错误响应就是典型：让 projects 和
conversations 各自定义一个字段一模一样的 `ErrorResponse`，除了让 OpenAPI 文档里多出几个同名
不同源的 schema 之外没有任何好处。
"""

from ninja import Field, Schema


class ErrorResponse(Schema):
    """一次失败的请求，`detail` 是可以直接展示给调用方的说明。"""

    detail: str = Field(description="面向调用方的错误描述，可直接展示")
