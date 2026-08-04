"""templates — artifacts as FILES, with the loader that reads them.

⚑ THIS PACKAGE HOLDS ARTIFACTS, NOT CODE.  Everything beside `loader.py` is a
QML, SVG or XML document that a generator reads and substitutes into. They live
here rather than inside Python string literals so they can be opened, linted,
previewed and diffed as themselves — see `loader.py` for why `$name` rather than
`{name}`, and why a missing hole raises instead of rendering blank.

The `__init__.py` is what makes `import templates.loader` a package import rather
than a path accident; without it, a dependency census reasonably reads
`templates` as an undeclared third-party module.
"""
