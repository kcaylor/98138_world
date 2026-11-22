"""The suite-wide offline guard in tests/conftest.py is active (SC-007)."""

import socket

import pytest


def test_network_connect_is_blocked():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="network access is blocked"):
            s.connect(("192.0.2.1", 80))  # TEST-NET-1, never routed
    finally:
        s.close()


def test_create_connection_is_blocked():
    with pytest.raises(RuntimeError, match="network access is blocked"):
        socket.create_connection(("192.0.2.1", 80), timeout=0.1)
