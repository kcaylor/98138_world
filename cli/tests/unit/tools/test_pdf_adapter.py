"""pypdf adapter tests on a tiny synthetic PDF built in the test (skipped without pypdf)."""

import io

import pytest

pypdf = pytest.importorskip("pypdf")

from PIL import Image  # noqa: E402
from pypdf.generic import (  # noqa: E402
    ArrayObject, DictionaryObject, FloatObject, NameObject, NumberObject, StreamObject,
)

from kit31203 import pdf_adapter  # noqa: E402


def _jpeg(w=16, h=12, color=(200, 30, 40)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _stream(data, **entries):
    s = StreamObject()
    s._data = data
    for k, v in entries.items():
        s[NameObject("/" + k)] = v
    return s


@pytest.fixture
def synthetic_pdf(tmp_path):
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=200, height=200)

    image = _stream(
        _jpeg(), Type=NameObject("/XObject"), Subtype=NameObject("/Image"),
        Width=NumberObject(16), Height=NumberObject(12), ColorSpace=NameObject("/DeviceRGB"),
        BitsPerComponent=NumberObject(8), Filter=NameObject("/DCTDecode"))
    image_ref = writer._add_object(image)

    form = _stream(
        b"q 30 0 0 30 5 5 cm /Im0 Do Q",
        Type=NameObject("/XObject"), Subtype=NameObject("/Form"),
        BBox=ArrayObject([NumberObject(0), NumberObject(0), NumberObject(200), NumberObject(200)]),
        Matrix=ArrayObject([FloatObject(1), FloatObject(0), FloatObject(0), FloatObject(1),
                            FloatObject(10), FloatObject(20)]),
        Resources=DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): image_ref})}),
    )
    form_ref = writer._add_object(form)

    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
        NameObject("/XObject"): DictionaryObject({NameObject("/Fm0"): form_ref}),
    })
    content = (
        b"BT /F1 8 Tf 1 0 0 1 50 100 Tm (12x) Tj ET\n"
        b"BT /F1 8 Tf 1 0 0 1 50 92.8 Tm (614101) Tj ET\n"
        b"q 2 0 0 2 0 0 cm /Fm0 Do Q\n"
    )
    page[NameObject("/Contents")] = writer._add_object(_stream(content))

    path = tmp_path / "synthetic.pdf"
    with open(path, "wb") as f:
        writer.write(f)
    return path


def test_page_words(synthetic_pdf):
    doc = pdf_adapter.open_pdf(synthetic_pdf)
    words = pdf_adapter.page_words(doc, 1)
    texts = {w.text: w for w in words}
    assert set(texts) == {"12x", "614101"}
    assert texts["12x"].x == pytest.approx(50, abs=0.01)
    assert texts["12x"].y == pytest.approx(100, abs=0.01)
    assert texts["614101"].y == pytest.approx(92.8, abs=0.01)
    assert tuple(texts["12x"]) == (texts["12x"].x, texts["12x"].y, "12x")


def test_image_placements_through_form_matrix(synthetic_pdf):
    doc = pdf_adapter.open_pdf(synthetic_pdf)
    placements = pdf_adapter.image_placements(doc, 1)
    assert len(placements) == 1
    p = placements[0]
    assert p.page == 1
    assert p.name == "/Im0"
    assert (p.width, p.height) == (16, 12)
    # image cm (30, at 5,5) inside form Matrix (+10,+20) inside page cm (x2)
    assert p.x == pytest.approx(30.0)
    assert p.y == pytest.approx(50.0)
    assert p.scale == pytest.approx(60.0)
    assert p.height_pt == pytest.approx(60.0)


def test_image_pixels(synthetic_pdf):
    doc = pdf_adapter.open_pdf(synthetic_pdf)
    p = pdf_adapter.image_placements(doc, 1)[0]
    img = pdf_adapter.load_image(doc, p)
    assert img.size == (16, 12)
    assert img.mode == "RGB"
    r, g, b = img.getpixel((8, 6))
    assert abs(r - 200) < 10 and abs(g - 30) < 10 and abs(b - 40) < 10


def test_page_out_of_range(synthetic_pdf):
    doc = pdf_adapter.open_pdf(synthetic_pdf)
    with pytest.raises(IndexError):
        pdf_adapter.page_words(doc, 2)
