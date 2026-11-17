# Verified Findings: Evidence Verification CLI

Deterministic, offline Python CLI to verify factual claims in incident reports against heterogeneous machine and officer records.

## Quickstart

Run test suite:
```bash
make test
# Or directly with Python:
python3 -m unittest discover -s tests -v
```

Run evidence verification CLI:
```bash
python3 plearun_cli.py reports/report_fictional_02.txt records/ > findings.json
```

---

## How It Works

The verification pipeline operates across six modular stages:

1. **Claim Extraction (`report_parser.py`)**: Parses the narrative text, filters non-evidential headers/banners, splits text into sentences, and identifies factual claims (times, speeds, zones, stops, counts).
2. **Resilient Data Ingestion (`record_loaders.py`)**: Ingests evidence records across formats without third-party dependencies:
   - CSVs with UTF-8 BOM (`utf-8-sig`) and leading marker lines (`#PLEARUN`).
   - Windows-1252 (`cp1252`) encoded CSVs with quoted multi-word strings.
   - Nested JSON exports (`dispatch.json`) handling three distinct timestamp formats (ISO with offset, un-timezone-qualified SQL strings, epoch milliseconds).
   - WebVTT transcripts (`bodycam_transcript.vtt`) parsing cue intervals and overlapping dialogue.
   - Every file's raw bytes and physical line numbers (1-based) are preserved in memory.
3. **Cross-Source Clock Synchronization (`clock_sync.py`)**: Devices do not share synchronized clocks. The pipeline establishes Computer-Aided Dispatch (CAD) as the reference clock and searches for multi-source anchor events:
   - *Anchor 1 (911 radio call)*: Aligns officer notes with dispatch.
   - *Anchor 2 (Stop at lot)*: Aligns traffic camera `CAM-07` and bodycam elapsed cue time against notes and dispatch stop records.
   - *Unsettled devices*: Devices without reliable multi-source corroboration (e.g. `CAM-03`) are explicitly marked unaligned and excluded from time-sensitive checks.
4. **Domain Verification Engine (`verifier.py`)**: Tests each claim against relevant evidence:
   - Compares speeds against aligned cameras within observation time windows.
   - Evaluates stop timestamps and arrival logs.
   - Categorizes claims without instrumented evidence (e.g., lane occupancy) as `not_checkable`.
5. **Exact Substring Quotation Guard (`quote_validator.py`)**: Enforces Rule 1. Every candidate `match` or `conflict` is verified against the raw text of the cited physical row. If the quote is not an exact literal substring of that row, the finding is safely downgraded to `not_settled`, and `cite` and `quote` are stripped.
6. **JSON Serialization (`findings_exporter.py`)**: Emits schema-compliant findings JSON.

---

## The Three Hardest Engineering Decisions

1. **Preserving 1-Based Physical Line Mappings Across Format Quirks**:
   - *Problem*: CSV comment lines (`#PLEARUN`), header rows, and WebVTT cue structures make semantic row indexing differ from physical file line numbers.
   - *Decision*: Bound all citations to literal 1-based physical line numbers of the original file, storing `raw_lines` in an evidence repository. This guarantees that `quote in raw_lines[row - 1]` is foolproof across CSV, JSON, and WebVTT files.
2. **Principled Refusal to Synchronize Uncertain Devices**:
   - *Problem*: Traffic camera `CAM-03` logged intermittent 0 mph readings at 21:15:18, but lacked cross-source corroboration.
   - *Decision*: Strictly adhered to Rule 3 ("If you cannot estimate an offset reliably, do not align that device"). `CAM-03` was marked unaligned, preventing false conflicts on speed and location.
3. **Conservative Downgrading to `not_settled`**:
   - *Problem*: Grading penalizes false conflicts much more heavily than `not_settled`.
   - *Decision*: Implemented an automatic quote validation guard that unconditionally downgrades any finding to `not_settled` (and purges `cite`/`quote`) if citation bounds or substring checks fail.

---

## What It Gets Wrong

- **Sentence-Level Granularity**: If a single sentence contains multiple compound assertions (e.g. observing the car *and* clocking its speed *and* noting the mile marker), the parser treats the sentence as a unified claim.
- **Complex Clock Drift**: Assumes constant clock offset rather than time-varying drift across prolonged multi-hour recording windows.

---

## What Would Break First on Real Records

1. **Free-form Unstructured Reports**: Complex linguistic variations, typos in dates, or passive-voice narratives would require semantic dependency parsing rather than deterministic regex extraction.
2. **Multi-Gigabyte Video/Audio and Logs**: Reading entire logs into memory for line-indexed substring checking would exceed RAM limits on multi-gigabyte files; streaming line offsets and disk-backed indexing would be necessary.
3. **Multi-Jurisdiction Timezones**: Records crossing daylight saving transitions or disparate local timezones without UTC offsets.

---

## Tools Used

- **Python 3.12 Standard Library** (`csv`, `json`, `re`, `datetime`, `unittest`, `dataclasses`, `pathlib`).
- **Claude / Gemini coding assistant** via Antigravity for iterative code generation, test design, and architecture inspection.
