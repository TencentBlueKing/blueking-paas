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

    一个蓝鲸应用如果选择接入蓝鲸用户体系，那么就需要为其创建 OAuth2 体系中的 Client。
    事实上，这个行为目前是默认发生的。
    """

    client_id = models.CharField(verbose_name=u'应用编码', max_length=20, unique=True)
    client_secret = EncryptField(verbose_name=u"安全密钥")
