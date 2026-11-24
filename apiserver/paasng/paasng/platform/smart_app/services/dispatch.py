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

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from os import PathLike
from pathlib import Path
from typing import Callable, List, Set

from django.conf import settings
from django.utils.translation import gettext as _
from moby_distribution import ImageJSON, ImageRef, LayerRef

from paasng.infras.accounts.models import User
from paasng.platform.applications.models import Application
from paasng.platform.declarative.handlers import get_source_dir_from_desc
from paasng.platform.modules.models import Module
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.platform.smart_app.constants import SMartPackageBuilderVersionFlag
from paasng.platform.smart_app.entities import DockerExportedImageManifest
from paasng.platform.smart_app.exceptions import UnsupportedSMartPackageError
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.image_mgr import SMartImageManager
from paasng.platform.smart_app.services.patcher import patch_smart_tarball
from paasng.platform.sourcectl.models import SourcePackage, SPStat, SPStoragePolicy
from paasng.platform.sourcectl.package.uploader import generate_storage_path, upload_to_blob_store
from paasng.platform.sourcectl.utils import generate_temp_dir, uncompress_directory
from paasng.utils.dictx import get_items
from paasng.utils.file import safe_resolve_subpath
from paasng.utils.text import remove_prefix

logger = logging.getLogger(__name__)

# A flag value for parallel patching, turned on by default. A unittest might patch this value to
# alter the behaviour.
_PARALLEL_PATCHING = True

_BUILDER_FLAG_FILENAME = ".Version"
_ARTIFACT_FILENAME = "artifact.json"


def dispatch_package_to_modules(
    application: Application, tarball_filepath: PathLike, stat: SPStat, operator: User, modules: Set[str]
) -> List[SourcePackage]:
    """Dispatch package to those modules which mentioned in args modules"""
    # TODO: 优化分发镜像的逻辑(如果存在多个模块用同一个镜像层, 那么应该只上传一次镜像)
    with generate_temp_dir() as workplace:
        uncompress_directory(source_path=tarball_filepath, target_path=workplace)

        handler: Callable[[Module, Path, SPStat, User], SourcePackage]
        builder_flag = workplace / _BUILDER_FLAG_FILENAME
        if builder_flag.exists():
            version = builder_flag.read_text().strip()
            if version == SMartPackageBuilderVersionFlag.CNB_IMAGE_LAYERS:
                handler = partial(dispatch_cnb_image_to_registry, base_image_id=read_cnb_base_image_id(workplace))
            else:
                handler = dispatch_slug_image_to_registry
            tasks = [(module, workplace, stat, operator) for module in application.modules.filter(name__in=modules)]
        else:
            tasks = [
                (module, Path(tarball_filepath), stat, operator)
                for module in application.modules.filter(name__in=modules)
            ]
            handler = patch_and_store_package

        if _PARALLEL_PATCHING:
            with ThreadPoolExecutor() as executor:
                results = executor.map(handler, *zip(*tasks, strict=False))
            return list(results)
        else:
            # Execute Sequentially
            packages = []
            for task in tasks:
                packages.append(handler(*task))
            return packages


def validate_smart_package(tarball_filepath: PathLike):
    """在创建应用或写入数据之前, 校验当前平台能否部署该 S-Mart 包, 避免分发镜像时才失败

    :raises UnsupportedSMartPackageError: 包的基础镜像未配置, 或使用了不支持的打包方案
    """
    reader = SourcePackageStatReader(tarball_filepath)
    with reader.accessor(reader.path) as archive:
        # 成员名可能带 "./" 前缀, 统一按规范化后的路径匹配
        members = {os.path.normpath(name): name for name in archive.list()}
        # 没有 artifact.json 的包总是使用默认基础镜像, 无需额外读取文件
        if _ARTIFACT_FILENAME not in members or _BUILDER_FLAG_FILENAME not in members:
            return

        version = archive.read_file(members[_BUILDER_FLAG_FILENAME]).decode().strip()
        if version != SMartPackageBuilderVersionFlag.CNB_IMAGE_LAYERS:
            return
        parse_cnb_base_image_id(archive.read_file(members[_ARTIFACT_FILENAME]))


def read_cnb_base_image_id(workplace: Path) -> str:
    """从已解压的 S-Mart 包中读取基础镜像 ID, 没有 artifact.json 时使用默认基础镜像

    :raises UnsupportedSMartPackageError: 包的基础镜像未配置, 或使用了不支持的打包方案
    """
    artifact_json_file = workplace / _ARTIFACT_FILENAME
    if not artifact_json_file.exists():
        return settings.SMART_CNB_DEFAULT_IMAGE_ID
    return parse_cnb_base_image_id(artifact_json_file.read_bytes())


def parse_cnb_base_image_id(artifact_content: bytes) -> str:
    """解析 artifact.json 内容, 返回基础镜像 ID, 未声明时使用默认基础镜像

    artifact.json 格式为:
    {"version": "1.0", "runtime": {"base_image_id": "heroku-24", "architecture": "amd64"}}

    :raises UnsupportedSMartPackageError: 包含 app_artifacts(多模块共享镜像的新打包方案), 或基础镜像 ID 未配置
    """
    try:
        artifact = json.loads(artifact_content)
    except ValueError:
        raise UnsupportedSMartPackageError(_("S-Mart 包中的 artifact.json 不是合法的 JSON"))
    if not isinstance(artifact, dict):
        raise UnsupportedSMartPackageError(_("S-Mart 包中的 artifact.json 格式错误"))

    if "app_artifacts" in artifact:
        raise UnsupportedSMartPackageError(
            _("当前平台不支持 artifact.json 中包含 app_artifacts 的打包方案, 请使用 v1 打包方案重新构建")
        )

    base_image_id = get_items(artifact, "runtime.base_image_id") or settings.SMART_CNB_DEFAULT_IMAGE_ID
    if not bksmart_settings.cnb_base_image.is_supported(base_image_id):
        raise UnsupportedSMartPackageError(
            _("当前平台未配置 S-Mart 基础镜像 {base_image_id}, 请联系管理员").format(base_image_id=base_image_id)
        )
    return base_image_id


def patch_and_store_package(module: Module, tarball_filepath: Path, stat: SPStat, operator: User) -> SourcePackage:
    """Patch an uncompressed package and upload compressed tarball one blobstore,
    then bind the package to provided module.

    [deprecated] `patch_and_store_package` is a handler for legacy package which only contain source code.
    """
    logger.debug("Patching module for module '%s'", module.name)
    with generate_temp_dir() as workplace:
        dest = patch_smart_tarball(tarball_path=tarball_filepath, dest_dir=workplace, module=module, stat=stat)
        stat = SourcePackageStatReader(dest).read()

        # store package to blobstore
        obj_key = generate_storage_path(module, stat=stat)
        obj_url = upload_to_blob_store(dest, key=obj_key, allow_overwrite=True)

        # bind package to module
        policy = SPStoragePolicy(path=obj_key, url=obj_url, stat=stat, allow_overwrite=True)
        source_package = SourcePackage.objects.store(module, policy, operator=operator)
        return source_package


def dispatch_slug_image_to_registry(module: Module, workplace: Path, stat: SPStat, operator: User) -> SourcePackage:
    """Merge image layer to base image, then push the new image to registry

    [deprecated] `dispatch_slug_image_to_registry` is a handler for s-mart which is built with slug-pilot.
    """
    logger.debug("dispatching slug-image for module '%s', working at '%s'", module.name, workplace)

    source_dir = get_source_dir_from_desc(stat.meta_info, module.name)

    base_path = workplace / stat.relative_path
    layer_path = safe_resolve_subpath(base_path, f"{source_dir}/layer.tar.gz")
    procfile_path = safe_resolve_subpath(base_path, f"{source_dir}/{module.name}.Procfile.tar.gz")

    mgr = SMartImageManager(module)
    base_image = mgr.get_slugrunner_image_info()
    new_image_info = mgr.get_image_info(tag=stat.version)

    client = bksmart_settings.registry.get_client()
    image_ref = ImageRef.from_image(
        from_repo=base_image.name,
        from_reference=base_image.tag,
        to_repo=new_image_info.name,
        to_reference=new_image_info.tag,
        client=client,
    )
    image_ref.add_layer(LayerRef(local_path=layer_path))
    image_ref.add_layer(LayerRef(local_path=procfile_path))

    logger.debug("Start pushing Image.")
    manifest = image_ref.push(max_worker=5 if _PARALLEL_PATCHING else 1)

    stat.sha256_signature = remove_prefix(manifest.config.digest, "sha256:")
    policy = SPStoragePolicy(
        path=new_image_info.name,
        url=f"{new_image_info.domain}/{new_image_info.name}:{new_image_info.tag}",
        stat=stat,
        allow_overwrite=True,
        engine="docker",
    )
    source_package = SourcePackage.objects.store(module, policy, operator=operator)
    return source_package


def dispatch_cnb_image_to_registry(
    module: Module,
    workplace: Path,
    stat: SPStat,
    operator: User,
    base_image_id: str,
) -> SourcePackage:
    """Merge image layer to base image, then push the new image to registry

    :param base_image_id: 基础镜像 ID, 决定镜像层合并到哪个 run image 上
    """
    logger.debug(
        "dispatching cnb-image for module '%s', working at '%s', base image id '%s'",
        module.name,
        workplace,
        base_image_id,
    )

    mgr = SMartImageManager(module)
    base_image = mgr.get_cnb_runner_image_info(base_image_id=base_image_id)
    new_image_info = mgr.get_image_info(tag=stat.version)

    image_tarball = (workplace / module.name).with_suffix(".tgz")
    with generate_temp_dir() as image_tmp_folder:
        uncompress_directory(source_path=image_tarball, target_path=image_tmp_folder)
        # 解析 manifest.json 文件的第一个镜像, 逐层上传
        tarball_manifest = DockerExportedImageManifest(
            **json.loads((image_tmp_folder / "manifest.json").read_text())[0]
        )

        client = bksmart_settings.registry.get_client()
        image_ref = ImageRef.from_image(
            from_repo=base_image.name,
            from_reference=base_image.tag,
            to_repo=new_image_info.name,
            to_reference=new_image_info.tag,
            client=client,
        )

        # merge image json at first.
        # cnb_layers_image_json.config contains Env, default Entrypoint.
        base_image_json = image_ref.image_json
        config_path = safe_resolve_subpath(image_tmp_folder, tarball_manifest.config)
        cnb_layers_image_json = ImageJSON(**json.loads(config_path.read_text()))
        base_image_json.config = cnb_layers_image_json.config
        image_ref._initial_config = base_image_json.json(
            exclude_unset=True, exclude_defaults=True, separators=(",", ":")
        )

        for layer_path in tarball_manifest.layers:
            image_ref.add_layer(LayerRef(local_path=safe_resolve_subpath(image_tmp_folder, layer_path)))
        logger.debug("Start pushing Image.")

        manifest = image_ref.push(max_worker=5 if _PARALLEL_PATCHING else 1)

    stat.sha256_signature = remove_prefix(manifest.config.digest, "sha256:")
    policy = SPStoragePolicy(
        path=new_image_info.name,
        url=f"{new_image_info.domain}/{new_image_info.name}:{new_image_info.tag}",
        stat=stat,
        allow_overwrite=True,
        engine="docker",
    )
    source_package = SourcePackage.objects.store(module, policy, operator=operator)
    return source_package
