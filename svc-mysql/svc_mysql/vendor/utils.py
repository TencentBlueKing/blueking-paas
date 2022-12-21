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
