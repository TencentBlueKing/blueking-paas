from typing import Dict

import pytest
from django.db.models import ObjectDoesNotExist
from django_dynamic_fixture import G

from paas_wl.cnative.specs.constants import IMAGE_CREDENTIALS_REF_ANNO_KEY
from paas_wl.cnative.specs.credentials import get_references, validate_references
from paas_wl.workloads.images.models import AppImageCredential, AppUserCredential, ImageCredentialRef

pytestmark = pytest.mark.django_db


def build_manifest(refs: Dict[str, str], processes: Dict[str, str]) -> Dict:
    return {
        "metadata": {
            "annotations": {f"{IMAGE_CREDENTIALS_REF_ANNO_KEY}.{proc}": ref_name for proc, ref_name in refs.items()}
        },
        "spec": {"processes": [{"name": name, "image": image} for name, image in processes.items()]},
    }


@pytest.mark.parametrize(
    "manifest, expected",
    [
        (build_manifest({}, {}), []),
        (build_manifest({"foo": "example"}, {}), []),
        (build_manifest({}, {"foo": "nginx:latest"}), []),
        (
            build_manifest({"foo": "example"}, {"foo": "nginx:latest"}),
            [ImageCredentialRef(image="nginx", credential_name="example")],
        ),
    ],
)
def test_get_references(manifest, expected):
    assert get_references(manifest) == expected


def test_validate_references(bk_app):
    references = [ImageCredentialRef(image="foo", credential_name="example")]
    with pytest.raises(ValueError):
        validate_references(bk_app, references)

    G(AppUserCredential, application_id=bk_app.id, name="example", username="username")
    validate_references(bk_app, references)


def test_save_image_credentials_missing(bk_app, fake_app):
    references = [ImageCredentialRef(image="foo", credential_name="example")]
    with pytest.raises(ObjectDoesNotExist):
        AppImageCredential.objects.flush_from_refs(bk_app, fake_app, references)


def test_save_image_credentials(bk_app, fake_app):
    G(AppUserCredential, application_id=bk_app.id, name="example", username="username")
    references = [ImageCredentialRef(image="foo", credential_name="example")]
    assert AppImageCredential.objects.filter(app=fake_app).count() == 0

    AppImageCredential.objects.flush_from_refs(bk_app, fake_app, references)
    assert AppImageCredential.objects.filter(app=fake_app).count() == 1

    references = [ImageCredentialRef(image="bar", credential_name="example")]
    AppImageCredential.objects.flush_from_refs(bk_app, fake_app, references)
    assert AppImageCredential.objects.filter(app=fake_app).count() == 1
    assert AppImageCredential.objects.get(app=fake_app).username == "username"
