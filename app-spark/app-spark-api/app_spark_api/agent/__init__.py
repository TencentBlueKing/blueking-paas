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

"""让 Agent 替用户干活的那一整块，分成上下两层：

* :mod:`~app_spark_api.agent.conversations` 是领域层，也是唯一的 Django app：会话属于哪个
  Project、编号是几、对外的 HTTP 接口长什么样。
* :mod:`~app_spark_api.agent.runtime` 是设施层：Agent Runtime 在哪里跑、怎么把它拉起来、
  怎么跟它说话。上层只认这一层给出的抽象，因此本机进程换成远程沙箱时，上层不必改。
"""
