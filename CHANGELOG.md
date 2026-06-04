# Changelog

## 0.1.0 — 2026-06-04
- Initial release.
- `detect(text)` — inspect contamination type ("clean" / "fully_baked" / "partially_baked"),
  ratio, and word counts without modifying the text.
- `repair(text)` — paragraph-aware repair: de-shape presentation forms and restore logical
  word order. Blank lines and document structure preserved. Non-Arabic content untouched.
- `repair_stream(lines)` — generator for large PDF/OCR files; processes one line at a time,
  preserves trailing newlines.
- Requires `arabic-rt>=0.1.4` (the hardened `unfix()` that handles partial shaping).
- Designed to chain into CAMeL Tools: `normalize_unicode(repair(text))`.
