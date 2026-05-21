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

import pytest
from django.core.management import call_command

from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner

pytestmark = pytest.mark.django_db


class TestManageBuildpackStack:
    """测试 manage_buildpack 命令的 --stack 参数"""

    def _call_manage_buildpack(self, name, tag="v1", language="Python", address="test/address", stack="", **kwargs):
        """辅助方法：调用 manage_buildpack 命令"""
        args = [
            "--name",
            name,
            "--tag",
            tag,
            "--language",
            language,
            "--address",
            address,
        ]
        if stack:
            args.extend(["--stack", stack])
        call_command("manage_buildpack", *args)

    def test_create_without_stack(self):
        """不传 --stack 时，stack 默认为空字符串"""
        self._call_manage_buildpack("bk-buildpack-python")

        bp = AppBuildPack.objects.get(name="bk-buildpack-python", stack="")
        assert bp.stack == ""
        assert bp.language == "Python"

    def test_create_with_stack(self):
        """传 --stack heroku-24 时，能创建带 stack 的记录"""
        self._call_manage_buildpack("bk-buildpack-python", stack="heroku-24", tag="v285")

        bp = AppBuildPack.objects.get(name="bk-buildpack-python", stack="heroku-24")
        assert bp.stack == "heroku-24"
        assert bp.version == "v285"

    def test_same_name_different_stack_coexist(self):
        """同名不同 stack 的 buildpack 可以独立共存"""
        self._call_manage_buildpack("bk-buildpack-python", tag="v213", address="https://old-address")
        self._call_manage_buildpack("bk-buildpack-python", stack="heroku-24", tag="v285", address="blueking/python")

        # 应该有两条记录
        assert AppBuildPack.objects.filter(name="bk-buildpack-python").count() == 2

        bp_default = AppBuildPack.objects.get(name="bk-buildpack-python", stack="")
        bp_noble = AppBuildPack.objects.get(name="bk-buildpack-python", stack="heroku-24")

        assert bp_default.version == "v213"
        assert bp_default.address == "https://old-address"
        assert bp_noble.version == "v285"
        assert bp_noble.address == "blueking/python"

    def test_update_or_create_with_same_name_and_stack(self):
        """相同 (name, stack) 组合执行 update_or_create 时更新已有记录"""
        self._call_manage_buildpack("bk-buildpack-python", stack="heroku-24", tag="v280")
        self._call_manage_buildpack("bk-buildpack-python", stack="heroku-24", tag="v285")

        # 应该只有一条记录
        assert AppBuildPack.objects.filter(name="bk-buildpack-python", stack="heroku-24").count() == 1

        bp = AppBuildPack.objects.get(name="bk-buildpack-python", stack="heroku-24")
        assert bp.version == "v285"

    def test_update_default_stack_does_not_affect_noble(self):
        """更新默认 stack 的 buildpack 不影响 heroku-24 的同名 buildpack"""
        self._call_manage_buildpack("bk-buildpack-python", stack="heroku-24", tag="v285")
        self._call_manage_buildpack("bk-buildpack-python", tag="v214")

        bp_noble = AppBuildPack.objects.get(name="bk-buildpack-python", stack="heroku-24")
        bp_default = AppBuildPack.objects.get(name="bk-buildpack-python", stack="")

        # noble 版本不受影响
        assert bp_noble.version == "v285"
        assert bp_default.version == "v214"


class TestBindBuildpacksStack:
    """测试 bind_buildpacks 命令的 --stack 参数"""

    @pytest.fixture()
    def slugbuilder(self):
        """创建测试用的 slugbuilder"""
        return AppSlugBuilder.objects.create(
            name="blueking-noble",
            type="cnb",
            image="test-builder:latest",
        )

    @pytest.fixture()
    def buildpack_default(self):
        """创建默认 stack 的 buildpack"""
        return AppBuildPack.objects.create(
            name="bk-buildpack-python",
            stack="",
            language="Python",
            type="tar",
            address="https://old-address",
            version="v213",
        )

    @pytest.fixture()
    def buildpack_noble(self):
        """创建 heroku-24 stack 的 buildpack"""
        return AppBuildPack.objects.create(
            name="bk-buildpack-python",
            stack="heroku-24",
            language="Python",
            type="oci-embedded",
            address="blueking/python",
            version="v285",
        )

    def test_bind_with_stack_filters_correctly(self, slugbuilder, buildpack_default, buildpack_noble):
        """传 --stack heroku-24 时只绑定对应 stack 的 buildpack"""
        call_command(
            "bind_buildpacks",
            "--image",
            "blueking-noble",
            "--buildpack-name",
            "bk-buildpack-python",
            "--stack",
            "heroku-24",
        )

        bound_buildpacks = list(slugbuilder.buildpacks.all())
        assert len(bound_buildpacks) == 1
        assert bound_buildpacks[0].pk == buildpack_noble.pk

    def test_bind_without_stack_matches_empty_stack(self, slugbuilder, buildpack_default, buildpack_noble):
        """不传 --stack 时只匹配 stack 为空的 buildpack"""
        call_command(
            "bind_buildpacks",
            "--image",
            "blueking-noble",
            "--buildpack-name",
            "bk-buildpack-python",
        )

        bound_buildpacks = list(slugbuilder.buildpacks.all())
        assert len(bound_buildpacks) == 1
        assert bound_buildpacks[0].pk == buildpack_default.pk

    def test_bind_noble_does_not_include_default(self, slugbuilder, buildpack_default, buildpack_noble):
        """绑定 heroku-24 的 buildpack 不会包含默认 stack 的同名 buildpack"""
        call_command(
            "bind_buildpacks",
            "--image",
            "blueking-noble",
            "--buildpack-name",
            "bk-buildpack-python",
            "--stack",
            "heroku-24",
        )

        bound_ids = set(slugbuilder.buildpacks.values_list("pk", flat=True))
        assert buildpack_default.pk not in bound_ids
        assert buildpack_noble.pk in bound_ids

    def test_bind_by_id_ignores_stack_filter(self, slugbuilder, buildpack_noble):
        """通过 --buildpack (id) 查询时不受 stack 过滤影响"""
        call_command(
            "bind_buildpacks",
            "--image",
            "blueking-noble",
            "--buildpack",
            str(buildpack_noble.pk),
        )

        bound_buildpacks = list(slugbuilder.buildpacks.all())
        assert len(bound_buildpacks) == 1
        assert bound_buildpacks[0].pk == buildpack_noble.pk

    def test_empty_result_outputs_warning(self, slugbuilder, capsys):
        """查询结果为空时输出警告信息"""
        call_command(
            "bind_buildpacks",
            "--image",
            "blueking-noble",
            "--buildpack-name",
            "non-existent-buildpack",
        )

        captured = capsys.readouterr()
        assert "未找到匹配的 buildpack" in captured.err


class TestBindRuntimeStack:
    """测试 bind_runtime 命令的 --stack 参数"""

    @pytest.fixture()
    def image_name(self):
        return "test-runtime-image"

    @pytest.fixture()
    def slugbuilder(self, image_name, buildpack_default, buildpack_noble):
        slugbuilder = AppSlugBuilder.objects.create(
            name=image_name,
            type="cnb",
            image="test-builder",
            tag="latest",
        )
        slugbuilder.buildpacks.add(buildpack_default, buildpack_noble)
        return slugbuilder

    @pytest.fixture()
    def slugrunner(self, image_name):
        return AppSlugRunner.objects.create(
            name=image_name,
            type="cnb",
            image="test-runner",
            tag="latest",
        )

    @pytest.fixture()
    def buildpack_default(self):
        """创建默认 stack 的 buildpack"""
        return AppBuildPack.objects.create(
            name="bk-buildpack-python",
            stack="",
            language="Python",
            type="tar",
            address="https://old-address",
            version="v213",
        )

    @pytest.fixture()
    def buildpack_noble(self):
        """创建 heroku-24 stack 的 buildpack"""
        return AppBuildPack.objects.create(
            name="bk-buildpack-python",
            stack="heroku-24",
            language="Python",
            type="oci-embedded",
            address="blueking/python",
            version="v285",
        )

    def test_bind_with_stack_filters_correctly(
        self, bk_module, image_name, slugbuilder, slugrunner, buildpack_default, buildpack_noble
    ):
        """传 --stack heroku-24 时只绑定对应 stack 的 buildpack"""
        call_command(
            "bind_runtime",
            "--image",
            image_name,
            "--buildpack-name",
            "bk-buildpack-python",
            "--stack",
            "heroku-24",
            "--app-code",
            bk_module.application.code,
            "--module",
            bk_module.name,
        )

        bound_buildpacks = list(bk_module.build_config.buildpacks.all())
        assert len(bound_buildpacks) == 1
        assert bound_buildpacks[0].pk == buildpack_noble.pk

    def test_bind_without_stack_matches_empty_stack(
        self, bk_module, image_name, slugbuilder, slugrunner, buildpack_default, buildpack_noble
    ):
        """不传 --stack 时只匹配 stack 为空的 buildpack"""
        call_command(
            "bind_runtime",
            "--image",
            image_name,
            "--buildpack-name",
            "bk-buildpack-python",
            "--app-code",
            bk_module.application.code,
            "--module",
            bk_module.name,
        )

        bound_buildpacks = list(bk_module.build_config.buildpacks.all())
        assert len(bound_buildpacks) == 1
        assert bound_buildpacks[0].pk == buildpack_default.pk

    def test_bind_by_id_ignores_stack_filter(self, bk_module, image_name, slugbuilder, slugrunner, buildpack_noble):
        """通过 --buildpack (id) 查询时不受 stack 过滤影响"""
        call_command(
            "bind_runtime",
            "--image",
            image_name,
            "--buildpack",
            str(buildpack_noble.pk),
            "--app-code",
            bk_module.application.code,
            "--module",
            bk_module.name,
        )

        bound_buildpacks = list(bk_module.build_config.buildpacks.all())
        assert len(bound_buildpacks) == 1
        assert bound_buildpacks[0].pk == buildpack_noble.pk
