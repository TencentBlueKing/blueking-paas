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

import base64
import logging
from typing import Optional, Tuple

from django.utils.encoding import force_bytes, force_str

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.networking.ingress.models import AppDomain, AppDomainSharedCert, BasicCert, Domain

logger = logging.getLogger(__name__)


class DomainWithCert:
    def __init__(self, host: str, path_prefix: str, https_enabled: bool, cert: Optional[BasicCert] = None):
        """DomainWithCert is a combination with an accessible address and cert

        :param host: 域名
        :param path_prefix: 该域名的可访问路径前缀
        :param https_enabled: 该域名是否开启 https
        :param cert: 该域名关联的证书
        """
        self.host = host
        self.path_prefix = path_prefix
        self.https_enabled = https_enabled
        self.cert = cert

    @classmethod
    def from_app_domain(cls, domain: AppDomain) -> "DomainWithCert":
        """Get DomainWithCert from `AppDomain`, will set shared_cert if found some matched"""
        cert = domain.cert or domain.shared_cert
        if not cert:
            cert = pick_shared_cert(domain.tenant_id, domain.host)
            if cert:
                domain.shared_cert = cert
                domain.save(update_fields=["shared_cert", "updated"])
        return cls(host=domain.host, path_prefix=domain.path_prefix, https_enabled=domain.https_enabled, cert=cert)

    @classmethod
    def from_custom_domain(cls, domain: Domain) -> "DomainWithCert":
        """Get DomainWithCert by `Domain`, will pick shared cert by domain.name for backward compatibility"""
        cert = pick_shared_cert(domain.tenant_id, domain.name)
        return cls(host=domain.name, path_prefix=domain.path_prefix, https_enabled=domain.https_enabled, cert=cert)


def update_or_create_secret_by_cert(app: WlApp, cert: BasicCert) -> Tuple[str, bool]:
    """Update or create the secret resource by cert object

    :param app: `WlApp` object, the Secret resource which holds HTTPS cert will be created
        in this app's namespace.
    :param cert: The certificate object
    :return: (<name of Secret resource>, <created>)
    """
    client = get_client_by_app(app)
    secret_name = cert.get_secret_name()
    body = {
        "metadata": {
            "name": secret_name,
            "annotations": {"related_cert_type": cert.type, "related_cert_pk": str(cert.pk)},
        },
        "type": "kubernetes.io/tls",
        "data": {
            "tls.crt": force_str(base64.b64encode(force_bytes(cert.cert_data))),
            "tls.key": force_str(base64.b64encode(force_bytes(cert.key_data))),
        },
    }
    _, created = kres.KSecret(client).create_or_update(
        name=secret_name, namespace=app.namespace, body=body, update_method="patch"
    )
    return secret_name, created


def pick_shared_cert(tenant_id: str, host: str) -> Optional[AppDomainSharedCert]:
    """Try to select a shared certificate for the current application domain, search
    only within a given tenant.

    :param tenant_id: The tenant_id.
    :param host: Hostname for finding valid cert object.
    """
    for cert in AppDomainSharedCert.objects.filter(tenant_id=tenant_id):
        if cert.match_hostname(host):
            return cert
    return None
