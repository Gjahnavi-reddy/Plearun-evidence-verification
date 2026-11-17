"""Resilient record loaders for CSV, JSON, and WebVTT evidence sources."""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from plearun_pipeline.models import RawFileRecord, RecordItem


# Timezone for the Route 21 corridor (US Eastern, UTC-5 in March standard time)
DEFAULT_TIMEZONE = timezone(timedelta(hours=-5))
DEFAULT_DATE = "2026-03-02"


def read_file_raw(filepath: Path) -> RawFileRecord:
    """Read a file safely detecting BOM and handling encodings (utf-8, cp1252, etc.).
    
    Preserves exact raw lines for citation substring verification.
    """
    raw_bytes = filepath.read_bytes()
    filename = filepath.name

    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        encodings = ("utf-8-sig", "utf-8")
    elif "cp1252" in filename.lower() or "windows-1252" in filename.lower():
        encodings = ("cp1252", "utf-8", "latin-1")
    else:
        encodings = ("utf-8", "cp1252", "latin-1")

    for encoding in encodings:
        try:
            text = raw_bytes.decode(encoding)
            lines = text.splitlines()
            return RawFileRecord(
                filename=filename,
                filepath=filepath,
                raw_lines=lines,
                encoding=encoding,
            )
        except UnicodeDecodeError:
            continue

    # Fallback with replacement if all encodings failed
    text = raw_bytes.decode("utf-8", errors="replace")
    return RawFileRecord(
        filename=filename,
        filepath=filepath,
        raw_lines=text.splitlines(),
        encoding="utf-8-replace",
    )


def parse_timestamp(
    raw_val: Any,
    default_date: str = DEFAULT_DATE,
    default_tz: timezone = DEFAULT_TIMEZONE,
) -> Optional[datetime]:
    """Parse various timestamp representations into timezone-aware datetime.
    
    Supports:
    - Unix epoch milliseconds (int or digit string): e.g. 1772502579000
    - ISO 8601 with offset: e.g. 2026-03-02T20:51:06-05:00
    - Naive ISO / SQL datetime: e.g. 2026-03-02 21:10:19
    - Local time HH:MM or HH:MM:SS: e.g. 21:15 or 21:10:19
    """
    if raw_val is None:
        return None

    s = str(raw_val).strip()
    if not s:
        return None

    # 1. Unix epoch milliseconds (12-14 digits)
    if s.isdigit() and len(s) >= 12:
        try:
            epoch_seconds = int(s) / 1000.0
            dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
            return dt.astimezone(default_tz)
        except (ValueError, OverflowError):
            pass

    # 2. ISO 8601 with or without offset
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=default_tz)
        return dt
    except ValueError:
        pass

    # 3. Time only HH:MM[:SS]
    m_time = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if m_time:
        hour = int(m_time.group(1))
        minute = int(m_time.group(2))
        second = int(m_time.group(3)) if m_time.group(3) else 0
        try:
            y, m, d = (int(x) for x in default_date.split("-"))
            return datetime(y, m, d, hour, minute, second, tzinfo=default_tz)
        except ValueError:
            pass

    return None


def parse_vtt_timestamp(ts_str: str) -> Optional[float]:
    """Parse WebVTT timestamp string (HH:MM:SS.mmm or MM:SS.mmm) into seconds."""
    s = ts_str.strip()
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            sec = float(parts[2])
            return h * 3600 + m * 60 + sec
        elif len(parts) == 2:
            m = float(parts[0])
            sec = float(parts[1])
            return m * 60 + sec
    except ValueError:
        pass
    return None


class EvidenceRepository:
    """Loads, indexes, and holds all evidence files from a directory."""

    def __init__(self, records_dir: Path) -> None:
        self.records_dir = records_dir
        self.raw_files: dict[str, RawFileRecord] = {}
        self.items: list[RecordItem] = []
        self._load_all()

    def _load_all(self) -> None:
        if not self.records_dir.exists() or not self.records_dir.is_dir():
            return

        # Find all files in the records directory
        for filepath in sorted(self.records_dir.iterdir()):
            if not filepath.is_file():
                continue
            raw_record = read_file_raw(filepath)
            self.raw_files[filepath.name] = raw_record

            ext = filepath.suffix.lower()
            if ext == ".csv":
                self._load_csv(raw_record)
            elif ext == ".json":
                self._load_json(raw_record)
            elif ext in (".vtt", ".webvtt"):
                self._load_vtt(raw_record)

    def _load_csv(self, raw_record: RawFileRecord) -> None:
        """Parse CSV preserving 1-based line index."""
        header_row_idx: Optional[int] = None
        headers: list[str] = []

        for line_idx, line in enumerate(raw_record.raw_lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # Skip comments/markers like #PLEARUN
            if stripped.startswith("#"):
                continue

            # Parse line using standard csv.reader
            row_parts = next(csv.reader([line]))
            if not row_parts or not any(row_parts):
                continue

            if header_row_idx is None:
                # First non-comment row is the header
                header_row_idx = line_idx
                headers = [h.strip() for h in row_parts]
                continue

            # Data row
            data_dict = dict(zip(headers, [p.strip() for p in row_parts]))
            ts = None
            device = None

            # Detect timestamp field
            for ts_col in ("timestamp", "Time", "logged", "time"):
                if ts_col in data_dict:
                    ts = parse_timestamp(data_dict[ts_col])
                    if ts:
                        break

            # Detect device/author
            for dev_col in ("device", "Author", "unit", "author"):
                if dev_col in data_dict:
                    device = data_dict[dev_col]
                    break

            # If speed / zone present, convert to int if possible
            if "speed_mph" in data_dict:
                try:
                    data_dict["speed_mph"] = int(data_dict["speed_mph"])
                except ValueError:
                    pass
            if "zone_mph" in data_dict:
                try:
                    data_dict["zone_mph"] = int(data_dict["zone_mph"])
                except ValueError:
                    pass

            item = RecordItem(
                file=raw_record.filename,
                row=line_idx,
                raw_text=line,
                timestamp=ts,
                device=device,
                payload=data_dict,
            )
            self.items.append(item)

    def _load_json(self, raw_record: RawFileRecord) -> None:
        """Parse JSON events while indexing their line locations."""
        full_text = "\n".join(raw_record.raw_lines)
        try:
            data = json.loads(full_text)
        except json.JSONDecodeError:
            return

        # Check for standard CAD events list: data["export"]["events"]
        events = []
        if isinstance(data, dict):
            if "export" in data and isinstance(data["export"], dict):
                events = data["export"].get("events", [])
            elif "events" in data:
                events = data.get("events", [])

        for ev in events:
            if not isinstance(ev, dict):
                continue

            ev_id = str(ev.get("id", ""))
            ev_type = str(ev.get("type", ""))
            logged = ev.get("logged")
            unit = ev.get("unit")
            ts = parse_timestamp(logged)

            # Locate the exact line number in the JSON file
            # Prefer the line containing logged timestamp or event id
            best_line_idx = 1
            for l_idx, line in enumerate(raw_record.raw_lines, start=1):
                if ev_id and ev_id in line:
                    best_line_idx = l_idx
                    break

            # Check if there's a specific line for 'logged'
            logged_str = str(logged)
            for l_idx, line in enumerate(raw_record.raw_lines, start=1):
                if logged_str and logged_str in line:
                    best_line_idx = l_idx
                    break

            payload = dict(ev)
            payload["event_id"] = ev_id
            payload["event_type"] = ev_type

            item = RecordItem(
                file=raw_record.filename,
                row=best_line_idx,
                raw_text=raw_record.raw_lines[best_line_idx - 1] if best_line_idx <= len(raw_record.raw_lines) else "",
                timestamp=ts,
                device=unit or ev_type,
                payload=payload,
            )
            self.items.append(item)

    def _load_vtt(self, raw_record: RawFileRecord) -> None:
        """Parse WebVTT file into items with cue timestamps and text lines."""
        lines = raw_record.raw_lines
        cue_idx = 0
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].strip()
            if not line or line.startswith("WEBVTT"):
                i += 1
                continue

            # Check for cue timing line: 00:00:00.000 --> 00:00:04.000
            if "-->" in line:
                cue_idx += 1
                timing_line_idx = i + 1
                timing_parts = line.split("-->")
                start_sec = parse_vtt_timestamp(timing_parts[0].strip().split()[0])
                end_sec = parse_vtt_timestamp(timing_parts[1].strip().split()[0])

                # Read subsequent text lines for this cue
                i += 1
                cue_text_lines: list[tuple[int, str]] = []
                while i < n and lines[i].strip():
                    cue_text_lines.append((i + 1, lines[i]))
                    i += 1

                for text_line_idx, text_line in cue_text_lines:
                    # Parse speaker if formatted like [SYNTHETIC] Officer Lee: 58 in a 45.
                    speaker = None
                    dialogue = text_line
                    m_speaker = re.match(r"^(?:\[[^\]]+\]\s*)?([^:]+):\s*(.*)$", text_line)
                    if m_speaker:
                        speaker = m_speaker.group(1).strip()
                        dialogue = m_speaker.group(2).strip()

                    payload = {
                        "cue_index": cue_idx,
                        "timing_line": timing_line_idx,
                        "start_seconds": start_sec,
                        "end_seconds": end_sec,
                        "speaker": speaker,
                        "dialogue": dialogue,
                    }

                    item = RecordItem(
                        file=raw_record.filename,
                        row=text_line_idx,
                        raw_text=text_line,
                        timestamp=None,  # WebVTT is relative; anchored by clock_sync
                        device=speaker,
                        payload=payload,
                    )
                    self.items.append(item)
            else:
                i += 1

    def get_items_by_file(self, filename: str) -> list[RecordItem]:
        return [item for item in self.items if item.file == filename]

    def get_raw_line(self, filename: str, row: int) -> Optional[str]:
        raw_file = self.raw_files.get(filename)
        if raw_file:
            return raw_file.get_line(row)
        return None
