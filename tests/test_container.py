from container import Container


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age


def test_container():
    p = Person("james", 11)
    assert p.name == "james"
    SYSTEM_DATA = (
        ("name", "jack", None),
        ("age", 29, None),
        ("person", Person, ("name", "age")),
    )

    c = Container(SYSTEM_DATA)

    assert c.name == "jack"
    assert c.person.name == "jack"
