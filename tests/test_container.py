from container import Container
import unittest


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age


class TestContainer(unittest.TestCase):
    def test_container(self):
        p = Person("james", 11)
        assert p.name == "james"
        SYSTEM_DATA = (
            ("name", "jack", None),
            ("age", 29, None),
            ("person", Person, ("name", "age")),
        )

        c = Container(SYSTEM_DATA)

        self.assertEqual(c.name, "jack")
        self.assertEqual(c.person.name, "jack")
