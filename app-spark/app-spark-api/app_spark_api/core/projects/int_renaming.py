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

"""从一句话创建项目后的自动命名：真正执行一次命名并把结论写回去。

任务的建记录、换 token、投递与 worker 入口都在 ``tasks``；这里只关心「拿到模型客户端之后怎么命名」，
方便脱离 broker 直接测。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app_spark_api.core.projects.models import Project, ProjIntRenaming
from app_spark_api.ext.llm.int_renaming import generate_project_name
from app_spark_api.infras.llm import LLMError

if TYPE_CHECKING:
    from app_spark_api.infras.llm import LLMClient

logger = logging.getLogger(__name__)

# 不是 LLMError 的意外失败，错误文本可能带上网关地址等运维信息，只写一句通用的话。
UNEXPECTED_ERROR_MESSAGE = "Unexpected error while generating a project name."


async def run(project_id: str, *, llm: LLMClient) -> None:
    """执行一次命名并把结论写回数据库。

    任务可能因 broker 重投而跑第二次；记录已结束时直接返回，不再调模型。

    :param project_id: 要命名的项目。
    :param llm: 用来起名的模型。
    """
    project = await Project.objects.filter(pk=project_id).afirst()
    if project is None:
        # 项目在任务执行前被删掉了，没有需要命名的东西。
        logger.info("Project %s is gone, skipping int renaming", project_id)
        return

    record = await ProjIntRenaming.objects.filter(project_id=project_id).afirst()
    if record is None:
        logger.warning("Project %s has no int-renaming record, skipping", project_id)
        return
    if record.is_finished:
        return

    if not project.initial_prompt.strip():
        # 建项目的接口已经拒绝了纯空白，这里只是兜底：没有起名素材，按「无需起名」结束。
        await record.complete(None)
        return

    try:
        name = await generate_project_name(project.initial_prompt, llm=llm)
    except LLMError as exc:
        # LLMError 的文案对运维安全，可以原样留给排查。
        await record.fail(str(exc))
        return
    except Exception:
        logger.exception("Generating a name for project %s failed unexpectedly", project_id)
        await record.fail(UNEXPECTED_ERROR_MESSAGE)
        return

    await record.complete(name)
