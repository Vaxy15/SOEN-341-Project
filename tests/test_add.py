# SOEN-341-Project\tests\test_add.py

import pytest
from src.add import add

def test_add_integers():
    assert add(2, 3) == 5

