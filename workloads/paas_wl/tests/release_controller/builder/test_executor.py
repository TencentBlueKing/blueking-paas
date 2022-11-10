# -*- coding: utf-8 -*-
from unittest import mock

import pytest
from django.conf import settings

from paas_wl.release_controller.builder.executor import BuildProcessExecutor
from paas_wl.utils.constants import BuildStatus
from paas_wl.utils.stream import ConsoleStream
from tests.utils.build_process import random_fake_bp

pytestmark = pytest.mark.django_db


class TestBuildProcessExecutor:
    def test_create_and_bind_build_instance(self, app):
        bp = random_fake_bp(app)
        bpe = BuildProcessExecutor(bp, ConsoleStream())

        assert bp.status != BuildStatus.SUCCESSFUL.value, "build_process status 初始值异常"
        build_instance = bpe.create_and_bind_build_instance(dict(procfile=["sth"]))
        assert str(bp.build_id) == str(build_instance.uuid), "绑定 build instance 失败"
        assert build_instance.owner == settings.BUILDER_USERNAME, "build instance 绑定 owner 异常"
        assert build_instance.procfile == ["sth"], "build instance 绑定 procfile 异常"
        assert bp.status == BuildStatus.SUCCESSFUL.value, "build_process status 未设置为 SUCCESSFUL"

    def test_execute(self, app):
        bp = random_fake_bp(app)
        bpe = BuildProcessExecutor(bp, ConsoleStream())

        # TODO: Too much mocks, both tests and codes need refactor
        with mock.patch("paas_wl.resources.base.client.K8sScheduler.get_build_log"), mock.patch(
            "paas_wl.resources.base.client.K8sScheduler.wait_build_succeeded"
        ), mock.patch(
            "paas_wl.release_controller.builder.executor.BuildProcessExecutor.start_slugbuilder"
        ), mock.patch(
            "paas_wl.resources.base.controllers.KPod.wait_for_status"
        ):
            bpe.execute()
        assert bp.status == BuildStatus.SUCCESSFUL.value, "部署失败"
