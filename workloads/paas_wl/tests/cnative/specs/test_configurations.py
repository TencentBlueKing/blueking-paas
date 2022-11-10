from unittest import mock

import pytest

from paas_wl.cnative.specs.configurations import MergeStrategy, generate_builtin_configurations, merge_envvars
from paas_wl.cnative.specs.v1alpha1.bk_app import EnvVar


def test_generate_builtin_configurations():
    with mock.patch("paas_wl.cnative.specs.configurations.get_plat_client") as mocked_client:
        mocked_client().list_builtin_envs.return_value = {"foo": "bar"}
        assert generate_builtin_configurations("", "") == [
            EnvVar(name="PORT", value="5000"),
            EnvVar(name="FOO", value="bar"),
        ]


@pytest.mark.parametrize(
    "x, y, strategy, z",
    [
        ([], [], MergeStrategy.OVERRIDE, []),
        ([], [EnvVar(name="a", value="a")], MergeStrategy.OVERRIDE, [EnvVar(name="a", value="a")]),
        ([EnvVar(name="a", value="a")], [], MergeStrategy.OVERRIDE, [EnvVar(name="a", value="a")]),
        (
            [EnvVar(name="a", value="a")],
            [EnvVar(name="a", value="A")],
            MergeStrategy.OVERRIDE,
            [EnvVar(name="a", value="A")],
        ),
        (
            [EnvVar(name="a", value="a")],
            [EnvVar(name="a", value="A")],
            MergeStrategy.IGNORE,
            [EnvVar(name="a", value="a")],
        ),
        # override 在原来的位置修改, 然后再 append
        (
            [EnvVar(name="a", value="a"), EnvVar(name="b", value="b")],
            [EnvVar(name="B", value="B"), EnvVar(name="a", value="A")],
            MergeStrategy.OVERRIDE,
            [EnvVar(name="a", value="A"), EnvVar(name="b", value="b"), EnvVar(name="B", value="B")],
        ),
    ],
)
def test_merge_envvars(x, y, strategy, z):
    assert merge_envvars(x, y, strategy) == z
