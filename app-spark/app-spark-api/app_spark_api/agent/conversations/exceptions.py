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


class InvalidHistoryCursorError(Exception):
    """翻历史时带来的游标不是本服务签发的，或者签发格式已经换掉了。"""


class RunNotFoundError(Exception):
    """这个会话里没有这一轮：run_id 不是本会话接受过的某一轮对话。"""


class RunNotInProgressError(Exception):
    """这一轮属于这个会话，但此刻没有在跑：已经结束了，或者它所在的 Runtime 已经不在了。"""


class AttachmentNotFoundError(Exception):
    """附件不存在，或者不属于这个会话。两种情况对调用方是一回事，不区分。"""


class AttachmentAlreadyUsedError(Exception):
    """附件已经被某一轮对话引用过，一张附件只能随一轮发出。"""


class AttachmentTooLargeError(Exception):
    """上传的文件超过了单个附件的大小上限。"""


class AttachmentTypeUnsupportedError(Exception):
    """上传的文件按文件头识别不是允许的图片类型。"""


class AttachmentStorageError(Exception):
    """附件存储写不进去或读不出来。与请求内容无关，稍后重试可能恢复。"""


class ModelImageInputUnsupportedError(Exception):
    """这一轮带了图片，但本轮所用的模型不支持图片输入。"""
