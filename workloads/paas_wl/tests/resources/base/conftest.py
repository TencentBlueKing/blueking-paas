# -*- coding: utf-8 -*-
import pytest

from paas_wl.resources.base.client import K8sScheduler
from tests.conftest import CLUSTER_NAME_FOR_TESTING


@pytest.fixture
def scheduler_client() -> 'K8sScheduler':
    """Scheduler client connecting to testing cluster"""
    return K8sScheduler.from_cluster_name(CLUSTER_NAME_FOR_TESTING)
