# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Handing a Project's saved source to a caller as one archive."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

import attrs

from app_spark_api.repository.git.factory import make_forgejo_async_client
from app_spark_api.utils.urls import reverse_public

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import httpx2

    from app_spark_api.infras.forgejo.async_client import ForgejoAsyncClient
    from app_spark_api.repository.git.models import ProjectGitRepository

# zip rather than tar.gz: the caller is a browser on whatever the user happens to run, and
# zip is the one format every desktop opens without a tool. Forgejo selects the format by
# extension, so a second one is a parameter away if a caller ever needs it.
ARCHIVE_SUFFIX = "zip"
ARCHIVE_MEDIA_TYPE = "application/zip"

# Long enough that a source tree is a handful of reads, short enough that the first bytes
# reach the caller promptly instead of sitting in a buffer.
_CHUNK_SIZE = 64 * 1024
# Enough to identify a commit to a human, matching what `git log --oneline` shows.
_SHORT_COMMIT_LENGTH = 7
# Must match the `url_name` the archive route declares in `api.py`; nothing but a failed
# reverse at request time would report a rename.
_ARCHIVE_URL_NAME = "api:git-repository-archive"


def archive_url_for(repo: ProjectGitRepository) -> str | None:
    """Return where a caller can download ``repo``'s source, or ``None`` if nowhere yet.

    :param repo: Persisted repository row; only its Project and remote state are read.
    :return: A browser-facing path, including the public ingress prefix, or ``None`` while
        the remote repository does not exist.
    """
    if not repo.has_remote_repository:
        return None
    return reverse_public(_ARCHIVE_URL_NAME, kwargs={"project_id": repo.project_id})


@attrs.frozen
class SourceArchive:
    """An archive whose download has started and whose bytes have not been read yet.

    :param commit: Full SHA the archive was cut from.
    :param filename: File name to offer the caller.
    :param media_type: Content type of ``chunks``.
    :param chunks: The archive's bytes. Iterating it to the end -- or abandoning it, which
        closes it -- releases the upstream connection and the client that opened it.
    """

    commit: str
    filename: str
    media_type: str
    chunks: AsyncIterator[bytes] = attrs.field(repr=False)


async def open_project_source_archive(repo: ProjectGitRepository) -> SourceArchive:
    """Start downloading the tip of ``repo``'s working branch as an archive.

    Two round trips, in this order on purpose. The branch lookup names the commit, which
    the file name needs, and it fails while an ordinary error response can still be
    produced; by the time ``chunks`` is being written the status line has already gone out
    and a failure could only truncate the download.

    :param repo: A repository row whose remote exists, i.e.
        :attr:`~app_spark_api.repository.git.models.ProjectGitRepository.has_remote_repository`.
    :return: The open archive. The caller must consume or close ``chunks``.
    :raises app_spark_api.infras.forgejo.exceptions.ForgejoError: Forgejo was unreachable,
        refused the read, or has no such branch.

    Example::

        archive = await open_project_source_archive(repo)
        return StreamingHttpResponse(archive.chunks, content_type=archive.media_type)
    """
    async with AsyncExitStack() as stack:
        client = make_forgejo_async_client()
        stack.push_async_callback(client.aclose)
        branch = await client.get_branch(repo.owner, repo.name, repo.default_branch)
        response = await client.open_archive(
            owner=repo.owner,
            name=repo.name,
            ref=repo.default_branch,
            suffix=ARCHIVE_SUFFIX,
        )
        # Both now belong to `_drain`, which closes them once the caller is done. Dropping
        # the popped stack on the floor is what stops this `async with` from closing the
        # client the moment we return; on the failure paths above it still runs.
        stack.pop_all()
        return SourceArchive(
            commit=branch.commit,
            filename=f"{repo.project_id}-{branch.commit[:_SHORT_COMMIT_LENGTH]}.{ARCHIVE_SUFFIX}",
            media_type=ARCHIVE_MEDIA_TYPE,
            chunks=_drain(client, response),
        )


async def _drain(client: ForgejoAsyncClient, response: httpx2.Response) -> AsyncIterator[bytes]:
    """Yield the response body, then release the connection and the client.

    ``finally`` rather than closing after the loop: Django stops iterating a streaming
    response as soon as the client disconnects, and a generator torn down that way still
    has to hand its connection back.
    """
    try:
        async for chunk in response.aiter_bytes(_CHUNK_SIZE):
            yield chunk
    finally:
        await response.aclose()
        await client.aclose()
