# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""arabic-repair — detect and repair visually-baked Arabic text.

Fixes Arabic text extracted from PDFs, OCR engines, and legacy sources
where the text is stored in visual/presentation-form order rather than
logical Unicode order.  Output is clean logical Arabic, ready to pass
directly into CAMeL Tools, PyArabic, or any downstream NLP pipeline.

Quick start::

    import arabic_repair as ar

    text = ar.repair(raw_text)          # repair a string
    info = ar.detect(raw_text)          # inspect without modifying
    print(info.contamination_type)      # "fully_baked" | "partially_baked" | "clean"

    # Chain into CAMeL Tools:
    from camel_tools.utils.normalize import normalize_unicode
    cleaned = normalize_unicode(ar.repair(raw_text))

    # Large document (line-by-line generator):
    for repaired_line in ar.repair_stream(open("doc.txt")):
        process(repaired_line)
"""
from __future__ import annotations

from ._repair import (
    DetectionResult,
    detect,
    repair,
    repair_stream,
)

__version__ = "0.1.0"
__author__ = "Bandar AlSwyan"
__license__ = "MPL-2.0"

__all__ = [
    "DetectionResult",
    "detect",
    "repair",
    "repair_stream",
    "__version__",
]
