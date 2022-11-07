# -*- coding: utf-8 -*-
import pytest

from paas_wl.release_controller.process.models import PlainInstance, PlainProcess


@pytest.fixture
def instance():
    return PlainInstance(name="instance-foo", version=1, process_type="web", ready=False)


@pytest.fixture()
def process(instance):
    return PlainProcess(
        name="web",
        version=1,
        replicas=1,
        type="web",
        command="foo",
        instances=[instance],
    )
