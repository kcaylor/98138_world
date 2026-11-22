"""Owned / missing parts files (005 T027, Q1): Rebrickable import CSV shapes and errors."""

import hashlib
from fractions import Fraction

import pytest

from lego_image_processor.parts import OwnedFileError, OwnedInputs, parse_owned_csv, parse_percent
from lego_image_processor.parts.owned import percent_text

WHITE_PLATE = ("6141", "lego_white")
AZUR_TILE = ("98138", "lego_medium_azur")


def test_part_color_quantity(write_csv):
    p = write_csv("a.csv", "Part,Color,Quantity\n6141,15,40\n98138,322,12\n")
    f = parse_owned_csv(p)
    assert f.quantities == {WHITE_PLATE: 40, AZUR_TILE: 12}
    assert f.ignored_rows == 0
    assert f.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()


def test_element_quantity(write_csv):
    f = parse_owned_csv(write_csv("e.csv", "Element,Quantity\n614101,40\n6322819,12\n"))
    assert f.quantities == {WHITE_PLATE: 40, AZUR_TILE: 12}
    # any element listed for a cited row matches it (here a second White plate element)
    assert parse_owned_csv(write_csv("e2.csv", "Element,Quantity\n6601919,3\n")).quantities == {WHITE_PLATE: 3}


def test_headers_case_order_extra_columns_bom_crlf_blank_and_duplicates(write_csv):
    text = "quantity,Is Spare,color,PART\r\n10,False,15,6141\r\n\r\n5,True,15,6141\r\n,,,\r\n"
    f = parse_owned_csv(write_csv("b.csv", "", raw=b"\xef\xbb\xbf" + text.encode()))
    assert f.quantities == {WHITE_PLATE: 15}


def test_non_map_parts_ignored_and_counted(write_csv):
    f = parse_owned_csv(write_csv("set.csv", "Part,Color,Quantity\n3001,15,4\n6141,15,1\n2412b,0,2\n"))
    assert f.quantities == {WHITE_PLATE: 1} and f.ignored_rows == 2


def test_header_only_is_empty(write_csv):
    assert parse_owned_csv(write_csv("h.csv", "Part,Color,Quantity\n")).quantities == {}


@pytest.mark.parametrize("text,line,match", [
    ("", None, "empty file"),
    ("Item,Qty\n6141,1\n", 1, "not recognised"),
    ("Part,Color,Quantity\n6141,15,-1\n", 2, "whole number"),
    ("Part,Color,Quantity\n6141,15,2.5\n", 2, "whole number"),
    ("Part,Color,Quantity\n6141,15,\n", 2, "whole number"),
    ("Part,Color,Quantity\n6141,15,1\n6141,41,1\n", 3, "no cited row"),   # Trans-Light Blue plate
    ("Part,Color,Quantity\n4073,15,1\n", 2, "Rebrickable part numbers"),  # BrickLink numbering
    ("Part,Color,Quantity\n6141,Tan,1\n", 2, "color"),
    ("Element,Quantity\n999999,1\n", 2, "element"),
])
def test_errors_carry_file_and_line(write_csv, text, line, match):
    p = write_csv("bad.csv", text)
    with pytest.raises(OwnedFileError, match=match) as exc:
        parse_owned_csv(p)
    assert exc.value.line == line
    assert str(p) in str(exc.value)


def test_unreadable_file(tmp_path):
    with pytest.raises(OwnedFileError, match="cannot read"):
        parse_owned_csv(tmp_path / "absent.csv")


def test_owned_inputs_validation():
    with pytest.raises(ValueError):
        OwnedInputs(kits=-1)
    with pytest.raises(ValueError):
        OwnedInputs(spares_percent=Fraction(101))
    assert OwnedInputs(kits=2).kits == 2


def test_percent_parsing_is_exact():
    assert parse_percent("2") == Fraction(2)
    assert parse_percent("2.5") == Fraction(5, 2)
    assert parse_percent("0.1") == Fraction(1, 10)  # not 0.1000000000000000055...
    for bad in ("-1", "100.5", "abc"):
        with pytest.raises(ValueError):
            parse_percent(bad)
    assert percent_text(Fraction(5, 2)) == "2.5" and percent_text(Fraction(0)) == "0"
