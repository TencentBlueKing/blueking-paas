import base64
import logging
import re
from typing import Optional, Tuple

from django.utils.encoding import force_bytes, force_str

from paas_wl.networking.ingress.models import AppDomain, AppDomainSharedCert, BasicCert
from paas_wl.platform.applications.models import App
from paas_wl.resources.base import kres
from paas_wl.resources.utils.basic import get_client_by_app

logger = logging.getLogger(__name__)


class AppDomainCertController:
    """Controller for app_domains's certs"""

    def __init__(self, app_domain: AppDomain):
        self.app_domain = app_domain
        self.app = self.app_domain.app

    def get_cert(self) -> Optional[BasicCert]:
        """Get cert object"""
        if self.app_domain.cert:
            return self.app_domain.cert
        if self.app_domain.shared_cert:
            return self.app_domain.shared_cert

        # Try to pick a matched shared cert by CN
        shared_cert = pick_shared_cert(self.app.region, self.app_domain.host)
        if shared_cert:
            logger.debug('Shared cert found for %s', self.app_domain)
            self.app_domain.shared_cert = shared_cert
            self.app_domain.save(update_fields=['shared_cert'])
            return shared_cert
        return None

    def update_or_create_secret_by_cert(self, cert: BasicCert) -> Tuple[str, bool]:
        # Forward function call directly
        return update_or_create_secret_by_cert(self.app, cert)


def update_or_create_secret_by_cert(app: App, cert: BasicCert) -> Tuple[str, bool]:
    """Update or create the secret resource by cert object

    :param app: `App` object, the Secret resource which holds HTTPS cert will be created
        in this app's namespace.
    :param cert: The certificate object
    :return: (<name of Secret resource>, <created>)
    """
    client = get_client_by_app(app)
    secret_name = cert.get_secret_name()
    body = {
        'metadata': {
            'name': secret_name,
            'annotations': {"related_cert_type": cert.type, "related_cert_pk": str(cert.pk)},
        },
        'type': "kubernetes.io/tls",
        'data': {
            "tls.crt": force_str(base64.b64encode(force_bytes(cert.cert_data))),
            'tls.key': force_str(base64.b64encode(force_bytes(cert.key_data))),
        },
    }
    # FIXME: For cloud-native applications, we should use EnvPlaner to get namespace
    # instead of app.namespace, although these two are returning identical values.
    _, created = kres.KSecret(client).create_or_update(
        name=secret_name, namespace=app.namespace, body=body, update_method='patch'
    )
    return secret_name, created


def pick_shared_cert(region: str, host: str) -> Optional[AppDomainSharedCert]:
    """Try to pick a shared cert for current app domain

    :param region: Filter certs by given region
    :param host: Hostname for finding valid cert object
    """
    for cert in AppDomainSharedCert.objects.filter(region=region):
        for cn in cert.auto_match_cns.split(';'):
            # CN format: foo.com / *.bar.com
            pattern = re.escape(cn).replace(r'\*', r'[a-zA-Z0-9-]+')
            if re.match(f'^{pattern}$', host):
                return cert
    return None
