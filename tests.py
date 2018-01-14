import unittest

from script import load_file
from script import extract_tabs
from script import convert_bar

class TestScript(unittest.TestCase):

    def test_extract_tabs(self):
        data = load_file("data/perfect.tab")
        tabs = extract_tabs(data)

        self.assertEqual(len(tabs), 18*6)

    def test_convert_bar(self):
        bar = "|-|"
        expected = [-1]
        output = convert_bar(bar)
        self.assertEqual(output, expected)

        bar = "|-5-|"
        expected = [-1,5,-1]
        output = convert_bar(bar)
        self.assertEqual(output, expected)

        bar = "|-12-9-|"
        expected = [-1,12,-1,-1,9,-1]
        output = convert_bar(bar)
        self.assertEqual(output, expected)

if __name__ == '__main__':
    unittest.main()
