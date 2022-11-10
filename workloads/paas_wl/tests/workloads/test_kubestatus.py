import pytest
from kubernetes.client.models import V1Container, V1Pod, V1PodSpec
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.utils.kubestatus import (
    HealthStatus,
    HealthStatusType,
    extract_exit_code,
    get_any_container_fail_message,
    parse_pod,
)


def make_status(
    message: str = "", reason: str = "", status: HealthStatusType = HealthStatusType.UNKNOWN
) -> HealthStatus:
    return HealthStatus(message=message, reason=reason, status=status)


@pytest.mark.parametrize(
    "instance, expected",
    [
        (ResourceInstance(None, {"kind": ""}), V1Pod(kind="")),
        (ResourceInstance(None, {"kind": "Pod"}), V1Pod(kind="Pod")),
        (
            ResourceInstance(None, {"kind": "Pod", "spec": {"containers": [{"name": "foo"}]}}),
            V1Pod(kind="Pod", spec=V1PodSpec(containers=[V1Container(name="foo")])),
        ),
        pytest.param(
            ResourceInstance(None, {"kind": "Pod", "spec": {}}), None, marks=pytest.mark.xfail(raises=ValueError)
        ),
    ],
)
def test_parse_pod(instance, expected):
    assert parse_pod(instance) == expected


@pytest.mark.parametrize(
    "health_status, expected",
    [
        (make_status(message="foo"), None),
        (make_status(message="failed with exit code 0"), 0),
        (make_status(message="failed with exit code 1111111111"), 1111111111),
        (make_status(message="failed with exit code -1"), -1),
    ],
)
def test_extract_exit_code(health_status, expected):
    assert extract_exit_code(health_status) == expected


def make_container_status(state: dict, last_state: dict):
    return {
        "image": "",
        "imageID": "",
        "name": "",
        "ready": True,
        "restartCount": 0,
        "state": state,
        "lastState": last_state,
    }


@pytest.mark.parametrize(
    "container_statuses, expected",
    [
        ([], None),
        (
            [make_container_status({}, {})],
            None,
        ),
        (
            [make_container_status({"terminated": {"message": "foo", "exitCode": 1}}, {})],
            "foo",
        ),
        (
            [make_container_status({"terminated": {"reason": "OOMKilled", "exitCode": 1}}, {})],
            "OOMKilled",
        ),
        (
            [make_container_status({"terminated": {"exitCode": 127}}, {})],
            "failed with exit code 127",
        ),
    ],
)
def test_get_any_container_fail_message(container_statuses, expected):
    pod = parse_pod(ResourceInstance(None, {"kind": "Pod", "status": {"containerStatuses": container_statuses}}))
    assert get_any_container_fail_message(pod) == expected
