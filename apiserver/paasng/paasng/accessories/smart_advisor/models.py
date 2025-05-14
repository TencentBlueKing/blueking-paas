# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
from django.conf import settings
from django.db import models
from django.utils import timezone
from jsonfield import JSONField
from translated_fields import TranslatedFieldWithFallback

from paasng.core.tenant.fields import tenant_id_field_factory

from .constants import DeployFailurePatternType
from .tags import get_default_tagset, get_dynamic_tag


class AppModuleTagManager(models.Manager):
    """Manager for module tag"""

    def get_tags(self, app_module):
        """Tag tags on given module"""
        qs = self.get_queryset().filter(module=app_module)
        return set(get_default_tagset().get_tags([item.tag_str for item in qs]))

    def tag_module(self, app_module, tags, source="default"):
        """Tag tags on given module"""
        get_default_tagset().validate_tags(tags)
        for tag in tags:
            self.get_queryset().update_or_create(
                module=app_module, tag_str=str(tag), defaults={"source": source, "tenant_id": app_module.tenant_id}
            )

    def cleanup_module(self, app_module):
        """Clean up all tags on given module"""
        self.get_queryset().filter(module=app_module).delete()


class AppModuleTagRel(models.Model):
    """A M2M relationship table for storing the relationship between application module and AppTag"""

    module = models.ForeignKey(
        "modules.Module", on_delete=models.CASCADE, db_constraint=False, related_name="tag_rels"
    )
    tag_str = models.CharField(max_length=128, blank=False)
    source = models.CharField(max_length=32, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    tenant_id = tenant_id_field_factory()

    objects = AppModuleTagManager()

    class Meta:
        unique_together = ("module", "tag_str")


# Shortcut functions
get_tags = AppModuleTagRel.objects.get_tags
tag_module = AppModuleTagRel.objects.tag_module
cleanup_module = AppModuleTagRel.objects.cleanup_module


class DocumentaryLink(models.Model):
    """Links from document systems including blueking doc and other open-source documentations

    [multi-tenancy] This model is not tenant-aware.
    """

    title = TranslatedFieldWithFallback(models.CharField(max_length=256, blank=False))
    short_description = TranslatedFieldWithFallback(models.CharField(max_length=512, blank=True))
    location = models.CharField(max_length=256, blank=False)
    affinity_tags = JSONField(max_length=256, blank=True, default=[])
    anti_affinity_tags = JSONField(max_length=256, blank=True, default=[])
    priority = models.IntegerField(default=1)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

    def get_affinity_tags(self):
        return [get_dynamic_tag(s) for s in self.affinity_tags]

    def get_affinity_tags_by_type(self, tag_type):
        return [tag for tag in self.get_affinity_tags() if tag.tag_type == tag_type]

    @property
    def format_location(self) -> str:
        return self.location.format(paas_doc_url_prefix=settings.PAAS_DOCS_URL_PREFIX)


class DeployFailurePattern(models.Model):
    """Stores common failure patterns for failed deployments.

    [multi-tenancy] This model is not tenant-aware.
    """

    type = models.IntegerField(default=DeployFailurePatternType.REGULAR_EXPRESSION)
    value = models.CharField(max_length=2048, blank=False)
    tag_str = models.CharField(max_length=128, blank=False)
    created = models.DateTimeField(default=timezone.now)
