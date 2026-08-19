import pytest

from app_spark_api.repository.storage.backends import HostTmpPath
from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.models import ProjectSourceStorage

pytestmark = pytest.mark.django_db


def test_project_source_storage_builds_backend(project, tmp_path):
    package_path = tmp_path / "source.tgz"
    source_storage = ProjectSourceStorage.objects.create(
        project=project,
        backend=StorageBackend.HOST_TMP_PATH,
        config={"path": str(package_path)},
    )

    backend = source_storage.get_backend()

    assert isinstance(backend, HostTmpPath)
    assert backend.path == package_path
    assert project.source_storage == source_storage
