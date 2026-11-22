"""pypdf adapter: page words with positions, image placements and image pixels.

This is the only module of the tool (and of the project) that imports pypdf.
Coordinates are PDF points with the origin at the bottom left of the page (y grows upward).
Page numbers are 1-based, as printed in the instructions.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, NamedTuple, Tuple

import pypdf
from PIL import Image
from pypdf.generic import ContentStream

Matrix = Tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class Word(NamedTuple):
    x: float
    y: float
    text: str


class ImagePlacement(NamedTuple):
    page: int
    name: str
    width: int   # pixels
    height: int  # pixels
    x: float     # origin of the drawn image, pt
    y: float
    scale: float  # drawn width, pt
    path: Tuple[str, ...]  # XObject names from the page down to the image (for lookup)
    height_pt: float = 0.0  # drawn height, pt


def open_pdf(path) -> pypdf.PdfReader:
    return pypdf.PdfReader(str(Path(path)))


def _page(doc: pypdf.PdfReader, page_number: int):
    if page_number < 1 or page_number > len(doc.pages):
        raise IndexError(f"page {page_number} out of range 1..{len(doc.pages)}")
    return doc.pages[page_number - 1]


def mul(m: Matrix, n: Matrix) -> Matrix:
    """Matrix product m × n in PDF row-vector convention."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def page_words(doc: pypdf.PdfReader, page_number: int) -> List[Word]:
    """Non-blank text runs on a page with their start position."""
    words: List[Word] = []

    def visitor(text, cm, tm, font_dict, font_size):
        t = text.strip()
        if not t:
            return
        x, y = tm[4], tm[5]
        a, b, c, d, e, f = cm
        words.append(Word(round(x * a + y * c + e, 2), round(x * b + y * d + f, 2), t))

    _page(doc, page_number).extract_text(visitor_text=visitor)
    return words


def _walk(doc, contents, resources, ctm: Matrix, page_number: int, path, out: list) -> None:
    if contents is None:
        return
    stream = ContentStream(contents, doc)
    xobjects = resources.get("/XObject") if resources else None
    xobjects = xobjects.get_object() if xobjects is not None else {}
    stack = []
    for operands, op in stream.operations:
        if op == b"q":
            stack.append(ctm)
        elif op == b"Q":
            ctm = stack.pop() if stack else IDENTITY
        elif op == b"cm":
            ctm = mul(tuple(float(v) for v in operands), ctm)
        elif op == b"Do":
            name = str(operands[0])
            if name not in xobjects:
                continue
            xobj = xobjects[name].get_object()
            subtype = xobj.get("/Subtype")
            if subtype == "/Image":
                a, b, c, d, e, f = ctm
                out.append(ImagePlacement(
                    page=page_number, name=name,
                    width=int(xobj["/Width"]), height=int(xobj["/Height"]),
                    x=round(e, 3), y=round(f, 3), scale=round((a * a + b * b) ** 0.5, 3),
                    path=tuple(path) + (name,),
                    height_pt=round((c * c + d * d) ** 0.5, 3),
                ))
            elif subtype == "/Form":
                matrix = tuple(float(v) for v in xobj.get("/Matrix", IDENTITY))
                form_res = xobj.get("/Resources")
                form_res = form_res.get_object() if form_res is not None else resources
                _walk(doc, xobj, form_res, mul(matrix, ctm), page_number,
                      tuple(path) + (name,), out)


def image_placements(doc: pypdf.PdfReader, page_number: int) -> List[ImagePlacement]:
    """Every image XObject drawn on the page, with its placement after all matrices."""
    page = _page(doc, page_number)
    resources = page.get("/Resources")
    resources = resources.get_object() if resources is not None else {}
    out: List[ImagePlacement] = []
    _walk(doc, page.get_contents(), resources, IDENTITY, page_number, (), out)
    return out


def _resolve_xobject(doc, placement: ImagePlacement):
    page = _page(doc, placement.page)
    res = page["/Resources"].get_object()
    obj = None
    for name in placement.path:
        obj = res["/XObject"].get_object()[name].get_object()
        if "/Resources" in obj:
            res = obj["/Resources"].get_object()
    return obj


def load_image(doc: pypdf.PdfReader, placement: ImagePlacement) -> Image.Image:
    """Decode an image placement to an RGB Pillow image (JPEG streams decoded by Pillow)."""
    xobj = _resolve_xobject(doc, placement)
    filters = xobj.get("/Filter")
    if filters == "/DCTDecode":
        img = Image.open(io.BytesIO(xobj._data))
    else:
        img = xobj.decode_as_image()
    return img.convert("RGB")
