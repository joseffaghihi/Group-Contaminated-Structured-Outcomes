from __future__ import annotations

import io
import os
import binascii
import re
import struct
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .progress import ProgressTracker


class HttpRangeReader(io.RawIOBase):
    """Seekable read-only HTTP object backed by byte-range requests."""

    def __init__(self, url: str, *, timeout: float = 90.0, retries: int = 4) -> None:
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self.length = self._resolve_length(url, timeout)
        self.position = 0

    @staticmethod
    def _resolve_length(url: str, timeout: float) -> int:
        """Resolve object length, proving byte-range support when HEAD is insufficient."""
        head_error: Exception | None = None
        request = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                length_header = response.headers.get("Content-Length")
                accepts_ranges = response.headers.get("Accept-Ranges", "")
                if length_header is not None and "bytes" in accepts_ranges.lower():
                    length = int(length_header)
                    if length <= 0:
                        raise ValueError("Content-Length must be positive.")
                    return length
        except (OSError, urllib.error.URLError, ValueError) as exc:
            head_error = exc

        probe = urllib.request.Request(
            url,
            headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"},
        )
        try:
            with urllib.request.urlopen(probe, timeout=timeout) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                if status != 206:
                    raise OSError(
                        f"Range probe returned HTTP {status}; expected HTTP 206."
                    )
                content_range = response.headers.get("Content-Range", "")
                match = re.fullmatch(r"bytes 0-0/([1-9][0-9]*)", content_range.strip())
                if match is None:
                    raise OSError(
                        "Range probe returned malformed Content-Range "
                        f"{content_range!r}; expected 'bytes 0-0/TOTAL'."
                    )
                payload = response.read()
                if len(payload) != 1:
                    raise OSError(
                        f"Range probe returned {len(payload)} bytes; expected 1."
                    )
                return int(match.group(1))
        except (OSError, urllib.error.URLError) as probe_error:
            detail = f"; HEAD error was {head_error!r}" if head_error else ""
            raise OSError(
                f"Remote object did not establish byte-range support{detail}: "
                f"{probe_error}"
            ) from probe_error

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_SET:
            target = offset
        elif whence == os.SEEK_CUR:
            target = self.position + offset
        elif whence == os.SEEK_END:
            target = self.length + offset
        else:
            raise ValueError(f"Unsupported whence={whence}")
        if target < 0:
            raise ValueError("Negative seek position.")
        self.position = min(target, self.length)
        return self.position

    def read(self, size: int = -1) -> bytes:
        if self.position >= self.length:
            return b""
        if size is None or size < 0:
            end = self.length - 1
        else:
            end = min(self.length - 1, self.position + size - 1)
        if end < self.position:
            return b""

        start = self.position
        request = urllib.request.Request(
            self.url,
            headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
        )
        last_error = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = response.read()
                expected = end - start + 1
                if len(data) != expected:
                    raise OSError(
                        f"Short range read {start}-{end}: expected {expected}, got {len(data)}."
                    )
                self.position = end + 1
                return data
            except (OSError, urllib.error.URLError) as exc:
                last_error = exc
                time.sleep(0.5 * (2**attempt))
        raise OSError(f"Range request failed after {self.retries} attempts: {last_error}")


def list_remote_zip(url: str) -> list[str]:
    reader = HttpRangeReader(url)
    with zipfile.ZipFile(reader) as archive:
        return archive.namelist()


@dataclass(frozen=True)
class RemoteZipEntry:
    filename: str
    header_offset: int
    compress_size: int
    file_size: int
    compress_type: int
    crc: int
    flag_bits: int


def remote_zip_entries(url: str, members: list[str]) -> dict[str, RemoteZipEntry]:
    """Read the central directory once and retain only requested entries."""
    wanted = set(members)
    reader = HttpRangeReader(url)
    with zipfile.ZipFile(reader) as archive:
        found = {}
        for info in archive.infolist():
            if info.filename in wanted:
                found[info.filename] = RemoteZipEntry(
                    filename=info.filename,
                    header_offset=info.header_offset,
                    compress_size=info.compress_size,
                    file_size=info.file_size,
                    compress_type=info.compress_type,
                    crc=info.CRC,
                    flag_bits=info.flag_bits,
                )
    missing = sorted(wanted - set(found))
    if missing:
        raise KeyError(f"{len(missing)} ZIP member(s) absent; first={missing[0]}")
    return found


def _http_range(url: str, start: int, end: int, *, retries: int = 5) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
    )
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=120.0) as response:
                data = response.read()
            expected = end - start + 1
            if len(data) != expected:
                raise OSError(f"Expected {expected} range bytes; received {len(data)}.")
            return data
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            time.sleep(0.5 * (2**attempt))
    raise OSError(f"Range request failed after {retries} attempts: {last_error}")


def _extract_one(url: str, entry: RemoteZipEntry, destination: Path) -> tuple[str, int]:
    if entry.flag_bits & 0x1:
        raise NotImplementedError("Encrypted ZIP entries are not supported.")
    local_header = _http_range(url, entry.header_offset, entry.header_offset + 29)
    fields = struct.unpack("<IHHHHHIIIHH", local_header)
    signature, _, _, _, _, _, _, _, _, name_length, extra_length = fields
    if signature != 0x04034B50:
        raise zipfile.BadZipFile(f"Invalid local header for {entry.filename}")
    data_start = entry.header_offset + 30 + name_length + extra_length
    compressed = _http_range(
        url, data_start, data_start + entry.compress_size - 1
    )
    if entry.compress_type == zipfile.ZIP_STORED:
        payload = compressed
    elif entry.compress_type == zipfile.ZIP_DEFLATED:
        payload = zlib.decompress(compressed, -15)
    else:
        raise NotImplementedError(
            f"Unsupported compression type {entry.compress_type} for {entry.filename}"
        )
    if len(payload) != entry.file_size:
        raise zipfile.BadZipFile(
            f"Size mismatch for {entry.filename}: {len(payload)} != {entry.file_size}"
        )
    if (binascii.crc32(payload) & 0xFFFFFFFF) != entry.crc:
        raise zipfile.BadZipFile(f"CRC mismatch for {entry.filename}")

    target = destination / entry.filename
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".partial")
    temporary.write_bytes(payload)
    os.replace(temporary, target)
    return entry.filename, entry.file_size


def _entry_payload_from_range(
    blob: bytes,
    range_start: int,
    entry: RemoteZipEntry,
) -> bytes:
    """Decode one member from a range that begins before its local header."""
    relative_header = entry.header_offset - range_start
    local_header = blob[relative_header : relative_header + 30]
    if len(local_header) != 30:
        raise zipfile.BadZipFile(f"Truncated local header for {entry.filename}")
    fields = struct.unpack("<IHHHHHIIIHH", local_header)
    signature, _, _, _, _, _, _, _, _, name_length, extra_length = fields
    if signature != 0x04034B50:
        raise zipfile.BadZipFile(f"Invalid local header for {entry.filename}")
    relative_data = relative_header + 30 + name_length + extra_length
    compressed = blob[relative_data : relative_data + entry.compress_size]
    if len(compressed) != entry.compress_size:
        raise zipfile.BadZipFile(f"Truncated compressed payload for {entry.filename}")
    if entry.compress_type == zipfile.ZIP_STORED:
        payload = compressed
    elif entry.compress_type == zipfile.ZIP_DEFLATED:
        payload = zlib.decompress(compressed, -15)
    else:
        raise NotImplementedError(
            f"Unsupported compression type {entry.compress_type} for {entry.filename}"
        )
    if len(payload) != entry.file_size:
        raise zipfile.BadZipFile(
            f"Size mismatch for {entry.filename}: {len(payload)} != {entry.file_size}"
        )
    if (binascii.crc32(payload) & 0xFFFFFFFF) != entry.crc:
        raise zipfile.BadZipFile(f"CRC mismatch for {entry.filename}")
    return payload


def _extract_batch(
    url: str,
    entries: list[RemoteZipEntry],
    destination: Path,
) -> list[tuple[str, int]]:
    """Extract nearby ZIP members using one HTTP request.

    RxRx1 stores the six channels of a site next to one another.  Fetching a
    single enclosing byte range therefore avoids two network round trips per
    PNG while preserving member-level size and CRC checks.
    """
    if not entries:
        return []
    if any(entry.flag_bits & 0x1 for entry in entries):
        raise NotImplementedError("Encrypted ZIP entries are not supported.")
    ordered = sorted(entries, key=lambda entry: entry.header_offset)
    range_start = ordered[0].header_offset
    # The local extra field is a 16-bit length.  This bound guarantees that the
    # final compressed member is present even when its local and central extra
    # fields differ.
    maximum_local_overhead = 30 + 65_535 + max(
        len(entry.filename.encode("utf-8")) for entry in ordered
    )
    last = ordered[-1]
    range_end = (
        last.header_offset
        + maximum_local_overhead
        + last.compress_size
        - 1
    )
    blob = _http_range(url, range_start, range_end)
    outputs: list[tuple[str, int]] = []
    for entry in ordered:
        payload = _entry_payload_from_range(blob, range_start, entry)
        target = destination / entry.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".partial")
        temporary.write_bytes(payload)
        os.replace(temporary, target)
        outputs.append((entry.filename, entry.file_size))
    return outputs


def _nearby_entry_batches(
    entries: list[RemoteZipEntry],
    *,
    maximum_gap: int = 256 * 1024,
    maximum_span: int = 8 * 1024 * 1024,
) -> list[list[RemoteZipEntry]]:
    """Group spatially nearby archive members into bounded byte ranges."""
    if not entries:
        return []
    ordered = sorted(entries, key=lambda entry: entry.header_offset)
    batches: list[list[RemoteZipEntry]] = []
    current = [ordered[0]]
    start = ordered[0].header_offset
    previous = ordered[0]
    for entry in ordered[1:]:
        gap = entry.header_offset - (
            previous.header_offset + previous.compress_size
        )
        span = entry.header_offset + entry.compress_size - start
        if gap <= maximum_gap and span <= maximum_span:
            current.append(entry)
        else:
            batches.append(current)
            current = [entry]
            start = entry.header_offset
        previous = entry
    batches.append(current)
    return batches


def extract_members(
    url: str,
    members: list[str],
    destination: str | Path,
    progress_path: str | Path,
    *,
    workers: int = 8,
) -> list[Path]:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    unique_members = list(dict.fromkeys(members))
    existing = [
        member
        for member in unique_members
        if (destination / member).is_file()
        and (destination / member).stat().st_size > 0
    ]
    pending = [member for member in unique_members if member not in set(existing)]
    tracker = ProgressTracker(
        "index-rxrx1-remote-archive", len(unique_members) + 1, progress_path
    )
    entries = remote_zip_entries(url, pending) if pending else {}
    tracker.state.stage = "download-rxrx1-selected-images"
    tracker.update(
        1 + len(existing),
        message=f"reused {len(existing)} verified-present files; indexed {len(entries)} pending",
    )
    outputs: list[Path] = [destination / member for member in existing]
    failures: list[tuple[str, str]] = []
    batches = _nearby_entry_batches([entries[member] for member in pending])
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_extract_batch, url, batch, destination): batch
            for batch in batches
        }
        completed = 1 + len(existing)
        for future in as_completed(futures):
            batch = futures[future]
            try:
                extracted_batch = future.result()
                outputs.extend(destination / name for name, _ in extracted_batch)
                completed += len(extracted_batch)
                size = sum(size for _, size in extracted_batch)
                message = (
                    f"{len(extracted_batch)} members "
                    f"({size / (1024 * 1024):.2f} MiB)"
                )
            except Exception as exc:  # surfaced and recorded below
                names = ",".join(entry.filename for entry in batch)
                failures.append((names, repr(exc)))
                completed += len(batch)
                message = f"FAILED batch of {len(batch)} members: {exc}"
            tracker.state.failures = len(failures)
            tracker.update(completed, message=message)

    if failures:
        tracker.fail(f"{len(failures)} member(s) failed; first={failures[0]}")
        formatted = "\n".join(f"{member}: {error}" for member, error in failures)
        raise RuntimeError(f"Remote ZIP extraction failures:\n{formatted}")
    tracker.complete(message=f"downloaded {len(outputs)} files")
    return sorted(outputs)
