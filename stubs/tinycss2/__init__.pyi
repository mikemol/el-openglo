# SPDX-License-Identifier: Apache-2.0
# Stub: tinycss2 as scripts/check_css.py, check_gtk.py and check_union.py use it (W255).
# Node `type` strings are the library's own (tinycss2/ast.py); each is a Literal on its
# own class so `if node.type == "qualified-rule"` narrows the union, as it does at run
# time. Only the attributes the checks read are declared.
from collections.abc import Iterable
from typing import Literal

class _Plain:
    type: Literal[
        "literal", "ident", "at-keyword", "hash", "string", "url", "unicode-range",
        "number", "percentage", "dimension", "whitespace", "comment", "function",
        "() block", "[] block", "{} block",
    ]

class ParseError:
    type: Literal["error"]
    kind: str
    message: str

class QualifiedRule:
    type: Literal["qualified-rule"]
    prelude: list[Node]
    content: list[Node]

class AtRule:
    type: Literal["at-rule"]
    at_keyword: str
    prelude: list[Node]
    content: list[Node] | None

class Declaration:
    type: Literal["declaration"]
    name: str
    value: list[Node]
    important: bool

type Node = _Plain | ParseError | QualifiedRule | AtRule | Declaration

def parse_stylesheet(
    input: str | Iterable[Node], skip_comments: bool = False, skip_whitespace: bool = False
) -> list[Node]: ...
def parse_rule_list(
    input: str | Iterable[Node], skip_comments: bool = False, skip_whitespace: bool = False
) -> list[Node]: ...
def parse_declaration_list(
    input: str | Iterable[Node], skip_comments: bool = False, skip_whitespace: bool = False
) -> list[Node]: ...
def serialize(nodes: Iterable[Node]) -> str: ...
