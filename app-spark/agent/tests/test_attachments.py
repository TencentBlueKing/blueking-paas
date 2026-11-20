"""Attachments land in the workspace before a turn; the model sees descriptions and recent image bytes."""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import httpx2
import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserContent,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app_spark_agent.attachments import (
    ATTACHMENT_FETCH_FAILED_TEXT,
    ATTACHMENT_URI_PREFIX,
    ATTACHMENTS_DIR,
    AttachmentFetchError,
    AttachmentMaterializer,
    AttachmentResolver,
    build_control_plane_fetcher,
    parse_attachment_id,
    sanitize_filename,
)
from app_spark_agent.replication import AttachmentMeta, AttachmentSource, ControlPlaneClient

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PNG = BinaryContent(data=PNG_BYTES, media_type="image/png")
CSV_BYTES = b"name,age\nbob,3\n"


class FakeFetcher:
    """Serve the known attachments, raise the queued failures first, and record every call."""

    def __init__(self, files: dict[str, tuple[str, str, bytes]], failures: tuple[AttachmentFetchError, ...] = ()):
        self.files = files
        self.failures = list(failures)
        self.calls: list[str] = []

    async def __call__(self, attachment_id: str) -> tuple[AttachmentMeta, bytes]:
        self.calls.append(attachment_id)
        if self.failures:
            raise self.failures.pop(0)

        if attachment_id not in self.files:
            raise AttachmentFetchError("gone", retryable=False)

        filename, mime_type, data = self.files[attachment_id]
        source = AttachmentSource(url="unused", authenticated=False)
        return AttachmentMeta(filename=filename, mime_type=mime_type, size=len(data), source=source), data


def make_image_ref(attachment_id: str) -> ImageUrl:
    return ImageUrl(url=f"{ATTACHMENT_URI_PREFIX}{attachment_id}", media_type="image/png")


def make_document_ref(attachment_id: str) -> DocumentUrl:
    return DocumentUrl(url=f"{ATTACHMENT_URI_PREFIX}{attachment_id}", media_type="text/csv")


def make_turn(*content: UserContent) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=list(content))])


def collect_user_content(message: ModelMessage) -> list[UserContent]:
    assert isinstance(message, ModelRequest)
    part = message.parts[0]
    assert isinstance(part, UserPromptPart)
    assert not isinstance(part.content, str)
    return list(part.content)


def describe(attachment_id: str, filename: str, mime_type: str, size: int) -> str:
    path = (ATTACHMENTS_DIR / attachment_id / filename).as_posix()
    return f"[Attached file: {filename} ({mime_type}, {size} bytes) at {path}]"


@pytest.fixture()
def image_id() -> str:
    return str(uuid4())


@pytest.fixture()
def csv_id() -> str:
    return str(uuid4())


@pytest.fixture()
def fetch(image_id: str, csv_id: str) -> FakeFetcher:
    return FakeFetcher({image_id: ("shot.png", "image/png", PNG_BYTES), csv_id: ("data.csv", "text/csv", CSV_BYTES)})


@pytest.fixture()
def materializer(tmp_path: Path, fetch: FakeFetcher) -> AttachmentMaterializer:
    return AttachmentMaterializer(tmp_path, fetch)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"{ATTACHMENT_URI_PREFIX}6f1c5c3e-5d5b-4e43-9a43-6a7d6c3c2e11", "6f1c5c3e-5d5b-4e43-9a43-6a7d6c3c2e11"),
        (f"{ATTACHMENT_URI_PREFIX}../../state/context", None),
        ("https://example.com/a.png", None),
    ],
)
def test_only_uuid_references_name_an_attachment(url: str, expected: str | None) -> None:
    assert parse_attachment_id(url) == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.csv", "report.csv"),
        ("../../etc/passwd", "passwd"),
        ("a;rm -rf $(x).md", "a_rm -rf __x_.md"),
        ("...", "attachment"),
        ("x" * 200 + ".json", "x" * 95 + ".json"),
    ],
)
def test_stored_file_names_are_safe_and_keep_their_extension(filename: str, expected: str) -> None:
    assert sanitize_filename(filename) == expected


async def test_ensure_downloads_only_what_is_missing(
    tmp_path: Path, materializer: AttachmentMaterializer, fetch: FakeFetcher, image_id: str, csv_id: str
) -> None:
    messages: list[ModelMessage] = [make_turn("look", make_image_ref(image_id), make_document_ref(csv_id))]

    await materializer.ensure(messages)
    await materializer.ensure(messages)

    assert sorted(fetch.calls) == sorted([image_id, csv_id]), "the second ensure finds both on disk"
    stored = materializer.find(csv_id)
    assert stored is not None
    assert (tmp_path / stored.path).read_bytes() == CSV_BYTES
    assert stored.describe() == describe(csv_id, "data.csv", "text/csv", len(CSV_BYTES))


async def test_a_failed_download_leaves_the_attachment_missing(tmp_path: Path, image_id: str) -> None:
    fetch = FakeFetcher({}, failures=(AttachmentFetchError("x", retryable=False),))
    materializer = AttachmentMaterializer(tmp_path, fetch)

    await materializer.ensure([make_turn(make_image_ref(image_id))])

    assert materializer.find(image_id) is None


async def test_without_a_control_plane_nothing_is_downloaded(tmp_path: Path, image_id: str) -> None:
    materializer = AttachmentMaterializer(tmp_path, None)

    await materializer.ensure([make_turn(make_image_ref(image_id))])

    assert materializer.find(image_id) is None


async def test_a_file_without_its_metadata_counts_as_missing(
    tmp_path: Path, materializer: AttachmentMaterializer, image_id: str
) -> None:
    """The metadata is written last, so a half-written download is fetched again."""
    await materializer.ensure([make_turn(make_image_ref(image_id))])
    (tmp_path / ATTACHMENTS_DIR / f"{image_id}.json").unlink()

    assert materializer.find(image_id) is None


@pytest.mark.parametrize("stored_name", ["../../../../etc/passwd", "/etc/passwd", "a/b.txt", ".."])
async def test_tampered_metadata_cannot_point_outside_the_attachment(
    tmp_path: Path, materializer: AttachmentMaterializer, image_id: str, stored_name: str
) -> None:
    """The sidecar lives in the workspace, where the model can rewrite it."""
    await materializer.ensure([make_turn(make_image_ref(image_id))])
    meta_path = tmp_path / ATTACHMENTS_DIR / f"{image_id}.json"
    meta = json.loads(meta_path.read_text())
    meta_path.write_text(json.dumps(meta | {"stored_name": stored_name}))

    assert materializer.find(image_id) is None


async def test_a_symlinked_attachments_directory_is_not_written_through(
    tmp_path: Path, fetch: FakeFetcher, image_id: str
) -> None:
    """A repository can commit .app-spark as a link; downloads must not follow it out of the workspace."""
    workspace, outside = tmp_path / "workspace", tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / ".app-spark").symlink_to(outside, target_is_directory=True)
    materializer = AttachmentMaterializer(workspace, fetch)

    await materializer.ensure([make_turn(make_image_ref(image_id))])

    assert list(outside.iterdir()) == []
    assert materializer.find(image_id) is None


async def test_a_stored_file_grown_past_the_limit_is_not_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, materializer: AttachmentMaterializer, image_id: str
) -> None:
    await materializer.ensure([make_turn(make_image_ref(image_id))])
    stored = materializer.find(image_id)
    assert stored is not None
    monkeypatch.setattr("app_spark_agent.attachments.MAX_ATTACHMENT_BYTES", len(PNG_BYTES) - 1)

    with pytest.raises(OSError, match="larger than"):
        materializer.read_bytes(stored)


async def test_recent_images_carry_bytes_and_everything_carries_a_description(
    tmp_path: Path, fetch: FakeFetcher, image_id: str, csv_id: str
) -> None:
    """Turns are counted by user prompts, so a picture three prompts back is only described."""
    old_image = str(uuid4())
    fetch.files[old_image] = ("old.png", "image/png", PNG_BYTES)
    materializer = AttachmentMaterializer(tmp_path, fetch)
    reply = ModelResponse(parts=[TextPart(content="ok")])
    messages: list[ModelMessage] = [
        make_turn("first", make_image_ref(old_image)),
        reply,
        make_turn("second"),
        reply,
        make_turn("third", make_image_ref(image_id), make_document_ref(csv_id)),
    ]
    await materializer.ensure(messages)
    resolver = AttachmentResolver(materializer, recent_turns=2, send_images=True)

    resolved = resolver.resolve_messages(messages)

    assert collect_user_content(resolved[0]) == ["first", describe(old_image, "old.png", "image/png", len(PNG_BYTES))]
    assert collect_user_content(resolved[4]) == [
        "third",
        describe(image_id, "shot.png", "image/png", len(PNG_BYTES)),
        PNG,
        describe(csv_id, "data.csv", "text/csv", len(CSV_BYTES)),
    ]
    assert collect_user_content(messages[4])[1] == make_image_ref(image_id), "the input is the run's history"


async def test_a_model_that_cannot_read_images_gets_descriptions_only(
    materializer: AttachmentMaterializer, image_id: str
) -> None:
    messages: list[ModelMessage] = [make_turn(make_image_ref(image_id))]
    await materializer.ensure(messages)

    resolved = AttachmentResolver(materializer, recent_turns=2, send_images=False).resolve_messages(messages)

    assert collect_user_content(resolved[0]) == [describe(image_id, "shot.png", "image/png", len(PNG_BYTES))]


def test_text_only_history_is_not_copied(materializer: AttachmentMaterializer) -> None:
    messages: list[ModelMessage] = [make_turn("hello")]

    assert AttachmentResolver(materializer, recent_turns=2, send_images=True).resolve_messages(messages) is messages


def test_a_missing_attachment_reaches_the_model_as_unavailable(
    materializer: AttachmentMaterializer, image_id: str
) -> None:
    messages: list[ModelMessage] = [make_turn(make_image_ref(image_id))]

    resolved = AttachmentResolver(materializer, recent_turns=2, send_images=True).resolve_messages(messages)

    assert collect_user_content(resolved[0]) == [ATTACHMENT_FETCH_FAILED_TEXT]


@pytest.mark.parametrize(
    ("item", "send_images", "expected"),
    [
        pytest.param(
            ImageUrl(url="https://example.com/a.png"), True, [ImageUrl(url="https://example.com/a.png")], id="image"
        ),
        pytest.param(
            ImageUrl(url="https://example.com/a.png"),
            False,
            ["[Linked file: https://example.com/a.png]"],
            id="image-text-model",
        ),
        pytest.param(
            DocumentUrl(url="https://example.com/a.pdf"), True, ["[Linked file: https://example.com/a.pdf]"], id="doc"
        ),
    ],
)
def test_external_links_reach_the_model_as_links(
    materializer: AttachmentMaterializer, item: UserContent, send_images: bool, expected: list[UserContent]
) -> None:
    resolver = AttachmentResolver(materializer, recent_turns=2, send_images=send_images)

    assert collect_user_content(resolver.resolve_messages([make_turn(item)])[0]) == expected


async def test_the_model_sees_bytes_while_the_run_keeps_the_reference(
    materializer: AttachmentMaterializer, image_id: str
) -> None:
    """Streamed like every Runtime run; all_messages() is what the context will store."""
    seen: list[list[ModelMessage]] = []

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        seen.append(messages)
        yield "I see it"

    await materializer.ensure([make_turn(make_image_ref(image_id))])
    agent = Agent(
        FunctionModel(stream_function=stream),
        capabilities=[AttachmentResolver(materializer, recent_turns=2, send_images=True)],
    )

    async with agent.run_stream(["what is this", make_image_ref(image_id)]) as result:
        assert await result.get_output() == "I see it"

    assert collect_user_content(seen[0][-1])[-1] == PNG
    assert collect_user_content(result.all_messages()[0]) == ["what is this", make_image_ref(image_id)]


def make_meta_body(url: str, *, authenticated: bool) -> bytes:
    source = {"url": url, "authenticated": authenticated}
    return json.dumps({"filename": "data.csv", "mime_type": "text/csv", "size": 15, "source": source}).encode()


@pytest.mark.parametrize(
    ("download_url", "authenticated", "expected_url", "expected_auth"),
    [
        pytest.param("attachments/{id}/content", True, "http://api.invalid/c/state/attachments/{id}/content", True),
        pytest.param("https://repo.example.com/x?sig=1", False, "https://repo.example.com/x?sig=1", False),
    ],
)
async def test_the_fetcher_downloads_with_the_token_only_when_told_to(
    csv_id: str, download_url: str, authenticated: bool, expected_url: str, expected_auth: bool
) -> None:
    downloads: list[tuple[str, bool]] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == f"/c/state/attachments/{csv_id}/":
            return httpx2.Response(
                200, content=make_meta_body(download_url.format(id=csv_id), authenticated=authenticated)
            )

        downloads.append((str(request.url), "authorization" in request.headers))
        return httpx2.Response(200, content=CSV_BYTES)

    client = ControlPlaneClient(
        base_url="http://api.invalid/c/state/", token="t", transport=httpx2.MockTransport(respond)
    )
    try:
        meta, data = await build_control_plane_fetcher(client)(csv_id)
    finally:
        await client.aclose()

    assert (meta.filename, data) == ("data.csv", CSV_BYTES)
    assert downloads == [(expected_url.format(id=csv_id), expected_auth)]


@pytest.mark.parametrize(
    ("status_code", "retryable", "calls"), [(404, False, 1), (401, False, 1), (502, True, 2), (None, True, 2)]
)
async def test_the_fetcher_retries_transient_failures_once(
    monkeypatch: pytest.MonkeyPatch, csv_id: str, status_code: int | None, retryable: bool, calls: int
) -> None:
    monkeypatch.setattr("app_spark_agent.attachments.FETCH_RETRY_DELAY_SECONDS", 0)
    requested: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requested.append(request.url.path)
        if status_code is None:
            raise httpx2.ConnectError("unreachable")

        return httpx2.Response(status_code)

    client = ControlPlaneClient(
        base_url="http://api.invalid/c/state/", token="t", transport=httpx2.MockTransport(respond)
    )
    try:
        with pytest.raises(AttachmentFetchError) as caught:
            await build_control_plane_fetcher(client)(csv_id)
    finally:
        await client.aclose()

    assert caught.value.retryable is retryable
    assert len(requested) == calls


async def test_an_oversized_download_is_refused_without_a_retry(monkeypatch: pytest.MonkeyPatch, csv_id: str) -> None:
    monkeypatch.setattr("app_spark_agent.attachments.MAX_ATTACHMENT_BYTES", 4)
    downloads: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith(f"{csv_id}/"):
            return httpx2.Response(200, content=make_meta_body("https://repo.example.com/x", authenticated=False))

        downloads.append(str(request.url))
        return httpx2.Response(200, content=CSV_BYTES)

    client = ControlPlaneClient(
        base_url="http://api.invalid/c/state/", token="t", transport=httpx2.MockTransport(respond)
    )
    try:
        with pytest.raises(AttachmentFetchError, match="exceeded 4 bytes") as caught:
            await build_control_plane_fetcher(client)(csv_id)
    finally:
        await client.aclose()

    assert caught.value.retryable is False
    assert len(downloads) == 1, "the same oversized body is not downloaded twice"
