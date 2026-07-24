# note: because you'll be modifying a valid json object, if you add a text
#       double quote ("), you need to escape the slash and the slashed quote
map_quotes = {
    "bdquo": '\\\"',
    "rdquo": '\\\"',
    "ldquo": '\\\"',
    "bsquo": "'",
    "rsquo": "'",
    "lsquo": "'",
    "sbquo": ",",
    "OpenCurlyDoubleQuote": '\\\"',
    "CloseCurlyDoubleQuote": '\\\"',
    "DiacriticalAcute": "'",
    "OpenCurlySingleQuote": "'",
    "CloseCurlySingleQuote": "'",
    "#8218": "'",
}

map_spaces = {
    "nbsp": " ",
    "zwnj": " ",
    "zwj": " ",
    "NonBreakingSpace": " ",
    "ZeroWidthSpace": " ",
}

map_ligatures = {
    "aelig": "ae",
    "AElig": "AE",
    "oelig": "oe",
    "OElig": "OE",
    "filig": "fi",
    "fflig": "ff",
    "fllig": "fl",
    "ffilig": "ffi",
    "ffllig": "ffl",
}

map_other = {
    "hyphen": "-",
    "minus": "-",
    "endash": "--",
    "ndash": "--",
    "emdash": "---",
    "mdash": "---",
    "HorizontalLine": "---",
    "#8208": "-",
    "bull": "*",
    "bullet": "*",
    "hellip": "...",
    "ldots": "...",
    "GreaterEqual": ">=",
    "#xff08": " (",
    "#65288": " (",
    "#xff09": ") ",
    "#65289": ") ",
    "THORN": "Th",
    "ETH": "D",
    "plusnm": "&plusmn;",  # this is a typo of plusmn
}

map_to_numeric = {
    "TildeTilde": "&#x2248;",
    "TildeEqual": "&#x2243;",
    "HorizontalLine": "&#x2500;",
    "GreaterEqual": "&#x2265;",
    "sigmaf": "&#x03c2;",
    "bot": "&#x22a5;",
    "imath": "&#x0131;",
    "times": "&#x00D7",
    "IEcy": "&#x0415;",
    "srarr": "&#x2192;",
    "#120484": "&#x0131;",  # bad encoding of Turkish i-no-bar
}


map_list = [map_quotes, map_spaces, map_ligatures, map_other, map_to_numeric]

ASCII_PUNCT_MAP = {}
for m in map_list:
    ASCII_PUNCT_MAP.update(m)
