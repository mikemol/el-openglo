---
name: struct-tools
description: A known-bad routing table for check_routes --json FIXTURE: one row names a tool outside the repo root, which policy R4 must deny (W75, W738).
---

## artifact → tool

| artifact | tool | run bare to list its modes | claims |
|---|---|---|---|
| BibTeX — the claim-DAG | `../paperkit/tools/bibstruct.py` | `.venv/bin/python ../paperkit/tools/bibstruct.py` | `.bib` |
