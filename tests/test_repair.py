"""Tests for arabic-repair.

Mirror the arabic-rt test style: deterministic, no ML, no network.
"""
import unicodedata
import arabic_rt as ar_rt
import arabic_repair as ar


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------

class TestDetect:
    def test_clean_returns_clean(self):
        info = ar.detect("مرحبا بالعالم")
        assert info.contamination_type == "clean"
        assert info.needs_repair is False
        assert info.contaminated_ratio == 0.0

    def test_empty_returns_clean(self):
        info = ar.detect("")
        assert info.contamination_type == "clean"
        assert info.needs_repair is False

    def test_latin_only_returns_clean(self):
        info = ar.detect("Hello World 123")
        assert info.contamination_type == "clean"
        assert info.needs_repair is False

    def test_fully_baked_detected(self):
        baked = ar_rt.fix("مرحبا بالعالم")
        info = ar.detect(baked)
        assert info.contamination_type == "fully_baked"
        assert info.needs_repair is True
        assert info.contaminated_ratio == 1.0
        assert info.total_arabic_words == 2
        assert info.contaminated_words == 2

    def test_partially_baked_detected(self):
        shaped_word = ar_rt.shape("مرحبا")   # first word shaped, second raw
        partial = shaped_word + " بالعالم"
        info = ar.detect(partial)
        assert info.contamination_type == "partially_baked"
        assert info.needs_repair is True
        assert 0.0 < info.contaminated_ratio < 1.0

    def test_multiline_fully_baked(self):
        baked = ar_rt.fix("السلام عليكم") + "\n" + ar_rt.fix("مرحبا بالعالم")
        info = ar.detect(baked)
        assert info.contamination_type == "fully_baked"
        assert info.needs_repair is True

    def test_ratio_correct(self):
        # 1 shaped word out of 3 arabic words
        shaped = ar_rt.shape("مرحبا")
        text = shaped + " بالعالم يا صديقي"
        info = ar.detect(text)
        assert info.total_arabic_words == 4
        assert info.contaminated_words == 1
        assert abs(info.contaminated_ratio - 0.25) < 0.01


# ---------------------------------------------------------------------------
# repair() — basic correctness
# ---------------------------------------------------------------------------

ROUND_TRIP_CASES = [
    "مرحبا",
    "مرحبا بالعالم",
    "السلام عليكم ورحمة الله",
    "Hello مرحبا World",
    "اكتب 123 و user@mail.com هنا",
    "بسم الله الرحمن الرحيم",
]


class TestRepair:
    def test_noop_on_clean(self):
        text = "مرحبا بالعالم"
        assert ar.repair(text) == text

    def test_noop_on_latin(self):
        text = "Hello World 123"
        assert ar.repair(text) == text

    def test_noop_on_empty(self):
        assert ar.repair("") == ""

    def test_fully_baked_restored(self):
        for text in ROUND_TRIP_CASES:
            baked = ar_rt.fix(text)
            assert ar.repair(baked) == text, f"failed for: {text!r}"

    def test_game_preset_restored(self):
        for text in ROUND_TRIP_CASES:
            baked = ar_rt.fix(text, ar_rt.GAME)
            assert ar.repair(baked) == text, f"failed for: {text!r}"

    def test_partial_shaping_repaired(self):
        shaped_word = ar_rt.shape("مرحبا")
        partial = shaped_word + " بالعالم"
        result = ar.repair(partial)
        assert result == "مرحبا بالعالم"

    def test_no_presentation_forms_remain_after_repair(self):
        for text in ROUND_TRIP_CASES:
            baked = ar_rt.fix(text)
            repaired = ar.repair(baked)
            pf = [c for c in repaired if 0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF]
            assert pf == [], f"presentation forms remain in {repaired!r}: {pf}"

    def test_nfkc_alone_does_not_restore_order(self):
        """Prove the gap: NFKC de-shapes but does NOT restore word order."""
        clean = "مرحبا بالعالم"
        baked = ar_rt.fix(clean)
        nfkc = unicodedata.normalize("NFKC", baked)
        # NFKC gives base letters but still in reversed order
        assert nfkc != clean
        # our repair restores it
        assert ar.repair(baked) == clean

    def test_latin_untouched_in_mixed_text(self):
        baked = ar_rt.fix("Hello مرحبا World")
        repaired = ar.repair(baked)
        assert "Hello" in repaired
        assert "World" in repaired
        assert "مرحبا" in repaired

    def test_digits_untouched(self):
        baked = ar_rt.fix("اكتب 123 هنا")
        repaired = ar.repair(baked)
        assert "123" in repaired


# ---------------------------------------------------------------------------
# repair() — document structure
# ---------------------------------------------------------------------------

class TestRepairDocumentStructure:
    def test_blank_lines_preserved(self):
        para1 = ar_rt.fix("مرحبا بالعالم")
        para2 = ar_rt.fix("السلام عليكم")
        doc = para1 + "\n\n" + para2
        repaired = ar.repair(doc)
        assert "\n\n" in repaired
        assert "مرحبا بالعالم" in repaired
        assert "السلام عليكم" in repaired

    def test_multiple_blank_lines_preserved(self):
        baked = ar_rt.fix("مرحبا")
        doc = baked + "\n\n\n" + baked
        repaired = ar.repair(doc)
        # two blank lines -> two empty-line markers preserved
        assert repaired.count("\n") >= 2

    def test_mixed_paragraphs_clean_and_baked(self):
        clean_para = "This is an English paragraph."
        baked_para = ar_rt.fix("مرحبا بالعالم")
        doc = clean_para + "\n\n" + baked_para
        repaired = ar.repair(doc)
        assert clean_para in repaired
        assert "مرحبا بالعالم" in repaired

    def test_multiline_paragraph_repaired(self):
        line1 = ar_rt.fix("مرحبا بالعالم")
        line2 = ar_rt.fix("السلام عليكم")
        para = line1 + "\n" + line2
        repaired = ar.repair(para)
        assert "مرحبا بالعالم" in repaired
        assert "السلام عليكم" in repaired


# ---------------------------------------------------------------------------
# repair_stream()
# ---------------------------------------------------------------------------

class TestRepairStream:
    def test_stream_repairs_lines(self):
        lines = [ar_rt.fix("مرحبا بالعالم") + "\n", ar_rt.fix("السلام عليكم") + "\n"]
        result = list(ar.repair_stream(lines))
        assert "مرحبا بالعالم" in result[0]
        assert "السلام عليكم" in result[1]

    def test_stream_preserves_trailing_newline(self):
        lines = [ar_rt.fix("مرحبا") + "\n", "Hello\n"]
        result = list(ar.repair_stream(lines))
        assert result[0].endswith("\n")
        assert result[1].endswith("\n")

    def test_stream_noop_on_clean(self):
        lines = ["مرحبا\n", "Hello\n"]
        result = list(ar.repair_stream(lines))
        assert result == lines

    def test_stream_large(self):
        """1 000 lines — smoke test for generator memory safety."""
        clean = "مرحبا بالعالم"
        baked = ar_rt.fix(clean)
        lines = [baked + "\n"] * 1000
        result = list(ar.repair_stream(lines))
        assert len(result) == 1000
        assert all(clean in r for r in result)


# ---------------------------------------------------------------------------
# CAMeL Tools chaining (skipped gracefully if not installed)
# ---------------------------------------------------------------------------

class TestCamelChain:
    def test_repair_then_camel_normalize(self):
        """repair() output must be accepted by CAMeL normalize_unicode."""
        pytest = __import__("pytest")
        try:
            from camel_tools.utils.normalize import normalize_unicode
        except ImportError:
            pytest.skip("camel-tools not installed")

        baked = ar_rt.fix("مرحبا بالعالم")
        repaired = ar.repair(baked)
        # normalize_unicode should not crash and should return a string
        result = normalize_unicode(repaired)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_nfkc_after_repair_no_presentation_forms(self):
        """NFKC after repair() should produce clean base-letter text."""
        baked = ar_rt.fix("مرحبا بالعالم")
        repaired = ar.repair(baked)
        nfkc = unicodedata.normalize("NFKC", repaired)
        pf = [c for c in nfkc if 0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF]
        assert pf == []
