"""Unit tests for the provenance block shared by every reference data file."""

import pytest

from lego_image_processor.kit.source import (
    DISCLAIMER,
    PINNED_SHA256,
    PINNED_URL,
    SOURCE_TITLE,
    Citation,
    SourceDocument,
)


def _source_dict(**overrides):
    data = {
        "title": SOURCE_TITLE,
        "url": PINNED_URL,
        "sha256": PINNED_SHA256,
        "pages": [159],
        "generator": "curated by hand",
        "generated_on": "2026-11-21",
        "citations": [
            {"id": "brickset", "title": "Brickset inventory 31203-1",
             "url": "https://brickset.com/inventories/31203-1", "accessed": "2026-11-21"},
        ],
        "disclaimer": DISCLAIMER,
    }
    data.update(overrides)
    return data


class TestConstants:
    def test_pinned_values(self):
        assert PINNED_URL == "https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf"
        assert PINNED_SHA256 == "b593e2f4befbc227c5b12fec9b58a1bd6141d19b54de5f5336dcc8cc9eb43c4c"
        assert DISCLAIMER == "Not affiliated with or endorsed by The LEGO Group."


class TestCitation:
    def test_round_trip(self):
        data = {"id": "ldraw", "title": "LDraw", "url": "https://example.org", "accessed": "2026-11-21"}
        assert Citation.from_dict(data).to_dict() == data

    @pytest.mark.parametrize("missing", ["id", "title", "url", "accessed"])
    def test_missing_field_rejected(self, missing):
        data = {"id": "ldraw", "title": "LDraw", "url": "https://example.org", "accessed": "2026-11-21"}
        del data[missing]
        with pytest.raises(ValueError, match=missing):
            Citation.from_dict(data)


class TestSourceDocument:
    def test_round_trip(self):
        data = _source_dict()
        src = SourceDocument.from_dict(data)
        assert src.sha256 == PINNED_SHA256
        assert src.pages == [159]
        assert src.citations[0].id == "brickset"
        assert src.to_dict() == data

    def test_citation_lookup(self):
        src = SourceDocument.from_dict(_source_dict())
        assert src.citation("brickset").url == "https://brickset.com/inventories/31203-1"
        with pytest.raises(KeyError):
            src.citation("nope")

    @pytest.mark.parametrize("bad", ["abc", "g" * 64, PINNED_SHA256.upper()[:63]])
    def test_sha256_not_hex64_rejected(self, bad):
        with pytest.raises(ValueError, match="sha256"):
            SourceDocument.from_dict(_source_dict(sha256=bad))

    def test_sha256_differs_from_pinned_rejected(self):
        with pytest.raises(ValueError, match="pinned"):
            SourceDocument.from_dict(_source_dict(sha256="0" * 64))

    def test_missing_disclaimer_rejected(self):
        data = _source_dict()
        del data["disclaimer"]
        with pytest.raises(ValueError, match="disclaimer"):
            SourceDocument.from_dict(data)

    def test_wrong_disclaimer_rejected(self):
        with pytest.raises(ValueError, match="disclaimer"):
            SourceDocument.from_dict(_source_dict(disclaimer="Made by LEGO"))

    @pytest.mark.parametrize("bad", ["21-11-2026", "2026-1-2", "yesterday", ""])
    def test_generated_on_format(self, bad):
        with pytest.raises(ValueError, match="generated_on"):
            SourceDocument.from_dict(_source_dict(generated_on=bad))

    def test_pages_must_be_ints(self):
        with pytest.raises(ValueError, match="pages"):
            SourceDocument.from_dict(_source_dict(pages=["159"]))

    def test_citations_parsed(self):
        with pytest.raises(ValueError):
            SourceDocument.from_dict(_source_dict(citations=[{"id": "x"}]))
