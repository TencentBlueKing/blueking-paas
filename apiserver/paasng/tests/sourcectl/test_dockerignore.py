import tarfile
from textwrap import dedent

import pytest

from paasng.dev_resources.sourcectl.utils import (
    DockerIgnore,
    compress_directory_ext,
    generate_temp_dir,
    generate_temp_file,
)


class TestDockerIgnore:
    @pytest.mark.parametrize(
        "content, expected",
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
        "content, cases, expected",
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


def test_compress_with_docker_ignore():
    di = DockerIgnore(
        dedent(
            """
        !**/*.py
        !**/*.md
        secret/README.md
        """
        )
    )
    with generate_temp_dir() as workdir, generate_temp_file(suffix=".tar.gz") as dest:
        (workdir / "secret").mkdir()
        (workdir / "secret" / "README.md").write_text("secret")
        (workdir / "src").mkdir()
        (workdir / "src" / "flag.md").write_text("flag")
        (workdir / "src" / "__init__.py").write_text("")
        (workdir / "src" / "__main__.py").write_text("")
        (workdir / "README.md").write_text("flag")

        compress_directory_ext(workdir, dest, di.should_ignore)
        with tarfile.open(dest, mode="r:gz") as tf:
            assert {m.name for m in tf.getmembers()} == {
                "README.md",
                "src/__init__.py",
                "src/flag.md",
                "src/__main__.py",
            }
