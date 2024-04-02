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
import hashlib
import json
from unittest import mock

import pytest
import requests

from paasng.platform.smart_app.utils.detector import SourcePackageStatReader
from paasng.platform.smart_app.utils.dispatch import dispatch_cnb_image_to_registry, dispatch_slug_image_to_registry
from paasng.platform.smart_app.utils.image_mgr import SMartImageManager
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, uncompress_directory
from tests.paasng.platform.smart_app.utils import MockAdapter, MockResponse

pytestmark = pytest.mark.django_db


@pytest.fixture()
def mock_adapter():
    session = requests.session()
    adapter = MockAdapter()
    session.mount("http://", adapter)
    with mock.patch("requests.sessions.Session") as mocked_session:
        mocked_session.return_value = session
        yield adapter


@pytest.fixture()
def image_manifest_content():
    return json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": 0,
                "digest": "example-config",
            },
            "layers": [],
        }
    ).encode()


@pytest.fixture()
def image_config_content():
    return json.dumps(
        {
            "architecture": "arm64",
            "created": "1980-01-01T00:00:01Z",
            "os": "linux",
            "rootfs": {"type": "layers", "diff_ids": []},
            "config": {},
            "history": [],
        },
        indent=0,
    ).encode()


def test_dispatch_slug_image_to_registry(
    bk_module, bk_user, assets_rootpath, mock_adapter, image_manifest_content, image_config_content
):
    """测试将 slug runner 镜像分发到 registry, 涉及多次网络请求, 要保证顺序正确。

    1. 获取镜像镜像信息 -> slugrunner_manifest_url & slugrunner_config_url
    2. 初始化上传 -> init_upload_url
    3. 上传层文件 -> upload_url
    4. 提交层文件 -> part_layer_commit_url
    5. 上传 Procfile -> upload_url
    6. 提交 Procfile -> part_procfile_commit_url
    7. 上传合并后的配置文件 -> upload_url
    8. 验证配置文件已上传成功 -> app_image_config_url
    9. 提交 App Image Manifest -> app_image_commit_url
    10. 验证镜像清单已上传成功 -> app_image_manifest_url
    """
    smart_asserts_path = assets_rootpath / "slugrunner-image"
    bk_module.name = "main"
    bk_module.save()
    mgr = SMartImageManager(bk_module)
    slug_runner_image = mgr.get_slugrunner_image_info()
    module_image = mgr.get_image_info()

    upload_url = "http://upload-endpoint/"
    commit_url = "http://commit-endpoint/"

    # Step 1: 获取镜像镜像信息
    slugrunner_manifest_url = (
        f"http://{slug_runner_image.domain}/v2/{slug_runner_image.name}/manifests/{slug_runner_image.tag}"
    )
    mock_adapter.register(slugrunner_manifest_url, MockResponse(body=image_manifest_content))
    slugrunner_config_url = f"http://{slug_runner_image.domain}/v2/{slug_runner_image.name}/blobs/example-config"
    mock_adapter.register(slugrunner_config_url, MockResponse(body=image_config_content))

    # Step 2: 初始化上传
    init_upload_url = f"http://{module_image.domain}/v2/{module_image.name}/blobs/uploads/"
    mock_adapter.register(
        init_upload_url, MockResponse(status_code=202, headers={"docker-upload-uuid": "abc", "location": upload_url})
    )
    mock_adapter.register(
        upload_url,
        MockResponse(
            status_code=202, headers={"range": "0-10000000", "docker-upload-uuid": "abc", "location": commit_url}
        ),
    )

    # 测试上传 layer.tar.gz 和 main.Procfile.tar.gz
    # Step 3 & 4: 上传层文件 & 提交层文件
    layer_tar_gz_sha256 = hashlib.sha256((smart_asserts_path / "main" / "layer.tar.gz").read_bytes()).hexdigest()
    part_layer_commit_url = f"{commit_url}?digest=sha256%3A{layer_tar_gz_sha256}"
    mock_adapter.register(part_layer_commit_url, MockResponse(status_code=201))
    # Step 5 & 6: 上传 Procfile & 提交 Procfile
    procfile_tar_gz_sha256 = hashlib.sha256(
        (smart_asserts_path / "main" / "main.Procfile.tar.gz").read_bytes()
    ).hexdigest()
    part_procfile_commit_url = f"{commit_url}?digest=sha256%3A{procfile_tar_gz_sha256}"
    mock_adapter.register(part_procfile_commit_url, MockResponse(status_code=201))

    # 由于有时间字段, 镜像 id 每个单测都会改变
    # Step 7 & 8: 上传合并后的配置文件 & 验证配置文件已上传成功
    app_image_config_url = f"http://{module_image.domain}/v2/{module_image.name}/blobs/sha256:.*"
    mock_adapter.register(
        app_image_config_url,
        MockResponse(headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"}),
    )

    # Step 9: 提交 App Image Manifest
    app_image_commit_url = f"{commit_url}\\?digest=.*"
    mock_adapter.register(app_image_commit_url, MockResponse(status_code=201))

    # Step 10: 验证镜像清单已上传成功
    # 1.0 是 app_desc 里的 app_version
    app_image_manifest_url = f"http://{module_image.domain}/v2/{module_image.name}/manifests/1.0"
    mock_adapter.register(app_image_manifest_url, MockResponse(body=image_manifest_content))

    with generate_temp_dir() as tempdir:
        tarball_path = tempdir / "tar.gz"
        workplace = tempdir / "workspace"
        compress_directory(smart_asserts_path, tarball_path)
        stat = SourcePackageStatReader(tarball_path).read()
        workplace.mkdir()
        uncompress_directory(tarball_path, workplace)
        dispatch_slug_image_to_registry(module=bk_module, workplace=workplace, stat=stat, operator=bk_user)


def test_dispatch_cnb_image_to_registry(
    bk_module, bk_user, assets_rootpath, mock_adapter, image_manifest_content, image_config_content
):
    """测试将 slug runner 镜像分发到 registry, 涉及多次网络请求, 要保证顺序正确。

    1. 获取镜像镜像信息 -> runner_manifest_url & runner_config_url
    2. 初始化上传 -> init_upload_url
    3. 逐层上传镜像层文件到 registry -> upload_url & layer_commit_url
    4. 上传合并后的配置文件 -> upload_url
    5. 验证配置文件已上传成功 -> app_image_config_url
    6. 提交 App Image Manifest -> app_image_commit_url
    7. 验证镜像清单已上传成功 -> app_image_manifest_url
    """

    smart_asserts_path = assets_rootpath / "cnb-image"
    bk_module.name = "main"
    bk_module.save()
    mgr = SMartImageManager(bk_module)
    cnb_runner_image = mgr.get_cnb_runner_image_info()
    module_image = mgr.get_image_info()

    upload_url = "http://upload-endpoint/"
    commit_url = "http://commit-endpoint/"

    # Step 1: 获取镜像镜像信息
    runner_manifest_url = (
        f"http://{cnb_runner_image.domain}/v2/{cnb_runner_image.name}/manifests/{cnb_runner_image.tag}"
    )
    mock_adapter.register(runner_manifest_url, MockResponse(body=image_manifest_content))
    runner_config_url = f"http://{cnb_runner_image.domain}/v2/{cnb_runner_image.name}/blobs/example-config"
    mock_adapter.register(runner_config_url, MockResponse(body=image_config_content))

    # Step 2: 初始化上传
    init_upload_url = f"http://{module_image.domain}/v2/{module_image.name}/blobs/uploads/"
    mock_adapter.register(
        init_upload_url, MockResponse(status_code=202, headers={"docker-upload-uuid": "abc", "location": upload_url})
    )
    mock_adapter.register(
        upload_url,
        MockResponse(
            status_code=202, headers={"range": "0-10000000", "docker-upload-uuid": "abc", "location": commit_url}
        ),
    )

    # Step 3: 逐层上传镜像层文件到 registry
    with generate_temp_dir() as main_exported:
        uncompress_directory(smart_asserts_path / "main.tgz", main_exported)
        for layer_file in (main_exported / "blobs/sha256/").iterdir():
            sha256_digest = hashlib.sha256(layer_file.read_bytes()).hexdigest()
            layer_commit_url = f"{commit_url}?digest=sha256%3A{sha256_digest}"
            mock_adapter.register(layer_commit_url, MockResponse(status_code=201))

    # 由于有时间字段, 镜像 id 每个单测都会改变
    # Step 4 & 5: 上传合并后的配置文件 & 验证配置文件已上传成功
    app_image_config_url = f"http://{module_image.domain}/v2/{module_image.name}/blobs/sha256:.*"
    mock_adapter.register(
        app_image_config_url,
        MockResponse(headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"}),
    )

    # Step 6: 提交 App Image Manifest
    app_image_commit_url = f"{commit_url}\\?digest=.*"
    mock_adapter.register(app_image_commit_url, MockResponse(status_code=201))

    # Step 7: 验证镜像清单已上传成功
    # 1.0 是 app_desc 里的 app_version
    app_image_manifest_url = f"http://{module_image.domain}/v2/{module_image.name}/manifests/1.0"
    mock_adapter.register(app_image_manifest_url, MockResponse(body=image_manifest_content))

    with generate_temp_dir() as tempdir:
        tarball_path = tempdir / "tar.gz"
        workplace = tempdir / "workspace"
        compress_directory(smart_asserts_path, tarball_path)
        stat = SourcePackageStatReader(tarball_path).read()
        workplace.mkdir()
        uncompress_directory(tarball_path, workplace)
        dispatch_cnb_image_to_registry(module=bk_module, workplace=workplace, stat=stat, operator=bk_user)
