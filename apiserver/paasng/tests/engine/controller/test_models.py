import cattr
import pytest

from paasng.engine.controller.models import IngressConfig


@pytest.mark.parametrize(
    'host,ret',
    [
        ('foo-1.example.com', False),
        ('foo-2.example.com', True),
        ('bar.example.com', False),
    ],
)
def test_find_https_enabled(host, ret):
    ing_cfg = cattr.structure(
        {
            'app_root_domains': [{"name": 'foo-1.example.com', 'https_enabled': False}],
            'sub_path_domains': [{"name": 'foo-2.example.com', 'https_enabled': True}],
        },
        IngressConfig,
    )
    assert ing_cfg.find_https_enabled(host) is ret
