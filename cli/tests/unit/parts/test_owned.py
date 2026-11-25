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


# --- the square tile 3070b (feature 016 T110; SC-001, FR-014) ------------------------------------
# A kit layout has no square tiles: its owned and missing CSVs are read for the kit's two map parts
# only, so 3070b rows and rows with 3070b's other catalog numbers are ignored and counted, as on
# main. A layout with square tiles (a non-kit template's margin) reads 3070b too.

SQUARE_NUMBERS = ("3070", "30039", "35403", "39727", "53836", "112412")
BLACK_SQUARE = ("3070b", "lego_black")
SQUARE_PARTS = ("6141", "98138", "3070b")


def test_square_numbers_are_part_numbers_of_3070b():
    from lego_image_processor.kit.part_numbers import load_part_numbers
    n = load_part_numbers().get("3070b")
    assert set(SQUARE_NUMBERS) == ({n.bricklink_item_no} | set(n.bricklink_alternates)
                                   | set(n.lego_design_ids)) - {"3070b"}


def test_kit_parts_ignore_square_tile_rows(write_csv):
    rows = "".join(f"{num},0,1\n" for num in ("3070b",) + SQUARE_NUMBERS)
    p = write_csv("kit.csv", "Part,Color,Quantity\n6141,15,2\n" + rows + "3001,15,4\n")
    for f in (parse_owned_csv(p), parse_owned_csv(p, parts=("6141", "98138"))):
        assert f.quantities == {WHITE_PLATE: 2}
        assert f.ignored_rows == 1 + len(SQUARE_NUMBERS) + 1


def test_kit_parts_reject_a_square_tile_element(write_csv):
    p = write_csv("e.csv", "Element,Quantity\n614101,4\n307026,6\n")  # 307026: Black square tile
    with pytest.raises(OwnedFileError, match="element '307026' is not listed") as exc:
        parse_owned_csv(p)
    assert exc.value.line == 3


def test_kit_parts_name_only_the_kit_parts_in_the_numbering_error(write_csv):
    with pytest.raises(OwnedFileError) as exc:
        parse_owned_csv(write_csv("b.csv", "Part,Color,Quantity\n4073,15,1\n"))
    assert str(exc.value).endswith("this file must use Rebrickable part numbers (6141, 98138)")


def test_square_tile_parts_count_3070b_rows(write_csv):
    p = write_csv("w.csv", "Part,Color,Quantity\n6141,15,2\n3070b,0,40\n3070b,0,2\n3001,15,4\n")
    f = parse_owned_csv(p, parts=SQUARE_PARTS)
    assert f.quantities == {WHITE_PLATE: 2, BLACK_SQUARE: 42} and f.ignored_rows == 1
    e = parse_owned_csv(write_csv("we.csv", "Element,Quantity\n307026,6\n"), parts=SQUARE_PARTS)
    assert e.quantities == {BLACK_SQUARE: 6}


@pytest.mark.parametrize("num", SQUARE_NUMBERS)
def test_square_tile_parts_reject_its_other_numbers(write_csv, num):
    with pytest.raises(OwnedFileError) as exc:
        parse_owned_csv(write_csv("o.csv", f"Part,Color,Quantity\n{num},0,1\n"), parts=SQUARE_PARTS)
    assert exc.value.line == 2
    assert (f"part {num} is another catalog's number for map part 3070b; this file must use "
            "Rebrickable part numbers (3070b, 6141, 98138)") in str(exc.value)


def test_square_tile_color_not_cited(write_csv):
    with pytest.raises(OwnedFileError, match=r"no cited row \(see: lego-image-processor kit part-colors --part 3070b\)"):
        parse_owned_csv(write_csv("c.csv", "Part,Color,Quantity\n3070b,9999,1\n"), parts=SQUARE_PARTS)
