import datetime
import json
import os
import unittest

from adsingestschema import ads_schema_validator

from adsingestp.parsers import datacite

# import logging
# proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "adsingestp"))
# logging.basicConfig(
#     format="%(levelname)s %(asctime)s %(message)s",
#     filename=os.path.join(proj_dir, "logs", "parser.log"),
#     level=logging.INFO,
#     force=True,
# )

TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


class TestDatacite(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_datacite(self):

        filenames = [
            "datacite_schema4.1_example-full",
            "datacite_schema3.1_example-full",
            "datacite_schema4.1_example-software",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = datacite.DataciteParser()

            with open(test_infile, "r") as fp:
                input_data = fp.read()

            with open(test_outfile, "r") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)

            parsed = list(parser.parse(input_data))[0]

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


if __name__ == "__main__":
    unittest.main()
