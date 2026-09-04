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

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from app_spark_api.agent.conversations.models import ConversationNumber
from app_spark_api.core.projects.models import Project


@receiver(post_save, sender=Project, dispatch_uid="conversations.create_conversation_number")
def create_conversation_number(
    sender: type[Project],
    instance: Project,
    created: bool,
    raw: bool = False,
    **kwargs: Any,
) -> None:
    """给刚建出来的 Project 备好会话计数器。

    在这里建，而不是等第一次开会话时再建：取号跑在事务里，若那时才去插这一行，同一个 Project
    的并发首次建会话就会变成几个事务各自握着锁去抢插同一个主键。
    """
    # `raw` 表示 loaddata 正在灌固件数据，此时不该派生任何附加数据。
    if created and not raw:
        ConversationNumber.objects.create(project=instance)
