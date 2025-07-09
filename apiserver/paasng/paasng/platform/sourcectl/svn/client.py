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

"""A simple SVN client by wrapping svn command line tool"""

import logging
import os
import pathlib
import re
import urllib.parse
from collections import Counter
from distutils.dir_util import copy_tree
from operator import attrgetter
from shutil import copyfile
from typing import Optional

import arrow
from django.utils.encoding import force_str
from svn.common import SvnException
from svn.local import LocalClient as OrigLocalClient
from svn.remote import RemoteClient as OrigRemoteClient

from paasng.platform.sourcectl.exceptions import ReadFileNotFoundError
from paasng.platform.sourcectl.svn.exceptions import AlreadyInitializedSvnRepo, CannotInitNonEmptyTrunk
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, get_all_intermediate_dirs

logger = logging.getLogger(__name__)


class VersionType:
    """Version type for svn repository type"""

    def __init__(self, name, dirname, include_subdirs):
        self.name = name
        self.dirname = dirname
        self.include_subdirs = include_subdirs

    def get_rel_path(self, tag_name):
        """Get the relative path for given tag_name"""
        if self.include_subdirs:
            return self.dirname + "/" + tag_name
        else:
            # Ignore tag name
            return self.dirname


class SvnVersionTypes:
    """All supported svn version types"""

    RE_SMART_REVISION = re.compile(r"^(\w+):(.+)$")

    def __init__(self):
        self.versions = (
            VersionType("trunk", "trunk", False),
            VersionType("tags", "tags", True),
            VersionType("branch", "branches", True),
        )
        self.name_map = {ver.name: ver for ver in self.versions}
        self.dirname_map = {ver.dirname: ver for ver in self.versions}

    def get_version_by_type(self, name) -> Optional[VersionType]:
        return self.name_map.get(name)

    def get_version_by_dirname(self, dirname) -> Optional[VersionType]:
        return self.dirname_map.get(dirname)

    def parse_smart_revision_str(self, name):
        """Parses a smart revision string

        :param str s: smart revision string, such as "trunk:runk"
        :returns: (<VersionType instance>, str:rel_path)
        :raises: ValueError if given string is not a valid smart revision
        """
        obj = self.RE_SMART_REVISION.match(name)
        if not obj:
            raise ValueError('Name "%s" is not a valid smart revision, format should be "{type}:{name}"' % name)

        ver_type, tag_name = obj.groups()
        ver = svn_version_types.get_version_by_type(ver_type)
        if not ver:
            raise ValueError('Type "%s" is not a valid version type' % ver_type)
        return ver, ver.get_rel_path(tag_name)


svn_version_types = SvnVersionTypes()


class RepoProvider:
    """Provider for svn repository"""

    default_init_repo_message = "Init repo for name: %s"

    def __init__(self, base_url, username, password, with_branches_and_tags=True):
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        self.base_url = force_str(base_url)
        self.username = username
        self.password = password
        self.with_branches_and_tags = with_branches_and_tags

        self.rclient = RemoteClient(self.base_url, username=self.username, password=self.password)

    def provision(self, desired_name):
        already_initialized = False
        with generate_temp_dir() as working_dir:
            try:
                self.initialize_repo(working_dir, desired_name=desired_name)
            except AlreadyInitializedSvnRepo:
                already_initialized = True
        return {
            "already_initialized": already_initialized,
            "repo_url": urllib.parse.urljoin(self.base_url, force_str(desired_name)),
        }

    def initialize_repo(self, working_dir: pathlib.Path, desired_name, message=None):
        """Creates an empty repo if app repo does not exist

        :param pathlib.Path working_dir: working dir
        :param str message: override default commit message
        """
        # First, checkout an empty directory to disk
        self.rclient.checkout(str(working_dir), depth="empty")

        try:
            list(self.rclient.list(rel_path=desired_name))

            logger.info("Skip init, %s already exists in svn server.", desired_name)
            raise AlreadyInitializedSvnRepo("Repo %s has already been initialized!" % desired_name)
        except SvnException as e:
            # Will raise svn: E200009 is directory does not exists
            # Only continue if direcoty does not exists
            if "svn: E200009" not in str(e):
                raise

        repo_path = working_dir / desired_name
        if not isinstance(repo_path, pathlib.Path):
            repo_path = pathlib.Path(repo_path)

        # Create an empty repo if subdir directory does not exists
        repo_path.mkdir(parents=True, exist_ok=True)
        if self.with_branches_and_tags:
            for subdir in ["trunk", "branches", "tags"]:
                (repo_path / subdir).mkdir(parents=True, exist_ok=True)

        # Commit to server
        lclient = LocalClient(working_dir, username=self.username, password=self.password)
        lclient.add(str(repo_path))
        message = message or (self.default_init_repo_message % desired_name)
        lclient.commit(
            message,
            [
                str(repo_path),
            ],
        )

    def make_tag_from_trunk(self, repo_path, tag_name, comment=None):
        if comment is None:
            comment = tag_name
        origin_path = os.path.join(repo_path, "trunk")
        target_path = os.path.join(repo_path, "tags", tag_name)
        return self.rclient.run_command("copy", [origin_path, target_path, "-m %s" % comment])


def smart_repo_client(repo_url, username, password):
    # TODO: Dynamic change username/password

    return SvnRepositoryClient(repo_url=repo_url, username=username, password=password)


class SvnRepositoryClient:
    """Client for SVN Repository"""

    default_ignores = [
        ".svn",
    ]

    def __init__(self, repo_url, username, password):
        if not repo_url.endswith("/"):
            repo_url = repo_url + "/"
        self.repo_url = force_str(repo_url)
        self.username = username
        self.password = password
        self.svn_credentials = {"username": self.username, "password": self.password}
        self.rclient = RemoteClient(self.repo_url, **self.svn_credentials)

    def sync_dir(self, local_path, remote_path, commit_message=""):
        """Sync a local dir to remote, usaully used for templating new repo"""
        remote_url = urllib.parse.urljoin(self.repo_url, force_str(remote_path))
        rclient = RemoteClient(remote_url, **self.svn_credentials)

        if list(rclient.list()):
            raise CannotInitNonEmptyTrunk("URL %s is not empty and can not be synced!" % remote_url)

        with generate_temp_dir() as working_dir:
            lclient = LocalClient(str(working_dir), **self.svn_credentials)
            rclient.checkout(str(working_dir))
            # Use copy_tree from distutils module because the dest direcotry could be existed already
            copy_tree(local_path, str(working_dir))

            for d in working_dir.iterdir():
                if d in self.default_ignores:
                    continue
                lclient.add(str(d))

            lclient.commit(
                commit_message or "Init with template",
                [
                    str(working_dir),
                ],
            )

    def read_file(self, file_path, revision=None):
        """Read a file content from SVN Server"""
        try:
            return self.rclient.cat(file_path, revision=revision)
        except SvnException as e:
            # Will raise svn: E200009 is file does not exists
            if "svn: E200009" not in str(e):
                raise
            raise ReadFileNotFoundError()

    def export(self, subdir, local_path, revision=None):
        """Export contents in a subdir to local_path

        :param str subdir: sub directory name, such as 'trunk'
        :param str local_path: local_path to be exported
        """
        url = os.path.join(self.repo_url, subdir)
        rclient = RemoteClient(url, **self.svn_credentials)
        rclient.export(local_path, force=True, revision=revision)

    def list_alternative_versions(self):
        """List all alternative versions"""
        from paasng.platform.sourcectl.models import AlternativeVersion

        pri_results, results = [], []
        for item in self.rclient.list(extended=True, rel_path="."):
            ver = svn_version_types.get_version_by_dirname(item["name"])
            if not ver:
                continue
            # "trunk"
            if not ver.include_subdirs:
                url = urllib.parse.urljoin(self.repo_url, force_str(item["name"]))
                pri_results.append(
                    AlternativeVersion(item["name"], ver.name, item["commit_revision"], url, item["date"])
                )
                continue

            for sub_item in self.rclient.list(extended=True, rel_path=ver.dirname):
                url = urllib.parse.urljoin(self.repo_url, force_str(ver.dirname + "/" + sub_item["name"]))
                results.append(
                    AlternativeVersion(sub_item["name"], ver.name, sub_item["commit_revision"], url, sub_item["date"])
                )

        results.sort(key=lambda item: item.last_update)  # type: ignore
        results = pri_results + results
        return results

    def get_latest_revision(self):
        """Get latest changed revision info"""
        info = self.rclient.info()
        return {
            "commit_revision": info["commit_revision"],
            "commit_author": info["commit/author"],
            "commit_date": info["commit/date"],
        }

    def get_commit_logs(self, from_revision, to_revision=None, rel_filepath=None):
        """Get commit message by given revision"""
        to_revision = to_revision or from_revision
        result = self.rclient.log_default(
            revision_from=from_revision, revision_to=to_revision, rel_filepath=rel_filepath, changelist=True
        )
        # SVN 的 log_default 总是返回当前 from_revision 的 commit 记录
        return [
            {
                "message": item.msg,
                "revision": item.revision,
                "date": item.date,
                "author": item.author,
                "changelist": item.changelist,
            }
            for item in result
        ]

    def package(self, subdir, local_file_name, revision=None):
        """Export contents and package it to a tar package

        :param str subdir: sub directory name, such as 'trunk'
        :param str local_path: local_path to be exported
        """
        with generate_temp_dir() as working_path:
            url = os.path.join(self.repo_url, subdir)
            rclient = RemoteClient(url, **self.svn_credentials)
            rclient.export(str(working_path), force=True)

            compress_directory(working_path, local_file_name)

    def patch_files(self, update_callback=None, update_list=None, add_list=None, delete_list=None, message=""):
        """
        update_callback, func, migrate(working_dir)
        update_list, list, ["requirements.txt", "settings.py", "conf/settings_env.py"]
        add_list, list, [("/data/abc/a.txt", "a.txt", True), ("")]
        delete_list, list, ["a.txt"]
        message, str, commit message
        """
        rclient = RemoteClient(self.repo_url, **self.svn_credentials)
        if not list(rclient.list()):
            raise RuntimeError("Fetch remote client failed")

        with generate_temp_dir() as working_dir:
            # 0. checkout
            rclient.checkout(str(working_dir), depth="empty")

            lclient = LocalClient(str(working_dir), **self.svn_credentials)

            # 1. svn update
            for update_rel_path in update_list or []:
                # 仅更新文件到最新版本
                lclient.update(str(working_dir / update_rel_path))

            # 2. svn add
            for origin_rel_path, add_rel_path, is_force_add in add_list or []:
                add_file = working_dir / add_rel_path
                add_file_dir = add_file.parent

                intermediate_dirs = get_all_intermediate_dirs(str(add_rel_path))
                for intermediate_dir in reversed(intermediate_dirs):
                    lclient.update(str(working_dir / intermediate_dir), silent=True)

                add_file_dir.mkdir(parents=True, exist_ok=True)

                is_need_add = is_force_add or not add_file.is_file()

                if is_need_add:
                    copyfile(origin_rel_path, add_file)

                for intermediate_dir in reversed(intermediate_dirs):
                    lclient.add(str(working_dir / intermediate_dir), silent=True)

            # 3. modify files
            update_callback and update_callback(working_dir)

            # 4. svn delete
            for del_rel_path in delete_list or []:
                delete_file = working_dir / del_rel_path
                lclient.update(str(delete_file), silent=True)
                if delete_file.exists():
                    lclient.delete(str(delete_file))

            lclient.commit(message, rel_filepaths=[working_dir])

    def extract_smart_revision(self, smart_revision) -> str:
        """A smart revision is a string which is not a regular numeric revision number but can also
        be used for revision comparisons

        :returns: a dict with extra info including revision number
        """
        ver, rel_path = svn_version_types.parse_smart_revision_str(smart_revision)
        try:
            result = self.rclient.info(rel_path=rel_path)
        except SvnException:
            raise ValueError('No revision info found for "%s"' % rel_path)
        return result

    def __str__(self):
        return "SvnRepositoryClient: %s" % self.repo_url


class RemoteClient(OrigRemoteClient):
    """SVN Remote Client for blueking"""

    def checkout(self, path, revision=None, depth=None):
        cmd = []
        if revision is not None:
            cmd += ["-r", str(revision)]
        if depth is not None:
            cmd += ["--depth", depth]

        cmd += [self.url, path]
        self.run_command("checkout", cmd)

    def delete(self, rel_path):
        self.run_command(
            "delete",
            [rel_path],
            # wd=self.path
        )

    def tag_trunk(self, tag_name):
        self.run_command("copy", [])

    def calculate_user_contribution(self, username: str):
        """
        :param username: 被统计的用户名
        """
        # 从 log_default 获取所有 commit 记录(revision/author/date)
        all_commits_log = sorted(self.log_default(changelist=True), key=attrgetter("date"))
        project_commit_nums = len(all_commits_log)
        if project_commit_nums == 0:
            return None
        # 内存里过滤可以拿到用户在项目里提交的 commit 数量
        user_commit_nums = 0
        # 项目首次提交时间
        project_first_commit_date = arrow.get().date()
        # 用户首次提交时间
        user_first_commit_date = arrow.get().date()
        # 用户 commit 日历
        user_commit_calendar: Counter = Counter()
        # 项目总代码行数.....
        project_total_lines = 0
        # 用户提交的总代码行数.....
        user_total_lines = 0
        for commit_log in all_commits_log:
            committed_date = arrow.get(commit_log.date).date()
            project_first_commit_date = min(project_first_commit_date, committed_date)
            if commit_log.author == username:
                user_commit_nums += 1
                user_commit_calendar[committed_date] += 1
                user_first_commit_date = min(user_first_commit_date, committed_date)

        return dict(
            project_total_lines=project_total_lines,
            user_total_lines=user_total_lines,
            project_commit_nums=project_commit_nums,
            user_commit_nums=user_commit_nums,
        )


class LocalClient(OrigLocalClient):
    """SVN Local Client for blueking"""

    def add(self, rel_path: str, silent: bool = False):
        try:
            self.run_command(
                "add",
                [rel_path],
                # wd=self.path
            )
        except Exception:
            logger.exception("SVN add error")
            if not silent:
                raise

    def update(self, rel_path: str, silent: bool = False):
        try:
            self.run_command(
                "update",
                [rel_path],
                # wd=self.path
            )
        except Exception:
            logger.exception("SVN update error")
            if not silent:
                raise

    def commit(self, message: str, rel_filepaths=None):
        if rel_filepaths is None:
            rel_filepaths = []
        args = ["-m", message] + rel_filepaths

        self.run_command(
            "commit",
            args,
            # wd=self.path
        )

    def delete(self, rel_path: str, silent: bool = False):
        try:
            self.run_command(
                "delete",
                [rel_path],
                # wd=self.path
            )
        except Exception:
            logger.exception("SVN delete error")
            if not silent:
                raise


def acquire_repo(desired_name, base_url, username, password, with_branches_and_tags):
    """Get a new repo url

    :param str desired_name: sub directory name of svn repo
    :param str base_url: base repo url
    :param str username: su name
    :param str password: su password
    :param bool with_branches_and_tags:
    """
    provider = RepoProvider(
        base_url=base_url, username=username, password=password, with_branches_and_tags=with_branches_and_tags
    )
    return provider.provision(desired_name=desired_name)
