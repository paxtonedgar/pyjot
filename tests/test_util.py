import threading

from jot.util import (
    add_caller_tags,
    hex_decode_bytes,
    hex_encode_bytes,
)


def test_add_caller_tags():
    tags = {}

    def inner(tags):
        return add_caller_tags(tags)

    inner(tags)
    assert tags["file"] == __file__
    assert tags["line"] == 14
    assert tags["function"] == "inner"


def test_add_caller_tags_without_file():
    # exec'd code (notebooks, python -c) has no __file__ in its globals
    tags = {}
    code = "def inner():\n    add_caller_tags(tags)\ninner()"
    globals = {"add_caller_tags": add_caller_tags, "tags": tags}
    thread = threading.Thread(target=exec, args=(code, globals), daemon=True)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert tags["file"] is None
    assert tags["line"] == 2
    assert tags["function"] == "inner"


def test_from_hex():
    actual = hex_decode_bytes("be71ef7f12c881e0fa9c01396a4a47db")
    expected = b"\xbeq\xef\x7f\x12\xc8\x81\xe0\xfa\x9c\x019jJG\xdb"
    assert actual == expected


def test_from_hex_none():
    actual = hex_decode_bytes(None)
    assert actual is None


def test_to_hex():
    actual = hex_encode_bytes(b"\xbeq\xef\x7f\x12\xc8\x81\xe0\xfa\x9c\x019jJG\xdb")
    expected = "be71ef7f12c881e0fa9c01396a4a47db"
    assert actual == expected


def test_to_hex_none():
    actual = hex_encode_bytes(None)
    assert actual is None
