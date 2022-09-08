import datetime
import json
import os
import unittest

from adsingestschema import ads_schema_validator

from adsingestp.parsers import crossref

TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TestCrossref(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_crossref(self):

        filenames = [
            "crossref_10.1002_1521-3994",
            "crossref_10.3847_2041-8213",
            "crossref_conf_10.1049-cp.2010.1342",
            "crossref_conf_10.1109-MWSYM.2013.6697399",
            "crossref_book_10.1017-CBO9780511709265",
            "crossref_book_10.1007-978-1-4614-3520-4",
            "crossref_10.1103_PhysRevD_64-117303",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = crossref.CrossrefParser()

            with open(test_infile, "rb") as fp:
                input_data = fp.read()

            with open(test_outfile, "rb") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)

            parsed = parser.parse(input_data)

            # make sure this is valid schema
            try:
                ads_schema_validator().validate(parsed)
            except Exception:
                self.fail("Schema validation failed")

            # this field won't match the test data, so check and then discard
            time_difference = (
                datetime.datetime.strptime(parsed["recordData"]["parsedTime"], TIMESTAMP_FMT)
                - datetime.datetime.utcnow()
            )
            self.assertTrue(abs(time_difference) < datetime.timedelta(seconds=10))
            parsed["recordData"]["parsedTime"] = ""

            self.assertEqual(parsed, output_data)
