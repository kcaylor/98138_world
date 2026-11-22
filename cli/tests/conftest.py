"""Suite-wide offline guard (SC-007, FR-022): no test may open a network connection.

Network sockets (IPv4/IPv6) raise on ``connect``/``connect_ex`` for the whole session. Local
AF_UNIX sockets are left alone.
"""

import socket

import pytest


class NetworkBlockedError(RuntimeError):
    """A test tried to open a network connection."""


_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_NETWORK_FAMILIES = {socket.AF_INET, socket.AF_INET6}


def _guard(original):
    def guarded(self, address, *args, **kwargs):
        if self.family in _NETWORK_FAMILIES:
            raise NetworkBlockedError(f"network access is blocked in tests (tried {address!r})")
        return original(self, address, *args, **kwargs)
    return guarded


@pytest.fixture(autouse=True, scope="session")
def _block_network():
    socket.socket.connect = _guard(_original_connect)
    socket.socket.connect_ex = _guard(_original_connect_ex)
    try:
        yield
    finally:
        socket.socket.connect = _original_connect
        socket.socket.connect_ex = _original_connect_ex
