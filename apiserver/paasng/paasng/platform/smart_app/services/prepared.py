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

from os import PathLike
from pathlib import Path
from typing import Tuple

from django.http.request import HttpRequest
from django.utils.text import slugify

from paasng.platform.smart_app.exceptions import PreparedPackageNotFound
from paasng.platform.sourcectl.package.downloader import download_file_via_url
from paasng.platform.sourcectl.package.uploader import upload_to_blob_store


class PreparedSourcePackage:
    """Upload a package to remote backend and store info in session for later usage"""

    _package_path_key = "prepared_package_path"

    def __init__(self, request: HttpRequest, namespace: str = "default"):
        self.request = request
        self._username = request.user.username
        self.path_key = self._package_path_key
        self.namespace = namespace

    def generate_storage_path(self, file_path: PathLike) -> str:
        """Generate storage path for current request"""
        basename, sep, suffix = Path(file_path).name.partition(".")
        filename = "".join([slugify(basename), sep, suffix])
        return f"prepared_packages/{self._username}:{self.namespace}:{filename}"

    def store(self, filepath: PathLike):
        """Store a local package file to remote storage backend"""
        store_path = self.generate_storage_path(filepath)
        obj_url = upload_to_blob_store(filepath, key=store_path, allow_overwrite=True)

        # Store the remote path and filename to session for later usage
        self.request.session[self._package_path_key] = [obj_url, Path(filepath).name]

    def get_stored_info(self) -> Tuple[str, str]:
        """Get the stored package URL and filename without downloading

        :return: A tuple of (store_url, filename)
        :raises PreparedPackageNotFound: If no package has been stored yet
        """
        store_url, filename = self.request.session.get(self._package_path_key)
        if not store_url:
            raise PreparedPackageNotFound("not prepared package has been uploaded yet")
        return store_url, filename

    def retrieve(self, output_dir: PathLike) -> PathLike:
        """Retrieve the previously uploaded source package path

        :param output_dir: a file path where the uploaded package will be downloaded into
        :return output_path
        """
        store_url, filename = self.get_stored_info()
        output_path = Path(output_dir) / filename

        # TODO: don't use dummy url, replace with the real one.
        download_file_via_url(url=store_url, local_path=output_path)
        return output_path
