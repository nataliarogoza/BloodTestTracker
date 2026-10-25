""" Tests for starting the app from the command line (python -m bloodtracker) """
import socket

import pytest

from bloodtracker.__main__ import main, port_is_free


@pytest.fixture
def busy_port():
    """ A port that something is already listening on, like a second running app """
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0)) # Port 0: the system picks any free port
    listener.listen()
    yield listener.getsockname()[1]
    listener.close()


def test_free_port_is_detected():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
    assert port_is_free("127.0.0.1", free)


def test_busy_port_is_detected(busy_port):
    assert not port_is_free("127.0.0.1", busy_port)


def test_busy_port_gives_a_helpful_message_instead_of_starting(busy_port):
    with pytest.raises(SystemExit) as stopped:
        main(["--no-browser"], host="127.0.0.1", port=busy_port)
    message = str(stopped.value.code)
    assert f"Port {busy_port} is already in use" in message
    assert "Ctrl+Z" in message and f"BLOODTRACKER_PORT={busy_port + 1}" in message
