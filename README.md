# ADSIngestParser

<p align="center">

![CI Status](https://github.com/adsabs/ADSIngestParser/actions/workflows/ci.yml/badge.svg)

  <!--
  <a href="https://codecov.io/gh/adsabs/adsingestp">
    <img src="https://img.shields.io/codecov/c/github/adsabs/ADSIngestParser.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
  //-->
</p>

ADSIngestParser is a library used to parse publisher-provided files, in well-structured XML or other formats, into our own data model, defined by the [ingest_data_model](https://github.com/adsabs/ingest_data_model). The output is a dictionary.

Example usage, with the arXiv parser:
```
from adsingestp.parsers import arxiv

with open("infile.xml", "rb") as fp:
    input_data = fp.read()

parser = arxiv.ArxivParser()
parsed = parser.parse(input_data)
```


## Installation

Install this via pip (or your favourite package manager):

```bash
pip install adsingestp
```

## Development

Install locally into virtualenv

```bash
virtualenv .venv
source .venv/bin/activate
pip install -e .
```

### Parser structure
Parsers for each source file format should be in their own file. The parser itself is object-oriented, and the class name should take the format `<Format>Parser` (e.g. `ArxivParser`). XML parsers should inherit `BaseBeautifulSoupParser`. All parser classes should ultimately inherit `IngestBase` (`BaseBeautifulSoupParser` inherits this base class). All parsers will parse the source file into an intermediate dictionary format, outlined in `IngestBase.format`. The intermediate dictionary format must then be converted to the final `ingest_data_model` format via 

```output = self.format(<intermediate_dictionary>, format=...)```

This final formatting into the `ingest_data_model` format is done separately from the parsing in order to simplify any updates that may need to happen if/when the upstream `ingest_data_model` is changed.

Required methods:
* `__init__`: initialize the intermediate dictionary and other needed structures
* `parse`: the primary external method. The primary input is the text of the source file (the source file must be read in prior to calling the `parse` method; no I/O is included in this library). The output is a dictionary in the `ingest_data_model` format

Other sub-functions may be included as needed, to enhance code readability. Prepend an underscore (`_`) to internal sub-function names.

### XML parsers
Parsers that handle XML source files should use BeautifulSoup to handle initial parsing. To do so, the parser should inherit `BaseBeautifulSoupParser`, then call the `bsstrtodict` method on the input text:

```d = self.bsstrtodict(text, parser="lxml-xml")```

The BS parser is generally `lxml-xml`, but this can be changed as needed. 

### Author name parsing
Many of the parsers utilize the `utils.AuthorNames.parse` method to parse a single raw author name string into a structured name dictionary. Use this method for author name parsing unless something more comprehensive is required.

### Unittests
Unittests must be included for each new parsers, with a minimum of 2 example source files per parser. Preferably, at least one of these source files should be of a more complex structure. Unittest coverage should be 80% or higher for each parser. If more example source files are needed, check with the curation team.


## Documentation

[documentation](https://adsingestp.readthedocs.io)
