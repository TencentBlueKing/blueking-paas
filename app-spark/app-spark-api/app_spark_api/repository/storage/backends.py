import abc
import os
import shutil
import tempfile
from collections.abc import Mapping
from os import PathLike
from pathlib import Path

from blue_krill.storages.blobstore.bkrepo import BKGenericRepo
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.entities import BkRepoConfig, HostTmpPathConfig, structure_storage_config
from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.repository.storage.utils import compress_directory, generate_temp_file, uncompress_directory

StrPath = str | PathLike[str]


class SourceStorage(abc.ABC):
    """Storage for the current source snapshot of a Project.

    Implementations only need to transfer the compressed package. This base
    class owns the directory validation and tgz compression lifecycle.
    """

    def store(self, source_dir: StrPath) -> None:
        """Compress and replace the current source snapshot.

        :param source_dir: Existing source directory to package and persist.
        :raises NotADirectoryError: If ``source_dir`` is not an existing directory.
        """
        source_path = Path(source_dir)
        if not source_path.is_dir():
            raise NotADirectoryError(f"Source directory does not exist: {source_path}")

        with generate_temp_file(suffix=".tgz") as package_path:
            compress_directory(source_path, package_path)
            self._store_package(package_path)

    def get(self, target_dir: StrPath) -> Path:
        """Extract the current source snapshot into an empty directory.

        :param target_dir: Missing or empty directory that will receive the source files.
        :return: The normalized target directory path.
        :raises NotADirectoryError: If ``target_dir`` exists and is not a directory.
        :raises ValueError: If ``target_dir`` is not empty.
        """
        target_path = Path(target_dir)
        if target_path.exists():
            if not target_path.is_dir():
                raise NotADirectoryError(f"Target path is not a directory: {target_path}")
            if any(target_path.iterdir()):
                raise ValueError(f"Target directory must be empty: {target_path}")
        else:
            target_path.mkdir(parents=True)

        with generate_temp_file(suffix=".tgz") as package_path:
            self._get_package(package_path)
            uncompress_directory(package_path, target_path)
        return target_path

    @abc.abstractmethod
    def _store_package(self, package_path: Path) -> None:
        """Persist a local tgz package.

        :param package_path: Path to the generated tgz package.
        """

    @abc.abstractmethod
    def _get_package(self, package_path: Path) -> None:
        """Fetch the persisted tgz package into a local path.

        :param package_path: Local path where the tgz package should be written.
        """


class HostTmpPath(SourceStorage):
    """Store a source package at a path on the current host.

    :param path: Host path where the tgz source package is persisted.
    """

    def __init__(self, path: StrPath):
        self.path = Path(path)

    def _store_package(self, package_path: Path) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            # Write beside the destination so os.replace remains atomic on one filesystem.
            with tempfile.NamedTemporaryFile(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
            shutil.copyfile(package_path, temporary_path)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def _get_package(self, package_path: Path) -> None:
        shutil.copyfile(self.path, package_path)


class BkRepo(SourceStorage):
    """Store source packages in a BlueKing generic artifact repository.

    :param bucket: Name of the BkRepo generic repository.
    :param key: Object key used for the current Project source package.
    """

    def __init__(self, bucket: str, key: str):
        self.key = key
        config = settings.BLOBSTORE_BKREPO_CONFIG
        if not isinstance(config, Mapping):
            raise ImproperlyConfigured("BLOBSTORE_BKREPO_CONFIG must be configured for the BkRepo backend")

        required_settings = {"PROJECT", "ENDPOINT", "USERNAME", "PASSWORD"}
        if missing := required_settings - config.keys():
            fields = ", ".join(sorted(missing))
            raise ImproperlyConfigured(f"BLOBSTORE_BKREPO_CONFIG is missing fields: {fields}")

        self.client = BKGenericRepo(
            bucket=bucket,
            project=config["PROJECT"],
            endpoint_url=config["ENDPOINT"],
            username=config["USERNAME"],
            password=config["PASSWORD"],
        )

    def _store_package(self, package_path: Path) -> None:
        self.client.upload_file(package_path, self.key, allow_overwrite=True)

    def _get_package(self, package_path: Path) -> None:
        self.client.download_file(key=self.key, filepath=package_path)


def make_storage_backend(backend: str, config: object) -> SourceStorage:
    """Build a source storage backend from persisted model configuration.

    Example::

        storage = make_storage_backend(
            StorageBackend.HOST_TMP_PATH,
            {"path": "/tmp/app-spark/project-source.tgz"},
        )
        storage.store("/tmp/app-spark/project-source")

    :param backend: A value from :class:`StorageBackend` identifying the storage engine.
    :param config: Backend-specific configuration mapping. HostTmpPath requires
        ``path``; BkRepo requires ``bucket`` and ``key``.
    :return: A validated storage backend instance.
    :raises StorageConfigurationError: If the backend is unknown or the configuration
        cannot be structured into the corresponding attrs model.
    """
    try:
        storage_backend = StorageBackend(backend)
    except ValueError as exc:
        raise StorageConfigurationError(f"Unknown storage backend: {backend}") from exc

    if storage_backend == StorageBackend.HOST_TMP_PATH:
        host_config = structure_storage_config(config, HostTmpPathConfig)
        return HostTmpPath(path=host_config.path)

    if storage_backend == StorageBackend.BK_REPO:
        bkrepo_config = structure_storage_config(config, BkRepoConfig)
        return BkRepo(bucket=bkrepo_config.bucket, key=bkrepo_config.key)

    raise StorageConfigurationError(f"Unsupported storage backend: {storage_backend}")
