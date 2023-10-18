"""
Unittest for SPIE parser
"""

import datetime
import json
import os
import unittest

from adsingestschema import ads_schema_validator

from adsingestp.parsers import spie

TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TestSPIE(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_spie(self):
        filenames = [
            "spie_jmnmm_1.JMM.21.4.041407",
            "spie_spie_12.2663387",
            "spie_spie_12.2665113",
            "spie_opten_1.OE.62.4.048103",
            "spie_spie_12.2663472",
            "spie_spie_12.2665157",
            "spie_opten_1.OE.62.4.066101",
            "spie_spie_12.2663687",
            "spie_spie_12.2665696",
            "spie_spie_12.2663029",
            "spie_spie_12.2664418",
            "spie_spie_12.2690579",  # only has editors, no authors
            "spie_spie_12.2663066",
            "spie_spie_12.2664959",
            "spie_spie_12.2663263",
            "spie_spie_12.2665099",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = spie.SPIEParser()

            with open(test_infile, "rb") as fp:
                input_data = fp.read()

            parsed = parser.parse(input_data)

            with open(test_outfile, "rb") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)

            # make sure this is valid schema
            try:
                ads_schema_validator().validate(parsed)
            except Exception:
                self.fail("Schema validation failed")
                pass

            # this field won't match the test data, so check and then discard
            time_difference = (
                datetime.datetime.strptime(parsed["recordData"]["parsedTime"], TIMESTAMP_FMT)
                - datetime.datetime.utcnow()
            )
            self.assertTrue(abs(time_difference) < datetime.timedelta(seconds=10))
            parsed["recordData"]["parsedTime"] = ""

            self.assertEqual(parsed, output_data)
