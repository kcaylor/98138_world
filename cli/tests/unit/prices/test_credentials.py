"""BrickLink credentials from the environment (011 T027; FR-006; research R8)."""

import pickle

import pytest

from lego_image_processor.prices.credentials import (ENV_VARS, Credentials, MissingCredentialsError,
                                                     credentials_from_env)

ENV = {"BRICKLINK_CONSUMER_KEY": "CK-leakcheck-7f3a", "BRICKLINK_CONSUMER_SECRET": "CS-leakcheck-91be",
       "BRICKLINK_TOKEN_VALUE": "TV-leakcheck-2c44", "BRICKLINK_TOKEN_SECRET": "TS-leakcheck-d0e8"}


def test_variable_names():
    assert ENV_VARS == ("BRICKLINK_CONSUMER_KEY", "BRICKLINK_CONSUMER_SECRET",
                        "BRICKLINK_TOKEN_VALUE", "BRICKLINK_TOKEN_SECRET")


def test_all_four_set():
    c = credentials_from_env(ENV)
    assert (c.consumer_key, c.consumer_secret, c.token_value, c.token_secret) == tuple(ENV.values())


@pytest.mark.parametrize("missing", list(ENV))
@pytest.mark.parametrize("how", ["absent", "empty", "blank"])
def test_any_missing_or_empty(missing, how):
    env = dict(ENV)
    if how == "absent":
        del env[missing]
    else:
        env[missing] = "" if how == "empty" else "   "
    with pytest.raises(MissingCredentialsError) as info:
        credentials_from_env(env)
    assert info.value.names == (missing,)
    assert str(info.value) == f"missing environment variable(s): {missing}"
    for value in ENV.values():
        assert value not in str(info.value) and value not in repr(info.value)


def test_several_missing_are_listed_in_order():
    with pytest.raises(MissingCredentialsError) as info:
        credentials_from_env({"BRICKLINK_TOKEN_VALUE": "x"})
    assert info.value.names == ("BRICKLINK_CONSUMER_KEY", "BRICKLINK_CONSUMER_SECRET",
                                "BRICKLINK_TOKEN_SECRET")
    assert str(info.value) == ("missing environment variable(s): BRICKLINK_CONSUMER_KEY, "
                               "BRICKLINK_CONSUMER_SECRET, BRICKLINK_TOKEN_SECRET")


def test_repr_and_str_are_redacted():
    c = credentials_from_env(ENV)
    assert repr(c) == str(c) == "Credentials(<redacted>)"
    assert f"{c}" == "Credentials(<redacted>)" and f"{c!r}" == "Credentials(<redacted>)"
    for value in ENV.values():
        assert value not in repr(c) and value not in str([c]) and value not in str({"c": c})


def test_credentials_cannot_be_pickled():
    with pytest.raises(TypeError):
        pickle.dumps(credentials_from_env(ENV))


def test_empty_values_rejected_directly():
    with pytest.raises(ValueError):
        Credentials(consumer_key="", consumer_secret="a", token_value="b", token_secret="c")
