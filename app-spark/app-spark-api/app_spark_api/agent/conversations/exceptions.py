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

"""会话自身的失败，与 Agent Runtime 的失败（见 :mod:`app_spark_api.agent.runtime.exceptions`）分开。

区别在于该怪谁：Runtime 那边报的是「拉起来的东西不好用」，这里报的是「这个会话现在不允许这么
干」——重试同一个请求永远不会变好，除非会话本身换了状态。
"""


class ConversationClosedError(Exception):
    """会话已经结束了，不能再推进，也不能再结束一次。

    结束是终态：一个会话的历史仍然可读，但它不再接受新的一轮对话。
    """
