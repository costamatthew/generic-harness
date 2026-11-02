from calc import add, sub


def test_add():
    assert add(1, 2) == 3


def test_add_negative():
    assert add(-1, 1) == 0


def test_sub():
    assert sub(3, 2) == 1
