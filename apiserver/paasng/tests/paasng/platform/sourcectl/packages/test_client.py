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

import tarfile
from contextlib import ExitStack
from pathlib import Path

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.test.utils import override_settings

from paasng.platform.sourcectl.exceptions import (
    PackageInvalidFileFormatError,
    ReadFileNotFoundError,
    ReadLinkFileOutsideDirectoryError,
)
from paasng.platform.sourcectl.package.client import (
    BasePackageClient,
    BinaryTarClient,
    GenericLocalClient,
    GenericRemoteClient,
    TarClient,
    ZipClient,
)
from paasng.platform.sourcectl.package.uploader import upload_to_blob_store
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar, gen_zip
from tests.utils.basic import generate_random_string


class TestBinaryTarClient:
    @pytest.fixture()
    def tarball_maker(self):
        with ExitStack() as stack:

            def factory(files):
                tempdir, tempfile = stack.enter_context(generate_temp_dir()), stack.enter_context(generate_temp_file())
                for file in files:
                    (tempdir / file).parent.mkdir(parents=True, exist_ok=True)
                    (tempdir / file).touch()

                compress_directory(source_path=tempdir, target_path=tempfile)
                return tempfile

            yield factory

    def test_tarfile_like(self, tarball_maker):
        tarball = tarball_maker(["a", "b", "c/d", "e/f", "g/h/i", "j/k/l"])
        with tarfile.open(tarball) as tar:
            assert BinaryTarClient(tarball).list(tarfile_like=True) == tar.getnames()

    def test_not_tarfile_like(self, tarball_maker):
        tarball = tarball_maker(["a", "b", "c/d", "e/f", "g/h/i", "j/k/l"])
        with tarfile.open(tarball) as tar:
            assert (set(BinaryTarClient(tarball).list(tarfile_like=False)) - set(tar.getnames())) == {
                "./",
                "./c/",
                "./e/",
                "./g/",
                "./g/h/",
                "./j/",
                "./j/k/",
            }

    def test_read_invalid_file(self, tmp_path):
        p = Path(tmp_path / "foo.tgz")
        p.write_text("Definitely not a tarball")
        with pytest.raises(PackageInvalidFileFormatError):
            BinaryTarClient(p).read_file("foo.txt")

    def test_list_invalid_file(self, tmp_path):
        p = Path(tmp_path / "foo.tgz")
        p.write_text("Definitely not a tarball")
        with pytest.raises(PackageInvalidFileFormatError):
            BinaryTarClient(p).list()


@pytest.mark.parametrize(
    "client_cls, archive_maker",
    [
        (TarClient, gen_tar),
        (ZipClient, gen_zip),
        (GenericLocalClient, gen_tar),
        (GenericLocalClient, gen_zip),
    ],
)
class TestLocalClient:
    @pytest.mark.parametrize(
        ("contents", "filename", "ctx", "expected"),
        [
            (dict(Procfile="web: npm run dev\n"), "Procfile", does_not_raise(), b"web: npm run dev\n"),
            (dict(Procfile="web: npm run dev\n"), "./Procfile", does_not_raise(), b"web: npm run dev\n"),
            (dict(Procfile="web: npm run dev\n"), "procfile", pytest.raises(ReadFileNotFoundError), None),
        ],
    )
    def test_read_file(self, client_cls, archive_maker, contents, filename, ctx, expected):
        with generate_temp_file() as file_path:
            archive_maker(file_path, contents)
            cli: BasePackageClient = client_cls(file_path=file_path)
            with ctx:
                assert cli.read_file(filename) == expected

    @pytest.mark.parametrize(
        ("contents", "relative_path", "filename", "ctx", "expected"),
        [
            ({"foo": "1"}, "./", "foo", does_not_raise(), b"1"),
            ({"foo": "1"}, "./", "./foo", does_not_raise(), b"1"),
            ({"foo/foo": "1"}, "./", "foo/foo", does_not_raise(), b"1"),
            ({"foo/foo": "1"}, "./", "./foo/foo", does_not_raise(), b"1"),
            ({"foo/foo": "1"}, "./foo", "foo", does_not_raise(), b"1"),
            ({"foo/foo": "1"}, "./foo", "./foo", does_not_raise(), b"1"),
            ({"foo/foo": "1"}, "./foo", "./foo/foo", pytest.raises(ReadFileNotFoundError), b"1"),
            ({"foo/foo": "1"}, "./foo", "foo/foo", pytest.raises(ReadFileNotFoundError), b"1"),
            ({"foo/foo/foo": "3"}, "./", "foo/foo/foo", does_not_raise(), b"3"),
            ({"foo/foo/foo": "3"}, "./", "./foo/foo/foo", does_not_raise(), b"3"),
            ({"foo/foo/foo": "3"}, "./foo/", "foo/foo", does_not_raise(), b"3"),
            ({"foo/foo/foo": "3"}, "./foo/", "./foo/foo", does_not_raise(), b"3"),
            ({"foo/foo/foo": "3"}, "./foo/foo", "foo", does_not_raise(), b"3"),
            ({"foo/foo/foo": "3"}, "./foo/foo", "./foo", does_not_raise(), b"3"),
            ({"foo/foo/foo": "3"}, "./foo/foo", "foo/foo/foo", pytest.raises(ReadFileNotFoundError), b"3"),
            ({"foo/foo/foo": "3"}, "./foo/foo", "./foo/foo/foo", pytest.raises(ReadFileNotFoundError), b"3"),
        ],
    )
    def test_read_file_with_relative_path(
        self, client_cls, archive_maker, contents, relative_path, filename, ctx, expected
    ):
        with generate_temp_file() as file_path:
            archive_maker(file_path, contents)
            cli: BasePackageClient = client_cls(file_path=file_path, relative_path=relative_path)
            with ctx:
                assert cli.read_file(filename) == expected

    @pytest.mark.parametrize(
        "contents",
        [
            (dict(Procfile="web: npm run dev\n")),
        ],
    )
    def test_export(self, client_cls, archive_maker, contents):
        with generate_temp_file() as file_path, generate_temp_dir() as working_dir:
            archive_maker(file_path, contents)
            cli = client_cls(file_path)
            cli.export(working_dir)

            assert {str(child.relative_to(working_dir)) for child in working_dir.iterdir()} == set(contents.keys())


@pytest.mark.parametrize(
    ("client_cls", "archive_maker"),
    [
        (TarClient, gen_tar),
        (GenericLocalClient, gen_tar),
    ],
)
class TestTarClientsShouldNotReadOutside:
    @pytest.mark.parametrize(
        ("symbolic_links", "filename"),
        [
            ({"passwd": "/etc/passwd"}, "./passwd"),
            ({"passwd": "../../../../../../../../../etc/passwd"}, "./passwd"),
        ],
    )
    def test_read_file_should_fail(self, client_cls, archive_maker, symbolic_links, filename):
        with generate_temp_file() as file_path:
            archive_maker(file_path, symbolic_links=symbolic_links)
            cli: BasePackageClient = client_cls(file_path=file_path)
            with pytest.raises(ReadFileNotFoundError, match="file .* not found"):
                cli.read_file(filename)

    @pytest.mark.parametrize(
        "symbolic_links",
        [
            ({"passwd": "/etc"}),
            ({"passwd": "../../../../../../../../../etc/passwd"}),
        ],
    )
    def test_export_should_fail(self, client_cls, archive_maker, symbolic_links):
        with generate_temp_file() as file_path, generate_temp_dir() as working_dir:
            archive_maker(file_path, symbolic_links=symbolic_links)
            cli = client_cls(file_path)
            with pytest.raises(ReadLinkFileOutsideDirectoryError):
                cli.export(working_dir)

    # TODO: Add malformed tar file which uses bad names


class TestZipClientsReadSymlinks:
    @pytest.mark.parametrize(
        ("symbolic_links", "filename"),
        [
            ({"passwd": "/etc/passwd"}, "./passwd"),
            ({"passwd": "../../../../../../../../../etc/passwd"}, "./passwd"),
        ],
    )
    def test_read_file_should_read_target_only(self, symbolic_links, filename):
        with generate_temp_file() as file_path:
            gen_zip(file_path, symbolic_links=symbolic_links)
            cli = ZipClient(file_path=str(file_path))

            content = cli.read_file(filename)
            assert content == symbolic_links[filename[2:]].encode(), "The content should be link target"

    @pytest.mark.parametrize(
        "symbolic_links",
        [
            ({"passwd": "/etc/passwd"}),
            ({"passwd": "../../../../../../../../../etc/passwd"}),
        ],
    )
    def test_export_should_produce_no_links(self, symbolic_links):
        with generate_temp_file() as file_path, generate_temp_dir() as working_dir:
            gen_zip(file_path, symbolic_links=symbolic_links)
            cli = ZipClient(str(file_path))

            cli.export(str(working_dir))

            # The zipfile module currently extract symlinks as files, check only the file type
            # and content.
            for name, target in symbolic_links.items():
                f = working_dir / name
                assert not f.is_symlink()
                assert f.read_text() == target, "The content should be link target"


class TestBinaryTarClientsShouldNotReadOutside:
    @pytest.mark.parametrize(
        ("symbolic_links", "filename"),
        [
            ({"passwd": "/etc/passwd"}, "./passwd"),
            ({"passwd": "../../../../../../../../../etc/passwd"}, "./passwd"),
        ],
    )
    def test_read_file_should_fail(self, symbolic_links, filename):
        with generate_temp_file() as file_path:
            gen_tar(file_path, symbolic_links=symbolic_links)
            cli = BinaryTarClient(file_path=file_path)
            with pytest.raises(ReadLinkFileOutsideDirectoryError, match=".*is invalid"):
                cli.read_file(filename)

    @pytest.mark.parametrize(
        "symbolic_links",
        [
            ({"passwd": "/etc/passwd"}),
            ({"passwd": "../../../../../../../../../etc/passwd"}),
        ],
    )
    def test_export_should_fail(self, symbolic_links):
        with generate_temp_file() as file_path, generate_temp_dir() as working_dir:
            gen_tar(file_path, symbolic_links=symbolic_links)
            cli = BinaryTarClient(file_path)
            with pytest.raises(ReadLinkFileOutsideDirectoryError):
                cli.export(str(working_dir))


@pytest.mark.parametrize("archive_maker", [gen_tar, gen_zip])
class TestGenericRemoteClient:
    @pytest.mark.parametrize(
        ("url_tmpl", "contents", "filename", "ctx", "expected"),
        [
            ("http://foo/{random}", dict(File="A: B\n"), "File", does_not_raise(), b"A: B\n"),
            ("http://foo/{random}", dict(File="A: B\n"), "./File", does_not_raise(), b"A: B\n"),
            ("http://foo/{random}", dict(File="A: B\n"), "file", pytest.raises(ReadFileNotFoundError), None),
        ],
    )
    def test_http_protocol(self, mock_adapter, archive_maker, url_tmpl, contents, filename, ctx, expected):
        url = url_tmpl.format(random=generate_random_string())
        with generate_temp_file() as file_path:
            archive_maker(file_path, contents)
            mock_adapter.register(url, open(file_path, mode="rb"))  # noqa: SIM115
            cli = GenericRemoteClient(url)
            with ctx:
                assert cli.read_file(filename) == expected

    @pytest.mark.parametrize(
        ("contents", "filename", "ctx", "expected"),
        [
            (dict(File="A: B\n"), "File", does_not_raise(), b"A: B\n"),
            (dict(File="A: B\n"), "./File", does_not_raise(), b"A: B\n"),
            (dict(File="A: B\n"), "file", pytest.raises(ReadFileNotFoundError), None),
        ],
    )
    def test_blobstore_protocol(self, archive_maker, contents, filename, ctx, expected):
        # NOTE: 这是数据库存量数据的格式
        obj_key = generate_random_string()
        with generate_temp_file() as file_path, override_settings(BLOBSTORE_BKREPO_CONFIG={}):
            archive_maker(file_path, contents)
            obj_url = upload_to_blob_store(file_path, obj_key, allow_overwrite=True)
            cli = GenericRemoteClient(obj_url)
            with ctx:
                assert cli.read_file(filename) == expected
