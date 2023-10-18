import logging

from adsingestp import utils
from adsingestp.ingest_exceptions import (
    MissingAuthorsException,
    MissingTitleException,
    NoSchemaException,
    WrongSchemaException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)


class SPIEParser(BaseBeautifulSoupParser):
    spie_schema = ["http://www.w3.org/1999/xlink", "http://www.w3.org/1998/Math/MathML"]

    author_collaborations_params = {
        "keywords": ["group", "team", "collaboration"],
        "remove_the": False,
    }

    def __init__(self):
        self.base_metadata = {}
        self.input_header = None
        self.article_metadata = None
        self.journal_metadata = None

    def _get_date(self, d):
        """
        Extract and standarize date from input BeautifulSoup date object
        :param d: BeautifulSoup date object
        :return: formatted date string (yyyy-mm-dd)
        """
        if d.find("year"):
            pubdate = d.find("year").get_text()
        else:
            pubdate = "0000"

        if d.find("month"):
            month_raw = d.find("month").get_text()
            if month_raw.isdigit():
                month = month_raw
            else:
                month_name = month_raw[0:3].lower()
                month = utils.MONTH_TO_NUMBER[month_name]

            if int(month) < 10 and len(str(month)) < 2:
                month = "0" + str(int(month))
            else:
                month = str(month)
            pubdate = pubdate + "-" + month
        else:
            pubdate = pubdate + "-" + "00"

        if d.find("day"):
            day_raw = d.find("day").get_text()
            if day_raw.isdigit():
                day = day_raw
            else:
                day = "00"

            if int(day) < 10 and len(str(day)) < 2:
                day = "0" + str(int(day))
            else:
                day = str(day)
            pubdate = pubdate + "-" + day
        else:
            pubdate = pubdate + "-" + "00"

        return pubdate

    def _parse_journal(self):
        if self.journal_metadata.find("journal_title"):
            self.base_metadata["publication"] = self.journal_metadata.find(
                "journal_title"
            ).get_text()

        issns = []
        issn_list = self.journal_metadata.find_all("issn")

        for issn in issn_list:
            if issn.get("pub-type") == "ppub":
                issns.append(("print", issn.get_text()))

            if issn.get("pub-type") == "epub":
                issns.append(("electronic", issn.get_text()))

        self.base_metadata["issn"] = issns

    def _parse_pagination(self):
        if self.article_metadata.find("volume_number"):
            self.base_metadata["volume"] = self.article_metadata.find("volume_number").get_text()

        if self.article_metadata.find("fpage"):
            self.base_metadata["page_first"] = self.article_metadata.find("fpage").get_text()

        if self.article_metadata.find("end_page"):
            self.base_metadata["page_last"] = self.article_metadata.find("lpage").get_text()

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        article_ids = self.article_metadata.find_all("article-id")

        for id_item in article_ids:
            if id_item.get("pub-id-type", "") == "doi":
                self.base_metadata["ids"]["doi"] = id_item.get_text()
            if id_item.get("pub-id-type", "") == "publisher-id":
                self.base_metadata["electronic_id"] = id_item.get_text()

    def _parse_title(self):
        title_array = self.article_metadata.find("title-group").find("article-title").get_text()
        if title_array:
            title_temp = self.bsstrtodict(title_array, "html.parser")
            title = title_temp.get_text().title()

            self.base_metadata["title"] = title

        else:
            raise MissingTitleException("No title found")

    def _parse_author(self):
        author_list = []
        editor_list = []
        name_parser = utils.AuthorNames()

        affil_map = {}

        # Create a dictionary to map affiliation names to affiliation numbers
        if self.article_metadata.find("contrib-group"):
            contrib_group = self.article_metadata.find_all("contrib-group")

        # pdb.set_trace()
        affil_list = sum([group.find_all("aff") for group in contrib_group], [])

        if not affil_list:
            affil_list = self.article_metadata.find_all("aff")

        for aff in affil_list:
            if aff.find("institution"):
                affil_map[aff.get("id", "")] = self._clean_output(
                    aff.find("institution").get_text()
                )
            else:
                affil_map[aff.get("id", "")] = self._clean_output(aff.get_text())

        author_array = sum([group.find_all("contrib") for group in contrib_group], [])
        # pdb.set_trace()
        for a in author_array:
            author_temp = {}
            name = a.find("name").get_text()
            parsed_name = name_parser.parse(
                name, collaborations_params=self.author_collaborations_params
            )
            author_temp = parsed_name[0]

            if a.find("email"):
                author_temp["email"] = a.find("email").get_text()

            if a.find("contrib-id"):
                orcid = a.find("contrib-id").get_text()
                orcid = orcid.replace("https://orcid.org/", "")
                orcid = orcid.replace("http://orcid.org/", "")
                author_temp["orcid"] = orcid

            if a.find("xref"):
                aff_temp = []
                for author_affil in str(a.find("xref").get("rid", "")).split(","):
                    aff_temp.append(affil_map[author_affil])
                author_temp["aff"] = aff_temp

            if a.get("contrib-type", "") == "author":
                author_list.append(author_temp)
            elif a.get("contrib-type", "") == "editor":
                editor_list.append(author_temp)

        if (not author_list) and (not editor_list):
            raise MissingAuthorsException("No contributors found for")

        self.base_metadata["authors"] = author_list
        self.base_metadata["contributors"] = editor_list

    def _parse_pubdate(self):
        if self.article_metadata.find("pub-date"):
            pub_dates = self.article_metadata.find_all("pub-date")

            for date in pub_dates:
                if (date.get("pub-type", "") == "epub") or (date.get("pub-type", "") == ""):
                    self.base_metadata["pubdate_electronic"] = self._get_date(date)
                elif (date.get("pub-type", "") == "ppub") or (date.get("pub-type", "") == ""):
                    self.base_metadata["pubdate_print"] = self._get_date(date)

    def _parse_abstract(self):
        abstract = None
        if self.article_metadata.find("abstract"):
            # for s in self.article_metadata.find("abstract"):
            abstract_html = self.article_metadata.find("abstract").get_text()

            # Use BS to remove html markup
            abstract_temp = self.bsstrtodict(abstract_html, "html.parser")
            abstract = abstract_temp.get_text()

        if self.article_metadata.find("abstract") and self.article_metadata.find("abstract").find(
            "p"
        ):
            abstract_all = self.article_metadata.find("abstract").find_all("p")
            abstract_paragraph_list = list()
            for paragraph in abstract_all:
                para = self.bsstrtodict(paragraph.get_text(), "html.parser")
                abstract_paragraph_list.append(str(para))

            abstract = "\n".join(abstract_paragraph_list)

        if abstract:
            self.base_metadata["abstract"] = self._clean_output(abstract)

    def _parse_references(self):
        if self.input_metadata.find("back") and self.input_metadata.find("back").find("ref-list"):
            references = []
            for ref in self.input_metadata.find("back").find_all("ref"):
                # output raw XML for reference service to parse later
                ref_xml = str(ref.extract()).replace("\n", " ")
                references.append(ref_xml)

            self.base_metadata["references"] = references

    def _parse_esources(self):
        links = []  # TODO find example for esources format
        if self.input_metadata.find("fulltext_pdf"):
            links.append(("pub_pdf", self.input_metadata.find("fulltext_pdf").get_text()))
        if self.input_metadata.find("abstract_html"):
            links.append(("pub_html", self.input_metadata.find("abstract_html").get_text()))

        self.base_metadata["esources"] = links

    def _parse_keywords(self):
        if self.article_metadata.find("kwd-group"):
            keywords = []
            for k in self.article_metadata.find("kwd-group").find_all("kwd"):
                keywords.append({"string": k.get_text(), "system": "spie"})
            self.base_metadata["keywords"] = keywords

    def parse(self, text):
        """
        Parser for SPIE Publishing

        Parse SPIE XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        try:
            self.input_metadata = d.find("article")
        except Exception as err:
            raise NoSchemaException(err)

        if self.input_metadata:
            self.article_metadata = self.input_metadata.find("article-meta")
            self.journal_metadata = self.input_metadata.find("journal-meta")

        schema = self.input_metadata.get("xmlns:xlink", "")
        if schema not in self.spie_schema:
            raise WrongSchemaException('Unexpected XML schema "%s"' % schema)

        self._parse_journal()
        self._parse_ids()
        self._parse_title()
        self._parse_author()
        self._parse_pubdate()
        self._parse_abstract()
        self._parse_references()
        self._parse_esources()
        self._parse_keywords()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="OtherXML")

        return output
