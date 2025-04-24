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

from django.db import transaction
from paas_service.models import ResourceId
from paas_service.utils import Base36Handler


def gen_unique_id(name: str, namespace: str = "default", max_length: int = 16, divide_char: str = "-"):
    """Generate an unique id via given name"""
    with transaction.atomic():
        # create a db instance for getting auto increment id
        resource_id = ResourceId.objects.create(namespace=namespace, uid=name)
        # use base 62 to shorten resource id
        encoded_resource_id = Base36Handler.encode(resource_id.id)

        # as default, restrict the length
        prefix = name[: max_length - len(str(encoded_resource_id)) - len(divide_char)]

        # update uid
        # example: "origin" + "-" + "aj"
        uid = prefix + divide_char + str(encoded_resource_id)
        resource_id.uid = uid
        resource_id.save(update_fields=["uid"])

    return resource_id.uid


def gen_addons_cert_mount_path(provider_name: str, cert_name: str) -> str:
    """生成蓝鲸应用挂载增强服务 ssl 证书的路径
    重要：不要随意调整该路径，可能会导致证书无法正常挂载（需要与 ApiServer 侧同步调整）

    :param provider_name: 增强服务提供者名称，如：redis，mysql，rabbitmq（也可能与 Service 同名）
    :param cert_name: 证书名称，必须是 ca.crt，tls.crt，tls.key 三者之一
    """
    if not provider_name:
        raise ValueError("provider_name is required")

    if cert_name not in ["ca.crt", "tls.crt", "tls.key"]:
        raise ValueError("cert_name must be one of ca.crt, tls.crt, tls.key")

    return f"/opt/blueking/bkapp-addons-certs/{provider_name}/{cert_name}"
