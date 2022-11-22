import cattr

from paasng.engine.controller.models import IngressConfig


def test_find_subdomain_domain():
    ing_cfg = cattr.structure(
        {
            'app_root_domains': [{"name": 'foo-1.example.com', 'https_enabled': True}],
        },
        IngressConfig,
    )
    d = ing_cfg.find_subdomain_domain('foo-1.example.com')
    assert d is not None
    assert d.https_enabled is True
    assert ing_cfg.find_subdomain_domain('foo-2.example.com') is None


def test_find_subpath_domain():
    ing_cfg = cattr.structure(
        {
            'sub_path_domains': [{"name": 'foo-1.example.com', 'https_enabled': True}],
        },
        IngressConfig,
    )
    d = ing_cfg.find_subpath_domain('foo-1.example.com')
    assert d is not None
    assert d.https_enabled is True
    assert ing_cfg.find_subpath_domain('bar.example.com') is None
