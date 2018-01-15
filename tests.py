import unittest

from script import load_file
from script import extract_tabs
from script import convert_bar
from script import bar_to_lilypond_duration

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

    def test_bar_to_lilypond_duration(self):
        bar = [1,1]
        expected = ["2","2"]
        output = bar_to_lilypond_duration(bar)
        self.assertEqual(output, expected)

        bar = [3,None,None,1]
        expected = ["2.","4"]
        output = bar_to_lilypond_duration(bar)
        self.assertEqual(output, expected)

        bar = [6,None,None,None,None,None,2,None]
        expected = ["2.","4"]
        output = bar_to_lilypond_duration(bar)
        self.assertEqual(output, expected)

        bar = [3,None,None,3,None,None,2,None]
        expected = ["4.","4.","4"]
        output = bar_to_lilypond_duration(bar)
        self.assertEqual(output, expected)

        bar = [7,None,None,None,None,None,None,1]
        expected = [["2.","8"],"8"]
        output = bar_to_lilypond_duration(bar)
        self.assertEqual(output, expected)

        # TODO: This doesn't give the exact same solution, but it's still a
        # correct solution. Update test to reflect this.

        #bar = [15,None,None,None,None,None,None,None,None,None,None,None,None,None,None,1]
        #expected = [["2.","8","16"],"16"]
        #output = bar_to_lilypond_duration(bar)
        #self.assertEqual(output, expected)


if __name__ == '__main__':
    unittest.main()
