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

"""本服务自己调大模型的高层入口。

两层结构，这里是上层：
- infras.llm：和大模型的具体交互，只接收显式传入的配置对象，不读 settings；
- ext.llm：按 settings 构造配置和客户端（config），以及基于它的业务能力，例如给项目起名（int_renaming）。
"""

from app_spark_api.ext.llm.config import LLMSource, build_llm_client, get_llm_config, requires_access_token

__all__ = ["LLMSource", "build_llm_client", "get_llm_config", "requires_access_token"]
