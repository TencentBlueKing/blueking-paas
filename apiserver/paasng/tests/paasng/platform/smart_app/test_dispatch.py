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

import hashlib
import json
import re
import shutil
import tarfile
from itertools import chain
from unittest import mock

import pytest
import requests
from requests_mock import Adapter

from paasng.platform.smart_app.exceptions import UnsupportedSMartPackageError
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.dispatch import (
    bksmart_settings,
    dispatch_cnb_image_to_registry,
    dispatch_package_to_modules,
    dispatch_slug_image_to_registry,
    read_cnb_base_image_id,
    validate_smart_package,
)
from paasng.platform.smart_app.services.image_mgr import SMartImageManager
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, uncompress_directory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _disable_parallel():
    with mock.patch("paasng.platform.smart_app.services.dispatch._PARALLEL_PATCHING", new=False):
        yield


@pytest.fixture()
def mock_adapter():
    session = requests.session()
    adapter = Adapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    with mock.patch("requests.sessions.Session", return_value=session):
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

    base_url = bksmart_settings.registry.get_client().api_base_url
    upload_url = "https://upload-endpoint/"
    commit_url = "https://commit-endpoint/"

    # Step 1: 获取镜像镜像信息
    slugrunner_manifest_url = f"{base_url}/v2/{slug_runner_image.name}/manifests/{slug_runner_image.tag}"
    mock_adapter.register_uri("GET", url=slugrunner_manifest_url, content=image_manifest_content)
    slugrunner_config_url = f"{base_url}/v2/{slug_runner_image.name}/blobs/example-config"
    mock_adapter.register_uri("GET", url=slugrunner_config_url, content=image_config_content)

    # Step 2: 初始化上传
    init_upload_url = f"{base_url}/v2/{module_image.name}/blobs/uploads/"
    mock_adapter.register_uri(
        "POST", url=init_upload_url, status_code=202, headers={"docker-upload-uuid": "abc", "location": upload_url}
    )
    mock_adapter.register_uri(
        "PATCH",
        url=upload_url,
        status_code=202,
        headers={"range": "0-10000000", "docker-upload-uuid": "abc", "location": commit_url},
    )

    # 测试上传 layer.tar.gz 和 main.Procfile.tar.gz
    # Step 3 & 4: 上传层文件 & 提交层文件
    layer_tar_gz_sha256 = hashlib.sha256((smart_asserts_path / "main" / "layer.tar.gz").read_bytes()).hexdigest()
    part_layer_commit_url = f"{commit_url}?digest=sha256%3A{layer_tar_gz_sha256}"
    mock_adapter.register_uri("POST", url=part_layer_commit_url, status_code=201)
    part_layer_touch_url = f"{base_url}/v2/{module_image.name}/blobs/sha256:{layer_tar_gz_sha256}"
    mock_adapter.register_uri(
        "HEAD",
        url=part_layer_touch_url,
        headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
    )
    # Step 5 & 6: 上传 Procfile & 提交 Procfile
    procfile_tar_gz_sha256 = hashlib.sha256(
        (smart_asserts_path / "main" / "main.Procfile.tar.gz").read_bytes()
    ).hexdigest()
    part_procfile_commit_url = f"{commit_url}?digest=sha256%3A{procfile_tar_gz_sha256}"
    mock_adapter.register_uri("POST", url=part_procfile_commit_url, status_code=201)
    part_procfile_touch_url = f"{base_url}/v2/{module_image.name}/blobs/sha256:{procfile_tar_gz_sha256}"
    mock_adapter.register_uri(
        "HEAD",
        url=part_procfile_touch_url,
        headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
    )

    # 由于有时间字段, 镜像 id 每个单测都会改变
    # Step 7 & 8: 上传合并后的配置文件 & 验证配置文件已上传成功
    app_image_config_url = f"{base_url}/v2/{module_image.name}/blobs/sha256:.*"
    mock_adapter.register_uri(
        "HEAD",
        url=re.compile(app_image_config_url),
        headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
    )

    # Step 9: 提交 App Image Manifest
    app_image_commit_url = f"{commit_url}\\?digest=.*"
    mock_adapter.register_uri("PUT", url=re.compile(app_image_commit_url), status_code=201)

    # Step 10: 验证镜像清单已上传成功
    # 1.0 是 app_desc 里的 app_version
    app_image_manifest_url = f"{base_url}/v2/{module_image.name}/manifests/1.0"
    mock_adapter.register_uri("PUT", url=app_image_manifest_url)
    mock_adapter.register_uri("GET", url=app_image_manifest_url, content=image_manifest_content)

    with generate_temp_dir() as tempdir:
        tarball_path = tempdir / "tar.gz"
        workplace = tempdir / "workspace"
        compress_directory(smart_asserts_path, tarball_path)
        stat = SourcePackageStatReader(tarball_path).read()
        workplace.mkdir()
        uncompress_directory(tarball_path, workplace)
        dispatch_slug_image_to_registry(module=bk_module, workplace=workplace, stat=stat, operator=bk_user)

    # expected request url history
    expected_request_url_history = [
        # 1. 获取镜像镜像信息
        ("GET", slugrunner_manifest_url),
        ("GET", slugrunner_config_url),
        # 2. 上传 slug 层
        ("POST", init_upload_url),
        ("PATCH", upload_url),
        ("PUT", part_layer_commit_url),
        ("HEAD", part_layer_touch_url),
        # 3. 上传 Procfile 层
        ("POST", init_upload_url),
        ("PATCH", upload_url),
        ("PUT", part_procfile_commit_url),
        ("HEAD", part_procfile_touch_url),
        # 4. 上传 image config
        ("POST", init_upload_url),
        ("PATCH", upload_url),
        ("PUT", re.compile(app_image_commit_url)),
        ("HEAD", re.compile(app_image_config_url)),
        # 5. 上传 manifest
        ("PUT", app_image_manifest_url),
        ("GET", app_image_manifest_url),
    ]

    for idx, (expected_method, expected_url) in enumerate(expected_request_url_history):
        req = mock_adapter.request_history[idx]
        assert expected_method == req.method
        if isinstance(expected_url, re.Pattern):
            assert expected_url.fullmatch(req.url)
        else:
            assert expected_url == req.url


@pytest.fixture()
def _with_heroku_24_image_conf():
    conf = {"heroku-24": {"name": "bkpaas/docker/run-heroku-noble", "tag": "v2.5.0-smart"}}
    with mock.patch.dict(bksmart_settings.cnb_base_image.image_conf, conf):
        yield


@pytest.mark.usefixtures("_with_heroku_24_image_conf")
@pytest.mark.parametrize("base_image_id", ["default", "heroku-24"])
def test_dispatch_cnb_image_to_registry(
    bk_module, bk_user, assets_rootpath, mock_adapter, image_manifest_content, image_config_content, base_image_id
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
    cnb_runner_image = mgr.get_cnb_runner_image_info(base_image_id=base_image_id)
    assert cnb_runner_image.name == bksmart_settings.cnb_base_image.get_name(base_image_id)
    module_image = mgr.get_image_info()

    base_url = bksmart_settings.registry.get_client().api_base_url
    upload_url = "https://upload-endpoint/"
    commit_url = "https://commit-endpoint/"

    # Step 1: 获取镜像镜像信息
    runner_manifest_url = f"{base_url}/v2/{cnb_runner_image.name}/manifests/{cnb_runner_image.tag}"
    mock_adapter.register_uri("GET", url=runner_manifest_url, content=image_manifest_content)
    runner_config_url = f"{base_url}/v2/{cnb_runner_image.name}/blobs/example-config"
    mock_adapter.register_uri("GET", url=runner_config_url, content=image_config_content)

    # Step 2: 初始化上传
    init_upload_url = f"{base_url}/v2/{module_image.name}/blobs/uploads/"
    mock_adapter.register_uri(
        "POST", url=init_upload_url, status_code=202, headers={"docker-upload-uuid": "abc", "location": upload_url}
    )
    mock_adapter.register_uri(
        "PATCH",
        url=upload_url,
        status_code=202,
        headers={"range": "0-10000000", "docker-upload-uuid": "abc", "location": commit_url},
    )

    # Step 3: 逐层上传镜像层文件到 registry
    layer_digest_list = [
        "1cad71326f6c0f3196ae135e80033987496ea7e2a6e6f31389e7cba9ce7c8996",
        "741772c7f3e2c81925ccb74a032df3ee0ff15079c81fdee1ae4f581cdf9fcdf2",
    ]
    for sha256_digest in layer_digest_list:
        layer_commit_url = f"{commit_url}?digest=sha256%3A{sha256_digest}"
        mock_adapter.register_uri("PUT", url=layer_commit_url, status_code=201)
        layer_touch_url = f"{base_url}/v2/{module_image.name}/blobs/sha256:{sha256_digest}"
        mock_adapter.register_uri(
            "HEAD",
            url=layer_touch_url,
            headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
        )

    # 由于有时间字段, 镜像 id 每个单测都会改变
    # Step 4 & 5: 上传合并后的配置文件 & 验证配置文件已上传成功
    app_image_config_url = f"{base_url}/v2/{module_image.name}/blobs/sha256:.*"
    mock_adapter.register_uri(
        "HEAD",
        url=re.compile(app_image_config_url),
        headers={"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"},
    )

    # Step 6: 提交 App Image Manifest
    app_image_commit_url = f"{commit_url}\\?digest=.*"
    mock_adapter.register_uri("PUT", url=re.compile(app_image_commit_url), status_code=201)

    # Step 7: 验证镜像清单已上传成功
    # 1.0 是 app_desc 里的 app_version
    app_image_manifest_url = f"{base_url}/v2/{module_image.name}/manifests/1.0"
    mock_adapter.register_uri("PUT", url=app_image_manifest_url)
    mock_adapter.register_uri("GET", url=app_image_manifest_url, content=image_manifest_content)

    with generate_temp_dir() as tempdir:
        tarball_path = tempdir / "tar.gz"
        workplace = tempdir / "workspace"
        compress_directory(smart_asserts_path, tarball_path)
        stat = SourcePackageStatReader(tarball_path).read()
        workplace.mkdir()
        uncompress_directory(tarball_path, workplace)
        dispatch_cnb_image_to_registry(
            module=bk_module, workplace=workplace, stat=stat, operator=bk_user, base_image_id=base_image_id
        )

    # expected request url history
    expected_request_url_history = [
        # 1. 获取镜像镜像信息
        ("GET", runner_manifest_url),
        ("GET", runner_config_url),
        # 2. 按序上传镜像层
        *list(
            chain.from_iterable(
                [
                    ("POST", init_upload_url),
                    ("PATCH", upload_url),
                    ("PUT", f"{commit_url}?digest=sha256%3A{sha256_digest}"),
                    ("HEAD", f"{base_url}/v2/{module_image.name}/blobs/sha256:{sha256_digest}"),
                ]
                for sha256_digest in layer_digest_list
            )
        ),
        # 4. 上传 image config
        ("POST", init_upload_url),
        ("PATCH", upload_url),
        ("PUT", re.compile(app_image_commit_url)),
        ("HEAD", re.compile(app_image_config_url)),
        # 5. 上传 manifest
        ("PUT", app_image_manifest_url),
        ("GET", app_image_manifest_url),
    ]

    for idx, (expected_method, expected_url) in enumerate(expected_request_url_history):
        req = mock_adapter.request_history[idx]
        assert expected_method == req.method
        if isinstance(expected_url, re.Pattern):
            assert expected_url.fullmatch(req.url)
        else:
            assert expected_url == req.url


@pytest.mark.parametrize(
    ("package_path", "dispatcher_uri"),
    [
        ("cnb-image", "paasng.platform.smart_app.services.dispatch.dispatch_cnb_image_to_registry"),
        ("slugrunner-image", "paasng.platform.smart_app.services.dispatch.dispatch_slug_image_to_registry"),
    ],
)
def test_dispatch_package_to_modules(bk_app, bk_module, bk_user, assets_rootpath, package_path, dispatcher_uri):
    """测试根据 s-mart 包结构选择不同的 dispatcher"""
    smart_asserts_path = assets_rootpath / package_path
    bk_module.name = "main"
    bk_module.save()

    with generate_temp_dir() as tempdir:
        tarball_path = tempdir / "tar.gz"
        compress_directory(smart_asserts_path, tarball_path)
        stat = SourcePackageStatReader(tarball_path).read()
        with mock.patch(dispatcher_uri) as dispatcher:
            dispatch_package_to_modules(bk_app, tarball_path, stat, bk_user, {"main"})
        assert dispatcher.called


@pytest.mark.usefixtures("_with_heroku_24_image_conf")
@pytest.mark.parametrize(
    ("artifact", "expected_base_image_id"),
    [
        (None, "default"),
        ({"version": "1.0", "runtime": {"architecture": "amd64"}}, "default"),
        ({"version": "1.0", "runtime": {"base_image_id": "default", "architecture": "amd64"}}, "default"),
        ({"version": "1.0", "runtime": {"base_image_id": "heroku-24", "architecture": "amd64"}}, "heroku-24"),
    ],
)
def test_dispatch_cnb_package_with_base_image_id(
    bk_app, bk_module, bk_user, assets_rootpath, artifact, expected_base_image_id
):
    bk_module.name = "main"
    bk_module.save()

    with generate_temp_dir() as tempdir:
        package_dir = tempdir / "package"
        shutil.copytree(assets_rootpath / "cnb-image", package_dir)
        if artifact is not None:
            (package_dir / "artifact.json").write_text(json.dumps(artifact))
        tarball_path = tempdir / "tar.gz"
        compress_directory(package_dir, tarball_path)
        stat = SourcePackageStatReader(tarball_path).read()
        with mock.patch("paasng.platform.smart_app.services.dispatch.dispatch_cnb_image_to_registry") as dispatcher:
            dispatch_package_to_modules(bk_app, tarball_path, stat, bk_user, {"main"})

    assert dispatcher.call_count == 1
    assert dispatcher.call_args.kwargs["base_image_id"] == expected_base_image_id


@pytest.fixture()
def _with_default_image_conf_only():
    conf = {"default": {"name": "bkpaas/docker/run-heroku-bionic", "tag": "v1.0.0-smart"}}
    with mock.patch.dict(bksmart_settings.cnb_base_image.image_conf, conf, clear=True):
        yield


_UNSUPPORTED_ARTIFACTS = [
    pytest.param(
        {"version": "1.0", "runtime": {"base_image_id": "heroku-24", "architecture": "amd64"}},
        id="unconfigured-heroku-24",
    ),
    pytest.param({"version": "1.0", "runtime": {"base_image_id": "ts4", "architecture": "amd64"}}, id="unknown-id"),
    pytest.param(
        {
            "version": "1.0",
            "runtime": {"base_image_id": "default", "architecture": "amd64"},
            "app_artifacts": {"main": {"image_tar": "main.tar", "proc_entrypoints": {}}},
        },
        id="packaging-v2",
    ),
    pytest.param("not-a-json", id="invalid-json"),
    pytest.param(["default"], id="not-an-object"),
]


def _dump_artifact(artifact) -> str:
    return artifact if isinstance(artifact, str) else json.dumps(artifact)


@pytest.mark.usefixtures("_with_default_image_conf_only")
@pytest.mark.parametrize("artifact", _UNSUPPORTED_ARTIFACTS)
def test_read_cnb_base_image_id_unsupported(artifact):
    """未配置的基础镜像和新打包方案, 都应直接报错, 而不是合并到默认基础镜像上"""
    with generate_temp_dir() as workplace:
        (workplace / "artifact.json").write_text(_dump_artifact(artifact))
        with pytest.raises(UnsupportedSMartPackageError):
            read_cnb_base_image_id(workplace)


def test_read_cnb_base_image_id_incomplete_conf():
    """覆盖配置只提供了 tag 而缺失 name 时, 视为未配置"""
    with (
        mock.patch.dict(bksmart_settings.cnb_base_image.image_conf, {"heroku-24": {"tag": "v2.5.0-smart"}}),
        generate_temp_dir() as workplace,
    ):
        (workplace / "artifact.json").write_text(json.dumps({"runtime": {"base_image_id": "heroku-24"}}))
        with pytest.raises(UnsupportedSMartPackageError):
            read_cnb_base_image_id(workplace)


def _make_tarball(tempdir, files: dict, prefix: str = "./"):
    """生成 tarball, prefix 用于模拟成员名是否带 "./" 前缀"""
    tarball_path = tempdir / "package.tar.gz"
    with tarfile.open(tarball_path, mode="w:gz") as tar:
        for name, content in files.items():
            path = tempdir / name.replace("/", "_")
            path.write_text(content)
            tar.add(path, arcname=f"{prefix}{name}")
    return tarball_path


_HEROKU_24_ARTIFACT = json.dumps({"version": "1.0", "runtime": {"base_image_id": "heroku-24"}})


class TestValidateSMartPackage:
    @pytest.mark.usefixtures("_with_default_image_conf_only")
    @pytest.mark.parametrize("prefix", ["./", ""])
    @pytest.mark.parametrize("artifact", _UNSUPPORTED_ARTIFACTS)
    def test_unsupported(self, artifact, prefix):
        with generate_temp_dir() as tempdir:
            tarball_path = _make_tarball(
                tempdir,
                {".Version": "cnb-image-layers\n", "artifact.json": _dump_artifact(artifact), "app_desc.yaml": ""},
                prefix=prefix,
            )
            with pytest.raises(UnsupportedSMartPackageError):
                validate_smart_package(tarball_path)

    @pytest.mark.usefixtures("_with_default_image_conf_only")
    @pytest.mark.parametrize(
        "files",
        [
            pytest.param({"app_desc.yaml": ""}, id="source-package"),
            pytest.param({".Version": "cnb-image-layers", "app_desc.yaml": ""}, id="cnb-without-artifact"),
            pytest.param(
                {".Version": "slug-layers", "artifact.json": _HEROKU_24_ARTIFACT}, id="slug-ignores-artifact"
            ),
            pytest.param(
                {"app_desc.yaml": "", "artifact.json": _HEROKU_24_ARTIFACT}, id="no-version-flag-ignores-artifact"
            ),
            pytest.param(
                {".Version": "cnb-image-layers", "artifact.json": json.dumps({"runtime": {"architecture": "amd64"}})},
                id="cnb-without-base-image-id",
            ),
        ],
    )
    def test_supported(self, files):
        with generate_temp_dir() as tempdir:
            validate_smart_package(_make_tarball(tempdir, files))

    @pytest.mark.usefixtures("_with_heroku_24_image_conf")
    def test_heroku_24_configured(self):
        with generate_temp_dir() as tempdir:
            files = {".Version": "cnb-image-layers", "artifact.json": _HEROKU_24_ARTIFACT}
            validate_smart_package(_make_tarball(tempdir, files))

    def test_cnb_image_assets(self, assets_rootpath):
        """仓库中的 cnb-image 样例包(无 artifact.json)应能通过校验"""
        with generate_temp_dir() as tempdir:
            tarball_path = tempdir / "tar.gz"
            compress_directory(assets_rootpath / "cnb-image", tarball_path)
            validate_smart_package(tarball_path)
