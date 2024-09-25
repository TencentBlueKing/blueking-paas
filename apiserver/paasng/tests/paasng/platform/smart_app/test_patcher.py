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

import tarfile
from unittest import mock

import pytest
import yaml
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.platform.declarative import constants
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.patcher import SourceCodePatcher
from paasng.platform.smart_app.services.path import LocalFSPath
from paasng.platform.sourcectl.utils import generate_temp_dir
from tests.paasng.platform.sourcectl.packages.utils import EXAMPLE_APP_YAML

pytestmark = pytest.mark.django_db
EXPECTED_WEB_PROCESS = constants.WEB_PROCESS


class TestSourcePackagePatcher:
    @pytest.fixture()
    def patched_tar(self, tar_path, bk_module_full):
        bk_module_full.name = "bar"
        bk_module_full.source_origin = SourceOrigin.BK_LESS_CODE.value
        stat = SourcePackageStatReader(tar_path).read()
        with generate_temp_dir() as working_dir:
            dest = SourceCodePatcher.patch_tarball(
                # 注: 模块名与下方测试用例对应
                module=bk_module_full,
                tarball_path=tar_path,
                working_dir=working_dir,
                stat=stat,
            )
            yield dest

    @pytest.mark.parametrize(
        "user_source_dir",
        [
            # Different kinds of value including empty, relative and absolute  path
            (""),
            ("foo"),
            ("/foo/bar"),
        ],
    )
    def test_module_dir(self, user_source_dir, tmp_path, tar_path, bk_module_full):
        bk_module_full.name = "bar"
        bk_module_full.source_origin = SourceOrigin.BK_LESS_CODE.value
        stat = SourcePackageStatReader(tar_path).read()
        patcher = SourceCodePatcher(
            module=bk_module_full,
            source_dir=LocalFSPath(tmp_path),
            desc_data=stat.meta_info,
            relative_path=stat.relative_path,
        )
        with mock.patch.object(patcher, "get_user_source_dir", return_value=user_source_dir):
            assert str(patcher.module_dir.path).startswith(str(tmp_path))

    @pytest.mark.parametrize(
        ("contents", "target", "ctx", "expected"),
        [
            # 我们的打包脚本会默认打成相对路径形式
            (
                {
                    "app.yaml": yaml.dump(
                        {
                            **EXAMPLE_APP_YAML,
                            "is_use_celery": True,
                        }
                    )
                },
                "./app.yaml",
                does_not_raise(),
                {
                    **EXAMPLE_APP_YAML,
                    "is_use_celery": True,
                },
            ),
            # 测试 procfile 内容
            (
                {"app.yaml": yaml.dump(EXAMPLE_APP_YAML)},
                "./Procfile",
                does_not_raise(),
                {"web": EXPECTED_WEB_PROCESS},
            ),
            # 测试 ./Procfile not found
            ({"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML)}, "./Procfile", pytest.raises(KeyError), None),
            (
                {"foo/app.yaml": yaml.dump(EXAMPLE_APP_YAML)},
                "./foo/Procfile",
                does_not_raise(),
                {"web": EXPECTED_WEB_PROCESS},
            ),
            (
                {
                    "foo/app.yaml": yaml.dump(
                        {
                            **EXAMPLE_APP_YAML,
                            "is_use_celery": True,
                        }
                    )
                },
                "./foo/Procfile",
                does_not_raise(),
                {"web": EXPECTED_WEB_PROCESS, "celery": constants.CELERY_PROCESS},
            ),
            (
                {
                    "foo/app.yaml": yaml.dump(
                        {
                            **EXAMPLE_APP_YAML,
                            "is_use_celery_with_gevent": True,
                        }
                    )
                },
                "./foo/Procfile",
                does_not_raise(),
                {
                    "web": EXPECTED_WEB_PROCESS,
                    "celery": constants.CELERY_PROCESS_WITH_GEVENT,
                },
            ),
            (
                {
                    "foo/app.yaml": yaml.dump(
                        {**EXAMPLE_APP_YAML, "is_use_celery": True, "is_use_celery_with_gevent": True}
                    )
                },
                "./foo/Procfile",
                does_not_raise(),
                {"web": EXPECTED_WEB_PROCESS, "celery": constants.CELERY_PROCESS},
            ),
            (
                {"foo/app.yaml": yaml.dump({**EXAMPLE_APP_YAML, "is_use_celery": True, "is_use_celery_beat": True})},
                "./foo/Procfile",
                does_not_raise(),
                {
                    "web": EXPECTED_WEB_PROCESS,
                    "celery": constants.CELERY_PROCESS,
                    "beat": constants.CELERY_BEAT_PROCESS,
                },
            ),
            # 以下测试 app_desc.yaml 规范
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "language": "python",
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'hello world!';"}},
                                }
                            },
                        }
                    )
                },
                "./foo/Procfile",
                does_not_raise(),
                # shlex 在某些情况会出现稍微偏差(这里的 ; 号位置变了)
                {"hello": "echo 'hello world!';"},
            ),
            # 测试 Procfile 不会被覆盖
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "language": "python",
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'good afternoon!';"}},
                                }
                            },
                        }
                    ),
                    "foo/Procfile": yaml.dump({"hello": "echo 'good morning!';"}),
                },
                "./foo/Procfile",
                does_not_raise(),
                {"hello": "echo 'good morning!';"},
            ),
            # 测试多模块.
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'Hello Foo, i am Bar!'"}},
                                    "source_dir": "./src/bar",
                                    "language": "python",
                                },
                                "foo": {
                                    "processes": {"hello": {"command": "echo 'Hello Bar, i am Foo!'"}},
                                    "source_dir": "./src/foo",
                                    "language": "python",
                                },
                            },
                        }
                    ),
                },
                "./foo/src/bar/Procfile",
                does_not_raise(),
                {"hello": "echo 'Hello Foo, i am Bar!'"},
            ),
            # 测试多模块(已加密)
            (
                {
                    "foo/app_desc.yaml": yaml.dump(
                        {
                            "spec_version": 2,
                            "app": {"bk_app_code": "foo", "bk_app_name": "foo"},
                            "modules": {
                                "bar": {
                                    "processes": {"hello": {"command": "echo 'Hello Foo, i am Bar!'"}},
                                    "source_dir": "./src/bar",
                                    "language": "python",
                                },
                                "foo": {
                                    "is_default": True,
                                    "processes": {"hello": {"command": "echo 'Hello Bar, i am Foo!'"}},
                                    "source_dir": "./src/foo",
                                    "language": "python",
                                },
                            },
                        }
                    ),
                    "foo/src/bar": "",
                },
                "./foo/Procfile",
                does_not_raise(),
                {"hello": "echo 'Hello Foo, i am Bar!'"},
            ),
        ],
    )
    def test_add_procfile(self, tar_path, patched_tar, target, ctx, expected):
        assert tar_path.name == patched_tar.name
        with tarfile.open(patched_tar) as tar, ctx:
            fp = tar.extractfile(target)
            assert fp
            data = yaml.full_load(fp.read())
            assert data == expected

    @pytest.mark.parametrize(
        ("contents", "target", "ctx", "expected"),
        [
            (
                {
                    "app.yaml": yaml.dump({**EXAMPLE_APP_YAML, "language": "python"}),
                },
                "./requirements.txt",
                pytest.raises(KeyError),
                None,
            ),
            (
                {
                    "app.yaml": yaml.dump(
                        {
                            **EXAMPLE_APP_YAML,
                            "language": "python",
                            "libraries": [dict(name="foo", version="1.1.1"), dict(name="bar", version="2.2.2")],
                        }
                    ),
                },
                "./requirements.txt",
                does_not_raise(),
                b"foo==1.1.1\nbar==2.2.2",
            ),
            (
                {
                    "app.yaml": yaml.dump(
                        {
                            **EXAMPLE_APP_YAML,
                            "language": "nodejs",
                            "libraries": [dict(name="foo", version="1.1.1"), dict(name="bar", version="2.2.2")],
                        }
                    ),
                },
                "./requirements.txt",
                pytest.raises(KeyError),
                None,
            ),
        ],
    )
    def test_add_requirements(self, tar_path, patched_tar, target, ctx, expected):
        assert tar_path.name == patched_tar.name
        with tarfile.open(patched_tar) as tar, ctx:
            fp = tar.extractfile(target)
            assert fp
            assert fp.read() == expected
