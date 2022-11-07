# -*- coding: utf-8 -*-
import pytest

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.resources.utils.basic import get_full_node_selector, get_full_tolerations, standardize_tolerations

pytestmark = pytest.mark.django_db


class TestGetFullNodeSelector:
    def test_empty(self, app):
        assert get_full_node_selector(app) == {}

    def test_integrated(self, app):
        config = app.config_set.latest()
        config.node_selector = {'key1': 'value1', 'key-c': 'value-new'}
        config.save()

        cluster = get_cluster_by_app(app)
        cluster.default_node_selector = {'key-c': 'value-c', 'key-c2': 'value-c2'}
        cluster.save()

        assert get_full_node_selector(app) == {'key1': 'value1', 'key-c': 'value-new', 'key-c2': 'value-c2'}


class TestGetFullTolerations:
    def test_empty(self, app):
        assert get_full_tolerations(app) == []

    def test_integrated(self, app):
        config = app.config_set.latest()
        config.tolerations = [{'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'}]
        config.save()

        cluster = get_cluster_by_app(app)
        cluster.default_tolerations = [
            {'key': 'app-c', 'operator': 'Equal', 'value': 'value-c', 'effect': 'NoSchedule'}
        ]
        cluster.save()
        assert get_full_tolerations(app) == [
            {'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'},
            {'key': 'app-c', 'operator': 'Equal', 'value': 'value-c', 'effect': 'NoSchedule'},
        ]


class TestStandardizeTolerations:
    """Testcases for `TestTolerationDataHelper` class"""

    def test_condensed_list_valid(self):
        tolerations = [
            {'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'},
            {'key': 'system-only', 'operator': 'Exists', 'effect': 'NoSchedule', 'foo': 'bar'},  # extra key
        ]
        assert standardize_tolerations(tolerations) == [
            {'key': 'app', 'operator': 'Equal', 'value': 'value1', 'effect': 'NoExecute'},
            {'key': 'system-only', 'operator': 'Exists', 'effect': 'NoSchedule'},
        ]
