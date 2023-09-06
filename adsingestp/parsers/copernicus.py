#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 30 14:46:15 2023

@author: mugdhapolimera

Parser for Copernicus Publishing
"""

import logging

from adsingestp import utils
from adsingestp.ingest_exceptions import (
    MissingAuthorsException,
    MissingTitleException,
    NoSchemaException,
    WrongSchemaException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser, IngestBase
import pdb
import re

logger = logging.getLogger(__name__)


class CopernicusParser(BaseBeautifulSoupParser):
    copernicus_schema = ["http://www.w3.org/1999/xlink", "http://www.w3.org/1998/Math/MathML"]

    author_collaborations_params = {
        "keywords": ["group", "team", "collaboration"],
        "remove_the": False}


    def __init__(self):
        self.base_metadata = {}
        self.input_header = None  
        self.input_metadata = None

    def _parse_journal(self):        
        if self.input_metadata.find('journal'):
            journal_metadata = self.input_metadata.find('journal')
            
            if journal_metadata.find('journal_title'):
                self.base_metadata['publication'] = journal_metadata.find('journal_title').get_text()
                
            if journal_metadata.find('volume_number'):
                self.base_metadata['volume'] = journal_metadata.find('volume_number').get_text()

    def _parse_pagination(self):
        if self.input_metadata.find('start_page'):
            self.base_metadata['page_first'] = self.input_metadata.find('start_page').get_text()

        if self.input_metadata.find('end_page'):
            self.base_metadata['page_last'] = self.input_metadata.find('end_page').get_text()
    

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        self.base_metadata["issn"] = []
        if self.input_metadata.find("prism:issn"):
            self.base_metadata["issn"] = [
                ("not specified", self.input_metadata.find("prism:issn").get_text())
            ]

        if self.input_metadata.find("doi"):
            self.base_metadata["ids"]["doi"] = self.input_metadata.find("doi").get_text()

    # # TODO: IS THIS FIELD NECESSARY??
    #     if self.pubmeta_unit.find("article_number"):
    #         self.base_metadata["ids"]["pub-id"] = self.pubmeta_unit.find(
    #             "article_number").get_text()

    def _parse_title(self):
        title_array = self.input_metadata.find_all("article_title")
        if title_array:
            title_array_text = [i.get_text() for i in title_array]
            if len(title_array) == 1:
                self.base_metadata["title"] = self._clean_output(
                    title_array_text[0])
            else:
                self.base_metadata["title"] = self._clean_output(
                    ": ".join(title_array_text))
                
        else:
            raise MissingTitleException("No title found")

    def _parse_author(self):
        author_list = []
        name_parser = utils.AuthorNames()
        
        affil_map = {}
        if self.input_metadata.find_all('affiliations'):
            affil_list = self.input_metadata.find_all('affiliations')[0].find_all('affiliation')
            for aff in affil_list:
                affil_map[aff.get('numeration','')] = aff.get_text()

        author_array = self.input_metadata.find_all("author")
        for a in author_array:
            author_temp = {}
            name = a.find('name').get_text()
            parsed_name = name_parser.parse(
                name, collaborations_params=self.author_collaborations_params)
            author_temp = parsed_name[0]        
            
            if a.find('email'):
                author_temp['email'] = a.find('email').get_text()
            if a.find('contrib-id'):
                author_temp['orcid'] = a.find('contrib-id').get_text()
                
            if a['affiliations']:
                aff_temp = []
                for author_affil in str(a['affiliations']).split(',') :
                    aff_temp.append(affil_map[author_affil])                    
                author_temp['aff'] = aff_temp
                                
                
            author_list.append(author_temp)
            
        if not author_list:
            raise MissingAuthorsException("No contributors found for")

        self.base_metadata["authors"] = author_list
        

    def _parse_pubdate(self):
        if self.input_metadata.find("publication_date"):
            self.base_metadata["pubdate_electronic"] = self.input_metadata.find(
                "publication_date").get_text()

        # if self.input_metadata.find("publication_date"):
        #     dates = []
        #     for d in self.input_metadata.find("publication_date").find_all("date"):
        #         t = d.get("dateType", "")
        #         dates.append({"type": t, "date": d.get_text()})

        #     if dates:
        #         self.base_metadata["pubdate_other"] = dates
        

    def _parse_abstract(self):
        abstract = None
        if self.input_metadata.find("abstract"):
            for s in self.input_metadata.find("abstract"):
                abstract_html = s.get_text()
                # abstract = ''.join(xml.etree.ElementTree.fromstring(abstract_html).itertext())
                clean = re.compile('<.*?>')
                abstract = re.sub(clean, '', abstract_html)    #TODO: use something other than regex? native xml library did not work     
        # pdb.set_trace()
        
        if abstract:
            self.base_metadata["abstract"] = self._clean_output(abstract)

    def _parse_references(self):
        if self.input_metadata.find("references") and self.input_metadata.find("references").find("reference"):
            references = []
            for ref in self.input_metadata.find("references").find_all("reference"):
                # output raw XML for reference service to parse later
                ref_xml = str(ref.extract()).replace("\n", " ")
                references.append(ref_xml)

            self.base_metadata["references"] = references
            
    def parse(self, text):
        """
        Parse Copernicus XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)
        
        if d.find("article"):
            self.input_metadata = d.find("article") 
#        else:
#            raise <someerror> #TODO

        schema = self.input_metadata.get("xmlns:xlink", "")
        if schema not in self.copernicus_schema:
            raise WrongSchemaException('Unexpected XML schema "%s"' % schema)

        self._parse_journal() #journal name, pub + issue number
        self._parse_ids()  # doi and alternate ids (e.g., article_number)
        self._parse_title()
        self._parse_author()
        self._parse_pubdate()
        self._parse_abstract()
        self._parse_references()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="OtherXML")

        return output
