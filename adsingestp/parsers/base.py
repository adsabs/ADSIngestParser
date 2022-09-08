import html
import re
from datetime import datetime

import bs4

from adsingestp.ingest_exceptions import WrongFormatException


class IngestBase(object):

    TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

    # TODO will need to add boolean keys here if we want to keep falsy values - check these
    required_keys = [
        "createdTime",
        "parsedTime",
        "loadType",
        "loadFormat",
        "loadLocation",
        "recordOrigin",
    ]

    def _clean_empty(self, input_to_clean, keys_to_keep=required_keys):
        """

        :param input_to_clean: dictionary that contains empty key/value pairs to remove
        :param keys_to_keep: list of keys to keep, even if they"re empty
        :return: copy of input dict with all keys that contain empty values removed
        """

        if isinstance(input_to_clean, dict):
            return {
                k: v
                for k, v in ((k, self._clean_empty(v)) for k, v in input_to_clean.items())
                if v or (k in keys_to_keep)
            }

        if isinstance(input_to_clean, list):
            return [v for v in map(self._clean_empty, input_to_clean) if v]

        return input_to_clean

    def _clean_output(self, input):
        """
        Remove extra spaces and line breaks
        :param input: text to clean
        :return: cleaned text
        """
        input = input.replace("\n", " ")
        output = re.sub(r"\s+", r" ", input)
        output = output.strip()

        return output

    def _entity_convert(self, input):
        for k, v in input.items():
            if isinstance(v, str):
                v = html.unescape(v)
            elif isinstance(v, list):
                newv = []
                for i in v:
                    if isinstance(i, str):
                        i = html.unescape(i)
                    newv.append(i)
                v = newv
            else:
                pass
            input[k] = v

        return input

    def format(self, input_dict, format):
        """

        :param input_dict: parsed metadata dictionary to format into formal data model
        :param format: JATS, OtherXML, HTML, Text
        :return: serialized JSON that follows our internal data model
        """

        if format not in ["JATS", "OtherXML", "HTML", "Text"]:
            raise WrongFormatException

        output = {}

        output["recordData"] = {
            "createdTime": "",
            "parsedTime": datetime.utcnow().strftime(self.TIMESTAMP_FMT),
            "loadType": "fromURL" if format == "HTML" else "fromFile",
            "loadFormat": format,
            "loadLocation": "",
            "recordOrigin": "",
        }

        output["relatedTo"] = [
            {"relationship": i.get("relationship", ""), "relatedDocID": i.get("id", "")}
            for i in input_dict.get("relatedto", [])
        ]

        output["editorialHistory"] = {
            "receivedDates": input_dict.get("edhist_rec", ""),
            "revisedDates": input_dict.get("edhist_rev", ""),
            "acceptedDate": input_dict.get("edhist_acc", ""),
        }

        output["pubDate"] = {
            "electrDate": input_dict.get("pubdate_electronic", ""),
            "printDate": input_dict.get("pubdate_print", ""),
            "otherDate": [
                {"otherDateType": i.get("type", ""), "otherDateValue": i.get("date", "")}
                for i in input_dict.get("pubdate_other", [])
            ],
        }

        output["publication"] = {
            # "docType": "XXX",
            "pubName": input_dict.get("publication", ""),
            "confName": input_dict.get("conf_name", ""),
            "confLocation": input_dict.get("conf_location", ""),
            "confDates": input_dict.get("conf_date", ""),
            # "confEditors": ["XXX"],
            # "confPID": "XXX",
            "publisher": input_dict.get("publisher", ""),
            "issueNum": input_dict.get("issue", ""),
            "volumeNum": input_dict.get("volume", ""),
            "pubYear": input_dict["pubdate_print"][0:4]
            if "pubdate_print" in input_dict
            else (
                input_dict["pubdate_electronic"][0:4] if "pubdate_electronic" in input_dict else ""
            ),
            "bookSeries": {
                "seriesName": input_dict.get("series_title", ""),
                "seriesID": input_dict.get("series_id", ""),
                "seriesDescription": input_dict.get("series_id_description", ""),
            },
            "ISSN": [
                {"pubtype": pubtype, "issnString": issn}
                for (pubtype, issn) in input_dict.get("issn", "")
            ],
            # "isRefereed": True or False
        }

        output["persistentIDs"] = [
            {
                # 'Crossref': 'XXX',
                "ISBN": [
                    {"pubtype": i.get("type", ""), "isbnString": i.get("isbn_str", "")}
                    for i in input_dict.get("isbn", [])
                ],
                "DOI": input_dict.get("ids", {}).get("doi", ""),
                "preprint": {
                    "source": input_dict.get("ids", {}).get("preprint", {}).get("source", ""),
                    "identifier": input_dict.get("ids", {}).get("preprint", {}).get("id", ""),
                },
            }
        ]

        output["publisherIDs"] = [
            {"attribute": i.get("attribute", ""), "Identifier": i.get("Identifier", "")}
            for i in input_dict.get("ids", {}).get("pub-id", "")
        ]

        output["pagination"] = {
            "firstPage": input_dict.get("page_first", ""),
            "lastPage": input_dict.get("page_last", ""),
            "pageCount": input_dict.get("numpages", ""),
            "pageRange": input_dict.get("page_range", ""),
            "electronicID": input_dict.get("electronic_id", ""),
        }

        output["authors"] = [
            {
                "name": {
                    "surname": i.get("surname", ""),
                    "given-name": i.get("given", ""),
                    "middle-name": i.get("middle", ""),
                    "prefix": i.get("prefix", ""),
                    "suffix": i.get("suffix", ""),
                    "pubraw": i.get("nameraw", ""),
                    # "native-lang": "XXX",
                    "collab": i.get("collab", ""),
                },
                "affiliation": [
                    {
                        "affPubRaw": j,
                        "affPubID": i.get("xaff")[idx] if i.get("xaff") else "",
                        # "affPubIDType": "XXX" # TODO ask MT
                    }
                    for idx, j in enumerate(i.get("aff", []))
                ],
                "attrib": {
                    "collab": True if i.get("collab", "") else False,
                    # "deceased": True or False, # TODO need an example
                    # "coauthor": True or False, # TODO need an example
                    "email": i.get("email", ""),
                    # "funding": "XXX", # TODO need an example
                    "orcid": i.get("orcid", ""),
                },
            }
            for i in input_dict.get("authors", [])
        ]

        output["otherContributor"] = [
            {
                "role": i.get("role", ""),
                "contrib": {
                    "name": {
                        "surname": i.get("surname", ""),
                        "given-name": i.get("given", ""),
                        "middle-name": i.get("middle", ""),
                        "prefix": i.get("prefix", ""),
                        "suffix": i.get("suffix", ""),
                        "pubraw": i.get("nameraw", ""),
                        # "native-lang": "XXX",
                        "collab": i.get("collab", ""),
                    },
                    "affiliation": [
                        {
                            "affPubRaw": j,
                            "affPubID": i.get["xaff"][idx] if i.get("xaff") else ""
                            # "affPubIDType": "XXX"
                        }
                        for idx, j in enumerate(i.get("aff", []))
                    ],
                    "attrib": {
                        "collab": True if i.get("collab", "") else False,
                        # "deceased": True or False,
                        # "coauthor": True or False,
                        "email": i.get("email", ""),
                        # "funding": "XXX",
                        "orcid": i.get("orcid", ""),
                    },
                },
            }
            for i in input_dict.get("contributors", [])
        ]

        output["title"] = {
            "textEnglish": input_dict.get("title", ""),
            "textNative": input_dict.get("title_native", ""),
            "langNative": input_dict.get("lang_native", ""),
        }

        output["subtitle"] = input_dict.get("subtitle", "")

        output["abstract"] = {
            "textEnglish": input_dict.get(
                "abstract", ""
            ),  # TODO need to tweak for case of foreign language abstract
            # "textNative": "XXX", # TODO
            # "langNative": "XXX" # TODO
        }

        output["comments"] = [
            {"commentOrigin": i.get("origin", ""), "commentText": i.get("text", "")}
            for i in input_dict.get("comments", [])
        ]

        # output["fulltext"] = {
        #     "language": "XXX",
        #     "body": "XXX"
        # } # TODO this is from fulltext

        # output["acknowledgements"] = "XXX" # TODO this is from fulltext

        if input_dict.get("references", None):
            if type(input_dict.get("references")) == list:
                input_refs = input_dict.get("references")
            elif type(input_dict.get("references")) == str:
                input_refs = list(input_dict.get("references"))
            else:
                # TODO add error handling here
                input_refs = ""
            output["references"] = input_refs

        # output["backmatter"] = [
        #     {
        #         "backType": "XXX",
        #         "language": "XXX",
        #         "body": "XXX"
        #     }
        # ] # TODO need an example

        # output["astronomicalObjects"] = [
        #     "XXX"
        # ] # TODO need an example

        # output["esources"] = [
        #     {
        #         "source": "XXX",
        #         "location": "XXX"
        #     }
        # ] # TODO need an example

        # output["dataLinks"] = [
        #     {
        #         "title": "XXX",
        #         "identifier": "XXX",
        #         "location": "XXX",
        #         "dataType": "XXX",
        #         "comment": "XXX"
        #     }
        # ] # TODO need an example

        output["doctype"] = input_dict.get("doctype", "")

        output["keywords"] = [
            {
                "keyString": i.get("string", ""),
                "keySystem": i.get("system", ""),
                # "keyIdent": {
                #     "system": "XXX",
                #     "keyID": "XXX"
                # }
            }
            for i in input_dict.get("keywords", [])
        ]

        output["copyright"] = {
            "status": True if "copyright" in input_dict else False,  # TODO ask MT about this
            "statement": input_dict.get("copyright", ""),
        }

        output["openAccess"] = {
            "open": input_dict.get("openAccess", {}).get("open", False)
            if input_dict.get("openAccess")
            else False,
            # "license": "XXX",
            # "licenseURL": "XXX",
            # "preprint": "XXX",
            # "startDate": "XXX",
            # "endDate": "XXX",
            # "embargoLength": "XXX"
        }  # TODO need an example

        # output["pubnote"] = "XXX" # TODO need an example
        #
        # output["funding"] = "XXX" # TODO need an example
        #
        # output["version"] = "XXX" # TODO need an example

        output_clean = self._clean_empty(output)

        return output_clean


class BaseBeautifulSoupParser(IngestBase):
    """
    An XML parser which uses BeautifulSoup to create a dictionary
    out of the input XML stream.
    """

    def bsstrtodict(self, input_xml, parser="lxml-xml"):
        """
        Returns a BeautifulSoup tree given an XML text
        :param input_xml: XML text blob
        :param parser: e.g. 'html.parser', 'html5lib', 'lxml-xml' (default)
        :return: BeautifulSoup object/tree
        """

        return bs4.BeautifulSoup(input_xml, parser)
