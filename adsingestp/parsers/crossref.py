import logging
import re

from adsingestp.ingest_exceptions import (
    NotCrossrefXMLException,
    TooManyDocumentsException,
    WrongSchemaException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)

# compile outside of the class definition -- it only needs to be compiled once
re_issn = re.compile(r"^\d{4}-?\d{3}[0-9X]$")  # XXXX-XXXX


class CrossrefParser(BaseBeautifulSoupParser):
    def __init__(self):
        self.base_metadata = {}
        self.input_metadata = None
        self.record_meta = None
        self.record_type = None

    def _get_date(self, date_raw):
        """
        Extract and standarize date from input BeautifulSoup date object
        :param date_raw: BeautifulSoup date object
        :return: formatted date string (yyyy-mm-dd)
        """
        if date_raw.find("year"):
            pubdate = date_raw.find("year").get_text()
        else:
            raise WrongSchemaException("No publication year found")

        if date_raw.find("month"):
            month = date_raw.find("month").get_text()
        else:
            month = "00"

        if len(month) == 1:
            month = "0" + month
        pubdate = pubdate + "-" + month

        if date_raw.find("day"):
            day = date_raw.find("day").get_text()
        else:
            day = "00"

        if len(day) == 1:
            day = "0" + day
        pubdate = pubdate + "-" + day

        return pubdate

    def _get_isbn(self, isbns):
        """
        Takes a list of the ISBN nodes, returns the ISBN text of the correct node

        :param isbns: list of BS nodes
        :return: list of dicts of ISBNs
        """
        isbns_out = []
        for i in isbns:
            isbn_type = i.get("media_type", "print")

            isbns_out.append({"type": isbn_type, "isbn_str": i.get_text()})

        return isbns_out

    def _parse_pub(self):
        # journal articles only
        journal_meta = self.input_metadata.find("journal").find("journal_metadata")

        if journal_meta.find("full_title"):
            self.base_metadata["publication"] = journal_meta.find("full_title").get_text()

        if journal_meta.find_all("issn"):
            issn_all = journal_meta.find_all("issn")
        else:
            issn_all = []

        issns = []
        for i in issn_all:
            if i.get_text() and re_issn.match(i.get_text()):
                if i.has_attr("media_type"):
                    issns.append((i["media_type"], i.get_text()))
                else:
                    issns.append(("print", i.get_text()))
        self.base_metadata["issn"] = issns

    def _parse_issue(self):
        if self.record_type == "journal":
            meta = self.input_metadata.find("journal").find("journal_issue")

            if meta.find("journal_volume") and meta.find("journal_volume").find("volume"):
                self.base_metadata["volume"] = (
                    meta.find("journal_volume").find("volume").get_text()
                )

        elif self.record_type == "book":
            meta = self.record_meta

            if meta.find("volume"):
                self.base_metadata["volume"] = meta.find("volume").get_text()

        else:
            # no handling here for conferences yet
            meta = None

        if meta and meta.find("issue"):
            self.base_metadata["issue"] = meta.find("issue").get_text()

    def _parse_conf_event_proceedings(self):
        # conferences only, parses event-level and proceedings-level metadata, not conference paper-level metadata
        event_meta = self.input_metadata.find("conference").find("event_metadata")
        proc_meta = self.input_metadata.find("conference").find("proceedings_metadata")

        if event_meta.find("conference_name"):
            self.base_metadata["conf_name"] = event_meta.find("conference_name").get_text()

        if event_meta.find("conference_location"):
            self.base_metadata["conf_location"] = event_meta.find("conference_location").get_text()

        if event_meta.find("conference_date"):
            self.base_metadata["conf_date"] = event_meta.find("conference_date").get_text()

        if proc_meta.find("proceedings_title"):
            self.base_metadata["publication"] = proc_meta.find("proceedings_title").get_text()

        if proc_meta.find("publisher_name"):
            self.base_metadata["publisher"] = proc_meta.find("publisher_name").get_text()

        # this will be overwritten by _parse_pubdate, if a pubdate is available for the conference paper itself, but
        # parsing the overall proceedings pubdate here at least provides a backstop
        if proc_meta.find("publication_date"):
            pubdate = self._get_date(proc_meta.find("publication_date"))
            # type of pubdate is not defined here, but default to print
            self.base_metadata["pubdate_print"] = pubdate

        if proc_meta.find("isbn"):
            self.base_metadata["isbn"] = self._get_isbn(proc_meta.find_all("isbn"))

    def _parse_book_series(self):
        series_meta = self.record_meta.find("series_metadata")

        if series_meta.find("title"):
            self.base_metadata["series_title"] = series_meta.find("title").get_text()

        # TODO need to add logic for other ID types
        if series_meta.find("issn"):
            self.base_metadata["series_id"] = series_meta.find("issn").get_text()
            self.base_metadata["series_id_description"] = "issn"

    def _parse_title_abstract(self):
        if self.record_meta.find("titles") and self.record_meta.find("titles").find("title"):
            self.base_metadata["title"] = self.record_meta.find("titles").find("title").get_text()

        if self.record_meta.find("jats:abstract") and self.record_meta.find("jats:abstract").find(
            "jats:p"
        ):
            self.base_metadata["abstract"] = self._clean_output(
                self.record_meta.find("jats:abstract").find("jats:p").get_text()
            )

    def _parse_contrib(self):
        contribs_section = self.record_meta.find("contributors").extract()
        contribs_raw = contribs_section.find_all("person_name")

        authors_out = []
        contribs_out = []
        for c in contribs_raw:
            contrib_tmp = {}
            if c.find("given_name"):
                contrib_tmp["given"] = c.find("given_name").get_text()

            if c.find("surname"):
                contrib_tmp["surname"] = c.find("surname").get_text()

            if c.find("suffix"):
                contrib_tmp["suffix"] = c.find("suffix").get_text()

            if c.find("ORCID"):
                orcid = c.find("ORCID").get_text()
                orcid = orcid.replace("http://orcid.org/", "")
                contrib_tmp["orcid"] = orcid

            role = c.get("contributor_role", "unknown")

            if role == "author":
                authors_out.append(contrib_tmp)
            else:
                contrib_tmp["role"] = role
                contribs_out.append(contrib_tmp)

        if authors_out:
            self.base_metadata["authors"] = authors_out
        if contribs_out:
            self.base_metadata["contributors"] = contribs_out

    def _parse_pubdate(self):
        pubdates_raw = self.record_meta.find_all("publication_date")
        for p in pubdates_raw:
            try:
                datetype = p.get("media_type", "print")
            except Exception as err:
                logger.warn("Pubdate without a media type! Assigning print: %s" % err)
                datetype = "print"

            pubdate = self._get_date(p)
            if datetype == "print":
                self.base_metadata["pubdate_print"] = pubdate
            elif datetype == "online":
                self.base_metadata["pubdate_electronic"] = pubdate
            else:
                logger.warning("Unknown date type")

    def _parse_edhistory_copyright(self):
        if self.record_meta.find("crossmark") and self.record_meta.find("crossmark").find(
            "custom_metadata"
        ):
            custom_meta = (
                self.record_meta.find("crossmark").find("custom_metadata").find_all("assertion")
            )
            received = []
            for c in custom_meta:
                if c["name"] == "date_received":
                    received.append(c.get_text())
                elif c["name"] == "date_accepted":
                    self.base_metadata["edhist_acc"] = c.get_text()
                elif c["name"] == "copyright_information":
                    self.base_metadata["copyright"] = c.get_text()

                self.base_metadata["edhist_rec"] = received

    def _parse_page(self):
        if self.record_meta.find("pages"):
            page_info = self.record_meta.find("pages")

            if page_info.find("first_page"):
                self.base_metadata["page_first"] = page_info.find("first_page").get_text()

            if page_info.find("last_page"):
                self.base_metadata["page_last"] = page_info.last_page.get_text()

        elif self.record_meta.find("publisher_item") and self.record_meta.find(
            "publisher_item"
        ).find("item_number"):
            ids = {}
            for idx, i in enumerate(
                self.record_meta.find("publisher_item").find_all("item_number")
            ):
                tag = i.get("item_number_type")
                ids[tag if tag else "other" + str(idx)] = i.get_text()
            if ids.get("article-number"):
                self.base_metadata["electronic_id"] = ids["article-number"]
            # TODO if there are any other relevant publisher items, add handling here

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        # TODO ask Matt about crossref ID
        if self.record_meta.find("doi_data") and self.record_meta.find("doi_data").find("doi"):
            self.base_metadata["ids"]["doi"] = (
                self.record_meta.find("doi_data").find("doi").get_text()
            )

    def _parse_references(self):
        if self.record_meta.find("citation_list"):
            refs_raw = self.record_meta.find("citation_list").find_all("citation")

            ref_list = []
            # output raw XML for reference parser to handle
            for r in refs_raw:
                ref_list.append(str(r.extract()).replace("\n", " "))

            self.base_metadata["references"] = ref_list

    def parse(self, text):
        """
        Parse Crossref XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        records_in_file = d.find_all("doi_record")
        if len(records_in_file) > 1:
            raise TooManyDocumentsException(
                "This file has %s records, should have only one!" % len(records_in_file)
            )

        try:
            self.input_metadata = d.find("crossref").extract()
        except AttributeError as err:
            raise NotCrossrefXMLException(err)

        type_found = False
        self.record_type = None
        if self.input_metadata.find("journal"):
            type_found = True
            self.record_type = "journal"
            self.record_meta = self.input_metadata.find("journal_article").extract()
        if self.input_metadata.find("conference"):
            if type_found:
                raise WrongSchemaException("Too many document types found in CrossRef record")
            else:
                type_found = True
                self.record_type = "conference"
                self.record_meta = self.input_metadata.find("conference_paper").extract()
        if self.input_metadata.find("book"):
            if type_found:
                raise WrongSchemaException("Too many document types found in CrossRef record")
            else:
                type_found = True
                self.record_type = "book"
                if self.input_metadata.find("book_metadata"):
                    self.record_meta = self.input_metadata.find("book_metadata").extract()
                elif self.input_metadata.find("book_series_metadata"):
                    self.record_meta = self.input_metadata.find("book_series_metadata").extract()

        if not type_found:
            raise WrongSchemaException(
                "Didn't find allowed document type (article, conference, book) in CrossRef record"
            )

        if self.record_type == "journal":
            self._parse_pub()

        if self.record_type == "conference":
            self._parse_conf_event_proceedings()

        if self.record_type == "book":
            if self.record_meta.find("publisher") and self.record_meta.find("publisher").find(
                "publisher_name"
            ):
                self.base_metadata["publisher"] = self.record_meta.find(
                    "publisher_name"
                ).get_text()

            if self.record_meta.find("isbn"):
                self.base_metadata["isbn"] = self._get_isbn(self.record_meta.find_all("isbn"))

            if self.record_meta.find("series_metadata"):
                self._parse_book_series()

        self._parse_issue()
        self._parse_title_abstract()
        try:
            self._parse_contrib()
        except Exception as err:
            # logger.warn('No contributors in parsed record: %s' % err)
            pass
        self._parse_pubdate()
        self._parse_edhistory_copyright()
        try:
            self._parse_page()
        except Exception as err:
            # logger.warn('No pages in parsed record: %s' % err)
            pass
        self._parse_ids()
        self._parse_references()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="OtherXML")

        return output
