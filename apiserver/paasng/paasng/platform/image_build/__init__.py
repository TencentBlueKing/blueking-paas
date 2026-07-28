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

"""平台级镜像构建公共层。

背景：镜像构建能力最初实现在 agent_sandbox 模块中（KanikoBuildExecutor、ImageBuildRecord 等），
服务于 AgentSandbox 场景的沙箱镜像构建。随着 SandboxInstance（基于 CR 的长期运行 AI Agent 应用）
场景引入，sidecar 容器镜像同样需要 Kaniko 构建能力。

为避免将 agent_sandbox 的内部实现直接暴露给其他模块，同时避免复杂的 Django migration 迁移，
本包作为公共层对外提供统一的 re-export 入口：
- builder.py  -> KanikoBuildExecutor（Kaniko 构建执行器）
- constants.py -> ImageBuildStatus / ImageType（构建状态与类型枚举）

各业务模块（agent_sandbox、sandbox_instance）通过本公共层引用构建基础设施，
而非直接跨模块 import，以保持模块间的解耦。
"""
