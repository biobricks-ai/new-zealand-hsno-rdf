import importlib.util
from pathlib import Path
import pandas as pd
from rdflib import Graph, URIRef

P = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("convert", P/"stages"/"convert.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_streaming_conversion_and_coverage(tmp_path):
    source = tmp_path/"source.parquet"
    pd.DataFrame([{"cas":"110-54-3", "substance_name":"n-Hexane", "smiles":"CCCCCC", "approval":"HSR001264",
                   "hsno_code":"6.1E", "classification_text":"Acutely toxic", "ghs_translation":"Acute Tox. 5", "key_study":""}]).to_parquet(source)
    output, coverage = tmp_path/"out.nt", tmp_path/"coverage.json"
    report = m.convert(source, output, coverage)
    assert report["record_count_coverage"] == 1
    assert report["identifier_row_coverage"] == 1
    graph = Graph(); graph.parse(output, format="nt")
    compound = URIRef("https://biobricks.ai/compound/unmapped/cas/110-54-3")
    assert (None, m.IAO_ABOUT, compound) in graph
    assert (compound, None, None) in graph


def test_real_source_contains_n_hexane():
    source = Path("/mnt/raid2/biobricks/new-zealand-hsno/brick/classifications.parquet")
    if not source.exists(): return
    frame = pd.read_parquet(source, columns=["cas"])
    assert frame.cas.astype(str).str.strip().eq("110-54-3").any()
