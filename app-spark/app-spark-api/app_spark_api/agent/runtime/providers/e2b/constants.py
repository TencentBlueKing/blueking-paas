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

"""Timeouts for provisioning, starting, stopping, and renewing an E2B sandbox."""

# 创建沙箱并绑定到占位这一整步的上限。限的是整步而不是单个请求，因为 SDK 会重试被限流的请求；
# 只有整步有上限，才能把一个早已没人管的未绑定占位，和一个还在创建中的占位区分开。
PROVISION_TIMEOUT_SECONDS = 120

# 未绑定的占位超过这个时长，说明创建它的 worker 在半路死掉了。多出的余量用来覆盖限时步骤前后的
# 数据库写入，以及各 worker 之间的时钟偏差。
ABANDONED_CLAIM_SECONDS = PROVISION_TIMEOUT_SECONDS + 60

# 已绑定的占位，超过启动超时再加这个余量仍没记下 Agent 已启动，说明启动它的 worker 在半路死掉了。
# 余量用来覆盖打开命令事件流、读取失败日志，以及各 worker 之间的时钟偏差。
STARTUP_GRACE_MARGIN_SECONDS = 60

# 每次 /health 探测都要经过 E2B 端口代理，所以给的时间比回环地址上的探测长；整段等待仍受
# E2BConfig.startup_timeout_seconds 限制。
HEALTH_POLL_INTERVAL_SECONDS = 0.5
HEALTH_PROBE_TIMEOUT_SECONDS = 3.0

# Agent 启动失败时，回传它自己日志末尾的多少行。配置错误会让它在 import 阶段就退出，那段 traceback
# 是唯一能说明原因的东西。
LOG_TAIL_LINES = 40

# 复用沙箱时，Agent 进程还在却不应答 /health，按这个次数、这个间隔探测，仍不应答才判定它不可用。
# 经端口代理的一次探测可能只是偶发失败，而换掉沙箱要让用户多等一次冷启动，还可能掐掉另一个标签页
# 正在跑的一轮。
REUSE_HEALTH_ATTEMPTS = 3
REUSE_HEALTH_RETRY_INTERVAL_SECONDS = 1.0

# 结束会话最多花多久，重连、发信号、等 Agent 退出都算在内，只有最后那次 kill 另算。Agent 有序关停
# 最多要 1 秒断连接、8 秒推送加回写、5 秒停应用子进程（见 agent settings 里的
# SHUTDOWN_DRAIN_TIMEOUT_SECONDS），剩下的留给重连。
STOP_GRACE_SECONDS = 20

# 沙箱里的停止命令每隔多久看一次 Agent 退出了没有。
STOP_POLL_INTERVAL_SECONDS = 0.2

# 等完 Agent 之后那次 kill 请求的上限，让结束会话的耗时贴近 STOP_GRACE_SECONDS，而不是 SDK 默认的
# 60 秒请求超时。
KILL_REQUEST_TIMEOUT_SECONDS = 5.0

# 一次续期的上限，SDK 自带的重试也算在内。续期挡在一轮的开头和结尾，控制面卡住时，不限时就会让
# 这一轮跟着多等一分钟。
RENEW_TIMEOUT_SECONDS = 5.0
