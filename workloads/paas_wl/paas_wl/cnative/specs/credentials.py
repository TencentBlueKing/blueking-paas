from contextlib import contextmanager
from typing import Dict, Iterator, List

from paas_wl.cnative.specs.constants import IMAGE_CREDENTIALS_REF_ANNO_KEY
from paas_wl.platform.applications.models import App
from paas_wl.platform.applications.struct_models import Application
from paas_wl.resources.base import kres
from paas_wl.workloads.images.entities import ImageCredentialsManager as _ImageCredentialsManager
from paas_wl.workloads.images.models import AppUserCredential, ImageCredentialRef


def split_image(repository: str) -> str:
    return repository.rsplit(":", 1)[0]


def get_references(manifest: Dict) -> List[ImageCredentialRef]:
    """get image credentials references from manifest annotations

    :raise: ValueError if the value is an invalid json
    """
    annotations = manifest["metadata"]["annotations"]
    processes = manifest["spec"]["processes"]
    # dynamic build references from annotations
    refs = []
    for process in processes:
        proc_name = process["name"]
        anno_key = f"{IMAGE_CREDENTIALS_REF_ANNO_KEY}.{proc_name}"
        if anno_key not in annotations:
            continue
        refs.append(ImageCredentialRef(image=split_image(process["image"]), credential_name=annotations[anno_key]))
    return refs


def validate_references(application: Application, references: List[ImageCredentialRef]):
    """validate if the reference credentials is defined

    :raises: ValueError if the reference credentials is undefined
    TODO: 验证 credential 是否可以拉取对应的镜像
    """
    request_names = {ref.credential_name for ref in references}
    all_names = set(AppUserCredential.objects.list_all_name(application))
    if missing_names := request_names - all_names:
        raise ValueError(f"missing credentials {missing_names}")


class ImageCredentialsManager(_ImageCredentialsManager):
    """An ImageCredentialsManager using given k8s client, the client must be closed by outer logic"""

    def __init__(self, client):
        super().__init__()
        self._client = client

    def _kres(self, app: App, api_version: str = '') -> Iterator[kres.BaseKresource]:
        """return kres object using given k8s client"""
        yield self.entity_type.Meta.kres_class(self._client, api_version=api_version)

    kres = contextmanager(_kres)
