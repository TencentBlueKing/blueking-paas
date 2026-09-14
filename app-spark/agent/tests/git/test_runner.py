"""How ``git`` is invoked: what it is told, and -- more importantly -- what is kept out of argv."""

from __future__ import annotations

from pathlib import Path

import pytest

from app_spark_agent.git import (
    GitAuthError,
    GitCommandError,
    GitIdentity,
    GitRemoteUnavailableError,
    GitResult,
    GitRunner,
    RemoteConfig,
)
from app_spark_agent.git.runner import classify_failure
from tests.git.conftest import plain_git

TOKEN = "tok-6c4f9d2a-secret"
REMOTE_URL = "https://forgejo.example/app-spark/proj.git"


@pytest.fixture
def runner(tmp_path: Path) -> GitRunner:
    return GitRunner(
        workspace=tmp_path,
        identity=GitIdentity(name="App-Spark", email="app-spark@localhost.invalid"),
        remote=RemoteConfig(url=REMOTE_URL, branch="main", username="app-spark-bot", token=TOKEN),
    )


class TestCredentialHandling:
    def test_the_credential_travels_in_the_environment_and_not_in_argv(self, runner: GitRunner, tmp_path: Path):
        """The model's shell runs as the same user, so anything in argv is readable via ps."""
        result = runner.run("init", "-b", "main")

        credential = RemoteConfig(url=REMOTE_URL, branch="main", username="app-spark-bot", token=TOKEN)
        encoded = credential.authorization_header()
        config_values = [value for key, value in runner.build_env().items() if key.startswith("GIT_CONFIG_VALUE_")]
        assert any(encoded in value for value in config_values), "the credential has to reach git somehow"

        for secret in (TOKEN, encoded):
            assert secret not in " ".join(result.args)
            assert secret not in (tmp_path / ".git" / "config").read_text()

    def test_a_process_without_this_runner_s_environment_cannot_recover_the_credential(
        self, runner: GitRunner, tmp_path: Path
    ):
        """The claim being tested: the credential exists only in one process's environment.

        Run inside the runner's own environment, ``git config --list`` naturally echoes the
        header straight back -- that is git reporting the configuration it was given. The
        property that matters is what anything *else* on the machine can see, which is what a
        second git run without that environment stands in for.
        """
        runner.run("init", "-b", "main")
        encoded = RemoteConfig(
            url=REMOTE_URL, branch="main", username="app-spark-bot", token=TOKEN
        ).authorization_header()

        visible = plain_git("config", "--list", "--show-origin", cwd=tmp_path)

        assert TOKEN not in visible
        assert encoded not in visible

    def test_the_header_is_scoped_to_the_configured_remote(self, runner: GitRunner):
        keys = {value for key, value in runner.build_env().items() if key.startswith("GIT_CONFIG_KEY_")}
        assert f"http.{REMOTE_URL}.extraHeader" in keys

    def test_a_local_only_runner_sends_no_credential(self, tmp_path: Path):
        runner = GitRunner(
            workspace=tmp_path,
            identity=GitIdentity(name="App-Spark", email="app-spark@localhost.invalid"),
        )
        assert not any(key.startswith("http.") for key in _config_keys(runner))

    def test_the_token_is_not_in_the_remote_config_repr(self):
        remote = RemoteConfig(url=REMOTE_URL, branch="main", username="bot", token=TOKEN)
        assert TOKEN not in repr(remote)


class TestEnvironment:
    def test_ambient_configuration_is_switched_off(self, runner: GitRunner):
        env = runner.build_env()
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GIT_CONFIG_NOSYSTEM"] == "1"
        assert env["GIT_CONFIG_GLOBAL"] == "/dev/null"
        assert dict(_config_pairs(runner))["credential.helper"] == ""

    def test_the_commit_identity_is_passed_per_process(self, runner: GitRunner):
        env = runner.build_env()
        assert env["GIT_AUTHOR_NAME"] == env["GIT_COMMITTER_NAME"] == "App-Spark"
        assert env["GIT_AUTHOR_EMAIL"] == env["GIT_COMMITTER_EMAIL"] == "app-spark@localhost.invalid"

    def test_inherited_config_pairs_are_dropped(self, runner: GitRunner, monkeypatch: pytest.MonkeyPatch):
        """A stale higher-numbered pair would be read as one of ours and change the config."""
        monkeypatch.setenv("GIT_CONFIG_KEY_9", "user.name")
        monkeypatch.setenv("GIT_CONFIG_VALUE_9", "someone else")

        env = runner.build_env()

        assert "GIT_CONFIG_KEY_9" not in env
        assert int(env["GIT_CONFIG_COUNT"]) == len(list(_config_pairs(runner)))


class TestFailureClassification:
    @pytest.mark.parametrize(
        "stderr",
        [
            "remote: HTTP Basic: Access denied\nfatal: Authentication failed for 'https://x/'",
            "fatal: could not read Username for 'https://x': terminal prompts disabled",
            "fatal: unable to access 'https://x/': The requested URL returned error: 403 Forbidden",
        ],
    )
    def test_credential_failures_are_named_as_such(self, stderr: str):
        assert isinstance(classify_failure(_failed(stderr)), GitAuthError)

    @pytest.mark.parametrize(
        "stderr",
        [
            "fatal: unable to access 'https://x/': Could not resolve host: x",
            "fatal: unable to access 'https://x/': Failed to connect to x port 443: Connection refused",
        ],
    )
    def test_transport_failures_are_named_as_such(self, stderr: str):
        """Separated from auth because these, and only these, are worth retrying unchanged."""
        assert isinstance(classify_failure(_failed(stderr)), GitRemoteUnavailableError)

    def test_anything_else_stays_generic(self):
        error = classify_failure(_failed("fatal: not a git repository"))
        assert type(error) is GitCommandError
        assert "not a git repository" in str(error)

    def test_a_leaked_token_is_masked_out_of_git_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Second-layer backstop: git never prints the token, but a remote could echo it."""
        monkeypatch.setattr("app_spark_agent.settings.GIT_TOKEN", TOKEN)
        runner = GitRunner(
            workspace=tmp_path,
            identity=GitIdentity(name="App-Spark", email="app-spark@localhost.invalid"),
        )
        result = runner.run("rev-parse", f"--verify={TOKEN}", check=False)

        assert TOKEN not in result.stderr
        assert TOKEN not in result.stdout


def _failed(stderr: str) -> GitResult:
    return GitResult(args=("push", "origin", "main"), returncode=128, stdout="", stderr=stderr)


def _config_pairs(runner: GitRunner) -> list[tuple[str, str]]:
    env = runner.build_env()
    return [
        (env[f"GIT_CONFIG_KEY_{index}"], env[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(int(env["GIT_CONFIG_COUNT"]))
    ]


def _config_keys(runner: GitRunner) -> list[str]:
    return [key for key, _ in _config_pairs(runner)]
