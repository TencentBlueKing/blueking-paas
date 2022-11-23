# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import tarfile
import zipfile

import pytest

from paasng.dev_resources.sourcectl.utils import generate_temp_dir, generate_temp_file
from paasng.extensions.smart_app.detector import SourcePackageStatReader
from paasng.extensions.smart_app.path import ZipPath
from tests.sourcectl.packages.utils import gen_tar, gen_zip


@pytest.fixture
def tar_path(contents):
    with generate_temp_file() as file_path:
        gen_tar(file_path, contents)
        yield file_path


@pytest.fixture
def zip_path(contents):
    with generate_temp_file() as file_path:
        gen_zip(file_path, contents)
        with zipfile.ZipFile(file_path) as zf:
            yield ZipPath(source=zf, path=".")


@pytest.fixture()
def untar_path(tar_path):
    with tarfile.open(tar_path) as tar, generate_temp_dir() as worker_dir:
        tar.extractall(worker_dir)
        yield worker_dir


@pytest.fixture()
def package_root(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def package_stat(request):
    package_root = request.getfixturevalue("package_root")
    if isinstance(package_root, ZipPath):
        return SourcePackageStatReader(request.getfixturevalue("zip_path").source.filename).read()
    else:
        return SourcePackageStatReader(request.getfixturevalue("tar_path")).read()
