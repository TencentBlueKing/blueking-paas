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
from typing import List

from attrs import define
from django.db import models
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from paas_wl.platform.applications.models import EngineApp, UuidAuditedModel
from paas_wl.platform.applications.struct_models import Application


class AppImageCredentialManager(models.Manager):
    @atomic
    def flush_from_refs(self, application: Application, engine_app: EngineApp, references: List['ImageCredentialRef']):
        """flush all AppImageCredentials for given 'engine_app' by the ImageCredentialRefs,
        will delete all outdated/not-used AppImageCredentials"""
        all_images = [ref.image for ref in references]
        # delete outdated/not-used image credentials, incase the secret size infinite inflate
        self.filter(app=engine_app).exclude(registry__in=all_images).delete()
        for ref in references:
            pair = AppUserCredential.objects.get(application_id=application.id, name=ref.credential_name)
            AppImageCredential.objects.update_or_create(
                app=engine_app, registry=ref.image, defaults={"username": pair.username, "password": pair.password}
            )


class AppImageCredential(UuidAuditedModel):
    """ImageCredential of applications, each object(entry) represents an (username + password) pair for a registry"""

    app = models.ForeignKey("api.App", on_delete=models.CASCADE, db_constraint=False)

    registry = models.CharField(max_length=255)
    username = models.CharField(max_length=32, blank=False)
    password = models.CharField(max_length=255, blank=True)

    objects = AppImageCredentialManager()

    class Meta:
        unique_together = ('app', 'registry')


class AppUserCredentialManager(models.Manager):
    def list_all_name(self, application: Application) -> List[str]:
        return list(self.filter(application_id=application.id).values_list("name", flat=True))


class AppUserCredential(UuidAuditedModel):
    """App owned UserCredential, aka (Username + Password) pair"""

    application_id = models.UUIDField(verbose_name=_('所属应用'), null=False)

    name = models.CharField(max_length=32, help_text="凭证名称")
    username = models.CharField(max_length=64, help_text="账号")
    password = models.CharField(max_length=255, help_text="密码")
    description = models.TextField(help_text="描述")

    objects = AppUserCredentialManager()

    class Meta:
        unique_together = ('application_id', 'name')


@define
class ImageCredentialRef:
    image: str
    credential_name: str
