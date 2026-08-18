from __future__ import annotations

import tempfile
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

from cqoi import remote_zip


class _FakeResponse:
    def __init__(
        self,
        *,
        headers: dict[str, str],
        status: int,
        payload: bytes = b"",
    ) -> None:
        self.headers = headers
        self.status = status
        self._payload = payload
        self.closed = False

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        self.closed = True


def test_http_range_reader_accepts_complete_head() -> None:
    response = _FakeResponse(
        headers={"Content-Length": "49039640485", "Accept-Ranges": "bytes"},
        status=200,
    )
    calls = []

    def fake_urlopen(request, *, timeout):
        calls.append((request, timeout))
        return response

    with patch.object(remote_zip.urllib.request, "urlopen", fake_urlopen):
        reader = remote_zip.HttpRangeReader("https://example.test/archive.zip")

    assert reader.length == 49_039_640_485
    assert len(calls) == 1
    assert calls[0][0].get_method() == "HEAD"
    assert response.closed


def test_http_range_reader_falls_back_when_head_omits_range_header(
) -> None:
    head = _FakeResponse(
        headers={"Content-Length": "49039640485"},
        status=200,
    )
    probe = _FakeResponse(
        headers={"Content-Range": "bytes 0-0/49039640485"},
        status=206,
        payload=b"P",
    )
    responses = iter([head, probe])
    requests = []

    def fake_urlopen(request, *, timeout):
        requests.append(request)
        return next(responses)

    with patch.object(remote_zip.urllib.request, "urlopen", fake_urlopen):
        reader = remote_zip.HttpRangeReader("https://example.test/archive.zip")

    assert reader.length == 49_039_640_485
    assert [request.get_method() for request in requests] == ["HEAD", "GET"]
    assert requests[1].get_header("Range") == "bytes=0-0"
    assert head.closed and probe.closed


def test_http_range_reader_falls_back_after_head_timeout() -> None:
    probe = _FakeResponse(
        headers={"Content-Range": "bytes 0-0/123"},
        status=206,
        payload=b"P",
    )
    calls = 0

    def fake_urlopen(request, *, timeout):
        nonlocal calls
        calls += 1
        if request.get_method() == "HEAD":
            raise urllib.error.URLError(TimeoutError("timed out"))
        return probe

    with patch.object(remote_zip.urllib.request, "urlopen", fake_urlopen):
        reader = remote_zip.HttpRangeReader("https://example.test/archive.zip")

    assert reader.length == 123
    assert calls == 2
    assert probe.closed


def test_http_range_reader_rejects_invalid_probe_response() -> None:
    cases = [
        (200, "bytes 0-0/123"),
        (206, "bytes 0-1/123"),
        (206, "bytes 0-0/*"),
        (206, "not-a-content-range"),
    ]
    for status, content_range in cases:
        head = _FakeResponse(headers={"Content-Length": "123"}, status=200)
        probe = _FakeResponse(
            headers={"Content-Range": content_range},
            status=status,
            payload=b"P",
        )
        responses = iter([head, probe])

        def fake_urlopen(request, *, timeout):
            return next(responses)

        with patch.object(remote_zip.urllib.request, "urlopen", fake_urlopen):
            try:
                remote_zip.HttpRangeReader("https://example.test/archive.zip")
            except OSError as exc:
                assert "byte-range support" in str(exc)
            else:
                raise AssertionError(
                    f"Probe status={status}, Content-Range={content_range!r} "
                    "was incorrectly accepted."
                )

        assert head.closed and probe.closed


def test_batched_range_extraction_preserves_payloads() -> None:
    payloads = {
        "images/site_w1.png": b"first-payload" * 100,
        "images/site_w2.png": b"second-payload" * 80,
        "images/site_w3.png": b"third-payload" * 120,
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        archive_path = root / "fixture.zip"
        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, payload in payloads.items():
                archive.writestr(name, payload)
        archive_bytes = archive_path.read_bytes()
        with zipfile.ZipFile(archive_path) as archive:
            entries = [
                remote_zip.RemoteZipEntry(
                    filename=info.filename,
                    header_offset=info.header_offset,
                    compress_size=info.compress_size,
                    file_size=info.file_size,
                    compress_type=info.compress_type,
                    crc=info.CRC,
                    flag_bits=info.flag_bits,
                )
                for info in archive.infolist()
            ]

        original_http_range = remote_zip._http_range

        def local_range(_url: str, start: int, end: int, **_kwargs) -> bytes:
            return archive_bytes[start : min(end + 1, len(archive_bytes))]

        remote_zip._http_range = local_range
        try:
            output = root / "output"
            extracted = remote_zip._extract_batch("fixture", entries, output)
        finally:
            remote_zip._http_range = original_http_range

        assert {name for name, _ in extracted} == set(payloads)
        for name, payload in payloads.items():
            assert (output / name).read_bytes() == payload


def test_nearby_entries_are_grouped() -> None:
    entries = [
        remote_zip.RemoteZipEntry(
            filename=f"member-{index}",
            header_offset=offset,
            compress_size=100,
            file_size=100,
            compress_type=zipfile.ZIP_STORED,
            crc=0,
            flag_bits=0,
        )
        for index, offset in enumerate((0, 500, 1_000, 2_000_000))
    ]
    batches = remote_zip._nearby_entry_batches(entries)
    assert [len(batch) for batch in batches] == [3, 1]
