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
from concurrent.futures import ThreadPoolExecutor
from os import PathLike
from pathlib import Path
from typing import Callable, List, Set

from moby_distribution import ImageJSON, ImageRef, LayerRef

from paasng.infras.accounts.models import User
from paasng.platform.applications.models import Application, SMartAppExtraInfo
from paasng.platform.declarative.handlers import get_source_dir_from_desc
from paasng.platform.modules.models import Module
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.platform.smart_app.constants import SMartPackageBuilderVersionFlag
from paasng.platform.smart_app.entities import DockerExportedImageManifest
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.image_mgr import SMartImageManager
from paasng.platform.smart_app.services.patcher import patch_smart_tarball
from paasng.platform.sourcectl.models import SourcePackage, SPStat, SPStoragePolicy
from paasng.platform.sourcectl.package.uploader import generate_storage_path, upload_to_blob_store
from paasng.platform.sourcectl.utils import generate_temp_dir, uncompress_directory
from paasng.utils.text import remove_prefix

logger = logging.getLogger(__name__)

# A flag value for parallel patching, turned on by default. A unittest might patch this value to
# alter the behaviour.
_PARALLEL_PATCHING = True


def dispatch_package_to_modules(
    application: Application, tarball_filepath: PathLike, stat: SPStat, operator: User, modules: Set[str]
) -> List[SourcePackage]:
    """Dispatch package to those modules which mentioned in args modules"""
    # TODO: 优化分发镜像的逻辑(如果存在多个模块用同一个镜像层, 那么应该只上传一次镜像)
    with generate_temp_dir() as workplace:
        uncompress_directory(source_path=tarball_filepath, target_path=workplace)

        handler: Callable[[Module, Path, SPStat, User], SourcePackage]
        builder_flag = workplace / ".Version"
        if builder_flag.exists():
            version = builder_flag.read_text().strip()
            if version == SMartPackageBuilderVersionFlag.CNB_IMAGE_LAYERS:
                parse_and_save_cnb_metadata(application, workplace)
                handler = dispatch_cnb_image_to_registry
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
                results = executor.map(handler, *zip(*tasks))
            return list(results)
        else:
            # Execute Sequentially
            packages = []
            for task in tasks:
                packages.append(handler(*task))
            return packages


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

    layer_path = workplace / stat.relative_path / source_dir / "layer.tar.gz"
    procfile_path = workplace / stat.relative_path / source_dir / f"{module.name}.Procfile.tar.gz"

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


def dispatch_cnb_image_to_registry(module: Module, workplace: Path, stat: SPStat, operator: User) -> SourcePackage:
    """Merge image layer to base image, then push the new image to registry"""
    logger.debug("dispatching cnb-image for module '%s', working at '%s'", module.name, workplace)

    mgr = SMartImageManager(module)
    base_image = mgr.get_cnb_runner_image_info()
    new_image_info = mgr.get_image_info(tag=stat.version)

    smart_app_extra = SMartAppExtraInfo.objects.get(app=module.application)
    image_tar = smart_app_extra.get_image_tar(module.name)

    image_tarball = workplace / image_tar
    with generate_temp_dir() as image_tmp_folder:
        uncompress_directory(source_path=image_tarball, target_path=image_tmp_folder)

        client = bksmart_settings.registry.get_client()
        image_ref = ImageRef.from_image(
            from_repo=base_image.name,
            from_reference=base_image.tag,
            to_repo=new_image_info.name,
            to_reference=new_image_info.tag,
            client=client,
        )

        tarball_manifest = _construct_exported_image_manifest(image_tmp_folder)

        # merge image json at first.
        # cnb_layers_image_json.config contains Env, default Entrypoint.
        base_image_json = image_ref.image_json
        cnb_layers_image_json = ImageJSON(**json.loads((image_tmp_folder / tarball_manifest.config).read_text()))
        base_image_json.config = cnb_layers_image_json.config
        image_ref._initial_config = base_image_json.json(
            exclude_unset=True, exclude_defaults=True, separators=(",", ":")
        )

        for layer_path in tarball_manifest.layers:
            image_ref.add_layer(LayerRef(local_path=image_tmp_folder / layer_path))
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


def parse_and_save_cnb_metadata(application: Application, workplace: Path):
    """解析 cnb 制品的元数据, 并将相关构建元数据写入 SMartAppExtraInfo

    构建元数据包括:
    - use_cnb 标记
    - 各模块进程的 entrypoints(如果有, 从 artifact.json 解析)
    - 各模块使用的 image_tar(如果有, 从 artifact.json 解析)

    artifact.json 格式为:
    {
       "module1": {"image_tar": "module1.tar", "proc_entrypoints": {进程名: 具体的 entrypoint}},
       "module2": {"image_tar": "module2.tar", "proc_entrypoints": {进程名: 具体的 entrypoint}}
     }
    """
    smart_app_extra = SMartAppExtraInfo.objects.get(app=application)
    smart_app_extra.set_use_cnb_flag(True)

    artifact_json_file = workplace / "artifact.json"
    if not artifact_json_file.exists():
        return

    artifact_json = json.loads(artifact_json_file.read_text())
    for module_name in artifact_json:
        smart_app_extra.set_proc_entrypoints(module_name, artifact_json[module_name]["proc_entrypoints"])
        smart_app_extra.set_image_tar(module_name, artifact_json[module_name]["image_tar"])


def _construct_exported_image_manifest(image_tmp_folder: Path) -> DockerExportedImageManifest:
    """基于 oci 镜像层文件, 生成对应的 DockerExportedImageManifest.

    生成 DockerExportedImageManifest 分为两种情况:
    - 制品中包含 manifest.json 时, 直接解析 manifest.json
    manifest.json 文件内容示例:
    [
        {
            "Config": "blobs/sha256/1403d9c60d0a0f24a305913e527e19fece5fd3acd1f00296e42df099ec50d371",
            "Layers": [
                "blobs/sha256/5e0230e216a7bbefb83517665bd5a48ee140bee0238e69f240a9d4e32e14c0ac",
                "blobs/sha256/913346a9a60b8aef7ef9c325d3826b9f684af3dd4bfe11cffea65ab56ae24c39",
                ...,
            ],
             "RepoTags": [
                "local/default:latest"
            ],
            "LayerSources": {...},
        }
    ]

    - 制品中不包含 manifest.json 时, 解析 index.json
    index.json 文件内容示例:
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": "sha256:a287e58837548de0da8e65f69bcf0d4bf45c5de2c964631b0f37443b30541c68",
                ...,
            }
        ]
    }
    文件中指向了 manifest 的 digest 信息, 因此需要进行转换才能生成符合 DockerExportedImageManifest 协议的数据
    """
    if (manifest_file := image_tmp_folder / "manifest.json") and manifest_file.exists():
        return DockerExportedImageManifest(**json.loads(manifest_file.read_text())[0])

    # 没有 manifest.json 时, 解析 index.json 文件
    index_json = json.loads((image_tmp_folder / "index.json").read_text())
    manifest_digest = index_json["manifests"][0]["digest"]
    manifest_file = image_tmp_folder / f"blobs/{manifest_digest.replace(':', '/')}"

    manifest = json.loads(manifest_file.read_text())
    config_digest = manifest["config"]["digest"]

    config = f"blobs/{config_digest.replace(':', '/')}"
    layers = [f"blobs/{layer['digest'].replace(':', '/')}" for layer in manifest["layers"]]
    return DockerExportedImageManifest(Config=config, Layers=layers)
