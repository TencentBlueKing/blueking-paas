from unittest.mock import Mock

import pytest
from kubernetes.dynamic.exceptions import NotFoundError

from paas_wl.bk_app.processes.exceptions import ScaleProcessError


class TestScaleProcessError:
    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            (ScaleProcessError(proc_type="web"), "scale web failed"),
            (ScaleProcessError(proc_type="web", exception=KeyError("foo")), "scale web failed, reason: 'foo'"),
            (ScaleProcessError(message="unknown error"), "unknown error"),
        ],
    )
    def test_string_representation(self, exc, expected):
        assert str(exc) == expected

    def test_caused_by_not_found(self):
        assert ScaleProcessError(proc_type="web", exception=KeyError("foo")).caused_by_not_found() is False

        # Build a NotFoundError
        _exc = Mock(
            body=(
                b'{"kind":"Status","apiVersion":"v1","metadata":{},"status":"Failure",'
                b'"message":"namespaces \\"foo\\" not found","reason":"NotFound",'
                b'"details":{"name":"bkapp-backend-app-prod","kind":"namespaces"},"code":404}\n'
            ),
        )
        exc = NotFoundError(_exc)
        assert ScaleProcessError(proc_type="web", exception=exc).caused_by_not_found() is True
