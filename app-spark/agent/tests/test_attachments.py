"""Attachment references in the context become image bytes only on the way to the model."""

from collections.abc import AsyncIterator
from uuid import uuid4

import httpx2
import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    BinaryContent,
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
    ATTACHMENT_URI_PREFIX,
    OMITTED_IMAGE_TEXT,
    UNAVAILABLE_IMAGE_TEXT,
    AttachmentFetchError,
    AttachmentImages,
    build_control_plane_fetcher,
    parse_attachment_id,
)
from app_spark_agent.replication import ControlPlaneClient

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PNG = BinaryContent(data=PNG_BYTES, media_type="image/png")


class FakeFetcher:
    """Serve PNGs for the known IDs, raise the queued failures first, and record every call."""

    def __init__(self, *known: str, failures: tuple[AttachmentFetchError, ...] = (), media_type: str = "image/png"):
        self.known = set(known)
        self.failures = list(failures)
        self.media_type = media_type
        self.calls: list[str] = []

    async def __call__(self, attachment_id: str) -> tuple[bytes, str]:
        self.calls.append(attachment_id)
        if self.failures:
            raise self.failures.pop(0)

        if attachment_id not in self.known:
            raise AttachmentFetchError("gone", retryable=False)

        return PNG_BYTES, self.media_type


def make_ref(attachment_id: str) -> ImageUrl:
    return ImageUrl(url=f"{ATTACHMENT_URI_PREFIX}{attachment_id}", media_type="image/png")


def make_turn(*content: UserContent) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=list(content))])


def collect_user_content(message: ModelMessage) -> list[UserContent]:
    assert isinstance(message, ModelRequest)
    part = message.parts[0]
    assert isinstance(part, UserPromptPart)
    assert not isinstance(part.content, str)
    return list(part.content)


async def resolve_one(images: AttachmentImages, attachment_id: str) -> list[UserContent]:
    return collect_user_content((await images.resolve_messages([make_turn(make_ref(attachment_id))]))[0])


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


async def test_only_the_latest_turns_carry_image_bytes() -> None:
    """Turns are counted by user prompts, so a picture three prompts back is omitted."""
    old, recent = str(uuid4()), str(uuid4())
    fetch = FakeFetcher(old, recent)
    images = AttachmentImages(fetch, recent_turns=2)
    text_only: list[ModelMessage] = [make_turn("hello")]
    assert await images.resolve_messages(text_only) is text_only, "nothing to resolve, nothing copied"
    reply = ModelResponse(parts=[TextPart(content="ok")])
    messages: list[ModelMessage] = [
        make_turn("first", make_ref(old)),
        reply,
        make_turn("second"),
        reply,
        make_turn("third", make_ref(recent)),
    ]

    resolved = await images.resolve_messages(messages)

    assert collect_user_content(resolved[0]) == ["first", OMITTED_IMAGE_TEXT]
    assert collect_user_content(resolved[4]) == ["third", PNG]
    assert fetch.calls == [recent]
    assert collect_user_content(messages[4])[1] == make_ref(recent), "the input is the run's history"


@pytest.mark.parametrize(
    ("fetch_failures", "media_type", "expected", "calls"),
    [
        pytest.param((), "image/png", [PNG], 1, id="fetched"),
        pytest.param((AttachmentFetchError("x", retryable=True),), "image/png", [PNG], 2, id="retried-once"),
        pytest.param(
            (AttachmentFetchError("x", retryable=True),) * 2,
            "image/png",
            [UNAVAILABLE_IMAGE_TEXT],
            2,
            id="still-failing",
        ),
        pytest.param(
            (AttachmentFetchError("x", retryable=False),), "image/png", [UNAVAILABLE_IMAGE_TEXT], 1, id="gone"
        ),
        pytest.param((), "text/html", [UNAVAILABLE_IMAGE_TEXT], 1, id="not-an-image"),
    ],
)
async def test_how_a_fetch_outcome_reaches_the_model(fetch_failures, media_type, expected, calls) -> None:
    attachment_id = str(uuid4())
    fetch = FakeFetcher(attachment_id, failures=fetch_failures, media_type=media_type)

    assert await resolve_one(AttachmentImages(fetch, recent_turns=2), attachment_id) == expected
    assert len(fetch.calls) == calls


async def test_without_a_control_plane_or_recent_turns_no_bytes_are_sent() -> None:
    attachment_id = str(uuid4())

    assert await resolve_one(AttachmentImages(None, recent_turns=2), attachment_id) == [UNAVAILABLE_IMAGE_TEXT]
    assert await resolve_one(AttachmentImages(FakeFetcher(attachment_id), recent_turns=0), attachment_id) == [
        OMITTED_IMAGE_TEXT
    ]


async def test_the_cache_keeps_recent_images_and_drops_the_least_recently_used() -> None:
    first, second, third = (str(uuid4()) for _ in range(3))
    fetch = FakeFetcher(first, second, third)
    images = AttachmentImages(fetch, recent_turns=1, cache_size=2)

    for attachment_id in (first, first, second, third, first):
        await resolve_one(images, attachment_id)

    assert fetch.calls == [first, second, third, first]


async def test_the_model_sees_bytes_while_the_run_keeps_the_reference() -> None:
    """Streamed like every Runtime run; all_messages() is what the context will store."""
    attachment_id = str(uuid4())
    seen: list[list[ModelMessage]] = []

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        seen.append(messages)
        yield "I see it"

    agent = Agent(
        FunctionModel(stream_function=stream),
        capabilities=[AttachmentImages(FakeFetcher(attachment_id), recent_turns=2)],
    )

    async with agent.run_stream(["what is this", make_ref(attachment_id)]) as result:
        assert await result.get_output() == "I see it"

    assert collect_user_content(seen[0][-1]) == ["what is this", PNG]
    assert collect_user_content(result.all_messages()[0]) == ["what is this", make_ref(attachment_id)]


@pytest.mark.parametrize(
    ("status_code", "retryable"), [(200, None), (404, False), (401, False), (502, True), (None, True)]
)
async def test_the_control_plane_fetcher_reads_the_content_path_and_classifies_failures(
    status_code, retryable
) -> None:
    attachment_id = str(uuid4())
    requested: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requested.append(request.url.path)
        if status_code is None:
            raise httpx2.ConnectError("unreachable")

        return httpx2.Response(status_code, content=PNG_BYTES, headers={"content-type": "image/png"})

    client = ControlPlaneClient(
        base_url="http://api.invalid/c/state/", token="t", transport=httpx2.MockTransport(respond)
    )
    fetch = build_control_plane_fetcher(client)
    try:
        if retryable is None:
            assert await fetch(attachment_id) == (PNG_BYTES, "image/png")
        else:
            with pytest.raises(AttachmentFetchError) as caught:
                await fetch(attachment_id)
            assert caught.value.retryable is retryable
    finally:
        await client.aclose()

    assert requested == [f"/c/state/attachments/{attachment_id}/content"]
