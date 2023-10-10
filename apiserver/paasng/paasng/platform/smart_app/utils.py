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
import logging
from concurrent.futures import ThreadPoolExecutor
from os import PathLike
from pathlib import Path
from typing import Callable, Set

from django.utils.translation import gettext_lazy as _
from moby_distribution import ImageRef, LayerRef
from moby_distribution.registry.utils import NamedImage, parse_image
from rest_framework.exceptions import ValidationError

from paasng.infras.accounts.models import User
from paasng.platform.sourcectl.models import SourcePackage, SPStat, SPStoragePolicy
from paasng.platform.sourcectl.package.uploader import generate_storage_path, upload_to_blob_store
from paasng.platform.sourcectl.utils import generate_temp_dir, uncompress_directory
from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.platform.smart_app.detector import SourcePackageStatReader
from paasng.platform.smart_app.patcher import SourceCodePatcher
from paasng.platform.applications.models import Application
from paasng.platform.modules.models.module import Module
from paasng.platform.modules.models.runtime import AppSlugRunner

logger = logging.getLogger(__name__)


def get_app_description(stat: SPStat) -> ApplicationDesc:
    """Get application description object from source package stats

    :raises: ValidationError when meta info is invalid or empty
    """
    if not stat.meta_info:
        raise ValidationError(_('找不到任何有效的应用描述信息'))

    try:
        desc = get_desc_handler(stat.meta_info).app_desc
    except DescriptionValidationError as e:
        raise ValidationError(str(e))
    return desc


def get_deploy_description(stat: SPStat) -> DeploymentDesc:
    """Get deployment description object from source package stats

    :raises: ValidationError when meta info is invalid or empty
    """
    if not stat.meta_info:
        raise ValidationError(_('找不到任何有效的应用描述信息'))

    try:
        desc = get_desc_handler(stat.meta_info).get_deploy_desc(None)
    except DescriptionValidationError as e:
        raise ValidationError(str(e))
    return desc


class SMartImageManager:
    def __init__(self, module: Module):
        self.module = module

    def get_base_image_info(self) -> NamedImage:
        """获取 S-Mart 应用的基础镜像的信息"""
        if bksmart_settings.base_image.name and bksmart_settings.base_image.tag:
            return NamedImage(
                domain=bksmart_settings.registry.host,
                name=bksmart_settings.base_image.name,
                tag=bksmart_settings.base_image.tag,
            )

        default_runner = AppSlugRunner.objects.filter(region=self.module.region, is_default=True).first()
        if not default_runner:
            raise ValueError("Unknown base image for S-Mart")
        named = parse_image(default_runner.image, default_registry=bksmart_settings.registry.host)
        return named

    def get_image_info(self, tag: str = "latest") -> NamedImage:
        """获取当前 S-Mart 应用的镜像信息"""
        # TODO: bkrepo 支持 https 访问后去除该逻辑.
        if ":80" in bksmart_settings.registry.host:
            host = bksmart_settings.registry.host.replace(":80", "")
        else:
            host = bksmart_settings.registry.host

        return NamedImage(
            domain=host,
            name=f"{bksmart_settings.registry.namespace}/{self.module.application.code}/{self.module.name}",
            tag=tag,
        )


# A flag value for parallel patching, turned on by default. A unittest might patch this value to
# alter the behaviour.
_PARALLEL_PATCHING = True


def dispatch_package_to_modules(
    application: Application, tarball_filepath: PathLike, stat: SPStat, operator: User, modules: Set[str]
):
    """Dispatch package to those modules which mentioned in args modules"""
    # TODO: 优化分发镜像的逻辑(如果存在多个模块用同一个镜像层, 那么应该只上传一次镜像)
    with generate_temp_dir() as workplace:
        uncompress_directory(source_path=tarball_filepath, target_path=workplace)

        handler: Callable[[Module, Path, SPStat, User], SourcePackage]
        builder_flag = workplace / ".Version"

        if builder_flag.exists():
            tasks = [(module, workplace, stat, operator) for module in application.modules.filter(name__in=modules)]
            handler = dispatch_image_to_registry
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


def patch_and_store_package(module: Module, tarball_filepath: Path, stat: SPStat, operator: User):
    """Patch an uncompressed package and upload compressed tarball one blobstore,
    then bind the package to provided module."""
    logger.debug("Patching module for module '%s'", module.name)
    with generate_temp_dir() as workplace:
        dest = SourceCodePatcher.patch_tarball(module, tarball_path=tarball_filepath, working_dir=workplace, stat=stat)
        stat = SourcePackageStatReader(dest).read()

        # store package to blobstore
        obj_key = generate_storage_path(module, stat=stat)
        obj_url = upload_to_blob_store(dest, key=obj_key, allow_overwrite=True)

        # bind package to module
        policy = SPStoragePolicy(path=obj_key, url=obj_url, stat=stat, allow_overwrite=True)
        source_package = SourcePackage.objects.store(module, policy, operator=operator)
        return source_package


def dispatch_image_to_registry(module: Module, workplace: Path, stat: SPStat, operator: User):
    """Merge Image Layer to BaseImage, then push the new image to registry"""
    logger.debug("dispatching image for module '%s', working '%s'", module.name, workplace)

    client = bksmart_settings.registry.get_client()

    desc_handler = get_desc_handler(stat.meta_info)
    deploy_desc = desc_handler.get_deploy_desc(module.name)

    layer_path = workplace / stat.relative_path / deploy_desc.source_dir / "layer.tar.gz"
    procfile_path = workplace / stat.relative_path / deploy_desc.source_dir / f"{module.name}.Procfile.tar.gz"

    mgr = SMartImageManager(module)
    base_image = mgr.get_base_image_info()
    new_image_info = mgr.get_image_info(tag=stat.version)

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
    manifest = image_ref.push()

    stat.name = stat.version
    stat.sha256_signature = manifest.config.digest.replace("sha256:", "")
    policy = SPStoragePolicy(
        path=new_image_info.name,
        url=f"{new_image_info.domain}/{new_image_info.name}:{new_image_info.tag}",
        stat=stat,
        allow_overwrite=True,
        engine="docker",
    )
    source_package = SourcePackage.objects.store(module, policy, operator=operator)
    return source_package
