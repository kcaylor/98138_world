"""Marketplace exports (005 T022, T023): BrickLink wanted-list XML and Rebrickable CSV."""

import xml.etree.ElementTree as ET

import pytest

from lego_image_processor.parts import (OwnedInputs, UnverifiedLotsError, build_parts_list,
                                        parse_owned_text, to_bricklink_xml, to_rebrickable_csv)

from .layouts import SMALL, UNCITED, make_grid


def _pl(specs=SMALL, kits=0):
    return build_parts_list(make_grid(specs), owned=OwnedInputs(kits=kits))


def test_bricklink_xml_format():
    xml = to_bricklink_xml(_pl())
    assert not xml.startswith("<?xml") and xml.startswith("<INVENTORY>\n") and xml.endswith("</INVENTORY>\n")
    assert "\r" not in xml and "CONDITION" not in xml
    root = ET.fromstring(xml)
    items = root.findall("ITEM")
    assert [[c.tag for c in i] for i in items] == [["ITEMTYPE", "ITEMID", "COLOR", "MINQTY"]] * 4
    got = [(i.findtext("ITEMTYPE"), i.findtext("ITEMID"), int(i.findtext("COLOR")), int(i.findtext("MINQTY")))
           for i in items]
    assert got == [("P", "4073", 1, 30), ("P", "4073", 2, 12), ("P", "98138", 5, 7), ("P", "98138", 156, 20)]
    assert "  <ITEM>\n    <ITEMTYPE>P</ITEMTYPE>\n" in xml


@pytest.mark.parametrize("cond,code", [("used", "U"), ("new", "N")])
def test_bricklink_condition(cond, code):
    items = ET.fromstring(to_bricklink_xml(_pl(), condition=cond)).findall("ITEM")
    assert all(i.findtext("CONDITION") == code and [c.tag for c in i][-1] == "CONDITION" for i in items)
    with pytest.raises(ValueError):
        to_bricklink_xml(_pl(), condition="mint")


def test_deterministic_bytes():
    assert to_bricklink_xml(_pl()) == to_bricklink_xml(_pl())
    assert to_rebrickable_csv(_pl()) == to_rebrickable_csv(_pl())


def test_nothing_to_buy_returns_none():
    pl = _pl([("plate", "lego_white", "White", "1", 30)], kits=1)
    assert to_bricklink_xml(pl) is None and to_rebrickable_csv(pl) is None


def test_unverified_lots_block_unless_partial():
    pl = _pl(UNCITED)
    with pytest.raises(UnverifiedLotsError) as exc:
        to_bricklink_xml(pl)
    assert exc.value.exit_code == 6 and "lego_medium_blue" in str(exc.value)
    with pytest.raises(UnverifiedLotsError):
        to_rebrickable_csv(pl)
    xml = to_bricklink_xml(pl, allow_partial=True)
    assert len(ET.fromstring(xml).findall("ITEM")) == 4
    assert to_rebrickable_csv(pl, allow_partial=True).count("\n") == 5


def test_only_lots_with_something_to_buy():
    pl = _pl([("plate", "lego_white", "White", "1", 3100), ("tile", "lego_medium_azur", "Medium Azur", "322", 20)],
             kits=1)
    items = ET.fromstring(to_bricklink_xml(pl)).findall("ITEM")
    assert [(i.findtext("ITEMID"), i.findtext("MINQTY")) for i in items] == [("4073", "36")]


def test_rebrickable_csv_format_and_round_trip():
    csv_text = to_rebrickable_csv(_pl())
    assert csv_text == "Part,Color,Quantity\n6141,15,30\n6141,19,12\n98138,4,7\n98138,322,20\n"
    assert not csv_text.startswith("﻿")
    quantities, ignored = parse_owned_text(csv_text)
    assert ignored == 0
    assert quantities == {("6141", "lego_white"): 30, ("6141", "lego_brick_yellow"): 12,
                          ("98138", "lego_bright_red"): 7, ("98138", "lego_medium_azur"): 20}


def test_xml_round_trip_quantities():
    pl = _pl()
    items = ET.fromstring(to_bricklink_xml(pl)).findall("ITEM")
    assert sum(int(i.findtext("MINQTY")) for i in items) == pl.totals()["to_buy"]
