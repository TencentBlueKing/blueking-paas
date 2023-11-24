# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""为了更好的对蓝鲸平台进行解耦，对于蓝鲸应用来说，其基本功能：包括发布、部署等等，应该和
牵扯到蓝鲸用户体系的功能模块区分开来。

但目前的处理方式也是有一些问题的。paasng 本身不应该直接修改 OAuth2 体系下的任何内容。
而是应该调用 OAuth2 Server（当前集成在 bk_api_gateway） 服务。

## Q：新的数据结构为何兼容旧数据？

采用数据库 trigger 方式，将新数据往旧数据表中同步。
"""
from blue_krill.models.fields import EncryptField
from django.db import models

from paasng.utils.models import TimestampedModel


class OAuth2Client(TimestampedModel):
    """OAuth2 体系中的基本单位：Client

    settings.ENABLE_BK_OAUTH 为 True 时，则不再使用该表，Auth 相关的数据直接调用 BKAuth 服务提供的 API。
    """

    client_id = models.CharField(verbose_name="应用编码", max_length=20, unique=True)
    client_secret = EncryptField(verbose_name="安全密钥")


class BkAppSecretInEnvVar(TimestampedModel):
    """
    环境变量默认密钥：内置环境变量 BKPAAS_APP_SECRET 使用的密钥
    """

    bk_app_code = models.CharField(max_length=20, unique=True)
    bk_app_secret_id = models.IntegerField(verbose_name="应用密钥的 ID", help_text="不存储密钥的信息，仅存储密钥 ID")

    def __str__(self) -> str:
        return f"[{self.bk_app_code}]{self.bk_app_secret_id}"
