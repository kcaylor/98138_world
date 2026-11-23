"""OAuth 1.0 HMAC-SHA1 signing (011 T023; RFC 5849; research R2).

Expected strings for the RFC examples are copied from the RFC 5849 text (§1.2, §3.4.1.1,
§3.4.1.3.2). The BrickLink vector uses made-up credentials and is frozen.
"""

from urllib.parse import parse_qsl

import pytest

from lego_image_processor.prices.credentials import Credentials
from lego_image_processor.prices.oauth1 import (authorization_header, base_string, base_string_uri,
                                                hmac_sha1_signature, normalize_parameters,
                                                oauth_parameters, percent_encode, signed_parameters)


# --- §3.6 percent encoding ------------------------------------------------------------------------

@pytest.mark.parametrize("raw, encoded", [
    ("abcXYZ019-._~", "abcXYZ019-._~"),          # unreserved characters stay
    (" ", "%20"),                                  # never "+"
    ("+", "%2B"), ("/", "%2F"), ("=", "%3D"), ("&", "%26"), ("%", "%25"), ("*", "%2A"),
    ("!", "%21"), ("'", "%27"), ("(", "%28"), (")", "%29"), (":", "%3A"), ("@", "%40"),
    ("é", "%C3%A9"),                                # UTF-8, uppercase hex
    ("%3D", "%253D"),
])
def test_percent_encode(raw, encoded):
    assert percent_encode(raw) == encoded


# --- §3.4.1 base string, on the RFC's own example ---------------------------------------------------

RFC_URL = "http://example.com/request?b5=%3D%253D&a3=a&c%40=&a2=r%20b"
RFC_BODY = "c2&a3=2+q"
RFC_OAUTH = [("oauth_consumer_key", "9djdj82h48djs9d2"), ("oauth_token", "kkk9d7dh3k39sjv7"),
             ("oauth_signature_method", "HMAC-SHA1"), ("oauth_timestamp", "137131201"),
             ("oauth_nonce", "7d8f3e4a")]
RFC_NORMALIZED = ("a2=r%20b&a3=2%20q&a3=a&b5=%3D%253D&c%40=&c2=&oauth_consumer_key=9djdj82h48djs9d2"
                  "&oauth_nonce=7d8f3e4a&oauth_signature_method=HMAC-SHA1"
                  "&oauth_timestamp=137131201&oauth_token=kkk9d7dh3k39sjv7")
RFC_BASE = ("POST&http%3A%2F%2Fexample.com%2Frequest&a2%3Dr%2520b%26a3%3D2%2520q"
            "%26a3%3Da%26b5%3D%253D%25253D%26c%2540%3D%26c2%3D%26oauth_consumer_"
            "key%3D9djdj82h48djs9d2%26oauth_nonce%3D7d8f3e4a%26oauth_signature_m"
            "ethod%3DHMAC-SHA1%26oauth_timestamp%3D137131201%26oauth_token%3Dkkk"
            "9d7dh3k39sjv7")


def _rfc_params():
    query = RFC_URL.split("?", 1)[1]
    return (parse_qsl(query, keep_blank_values=True) + parse_qsl(RFC_BODY, keep_blank_values=True)
            + RFC_OAUTH)


def test_parameter_normalization_rfc_example():
    assert normalize_parameters(_rfc_params()) == RFC_NORMALIZED


def test_base_string_rfc_example_with_query_in_url():
    body = parse_qsl(RFC_BODY, keep_blank_values=True)
    assert base_string("post", RFC_URL, body + RFC_OAUTH) == RFC_BASE


def test_base_string_rfc_example_with_query_as_parameters():
    assert base_string("POST", "http://example.com/request", _rfc_params()) == RFC_BASE


def test_oauth_signature_is_never_in_the_base_string():
    with_sig = RFC_OAUTH + [("oauth_signature", "bYT5CMsGcbgUdFHObYMEfcx6bsw=")]
    body = parse_qsl(RFC_BODY, keep_blank_values=True)
    assert base_string("POST", RFC_URL, body + with_sig) == RFC_BASE


@pytest.mark.parametrize("url, expected", [
    ("HTTP://EXAMPLE.COM:80/r%20v/X?id=123", "http://example.com/r%20v/X"),   # §3.4.1.2 example
    ("https://www.example.net:8080/?q=1", "https://www.example.net:8080/"),   # §3.4.1.2 example
    ("https://api.example.com:443/a", "https://api.example.com/a"),
    ("https://api.example.com", "https://api.example.com/"),
])
def test_base_string_uri(url, expected):
    assert base_string_uri(url) == expected


# --- §1.2 worked example: HMAC-SHA1 signature -------------------------------------------------------

PHOTOS = Credentials(consumer_key="dpf43f3p2l4k3l03", consumer_secret="kd94hf93k423kf44",
                     token_value="nnch734d00sl2jdk", token_secret="pfkkdhi9sl3r4s00")


def test_rfc_section_1_2_signature():
    params = [("file", "vacation.jpg"), ("size", "original"),
              ("oauth_consumer_key", "dpf43f3p2l4k3l03"), ("oauth_token", "nnch734d00sl2jdk"),
              ("oauth_signature_method", "HMAC-SHA1"), ("oauth_timestamp", "137131202"),
              ("oauth_nonce", "chapoH")]
    base = base_string("GET", "http://photos.example.net/photos", params)
    assert hmac_sha1_signature(base, "kd94hf93k423kf44", "pfkkdhi9sl3r4s00") == "MdpQcU8iPSUjWoN/UDMsK2sui9I="


def test_rfc_section_1_2_authorization_header():
    header = authorization_header("GET", "http://photos.example.net/photos",
                                  [("file", "vacation.jpg"), ("size", "original")], PHOTOS,
                                  nonce="chapoH", timestamp=137131202, realm="Photos", version=None)
    assert header == ('OAuth realm="Photos", oauth_consumer_key="dpf43f3p2l4k3l03", '
                      'oauth_token="nnch734d00sl2jdk", oauth_signature_method="HMAC-SHA1", '
                      'oauth_timestamp="137131202", oauth_nonce="chapoH", '
                      'oauth_signature="MdpQcU8iPSUjWoN%2FUDMsK2sui9I%3D"')


# --- BrickLink price-guide request: frozen vector ------------------------------------------------------

FAKE = Credentials(consumer_key="CK-test-0001", consumer_secret="CS-test-0002",
                   token_value="TV-test-0003", token_secret="TS-test-0004")
BL_URL = "https://api.bricklink.com/api/store/v1/items/PART/98138/price"
BL_QUERY = [("color_id", "63"), ("guide_type", "sold"), ("new_or_used", "N"),
            ("currency_code", "USD"), ("vat", "N")]


def test_bricklink_vector_is_frozen():
    header = authorization_header("GET", BL_URL, BL_QUERY, FAKE, nonce="0123456789abcdef",
                                  timestamp=1796148130)
    assert header == FROZEN_BL_HEADER


def test_authorization_header_field_order_and_quoting():
    header = authorization_header("GET", BL_URL, BL_QUERY, FAKE, nonce="n o/n", timestamp=1)
    assert header.startswith('OAuth realm="", oauth_consumer_key="CK-test-0001", '
                             'oauth_token="TV-test-0003", oauth_signature_method="HMAC-SHA1", '
                             'oauth_timestamp="1", oauth_nonce="n%20o%2Fn", oauth_version="1.0", '
                             'oauth_signature="')
    assert header.endswith('"')
    names = [part.split("=", 1)[0] for part in header[len("OAuth "):].split(", ")]
    assert names == ["realm", "oauth_consumer_key", "oauth_token", "oauth_signature_method",
                     "oauth_timestamp", "oauth_nonce", "oauth_version", "oauth_signature"]


def test_secrets_never_appear_in_the_header():
    header = authorization_header("GET", BL_URL, BL_QUERY, FAKE, nonce="abc", timestamp=1)
    assert "CS-test-0002" not in header and "TS-test-0004" not in header


def test_signature_depends_on_every_input():
    base = dict(nonce="abc", timestamp=100)
    ref = authorization_header("GET", BL_URL, BL_QUERY, FAKE, **base)
    other_query = BL_QUERY[:1] + [("guide_type", "stock")] + BL_QUERY[2:]
    assert authorization_header("GET", BL_URL, other_query, FAKE, **base) != ref
    assert authorization_header("GET", BL_URL, BL_QUERY, FAKE, nonce="abd", timestamp=100) != ref
    assert authorization_header("GET", BL_URL, BL_QUERY, FAKE, nonce="abc", timestamp=101) != ref


def test_oauth_parameters_order_and_signed_parameters():
    p = oauth_parameters(FAKE, nonce="abc", timestamp=7)
    assert [k for k, _ in p] == ["oauth_consumer_key", "oauth_token", "oauth_signature_method",
                                 "oauth_timestamp", "oauth_nonce", "oauth_version"]
    signed = signed_parameters("GET", BL_URL, BL_QUERY, FAKE, nonce="abc", timestamp=7)
    assert [k for k, _ in signed][-1] == "oauth_signature"


def test_timestamp_must_be_an_integer():
    with pytest.raises(TypeError):
        authorization_header("GET", BL_URL, BL_QUERY, FAKE, nonce="abc", timestamp=1.5)


# Computed once with this implementation after the RFC vectors above passed, then frozen.
FROZEN_BL_HEADER = ('OAuth realm="", oauth_consumer_key="CK-test-0001", oauth_token="TV-test-0003", '
                    'oauth_signature_method="HMAC-SHA1", oauth_timestamp="1796148130", '
                    'oauth_nonce="0123456789abcdef", oauth_version="1.0", '
                    'oauth_signature="DaJD1tZh4hXOrTFYDiWmvHVzGfQ%3D"')
