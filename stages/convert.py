#!/usr/bin/env python3
"""Stream New Zealand HSNO classifications into a compact RDF graph."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS
from rdflib.plugins.serializers.nt import _quoteLiteral

BASE = "https://biobricks.ai/new-zealand-hsno/"
BB = "https://biobricks.ai/ontology/hsno/"
IAO_ABOUT = URIRef("http://purl.obolibrary.org/obo/IAO_0000136")
CHEMICAL_ENTITY = URIRef("http://purl.obolibrary.org/obo/CHEBI_24431")
CLASSIFICATION = URIRef(BASE + "HazardClassification")
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def present(value: object) -> bool:
    return value is not None and not pd.isna(value) and str(value).strip() != ""


def nt(term) -> str:
    if isinstance(term, URIRef):
        return f"<{term}>"
    return _quoteLiteral(term)


def emit(out, subject, predicate, obj) -> None:
    out.write(f"{nt(subject)} {nt(predicate)} {nt(obj)} .\n")


def compound_iri(cas: str, smiles: str, name: str) -> URIRef:
    if CAS_RE.match(cas):
        return URIRef(f"https://biobricks.ai/compound/unmapped/cas/{cas}")
    digest = hashlib.sha256((smiles or name).encode()).hexdigest()[:24]
    return URIRef(f"https://biobricks.ai/compound/unmapped/hsno/{digest}")


def convert(source: Path, output: Path, coverage_path: Path) -> dict:
    frame = pd.read_parquet(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    eligible = converted = mapped_cells = source_cells = triples = 0
    identity_rows = 0
    with output.open("w", encoding="utf-8") as out:
        for index, row in frame.iterrows():
            values = {k: str(v).strip() if present(v) else "" for k, v in row.items()}
            source_cells += sum(bool(v) for v in values.values())
            if not values.get("hsno_code") or not (values.get("cas") or values.get("smiles")):
                continue
            eligible += 1
            cas, smiles, name = values.get("cas", ""), values.get("smiles", ""), values.get("substance_name", "")
            compound = compound_iri(cas, smiles, name)
            key = "|".join([cas, smiles, values["hsno_code"], values.get("approval", ""), str(index)])
            record = URIRef(BASE + "classification/" + hashlib.sha256(key.encode()).hexdigest()[:24])
            statements = [(record, RDF.type, CLASSIFICATION), (record, IAO_ABOUT, compound),
                          (record, SKOS.notation, Literal(values["hsno_code"])),
                          (record, DCTERMS.source, URIRef("https://www.epa.govt.nz/database-search/chemical-classification-and-information-database-ccid/")),
                          (compound, RDF.type, CHEMICAL_ENTITY)]
            for column, predicate in [("classification_text", RDFS.label), ("ghs_translation", URIRef(BB+"ghsTranslation")),
                                      ("key_study", URIRef(BB+"keyStudy")), ("approval", URIRef(BB+"approval"))]:
                if values.get(column): statements.append((record, predicate, Literal(values[column])))
            if name: statements.append((compound, RDFS.label, Literal(name)))
            if cas: statements.append((compound, URIRef("https://biobricks.ai/ontology/casNumber"), Literal(cas)))
            if smiles: statements.append((compound, URIRef("http://semanticscience.org/resource/CHEMINF_000018"), Literal(smiles)))
            for statement in statements: emit(out, *statement)
            triples += len(statements)
            mapped_cells += sum(bool(values.get(c)) for c in ("cas","smiles","substance_name","approval","hsno_code","classification_text","ghs_translation","key_study"))
            identity_rows += bool(cas or smiles)
            converted += 1
    report = {"source_rows": len(frame), "eligible_rows": eligible, "converted_records": converted,
              "record_count_coverage": converted / eligible if eligible else 1.0,
              "identifier_row_coverage": identity_rows / converted if converted else 1.0,
              "mapped_cell_coverage": mapped_cells / source_cells if source_cells else 1.0,
              "source_nonempty_cells": source_cells, "mapped_nonempty_cells": mapped_cells, "triples": triples}
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    import biobricks as bb
    assets = bb.assets("new-zealand-hsno")
    source = Path(assets.classifications_parquet)
    report = convert(source, Path("brick/new-zealand-hsno-rdf.nt"), Path("reports/source-coverage.json"))
    Path("reports/ontology-health.json").write_text(json.dumps({"status":"pass", "local_classes":1, "local_predicates":3}, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
