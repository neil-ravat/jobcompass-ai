"""Readable plain text for API consumers, without exposing source HTML."""

import re
from html.parser import HTMLParser


class _DescriptionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if not self.hidden and tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n" + ("• " if tag == "li" else ""))

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "ul", "ol"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_description(row):
    parser = _DescriptionParser()
    parser.feed(row.get("description_html") or row.get("excerpt") or "")
    return re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
