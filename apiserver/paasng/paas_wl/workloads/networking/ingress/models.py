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

import re

from blue_krill.models.fields import EncryptField
from django.core.validators import RegexValidator
from django.db import models

from paas_wl.bk_app.applications.models import AuditedModel, WlApp
from paas_wl.bk_app.applications.relationship import ModuleAttrFromID, ModuleEnvAttrFromID
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.utils.models import TimestampedModel
from paas_wl.utils.text import DNS_SAFE_PATTERN
from paas_wl.workloads.networking.ingress.constants import AppSubpathSource
from paasng.core.tenant.user import DEFAULT_TENANT_ID


class AppDomain(AuditedModel):
    """Domains of applications, each object(entry) represents an (domain + path_prefix) pair."""

    app = models.ForeignKey(WlApp, on_delete=models.CASCADE)
    # TODO: The region field is not used anymore, remove it in the next release
    region = models.CharField(max_length=32)
    host = models.CharField(max_length=128)

    # This field was designed for supported `path_prefix` customization, but only '/' (or None)
    # values are currently used.
    path_prefix = models.CharField(max_length=64, default="/", help_text="the accessible path for current domain")

    # HTTPS related fields
    https_enabled = models.BooleanField(default=False)
    https_auto_redirection = models.BooleanField(default=False)
    # "cert" field has higher priority than auto selected "shared cert"
    cert = models.ForeignKey("AppDomainCert", null=True, on_delete=models.SET_NULL)
    shared_cert = models.ForeignKey("AppDomainSharedCert", null=True, on_delete=models.SET_NULL)

    # See `AppDomainSource` for possible values
    source = models.IntegerField(help_text="数据来源分类")
    tenant_id = models.CharField(
        verbose_name="租户 ID", max_length=32, default=DEFAULT_TENANT_ID, help_text="本条数据的所属租户"
    )

    def has_customized_path_prefix(self) -> bool:
        """Check if current domain has configured a custom path prefix"""
        return self.path_prefix != "/"

    def __str__(self) -> str:
        return f"<AppDomain: https_enabled={self.https_enabled} host={self.host}>"

    class Meta:
        unique_together = ("tenant_id", "host", "path_prefix")
        db_table = "services_appdomain"


class BasicCert(AuditedModel):
    # TODO: The region field is not used anymore, remove it in the next release
    region = models.CharField(max_length=32)
    tenant_id = models.CharField(
        verbose_name="租户 ID", max_length=32, default=DEFAULT_TENANT_ID, help_text="本条数据的所属租户"
    )
    name = models.CharField(max_length=128, validators=[RegexValidator(DNS_SAFE_PATTERN)])
    cert_data = EncryptField()
    key_data = EncryptField()

    class Meta:
        abstract = True

    type: str = ""

    def get_secret_name(self) -> str:
        return f"eng-{self.type}-{self.name}"


class AppDomainCert(BasicCert):
    """WlApp's TLS Certifications, usually managed by user"""

    type = "normal"

    class Meta:
        db_table = "services_appdomaincert"
        unique_together = ("tenant_id", "name")


class AppDomainSharedCert(BasicCert):
    """Shared TLS Certifications for AppDomain, every app's domain may link to this certificate as
    long as the domain matched the certificate's common names.
    """

    # Multiple CN are seperated by ";", for example: "foo.com;*.bar.com"
    auto_match_cns = models.TextField(max_length=2048)

    type = "shared"

    class Meta:
        db_table = "services_appdomainsharedcert"
        unique_together = ("tenant_id", "name")

    def match_hostname(self, hostname: str) -> bool:
        """Check if current certificate object matches the given hostname

        :param hostname: hostname to be checked, such as "foo.com".
        :return: True if matched, False otherwise.
        """
        for cn in self.auto_match_cns.split(";"):
            # CN format: foo.com / *.bar.com
            pattern = re.escape(cn).replace(r"\*", r"[a-zA-Z0-9-]+")
            if re.match(f"^{pattern}$", hostname):
                return True
        return False


class AppSubpathManager(models.Manager):
    def create_obj(self, app: WlApp, subpath: str, source=AppSubpathSource.DEFAULT) -> "AppSubpath":
        """Create an subpath object."""
        cluster = get_cluster_by_app(app)
        return self.get_queryset().create(
            app=app, tenant_id=app.tenant_id, cluster_name=cluster.name, subpath=subpath, source=source
        )


class AppSubpath(AuditedModel):
    """stores application's subpaths"""

    app = models.ForeignKey(WlApp, on_delete=models.CASCADE, db_constraint=False)
    # TODO: The region field is not used anymore, remove it in the next release
    region = models.CharField(max_length=32)
    cluster_name = models.CharField(max_length=32)
    subpath = models.CharField(max_length=128)
    source = models.IntegerField()
    tenant_id = models.CharField(
        verbose_name="租户 ID", max_length=32, default=DEFAULT_TENANT_ID, help_text="本条数据的所属租户"
    )

    objects = AppSubpathManager()

    def __str__(self) -> str:
        return f"<AppSubpath: subpath={self.subpath}>"

    class Meta:
        unique_together = ("tenant_id", "subpath")
        db_table = "services_appsubpath"


# PaaS "custom domain"(end-user) model start


class Domain(TimestampedModel):
    """The custom domains of applications."""

    name = models.CharField(help_text="域名", max_length=253, null=False)
    path_prefix = models.CharField(max_length=64, default="/", help_text="the accessible path for current domain")
    module_id = models.UUIDField(help_text="关联的模块 ID", null=False)
    environment_id = models.BigIntegerField(help_text="关联的环境 ID", null=False)
    https_enabled = models.BooleanField(default=False, null=True, help_text="该域名是否开启 https")
    tenant_id = models.CharField(
        verbose_name="租户 ID", max_length=32, default=DEFAULT_TENANT_ID, help_text="本条数据的所属租户"
    )

    module = ModuleAttrFromID()
    environment = ModuleEnvAttrFromID()

    class Meta:
        unique_together = ("tenant_id", "name", "path_prefix", "module_id", "environment_id")
        db_table = "services_domain"

    @property
    def protocol(self) -> str:
        return "https" if self.https_enabled else "http"

    def has_customized_path_prefix(self) -> bool:
        """Check if current domain has configured a custom path prefix"""
        return self.path_prefix != "/"

    def __str__(self):
        return f"module={self.module_id}-{self.name}"


# PaaS "custom domain"(end-user) model end
