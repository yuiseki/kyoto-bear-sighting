import datetime as dt

import kyoto as k
import pytest

HEAD = ",".join(k.COLUMNS)
ROW = "2009100000,2009,宮津市小田宿野,路上,135.251591 ,35.565690 ,2009-04-08,1 ,,,目撃した,,周知,26205,262056,宮津市"


def csv_of(*lines, head=HEAD):
    return ("﻿" + head + "\n" + "\n".join(lines) + "\n").encode()


def test_parse_strips_the_padding():
    r = k.parse_csv(csv_of(ROW))[0]
    assert r["経度"] == "135.251591" and r["成獣(匹)"] == "1" and r["_date"] == dt.date(2009, 4, 8)
    assert r["_lat"] == 35.56569


def test_fiscal_year():
    assert (
        k.fiscal_year(dt.date(2010, 3, 31)) == 2009 and k.fiscal_year(dt.date(2010, 4, 1)) == 2010
    )


@pytest.mark.parametrize(
    "bad",
    [
        ROW.replace("2009-04-08", "2009/04/08"),
        ROW.replace("135.251591", "35.251591").replace("35.565690", "135.565690"),
        ROW.replace(",2009,", ",2010,"),
    ],
)
def test_refuses_what_it_does_not_know(bad):
    with pytest.raises(ValueError):
        k.parse_csv(csv_of(bad))


def test_refuses_a_changed_header():
    with pytest.raises(ValueError):
        k.parse_csv(csv_of(ROW, head=HEAD + ",x"))
