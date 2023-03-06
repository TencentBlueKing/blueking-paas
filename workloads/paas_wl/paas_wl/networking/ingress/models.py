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
from dataclasses import dataclass

from django.core.validators import RegexValidator
from django.db import models

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.constants import AppDomainSource, AppSubpathSource
from paas_wl.platform.applications.models import AuditedModel, WlApp
from paas_wl.platform.applications.struct_models import ModuleAttrFromID, ModuleEnvAttrFromID
from paas_wl.utils.constants import make_enum_choices
from paas_wl.utils.models import TimestampedModel
from paas_wl.utils.text import DNS_SAFE_PATTERN


@dataclass
class AutoGenDomain:
    """Domain object for application's auto-generated custom subdomains"""

    host: str
    https_enabled: bool = False


class AppDomain(AuditedModel):
    """Domains of applications, each object(entry) represents an (domain + path_prefix) pair."""

    app = models.ForeignKey(WlApp, on_delete=models.CASCADE)
    region = models.CharField(max_length=32)
    host = models.CharField(max_length=128)

    # Only source="independent" domain may set it's "path_prefix" field to non-default values.
    # domains managed by other sources('built_in', 'custom') does not support customizing
    # 'path_prefix', only '/'(or None) are supported for those domains.
    path_prefix = models.CharField(max_length=64, default='/', help_text="the accessable path for current domain")

    # HTTPS related fields
    https_enabled = models.BooleanField(default=False)
    https_auto_redirection = models.BooleanField(default=False)
    # "cert" field has higher priority than auto selected "shared cert"
    cert = models.ForeignKey('AppDomainCert', null=True, on_delete=models.SET_NULL)
    shared_cert = models.ForeignKey('AppDomainSharedCert', null=True, on_delete=models.SET_NULL)

    source = models.IntegerField(choices=make_enum_choices(AppDomainSource))

    def has_customized_path_prefix(self) -> bool:
        """Check if current domain has configured a custom path prefix"""
        return self.path_prefix != '/'

    def __str__(self) -> str:
        return f'<AppDomain: https_enabled={self.https_enabled} host={self.host}>'

    class Meta:
        unique_together = ("region", "host", "path_prefix")
        db_table = "services_appdomain"


class BasicCert(AuditedModel):
    region = models.CharField(max_length=32)
    name = models.CharField(max_length=128, unique=True, validators=[RegexValidator(DNS_SAFE_PATTERN)])
    cert_data = models.TextField()
    key_data = models.TextField()

    class Meta:
        abstract = True

    type: str = ''

    def get_secret_name(self) -> str:
        return f'eng-{self.type}-{self.name}'


class AppDomainCert(BasicCert):
    """WlApp's TLS Certifications, usually managed by user"""

    type = 'normal'

    class Meta:
        db_table = "services_appdomaincert"


class AppDomainSharedCert(BasicCert):
    """Shared TLS Certifications for AppDomain, every app's domain may link to this certificate as
    long as the domain matched the certificate's common names.
    """

    # Multiple CN are seperated by ";", for example: "foo.com;*.bar.com"
    auto_match_cns = models.TextField(max_length=2048)

    type = 'shared'

    class Meta:
        db_table = "services_appdomainsharedcert"


class AppSubpathManager(models.Manager):
    def create_obj(self, app: WlApp, subpath: str, source=AppSubpathSource.DEFAULT) -> 'AppSubpath':
        """Create an subpath object"""
        cluster = get_cluster_by_app(app)
        return self.get_queryset().create(
            app=app, region=app.region, cluster_name=cluster.name, subpath=subpath, source=source
        )

    class Meta:
        db_table = "services_appdomainsharedcert"


class AppSubpath(AuditedModel):
    """stores application's subpaths"""

    app = models.ForeignKey(WlApp, on_delete=models.CASCADE, db_constraint=False)
    region = models.CharField(max_length=32)
    cluster_name = models.CharField(max_length=32)
    subpath = models.CharField(max_length=128)
    source = models.IntegerField()

    objects = AppSubpathManager()

    def __str__(self) -> str:
        return f'<AppSubpath: subpath={self.subpath}>'

    class Meta:
        unique_together = ('region', 'subpath')
        db_table = "services_appsubpath"


def get_default_subpath(app: WlApp) -> str:
    """Get the default sub path for given application, this value will be used for:

    - sub path based ingress resource, used as request accessing location
    - injected builtin env variable: BKPAAS_SUB_PATH
    """
    return f"/{app.region}-{app.name}/"


# PaaS "custom domain"(end-user) model start


class Domain(TimestampedModel):
    """custom domain for application"""

    name = models.CharField(help_text='域名', max_length=253, null=False)
    path_prefix = models.CharField(max_length=64, default='/', help_text="the accessable path for current domain")
    module_id = models.UUIDField(help_text='关联的模块 ID', null=False)
    environment_id = models.BigIntegerField(help_text='关联的环境 ID', null=False)
    https_enabled = models.NullBooleanField(default=False, help_text="该域名是否开启 https.")

    module = ModuleAttrFromID()
    environment = ModuleEnvAttrFromID()

    class Meta:
        unique_together = ('name', 'path_prefix', 'module_id', 'environment_id')
        db_table = "services_domain"

    @property
    def protocol(self) -> str:
        return "https" if self.https_enabled else "http"

    def has_customized_path_prefix(self) -> bool:
        """Check if current domain has configured a custom path prefix"""
        return self.path_prefix != '/'

    def __str__(self):
        return f'module={self.module_id}-{self.name}'


# PaaS "custom domain"(end-user) model end
