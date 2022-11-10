# -*- coding: utf-8 -*-
import base64
from textwrap import dedent

import pytest


@pytest.fixture
def example_cluster_config():
    return {
        'ingress_config': {
            "app_root_domains": [{"name": "example.com"}],
            "sub_path_domains": [{"name": "example.com"}],
            "default_ingress_domain_tmpl": "%s.apps.com",
            "frontend_ingress_ip": "0.0.0.0",
            "port_map": {"http": "80", "https": "443"},
        },
        'ca_data': '',
        'cert_data': '',
        'key_data': '',
    }


@pytest.fixture()
def clusters():
    return {
        "foo": {
            "api_servers": [
                dict(
                    host="https://hostname-of-foo:6553",
                )
            ]
        },
        "bar": {
            "api_servers": [
                dict(
                    host="https://hostname-of-bar-a:6553",
                ),
                dict(
                    host="https://hostname-of-bar-b:6553",
                ),
            ]
        },
        "baz": {
            "api_servers": [
                dict(host="https://192.168.1.100:6553", overridden_hostname="baz-a.domain.com"),
                dict(host="https://192.168.1.101:6553", overridden_hostname="baz-b.domain.com"),
            ]
        },
    }


@pytest.fixture
def ca_data() -> str:
    return base64.b64encode(
        dedent(
            """-----BEGIN CERTIFICATE-----
            -----END CERTIFICATE-----
            """
        ).encode()
    ).decode()


@pytest.fixture
def cert_data() -> str:
    return base64.b64encode(
        dedent(
            """-----BEGIN CERTIFICATE-----
            -----END CERTIFICATE-----"""
        ).encode()
    ).decode()


@pytest.fixture
def key_data() -> str:
    return base64.b64encode(
        dedent(
            """-----BEGIN RSA PRIVATE KEY-----
            -----END RSA PRIVATE KEY-----"""
        ).encode()
    ).decode()
