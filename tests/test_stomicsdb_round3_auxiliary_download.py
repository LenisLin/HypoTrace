from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import sys
from threading import Thread
from urllib.error import URLError

import pytest
import yaml


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "stomicsdb_round3_auxiliary_download.py"
SPEC = importlib.util.spec_from_file_location("stomicsdb_round3_auxiliary_download", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
auxiliary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = auxiliary
SPEC.loader.exec_module(auxiliary)


class IndexHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/files/":
            body = b'<html><a href="data.csv">data</a><a href="sub/">sub</a></html>'
            content_type = "text/html"
        elif self.path == "/files/sub/":
            body = b'<html><a href="more.txt.gz">more</a><a href="../">up</a></html>'
            content_type = "text/html"
        elif self.path in {"/files/data.csv", "/files/sub/more.txt.gz"}:
            body = b"content"
            content_type = "application/octet-stream"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def index_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), IndexHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/files/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def write_case(root: Path, stds_id: str, *, resource_name: str, source_url: str) -> None:
    case = root / f"stomicsdb_{stds_id}"
    (case / "data").mkdir(parents=True)
    (case / "source_manifest.yaml").write_text(
        yaml.safe_dump({"source_manifest": {"stds_id": stds_id}})
    )
    (case / "case_manifest.yaml").write_text(
        yaml.safe_dump({"case_manifest": {"stds_id": stds_id}})
    )
    (case / "data/case_data_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "case_data_manifest": {
                    "stds_id": stds_id,
                    "auxiliary_resources": [
                        {
                            "resource_id": "A01",
                            "resource_name": resource_name,
                            "expected_content": "required bytes",
                            "source_url": source_url,
                            "access_classification": "anonymous_direct",
                            "local_availability": "absent",
                            "access_notes": "public",
                        }
                    ],
                    "result_data_links": [
                        {"result_id": "R01", "auxiliary_resource_ids": ["A01"]}
                    ],
                }
            }
        )
    )


def test_load_resources_deduplicates_and_preserves_case_result_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auxiliary, "FINAL_STDS_IDS", ("STDS0000001", "STDS0000007"))
    url = "https://example.org/data.tsv.gz"
    write_case(tmp_path, "STDS0000001", resource_name="shared", source_url=url)
    write_case(tmp_path, "STDS0000007", resource_name="shared", source_url=url)

    resources = auxiliary.load_resources(tmp_path)

    assert len(resources) == 1
    assert resources[0].source_cases == {"STDS0000001", "STDS0000007"}
    assert resources[0].result_ids_by_case == {
        "STDS0000001": {"R01"},
        "STDS0000007": {"R01"},
    }


def test_validate_public_url_rejects_secret_bearing_query() -> None:
    with pytest.raises(auxiliary.InventoryError, match="forbidden secret-bearing"):
        auxiliary.validate_public_url("https://example.org/data?token=secret")


def test_request_bytes_retries_transient_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    class Response:
        headers = {"Content-Type": "application/octet-stream"}

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, limit: int | None = None) -> bytes:
            return b"ok"

        def geturl(self) -> str:
            return "https://example.org/data.bin"

    def transient_urlopen(*args: object, **kwargs: object) -> Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise URLError("transient TLS EOF")
        return Response()

    monkeypatch.setattr(auxiliary, "urlopen", transient_urlopen)
    monkeypatch.setattr(auxiliary.time, "sleep", lambda _: None)

    data, _, final_url = auxiliary.request_bytes(
        "https://example.org/data.bin", timeout=5.0
    )

    assert data == b"ok"
    assert final_url == "https://example.org/data.bin"
    assert attempts == 3


def test_geo_accession_resolves_to_supplement_directory() -> None:
    assert auxiliary.geo_supplement_url(
        "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE144236"
    ) == "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE144nnn/GSE144236/suppl/"


def test_crawl_directory_discovers_files_without_parent_escape() -> None:
    with index_server() as url:
        artifacts = auxiliary.crawl_directory(url, timeout=5.0)

    assert [item.suggested_name for item in artifacts] == ["data.csv", "more.txt.gz"]


def test_github_repository_uses_head_archive() -> None:
    artifacts = auxiliary.resolve_github("https://github.com/shunfumao/cellmesh")

    assert artifacts == [
        auxiliary.Artifact(
            "https://github.com/shunfumao/cellmesh/archive/HEAD.zip",
            "cellmesh-HEAD.zip",
        )
    ]


@pytest.mark.parametrize(
    ("source_url", "expected_names"),
    [
        (
            "https://als-st.nygenome.org/",
            ["count_matrices.zip", "annotations.zip", "images.zip", "metadata.zip"],
        ),
        (
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10166856/#notes4",
            [
                "UMI_count.tsv",
                "E-MTAB-7320.idf.txt",
                "E-MTAB-7320.sdrf.txt",
                "GSE110823_RAW.tar",
            ],
        ),
        (
            "https://www.ebi.ac.uk/biostudies/arrayexpress/studies/E-MTAB-9260",
            ["E-MTAB-9260.idf.txt", "E-MTAB-9260.sdrf.txt"],
        ),
        (
            "https://www.reproductivecellatlas.org/non-pregnant-uterus.html",
            [
                "endometrium_all.h5ad",
                "endometrium_epithelial.h5ad",
                "endometrium_organoid.h5ad",
            ],
        ),
        (
            "https://pantherdb.org/tools/compareToRefList.jsp",
            [
                "PANTHER16.0_README.txt",
                "PANTHER16.0_LICENSE.txt",
                "PANTHER16.0_species.txt",
                "PTHR16.0_mouse.tsv",
            ],
        ),
        (
            "https://www.frontiersin.org/journals/immunology/articles/"
            "10.3389/fimmu.2022.1011125/full#supplementary-material",
            ["PMC9628215_SupplementaryFiles.zip"],
        ),
        (
            "https://help.partek.illumina.com/partek-flow/user-manual/task-menu/"
            "biological-interpretation/gene-set-enrichment",
            [
                "Partek_Flow_Gene_Set_Enrichment_current.md",
                "KEGG_release_info_current.txt",
                "KEGG_hsa_pathways_current.tsv",
                "KEGG_hsa_pathway_gene_links_current.tsv",
                "KEGG_hsa_article_pathways_current.txt",
            ],
        ),
        (
            "https://insight.jci.org/articles/view/147703",
            [
                "ReactomePA_1.56.0.tar.gz",
                "clusterProfiler_4.20.0.tar.gz",
                "reactome.db_1.96.0.tar.gz",
                "org.Mm.eg.db_3.23.0.tar.gz",
                "GO.db_3.23.1.tar.gz",
                "KEGG_release_info_current.txt",
                "KEGG_mmu_pathways_current.tsv",
                "KEGG_mmu_pathway_gene_links_current.tsv",
            ],
        ),
    ],
)
def test_known_resource_resolver_selects_only_required_artifacts(
    source_url: str, expected_names: list[str]
) -> None:
    artifacts = auxiliary.resolve_known_resource(source_url)

    assert artifacts is not None
    assert [artifact.suggested_name for artifact in artifacts] == expected_names
    assert all(artifact.source_url.startswith("https://") for artifact in artifacts)


def test_xena_known_resource_covers_all_article_cohorts_and_stays_partial() -> None:
    source_url = "https://xenabrowser.net/datapages/"

    artifacts = auxiliary.resolve_known_resource(source_url)

    assert artifacts is not None
    assert len(artifacts) == 62
    assert {
        artifact.suggested_name
        for artifact in artifacts
        if ".BRCA." in artifact.suggested_name
    } == {
        "TCGA.BRCA.HiSeqV2.gz",
        "TCGA.BRCA.Gistic2_all_thresholded.by_genes.gz",
    }
    assert source_url in auxiliary.PARTIAL_KNOWN_RESOURCE_REASONS
    assert "historical Xena dataset snapshots" in auxiliary.PARTIAL_KNOWN_RESOURCE_REASONS[
        source_url
    ]


def test_panther_archive_stays_pending_after_public_subset_discovery() -> None:
    source_url = "https://pantherdb.org/tools/compareToRefList.jsp"

    assert source_url in auxiliary.PARTIAL_KNOWN_RESOURCE_REASONS
    assert "historical Reactome" in auxiliary.PARTIAL_KNOWN_RESOURCE_REASONS[source_url]


def test_resource_selection_is_exact_and_rejects_unknown_ids() -> None:
    resources = [
        auxiliary.Resource("one", "bytes", "anonymous_direct", "https://one", ""),
        auxiliary.Resource("two", "bytes", "anonymous_direct", "https://two", ""),
    ]
    resources[0].inventory_id = "R3AUX021"
    resources[1].inventory_id = "R3AUX023"

    selected = auxiliary.select_resources(resources, ["R3AUX023"])

    assert [resource.inventory_id for resource in selected] == ["R3AUX023"]
    with pytest.raises(auxiliary.InventoryError, match="unknown resource IDs"):
        auxiliary.select_resources(resources, ["R3AUX999"])


def test_nonanonymous_public_substitute_requires_explicit_override() -> None:
    approved = auxiliary.Resource(
        "Partek",
        "current public substitute",
        "nonanonymous_access",
        "https://help.partek.illumina.com/partek-flow/user-manual/task-menu/"
        "biological-interpretation/gene-set-enrichment",
        "operator selected current release",
    )
    unapproved = auxiliary.Resource(
        "licensed",
        "private bytes",
        "nonanonymous_access",
        "https://example.org/private",
        "requires account",
    )

    assert auxiliary.public_download_eligible(approved)
    assert not auxiliary.public_download_eligible(unapproved)


def test_zenodo_published_record_uses_self_file_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auxiliary,
        "request_json",
        lambda url, timeout: {
            "files": [
                {
                    "key": "network.rds",
                    "links": {"self": "https://zenodo.org/api/records/1/files/network.rds/content"},
                }
            ]
        },
    )

    artifacts = auxiliary.resolve_zenodo("https://zenodo.org/records/1", timeout=5.0)

    assert artifacts == [
        auxiliary.Artifact(
            "https://zenodo.org/api/records/1/files/network.rds/content",
            "network.rds",
        )
    ]
