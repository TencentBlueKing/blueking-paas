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

"""Starting something on a conversation's Runtime: a turn, or the workspace application's preview.

Both bring the Runtime up if needed and resume it the same way before asking it for anything;
what they share is in :mod:`app_spark_api.agent.conversations.lifecycle.utils`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from asgiref.sync import sync_to_async

from app_spark_api.agent.conversations.attachments import (
    acheck_run_attachments,
    ahas_sent_attachments,
    build_attachment_uri,
)
from app_spark_api.agent.conversations.exceptions import ConversationClosedError, ModelImageInputUnsupportedError
from app_spark_api.agent.conversations.lifecycle.utils import (
    CLOSED_MESSAGE,
    reject_if_closed_meanwhile,
    resume_if_cold,
)
from app_spark_api.agent.conversations.models import ConversationUserMessage
from app_spark_api.agent.conversations.services import open_client
from app_spark_api.agent.model_catalog.services import list_models, resolve_run_model_id
from app_spark_api.agent.runtime import AgentWorkspaceSavePendingError
from app_spark_api.agent.runtime.entities import ImageInput

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from app_spark_api.agent.conversations.models import Conversation
    from app_spark_api.agent.runtime import AgentRun, AgentRuntimeClient, PreviewStartOutcome, RuntimeHealth
    from app_spark_api.infras.bk_access_token import UserCredential

logger = logging.getLogger(__name__)


async def start_run(
    conversation: Conversation,
    *,
    content: str,
    credential: UserCredential | None = None,
    model_id: str | None = None,
    attachment_ids: Sequence[UUID] = (),
) -> AgentRun:
    """Submit one turn and return its open event stream.

    The context version is read from ``/health`` immediately before the run rather than
    remembered between turns. Compaction can move it in the middle of a run, so a version
    carried over from the previous turn is not merely stale, it is wrong often enough to matter.

    :param conversation: Conversation the turn belongs to.
    :param content: The user's message; may be empty when the turn carries attachments.
    :param credential: The caller's BlueKing login, passed to :func:`~app_spark_api.agent.conversations.services.open_client`.
    :param model_id: The model this turn asked for; None runs it on the Runtime's default.
    :param attachment_ids: Images sent with this turn, in the order the user attached them.
    :return: The accepted run, whose bytes are still to come.
    :raises ConversationClosedError: If the conversation has been closed.
    :raises ModelNotAvailableError: If the model list does not offer model_id.
    :raises AttachmentNotFoundError: If an attachment is not the conversation's.
    :raises AttachmentAlreadyUsedError: If an attachment was already sent with another turn.
    :raises ModelImageInputUnsupportedError: If the turn carries images its model cannot read.
    :raises AgentBusyError: If a run is already occupying the Runtime.
    :raises AgentProvisionError: If no Runtime could be brought up.
    :raises ModelAccessConfigurationError: If the model source or its settings are invalid, or
        no model is left to run on.
    :raises ModelCredentialMissingError: If bkaidev needs the caller's login, to check
        model_id or to start a Runtime, and credential is None.
    :raises AccessTokenUnavailableError: If the caller's access_token could not be obtained.
    :raises BkAidevGatewayError: If the gateway could not give the model list.
    :raises AgentUnavailableError: If the Runtime cannot be reached or refuses the turn.
    """
    # 这道闸门是「结束会话」有意义的前提。没有它，结束一个会话只是杀掉了一个进程：下一轮对话
    # 会照常把 Runtime 重新拉起来，被回收的 workspace 也会被重新占上。
    if not conversation.is_live:
        raise ConversationClosedError(CLOSED_MESSAGE.format(id=conversation.id))

    # 模型不可用时在拉起沙箱、写入用户消息之前就拒掉：这一轮本来就不会发生，不该为它付启动成本，
    # 也不该在历史里留一条没有回答的输入。
    forwarded_model_id = await resolve_run_model_id(model_id, credential)

    # 附件归属和模型能力同理，在拉起沙箱之前查。绑定时还会在锁下复查一次归属。
    run_attachments = await acheck_run_attachments(conversation, attachment_ids)
    image_input = await _check_image_input(conversation, model_id, credential, sends_images=bool(run_attachments))

    client, health = await _open_resumed_client(conversation, credential)
    logger.info(
        "Conversation %s runtime health at %s: model_ready=%s model=%s context_version=%s "
        "dev_server_status=%s running=%s",
        conversation.id,
        client.handle.base_url,
        health.model_ready,
        health.model,
        health.context_version,
        health.dev_server_status,
        health.running,
    )

    # run_id 在请求 Runtime 之前就随消息落库。Runtime 一接受，/health 就会报出这个 run_id，前端随即可以
    # 拿它来停；要是等 Runtime 应答后再补写，这中间 stop_run 的归属校验会把一个真实的 run 当成不存在。
    # 落库在前，也就不会因为浏览器断开或任务取消而丢掉用户输入与 run 的关联。
    run_id = str(uuid4())
    message = await sync_to_async(ConversationUserMessage.objects.create_for_conversation)(
        conversation, content=content, run_id=run_id, attachment_ids=attachment_ids
    )
    try:
        run = await client.start_run(
            content=content,
            context_version=health.context_version,
            run_id=run_id,
            model_id=forwarded_model_id,
            # 只传引用不传字节，Agent 每次调模型前再经内部接口取图。
            images=[
                ImageInput(url=build_attachment_uri(attachment.id), mime_type=attachment.mime_type)
                for attachment in run_attachments
            ],
            image_input=image_input,
        )
    except AgentWorkspaceSavePendingError as exc:
        # 409 不会进 API 的异常日志，而页面上的文案是固定的，沙箱地址和 Runtime 的说明只在这里。
        logger.warning(
            "Conversation %s at %s refused the run because the previous turn is not saved yet: %s",
            conversation.id,
            client.handle.base_url,
            exc,
        )
        await message.adelete()
        raise
    except BaseException:
        # Runtime 拒绝的请求不应留在历史里；输入必须先于调用创建，才不会把本轮新事件算入游标。
        await message.adelete()
        raise

    logger.info(
        "Conversation %s accepted run %s at %s",
        conversation.id,
        run.run_id,
        client.handle.base_url,
    )
    return run


async def start_preview(
    conversation: Conversation, *, credential: UserCredential | None = None
) -> PreviewStartOutcome:
    """Bring the conversation's Runtime up if needed, and ask it to start the workspace application.

    The one read-side action that does provision a Runtime. Reading a conversation stays free;
    this is for a client that has decided the user is about to look at the preview -- typically
    on entering a Project whose code was written in an earlier session, when no turn is coming
    that would make the model launch it. The web client calls it on entering any live
    conversation, so that cost is paid for browsing too; see the preview section of docs/misc.md.

    The Runtime is resumed the way a turn resumes it, files and context both, before the start
    is asked for: the application is started from whatever is on disk, and a Runtime warmed here
    is one the user's next message does not have to wait for. Returns once the start is under
    way; installing a freshly restored project's dependencies can take minutes, and
    ``dev_server_status`` on :func:`~app_spark_api.agent.conversations.services.get_state` or the preview is what follows it.

    Example::

        outcome = await start_preview(conversation, credential=get_user_credential(request))
        # then poll services.get_dev_server_status(conversation) until it reads "ready"

    :param conversation: Conversation whose application is to be previewed.
    :param credential: The caller's BlueKing login, passed to :func:`~app_spark_api.agent.conversations.services.open_client`.
    :return: Whether a start is under way, or the workspace has no project to start yet.
    :raises ConversationClosedError: If the conversation has been closed.
    :raises AgentPreviewPortTakenError: If a process the Runtime did not start holds the port.
    :raises AgentUnavailableError: If the Runtime cannot be reached, or its files cannot be restored.
    :raises AgentProvisionError: Along with everything else :func:`~app_spark_api.agent.conversations.services.open_client` raises.
    """
    # 和 start_run 同一道闸门：已结束的会话交还了 workspace，看预览也不能把它重新占上。
    if not conversation.is_live:
        raise ConversationClosedError(CLOSED_MESSAGE.format(id=conversation.id))

    client, _health = await _open_resumed_client(conversation, credential)

    outcome = await client.start_preview()
    logger.info("Conversation %s asked its Agent Runtime to start the preview: %s", conversation.id, outcome)
    return outcome


async def _check_image_input(
    conversation: Conversation,
    model_id: str | None,
    credential: UserCredential | None,
    *,
    sends_images: bool,
) -> bool:
    """Return whether this turn's model may be handed the conversation's images.

    :param conversation: Conversation the turn belongs to.
    :param model_id: The model the turn asked for; None means the catalog's default model.
    :param credential: The caller's BlueKing login, needed to read the bkaidev model list.
    :param sends_images: Whether this turn itself carries images.
    :return: False when the model cannot read images, so the Runtime sends none of them.
    :raises ModelImageInputUnsupportedError: If this turn carries images its model cannot read.
    """
    # 会话里从没发过图，就没有图会被发给模型，纯文字对话不必为此多查一次模型列表。
    if not sends_images and not await ahas_sent_attachments(conversation):
        return True

    # Runtime 会把最近几轮的历史图片也发给模型，所以本轮没带图也要看模型能不能读图：
    # 上一轮在多模态模型上发了图、这一轮换成纯文本模型时，图片不能跟着发过去。
    catalog = await list_models(credential)

    # 不选模型时按列表的默认模型判断：沙箱的 MODEL_ID 由 resolve_model_access 取同一个默认模型，
    # 改了一边就要同步改另一边。
    effective_model_id = model_id or catalog.default_model_id

    # 列表里找不到也按不支持处理：说不清能不能看图的模型，宁可不发图，也不让模型调用因此失败。
    option = next((model for model in catalog.models if model.id == effective_model_id), None)
    supports_vision = option is not None and option.supports_vision

    # 本轮自己带的图被拒绝而不是换成占位：用户会拿到一个无视了图片的回答，却不知道为什么。
    if sends_images and not supports_vision:
        raise ModelImageInputUnsupportedError(f"Model {effective_model_id!r} does not support image input")

    return supports_vision


async def _open_resumed_client(
    conversation: Conversation, credential: UserCredential | None
) -> tuple[AgentRuntimeClient, RuntimeHealth]:
    """Bring the conversation's Runtime up and resume it if cold, for :func:`start_run` and :func:`start_preview`.

    :return: The client, and the health to work against once any resume is done.
    """
    client = await open_client(conversation, credential=credential)

    # 先回库确认会话还活着，再读 client。open_client 要花好几秒，这中间会话可能已被关掉；
    # 确认没过会收掉刚拉起来的 Runtime 并返回 409。先碰 client.handle 会把这次拒绝变成 500。
    await reject_if_closed_meanwhile(conversation)

    logger.info(
        "Conversation %s is using the Agent Runtime at %s",
        conversation.id,
        client.handle.base_url,
    )
    health = await resume_if_cold(conversation, client, await client.health())
    return client, health
