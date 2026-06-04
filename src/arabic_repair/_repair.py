# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Core detection and repair logic.

This module is the only dependency on arabic-rt.  Everything else in the
package is pure standard-library Python.

Design principles
-----------------
- **Complement, not replace**: we repair byte-order corruption (visual->logical).
  We do NOT normalise alef variants, teh-marbuta, diacritics, or anything else
  that CAMeL Tools / PyArabic already handle well.
- **Deterministic**: same input always produces the same output.
- **Paragraph-aware**: blank lines are preserved so the caller's document
  structure survives the repair pass.
- **Zero false positives on clean text**: if a string contains no presentation
  forms, repair() is a no-op (identity function).
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Generator, Iterable

from arabic_rt._engine import is_shaped, is_arabic_letter, unfix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_arabic_cp(cp: int) -> bool:
    return (
        is_arabic_letter(cp)
        or 0xFB50 <= cp <= 0xFDFF
        or 0xFE70 <= cp <= 0xFEFF
    )


def _word_stats(text: str) -> tuple[int, int]:
    """Return (total_arabic_words, shaped_arabic_words) for *text*."""
    total = 0
    shaped = 0
    for token in text.split():
        if any(_is_arabic_cp(ord(c)) for c in token):
            total += 1
            if is_shaped(token):
                shaped += 1
    return total, shaped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DetectionResult:
    """Contamination report for a piece of text.

    Attributes
    ----------
    contamination_type:
        ``"clean"``           — no presentation forms detected.
        ``"fully_baked"``     — every Arabic word is in presentation form
                                (typical of fix() output or old PDF streams).
        ``"partially_baked"`` — some Arabic words are in presentation form,
                                others are raw base letters (OCR artefacts,
                                mixed sources).
    contaminated_words:
        Number of Arabic words that carry presentation-form characters.
    total_arabic_words:
        Total number of Arabic-containing words in the text.
    contaminated_ratio:
        ``contaminated_words / total_arabic_words`` (0.0 – 1.0).
        0.0 for clean text; 1.0 for fully baked text.
    needs_repair:
        ``True`` when repair() will change the text (i.e. not clean).
    """
    contamination_type: str
    contaminated_words: int
    total_arabic_words: int
    contaminated_ratio: float
    needs_repair: bool

    def __str__(self) -> str:
        return (
            f"DetectionResult(type={self.contamination_type!r}, "
            f"ratio={self.contaminated_ratio:.0%}, "
            f"words={self.contaminated_words}/{self.total_arabic_words})"
        )


def detect(text: str) -> DetectionResult:
    """Inspect *text* for visual-order / presentation-form contamination.

    Does **not** modify the text.  Use :func:`repair` to fix it.

    Parameters
    ----------
    text:
        Any string.  May be multi-line.

    Returns
    -------
    DetectionResult
        Contamination report.  Check ``.needs_repair`` to decide whether to
        call :func:`repair`.

    Examples
    --------
    >>> info = detect("ملاعلاب ابحرم")   # NFKC output of baked Arabic
    >>> info.contamination_type
    'clean'                               # base letters, but wrong order — not our job
    >>> info = detect(arabic_rt.fix("مرحبا بالعالم"))
    >>> info.contamination_type
    'fully_baked'
    """
    if not text:
        return DetectionResult(
            contamination_type="clean",
            contaminated_words=0,
            total_arabic_words=0,
            contaminated_ratio=0.0,
            needs_repair=False,
        )

    total, shaped = _word_stats(text)

    if total == 0 or shaped == 0:
        ctype = "clean"
        ratio = 0.0
    elif shaped == total:
        ctype = "fully_baked"
        ratio = 1.0
    else:
        ctype = "partially_baked"
        ratio = shaped / total

    return DetectionResult(
        contamination_type=ctype,
        contaminated_words=shaped,
        total_arabic_words=total,
        contaminated_ratio=ratio,
        needs_repair=(shaped > 0),
    )


def repair(text: str) -> str:
    """Repair visually-baked Arabic in *text*, returning clean logical Arabic.

    Processes the text paragraph by paragraph (blank lines are preserved).
    Within each paragraph, delegates to :func:`arabic_rt.unfix` which handles
    both fully-baked and partially-baked lines correctly after the 0.1.4
    hardening.

    The output is suitable for direct use with CAMeL Tools::

        from camel_tools.utils.normalize import normalize_unicode
        clean = normalize_unicode(repair(raw_text))

    Parameters
    ----------
    text:
        Raw string from a PDF extractor, OCR engine, or legacy source.

    Returns
    -------
    str
        Text with presentation-form characters replaced by base logical letters
        and visual word-order restored to logical order.  Non-Arabic content
        (Latin, digits, punctuation) is untouched.  Blank lines are preserved.
        If the text contains no presentation forms, the input is returned
        unchanged (zero-cost identity).

    Notes
    -----
    *What we fix*: presentation-form codepoints (U+FB50–U+FDFF,
    U+FE70–U+FEFF) and reversed visual word-order.

    *What we do NOT fix*: alef variant normalisation, teh-marbuta/yaa
    variants, diacritics, or any linguistic normalisation — use CAMeL Tools
    or PyArabic for those after calling this function.

    Known limitation
    ----------------
    A paragraph where every Arabic word is shaped but the text happens to be
    in logical order (e.g. output of ``arabic_rt.shape()`` without ``fix()``)
    is indistinguishable from a fully-baked paragraph and will be reversed.
    This is an inherent ambiguity; in practice such input does not appear in
    PDF/OCR pipelines.
    """
    if not text or not is_shaped(text):
        return text

    paragraphs: list[str] = []
    for para in _split_paragraphs(text):
        if para == "":
            paragraphs.append("")
        elif not is_shaped(para):
            paragraphs.append(para)
        else:
            paragraphs.append(unfix(para))
    return "\n".join(paragraphs)


def repair_stream(lines: Iterable[str]) -> Generator[str, None, None]:
    """Repair *lines* one at a time; memory-efficient for large documents.

    Each line is processed independently.  Paragraph grouping is NOT applied
    (use :func:`repair` if you want blank-line-aware paragraph handling).

    Parameters
    ----------
    lines:
        Any iterable of strings (e.g. an open file, a list of OCR segments).
        Newline characters at the end of each line are stripped and then
        re-added to the output.

    Yields
    ------
    str
        Repaired line, with its original trailing newline restored if present.

    Examples
    --------
    >>> with open("arabic_doc.txt", encoding="utf-8") as f:
    ...     with open("repaired.txt", "w", encoding="utf-8") as out:
    ...         for line in repair_stream(f):
    ...             out.write(line)
    """
    for raw in lines:
        trailing = "\n" if raw.endswith("\n") else ""
        line = raw.rstrip("\n")
        if is_shaped(line):
            yield unfix(line) + trailing
        else:
            yield raw


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_paragraphs(text: str) -> list[str]:
    """Split *text* on blank lines, preserving the blank-line markers."""
    paragraphs: list[str] = []
    current: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.strip() == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
            paragraphs.append("")   # blank line marker
        else:
            current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs
