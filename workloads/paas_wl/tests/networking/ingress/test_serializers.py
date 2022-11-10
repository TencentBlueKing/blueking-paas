# -*- coding: utf-8 -*-
import pytest

from paas_wl.networking.ingress.serializers import DomainEditableMixin


class TestDomainEditableMixin:
    @pytest.mark.parametrize(
        'path_prefix,is_valid,expected_path_prefix',
        [
            (None, True, '/'),
            ('', True, '/'),
            ('/foo/', True, '/foo/'),
            ('/foo///', True, '/foo/'),
            # Does not match pattern
            ('/foo/bar/', False, None),
            ('foobar', False, None),
        ],
    )
    def test_path_prefix(self, path_prefix, is_valid, expected_path_prefix):
        slz = DomainEditableMixin(data={'path_prefix': path_prefix})
        is_valid = slz.is_valid()
        assert is_valid is is_valid
        if is_valid:
            assert slz.validated_data['path_prefix'] == expected_path_prefix
