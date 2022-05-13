import os
import unittest

from adsingestp.parsers import base


class TestBase(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_chunks(self):
        class MyParser(base.BaseXmlToDictParser):
            pass

        parser = MyParser()

        input = """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article SYSTEM "http://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd"><article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" dtd-version="1.2" article-type="research-article" xml:lang="en"><front>foo</front></article><article><title>hey1</title></article> <article ><title>hey2</title></article></footer>"""

        papers = list(parser.get_chunks(input, r"<article[^>]*>", r"</article[^>]*>"))

        expected = [
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article SYSTEM "http://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd"><article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" dtd-version="1.2" article-type="research-article" xml:lang="en"><front>foo</front></article>/footer>',
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article SYSTEM "http://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd"><article><title>hey1</title></article> /footer>',
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article SYSTEM "http://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd"><article ><title>hey2</title></article></footer>',
        ]

        assert papers == expected


if __name__ == "__main__":
    unittest.main()
