"""Persisting the workspace as a Git repository.

The component is standalone on purpose: it is assembled and tested against real ``git``
processes and a real remote without a run, a conversation, or an HTTP request anywhere near it.
Later stages wire it into cold restore.

Start at :class:`~app_spark_agent.git.workspace.GitWorkspace`; the file policy it enforces is
documented in :mod:`app_spark_agent.git.policy`, and why ``git`` is invoked the way it is in
:mod:`app_spark_agent.git.runner`. :class:`~app_spark_agent.git.saver.WorkspaceSaver` is what
the server drives: it splits a turn into a local commit and a background push.
"""

from app_spark_agent.git.errors import (
    GitAuthError,
    GitCommandError,
    GitDivergedError,
    GitError,
    GitNotConfiguredError,
    GitPolicyError,
    GitRemoteUnavailableError,
    GitTimeoutError,
    GitWorkspaceConflictError,
)
from app_spark_agent.git.policy import (
    DEFAULT_EXCLUDES,
    WorkspaceFile,
    WorkspacePolicy,
)
from app_spark_agent.git.runner import GitIdentity, GitResult, GitRunner, RemoteConfig
from app_spark_agent.git.saver import (
    CHECKPOINT_TAG_PREFIX,
    Checkpoint,
    CheckpointReporter,
    RestoreOutcome,
    SaveState,
    SaveStatus,
    WorkspaceSaver,
    checkpoint_tag,
)
from app_spark_agent.git.workspace import GitWorkspace, StatusEntry, WorkspaceStatus

__all__ = [
    "CHECKPOINT_TAG_PREFIX",
    "DEFAULT_EXCLUDES",
    "Checkpoint",
    "CheckpointReporter",
    "GitAuthError",
    "GitCommandError",
    "GitDivergedError",
    "GitError",
    "GitIdentity",
    "GitNotConfiguredError",
    "GitPolicyError",
    "GitRemoteUnavailableError",
    "GitResult",
    "GitRunner",
    "GitTimeoutError",
    "GitWorkspace",
    "GitWorkspaceConflictError",
    "RemoteConfig",
    "RestoreOutcome",
    "SaveState",
    "SaveStatus",
    "StatusEntry",
    "WorkspaceFile",
    "WorkspacePolicy",
    "WorkspaceSaver",
    "WorkspaceStatus",
    "checkpoint_tag",
]
