# arabic-repair

Detect and repair visually-baked Arabic text extracted from PDFs, OCR engines, and legacy sources.

![arabic-repair demo](docs/demo.png)

## The problem

Arabic text stored in old PDF streams, scanned documents (OCR), and legacy systems is often
**baked**: characters are stored as Unicode Presentation Forms (U+FB50–U+FEFF) in **reversed
visual order** rather than logical reading order. Standard tools like Unicode NFKC normalization
and CAMeL Tools remove the presentation forms but **do not restore the character order** — the
text remains scrambled.

`arabic-repair` fixes both: it de-shapes the presentation forms *and* restores logical word order,
then hands clean text to your downstream NLP pipeline.

## Install

```bash
pip install arabic-repair
```

## Quick start

```python
import arabic_repair as ar

# Repair a string from a PDF extractor or OCR engine
clean = ar.repair(raw_text)

# Inspect contamination before committing to repair
info = ar.detect(raw_text)
print(info.contamination_type)   # "fully_baked" | "partially_baked" | "clean"
print(info.contaminated_ratio)   # 0.0 – 1.0

# Chain into CAMeL Tools for full normalization
from camel_tools.utils.normalize import normalize_unicode
fully_clean = normalize_unicode(ar.repair(raw_text))

# Stream large documents line by line
with open("big_doc.txt", encoding="utf-8") as f:
    for line in ar.repair_stream(f):
        process(line)
```

## What it fixes / what it doesn't

| | arabic-repair | NFKC | CAMeL Tools |
|---|:---:|:---:|:---:|
| Presentation forms → base letters | ✓ | ✓ | ✓ |
| Visual order → logical order | **✓** | ✗ | ✗ |
| Alef variant normalization | ✗ | ✗ | ✓ |
| Yaa / teh-marbuta normalization | ✗ | ✗ | ✓ |
| Diacritics | ✗ | ✗ | ✓ |

Use `arabic-repair` **first**, then CAMeL Tools for linguistic normalization.

## License

MPL-2.0
