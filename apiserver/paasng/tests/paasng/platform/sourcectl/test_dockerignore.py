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

import tarfile
from textwrap import dedent

import pytest

from paasng.platform.sourcectl.utils import DockerIgnore, compress_directory_ext, generate_temp_dir, generate_temp_file


class TestDockerIgnore:
    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (
                # test case from
                # https://github.com/moby/buildkit/tree/master/frontend/dockerfile/dockerignore/dockerignore_test.go
                "test1\n/test2\n/a/file/here\n\nlastfile\n# this is a comment\n! /inverted/abs/path\n!\n! \n",
                ["test1", "test2", "a/file/here", "lastfile", "!inverted/abs/path", "!", "!"],
            ),
            (
                dedent(
                    """
                # comment
                */temp*
                */*/temp*
                temp?
                """
                ),
                ["*/temp*", "*/*/temp*", "temp?"],
            ),
        ],
    )
    def test_parse(self, content, expected):
        assert DockerIgnore(content).content == expected

    @pytest.mark.parametrize(
        ("content", "cases", "expected"),
        # All case are from https://docs.docker.com/engine/reference/builder/#dockerignore-file
        [
            (
                dedent(
                    """
            # comment
            */temp*
            """
                ),
                [
                    "comment",
                    "somedir/temporary.txt",
                    "somedir/subdir/temporary.txt",
                    "temp",
                    "tempa",
                    "tempb",
                ],
                [False, True, False, False, False, False],
            ),
            (
                dedent(
                    """
                # comment
                */*/temp*
                """
                ),
                [
                    "comment",
                    "somedir/temporary.txt",
                    "somedir/subdir/temporary.txt",
                    "temp",
                    "tempa",
                    "tempb",
                ],
                [False, False, True, False, False, False],
            ),
            (
                dedent(
                    """
                    # comment
                    temp?
                    """
                ),
                [
                    "comment",
                    "somedir/temporary.txt",
                    "somedir/subdir/temporary.txt",
                    "temp",
                    "tempa",
                    "tempb",
                ],
                [False, False, False, False, True, True],
            ),
            (
                dedent(
                    """
                    # comment
                    */temp*
                    */*/temp*
                    temp?
                    """
                ),
                [
                    "comment",
                    "somedir/temporary.txt",
                    "somedir/subdir/temporary.txt",
                    "temp",
                    "tempa",
                    "tempb",
                ],
                [False, True, True, False, True, True],
            ),
            (
                dedent(
                    """
                *.md
                !README.md
                """
                ),
                ["README.md", "README-secret.md"],
                [False, True],
            ),
            (
                dedent(
                    """
                *.md
                !README*.md
                README-secret.md
                """
                ),
                ["README.md", "README-secret.md"],
                [False, True],
            ),
            (
                dedent(
                    """
                *.md
                README-secret.md
                !README*.md
                """
                ),
                ["README.md", "README-secret.md"],
                [False, False],
            ),
        ],
    )
    def test_should_ignore(self, content, cases, expected):
        di = DockerIgnore(content)
        assert [di.should_ignore(case) for case in cases] == expected

    @pytest.mark.parametrize("whitelist", [["Dockerfile"], ["./Dockerfile"]])
    def test_whitelist(self, whitelist):
        di = DockerIgnore("Dockerfile", whitelist=whitelist)
        with generate_temp_dir() as workdir, generate_temp_file(suffix=".tar.gz") as dest:
            (workdir / "Dockerfile").write_text("flag")

            compress_directory_ext(workdir, dest, di.should_ignore)
            with tarfile.open(dest, mode="r:gz") as tf:
                assert {m.name for m in tf.getmembers()} == {"Dockerfile"}


def test_compress_with_docker_ignore():
    di = DockerIgnore(
        dedent(
            """
        !**/*.py
        !**/*.md
        secret/README.md
        Dockerfile
        """
        ),
        whitelist=["./Dockerfile"],
    )
    with generate_temp_dir() as workdir, generate_temp_file(suffix=".tar.gz") as dest:
        (workdir / "secret").mkdir()
        (workdir / "secret" / "README.md").write_text("secret")
        (workdir / "src").mkdir()
        (workdir / "src" / "flag.md").write_text("flag")
        (workdir / "src" / "__init__.py").write_text("")
        (workdir / "src" / "__main__.py").write_text("")
        (workdir / "README.md").write_text("flag")
        (workdir / "Dockerfile").write_text("flag")

        compress_directory_ext(workdir, dest, di.should_ignore)
        with tarfile.open(dest, mode="r:gz") as tf:
            assert {m.name for m in tf.getmembers()} == {
                "README.md",
                "src/__init__.py",
                "src/flag.md",
                "src/__main__.py",
                "Dockerfile",
            }
