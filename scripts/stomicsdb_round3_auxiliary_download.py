#!/usr/bin/env python3
"""Discover and download Round 3 auxiliary resources into NAS staging."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

import yaml

from stomicsdb_round2_download import (
    DownloadConfig,
    DownloadError,
    DownloadResult,
    JsonlLogger,
    PlanRow,
    download_row,
    fsync_directory,
)


DEFAULT_DATA_ROOT = Path("/mnt/NAS_21T/ProjectData/HypoTrace_Data")
STOMICS_RELATIVE = PurePosixPath("raw_data/public_database/stomicsdb")
DEFAULT_CASES_ROOT = DEFAULT_DATA_ROOT / Path(*STOMICS_RELATIVE.parts) / "cases"
DEFAULT_OUTPUT_ROOT = (
    DEFAULT_DATA_ROOT / Path(*STOMICS_RELATIVE.parts) / "staging/round3_auxiliary_downloads"
)
USER_AGENT = "HypoTrace-STOmicsDB-Round3-Auxiliary/1.0"

FINAL_STDS_IDS = (
    "STDS0000001",
    "STDS0000007",
    "STDS0000066",
    "STDS0000073",
    "STDS0000081",
    "STDS0000089",
    "STDS0000091",
    "STDS0000106",
    "STDS0000124",
    "STDS0000162",
    "STDS0000181",
    "STDS0000182",
    "STDS0000201",
    "STDS0000212",
    "STDS0000217",
    "STDS0000227",
)

DIRECT_SUFFIXES = {
    ".7z",
    ".bam",
    ".bed",
    ".bz2",
    ".csv",
    ".fastq",
    ".feather",
    ".gmt",
    ".gz",
    ".h5",
    ".h5ad",
    ".jpeg",
    ".jpg",
    ".json",
    ".loom",
    ".mtx",
    ".pdf",
    ".png",
    ".rds",
    ".tar",
    ".tgz",
    ".tif",
    ".tiff",
    ".tsv",
    ".txt",
    ".xlsx",
    ".xml",
    ".zip",
}

SECRET_QUERY_KEYS = {
    "access_token",
    "authorization",
    "credential",
    "key-pair-id",
    "policy",
    "signature",
    "sig",
    "token",
    "x-amz-credential",
    "x-amz-security-token",
    "x-amz-signature",
}


class InventoryError(ValueError):
    pass


class DiscoveryError(RuntimeError):
    pass


@dataclass
class Resource:
    resource_name: str
    expected_content: str
    access_classification: str
    source_url: str
    access_notes: str
    source_cases: set[str] = field(default_factory=set)
    result_ids_by_case: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    inventory_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "inventory_id": self.inventory_id,
            "resource_name": self.resource_name,
            "expected_content": self.expected_content,
            "access_classification": self.access_classification,
            "source_url": self.source_url,
            "access_notes": self.access_notes,
            "source_cases": sorted(self.source_cases),
            "result_ids_by_case": {
                key: sorted(value) for key, value in sorted(self.result_ids_by_case.items())
            },
        }


@dataclass(frozen=True)
class Artifact:
    source_url: str
    suggested_name: str


KNOWN_RESOURCE_ARTIFACTS: dict[str, tuple[Artifact, ...]] = {
    "https://als-st.nygenome.org/": tuple(
        Artifact(f"https://als-st.nygenome.org/compressed_data/{name}", name)
        for name in (
            "count_matrices.zip",
            "annotations.zip",
            "images.zip",
            "metadata.zip",
        )
    ),
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC10166856/#notes4": (
        Artifact(
            "https://www.ebi.ac.uk/biostudies/files/E-MTAB-7320/UMI_count.tsv",
            "UMI_count.tsv",
        ),
        Artifact(
            "https://www.ebi.ac.uk/biostudies/files/E-MTAB-7320/E-MTAB-7320.idf.txt",
            "E-MTAB-7320.idf.txt",
        ),
        Artifact(
            "https://www.ebi.ac.uk/biostudies/files/E-MTAB-7320/E-MTAB-7320.sdrf.txt",
            "E-MTAB-7320.sdrf.txt",
        ),
        Artifact(
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE110nnn/GSE110823/suppl/"
            "GSE110823_RAW.tar",
            "GSE110823_RAW.tar",
        ),
    ),
    "https://www.ebi.ac.uk/biostudies/arrayexpress/studies/E-MTAB-9260": (
        Artifact(
            "https://www.ebi.ac.uk/biostudies/files/E-MTAB-9260/E-MTAB-9260.idf.txt",
            "E-MTAB-9260.idf.txt",
        ),
        Artifact(
            "https://www.ebi.ac.uk/biostudies/files/E-MTAB-9260/E-MTAB-9260.sdrf.txt",
            "E-MTAB-9260.sdrf.txt",
        ),
    ),
    "https://www.reproductivecellatlas.org/non-pregnant-uterus.html": tuple(
        Artifact(
            f"https://cellgeni.cog.sanger.ac.uk/vento/reproductivecellatlas/{name}",
            name,
        )
        for name in (
            "endometrium_all.h5ad",
            "endometrium_epithelial.h5ad",
            "endometrium_organoid.h5ad",
        )
    ),
    "https://pantherdb.org/tools/compareToRefList.jsp": (
        Artifact(
            "https://data.pantherdb.org/ftp/sequence_classifications/16.0/README",
            "PANTHER16.0_README.txt",
        ),
        Artifact(
            "https://data.pantherdb.org/ftp/sequence_classifications/16.0/LICENSE",
            "PANTHER16.0_LICENSE.txt",
        ),
        Artifact(
            "https://data.pantherdb.org/ftp/sequence_classifications/16.0/species",
            "PANTHER16.0_species.txt",
        ),
        Artifact(
            "https://data.pantherdb.org/ftp/sequence_classifications/16.0/"
            "PANTHER_Sequence_Classification_files/PTHR16.0_mouse",
            "PTHR16.0_mouse.tsv",
        ),
    ),
    "https://www.frontiersin.org/journals/immunology/articles/10.3389/"
    "fimmu.2022.1011125/full#supplementary-material": (
        Artifact(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9628215/"
            "supplementaryFiles",
            "PMC9628215_SupplementaryFiles.zip",
        ),
    ),
    "https://help.partek.illumina.com/partek-flow/user-manual/task-menu/"
    "biological-interpretation/gene-set-enrichment": (
        Artifact(
            "https://help.partek.illumina.com/partek-flow/user-manual/task-menu/"
            "biological-interpretation/gene-set-enrichment.md",
            "Partek_Flow_Gene_Set_Enrichment_current.md",
        ),
        Artifact(
            "https://rest.kegg.jp/info/kegg",
            "KEGG_release_info_current.txt",
        ),
        Artifact(
            "https://rest.kegg.jp/list/pathway/hsa",
            "KEGG_hsa_pathways_current.tsv",
        ),
        Artifact(
            "https://rest.kegg.jp/link/hsa/pathway",
            "KEGG_hsa_pathway_gene_links_current.tsv",
        ),
        Artifact(
            "https://rest.kegg.jp/get/"
            "hsa04110+hsa04668+hsa04151+hsa04512+hsa04510",
            "KEGG_hsa_article_pathways_current.txt",
        ),
    ),
    "https://insight.jci.org/articles/view/147703": (
        Artifact(
            "https://bioconductor.org/packages/3.23/bioc/src/contrib/"
            "ReactomePA_1.56.0.tar.gz",
            "ReactomePA_1.56.0.tar.gz",
        ),
        Artifact(
            "https://bioconductor.org/packages/3.23/bioc/src/contrib/"
            "clusterProfiler_4.20.0.tar.gz",
            "clusterProfiler_4.20.0.tar.gz",
        ),
        Artifact(
            "https://bioconductor.org/packages/3.23/data/annotation/src/contrib/"
            "reactome.db_1.96.0.tar.gz",
            "reactome.db_1.96.0.tar.gz",
        ),
        Artifact(
            "https://bioconductor.org/packages/3.23/data/annotation/src/contrib/"
            "org.Mm.eg.db_3.23.0.tar.gz",
            "org.Mm.eg.db_3.23.0.tar.gz",
        ),
        Artifact(
            "https://bioconductor.org/packages/3.23/data/annotation/src/contrib/"
            "GO.db_3.23.1.tar.gz",
            "GO.db_3.23.1.tar.gz",
        ),
        Artifact(
            "https://rest.kegg.jp/info/kegg",
            "KEGG_release_info_current.txt",
        ),
        Artifact(
            "https://rest.kegg.jp/list/pathway/mmu",
            "KEGG_mmu_pathways_current.tsv",
        ),
        Artifact(
            "https://rest.kegg.jp/link/mmu/pathway",
            "KEGG_mmu_pathway_gene_links_current.tsv",
        ),
    ),
    "https://xenabrowser.net/datapages/": tuple(
        artifact
        for cohort in (
            "ACC",
            "BLCA",
            "BRCA",
            "CESC",
            "CHOL",
            "COAD",
            "ESCA",
            "GBM",
            "HNSC",
            "KICH",
            "KIRC",
            "KIRP",
            "LGG",
            "LIHC",
            "LUAD",
            "LUSC",
            "MESO",
            "OV",
            "PAAD",
            "PCPG",
            "PRAD",
            "READ",
            "SARC",
            "SKCM",
            "STAD",
            "TGCT",
            "THCA",
            "THYM",
            "UCEC",
            "UCS",
            "UVM",
        )
        for artifact in (
            Artifact(
                f"https://tcga.xenahubs.net/download/TCGA.{cohort}.sampleMap/HiSeqV2.gz",
                f"TCGA.{cohort}.HiSeqV2.gz",
            ),
            Artifact(
                "https://tcga.xenahubs.net/download/"
                f"TCGA.{cohort}.sampleMap/"
                "Gistic2_CopyNumber_Gistic2_all_thresholded.by_genes.gz",
                f"TCGA.{cohort}.Gistic2_all_thresholded.by_genes.gz",
            ),
        )
    ),
}


PUBLIC_CURRENT_RELEASE_OVERRIDES = frozenset(
    {
        "https://help.partek.illumina.com/partek-flow/user-manual/task-menu/"
        "biological-interpretation/gene-set-enrichment",
    }
)


PARTIAL_KNOWN_RESOURCE_REASONS = {
    "https://pantherdb.org/tools/compareToRefList.jsp": (
        "official PANTHER 16.0 mouse classification and release metadata were located; "
        "the frozen historical Reactome overrepresentation annotations and service state "
        "remain unbound"
    ),
    "https://xenabrowser.net/datapages/": (
        "current per-cohort HiSeqV2 expression and Gistic2 thresholded copy-number files "
        "were located for all 31 article-listed TCGA cohorts; the article does not identify "
        "the exact historical Xena dataset snapshots"
    ),
}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = next((value for key, value in attrs if key.lower() == "href"), None)
        if href:
            self.links.append(href)


def emit(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True, ensure_ascii=True), flush=True)


def unwrap_yaml(path: Path, wrapper: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InventoryError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get(wrapper), dict):
        raise InventoryError(f"{path} must contain a {wrapper} mapping")
    return value[wrapper]


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InventoryError(f"unsupported source URL: {url}")
    if parsed.username or parsed.password:
        raise InventoryError("source URL must not contain embedded credentials")
    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    secret_key = next(iter(query_keys & SECRET_QUERY_KEYS), None)
    if secret_key is not None:
        raise InventoryError(f"source URL contains forbidden secret-bearing query key: {secret_key}")


def load_resources(cases_root: Path) -> list[Resource]:
    resources: dict[tuple[str, str], Resource] = {}
    for stds_id in FINAL_STDS_IDS:
        case_root = cases_root / f"stomicsdb_{stds_id}"
        source = unwrap_yaml(case_root / "source_manifest.yaml", "source_manifest")
        data = unwrap_yaml(
            case_root / "data/case_data_manifest.yaml", "case_data_manifest"
        )
        case = unwrap_yaml(case_root / "case_manifest.yaml", "case_manifest")
        if {source.get("stds_id"), data.get("stds_id"), case.get("stds_id")} != {stds_id}:
            raise InventoryError(f"case identity mismatch for {stds_id}")
        auxiliary = data.get("auxiliary_resources")
        links = data.get("result_data_links")
        if not isinstance(auxiliary, list) or not isinstance(links, list):
            raise InventoryError(f"invalid auxiliary resource structure for {stds_id}")
        local_by_id: dict[str, tuple[str, str]] = {}
        for value in auxiliary:
            if not isinstance(value, dict):
                raise InventoryError(f"invalid auxiliary resource for {stds_id}")
            required = {
                "resource_id",
                "resource_name",
                "expected_content",
                "source_url",
                "access_classification",
                "local_availability",
                "access_notes",
            }
            if not required.issubset(value):
                raise InventoryError(f"incomplete auxiliary resource for {stds_id}")
            if value["local_availability"] != "absent":
                raise InventoryError(f"unexpected localized Axx in Round 3 case {stds_id}")
            validate_public_url(value["source_url"])
            identity = (value["resource_name"], value["source_url"])
            local_by_id[value["resource_id"]] = identity
            existing = resources.get(identity)
            if existing is None:
                existing = Resource(
                    resource_name=value["resource_name"],
                    expected_content=value["expected_content"],
                    access_classification=value["access_classification"],
                    source_url=value["source_url"],
                    access_notes=value["access_notes"],
                )
                resources[identity] = existing
            elif (
                existing.expected_content != value["expected_content"]
                or existing.access_classification != value["access_classification"]
                or existing.access_notes != value["access_notes"]
            ):
                raise InventoryError(f"conflicting duplicate auxiliary resource: {identity[0]}")
            existing.source_cases.add(stds_id)
        for link in links:
            result_id = link.get("result_id")
            for resource_id in link.get("auxiliary_resource_ids", []):
                identity = local_by_id.get(resource_id)
                if identity is None:
                    raise InventoryError(
                        f"unresolved auxiliary reference {stds_id}:{result_id}:{resource_id}"
                    )
                resources[identity].result_ids_by_case[stds_id].add(result_id)
    ordered = sorted(resources.values(), key=lambda item: (item.source_url, item.resource_name))
    for index, resource in enumerate(ordered, 1):
        resource.inventory_id = f"R3AUX{index:03d}"
    return ordered


def select_resources(
    resources: list[Resource], requested_ids: list[str]
) -> list[Resource]:
    if not requested_ids:
        return resources
    requested = set(requested_ids)
    known = {resource.inventory_id for resource in resources}
    missing = sorted(requested - known)
    if missing:
        raise InventoryError(f"unknown resource IDs: {', '.join(missing)}")
    return [resource for resource in resources if resource.inventory_id in requested]


def public_download_eligible(resource: Resource) -> bool:
    return (
        resource.access_classification == "anonymous_direct"
        or resource.source_url in PUBLIC_CURRENT_RELEASE_OVERRIDES
    )


def request_bytes(url: str, timeout: float, *, limit: int | None = None) -> tuple[bytes, Any, str]:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if limit is not None:
        headers["Range"] = f"bytes=0-{max(limit - 1, 0)}"
    request = Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read() if limit is None else response.read(limit)
                return data, response.headers, response.geturl()
        except HTTPError as exc:
            raise DiscoveryError(f"HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            if attempt == 2:
                raise DiscoveryError(f"transport error: {exc.reason}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def request_json(url: str, timeout: float) -> Any:
    data, _, _ = request_bytes(url, timeout)
    try:
        return json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DiscoveryError(f"invalid JSON response from {url}") from exc


def safe_filename(value: str, default: str = "download.bin") -> str:
    value = unquote(value).strip().replace("\\", "_").replace("/", "_")
    value = re.sub(r"[^A-Za-z0-9._+-]+", "_", value).strip("._")
    if not value:
        value = default
    return value[:180]


def url_filename(url: str, default: str = "download.bin") -> str:
    return safe_filename(Path(unquote(urlparse(url).path)).name, default)


def is_html(headers: Any, prefix: bytes) -> bool:
    content_type = headers.get("Content-Type", "").lower()
    stripped = prefix.lstrip().lower()
    return (
        "text/html" in content_type
        or "application/xhtml" in content_type
        or stripped.startswith(b"<!doctype html")
        or stripped.startswith(b"<html")
    )


def crawl_directory(start_url: str, timeout: float, max_files: int = 100_000) -> list[Artifact]:
    root = urlparse(start_url)
    root_path = root.path if root.path.endswith("/") else root.path + "/"
    pending = [start_url]
    visited: set[str] = set()
    artifacts: dict[str, Artifact] = {}
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        data, headers, final_url = request_bytes(current, timeout)
        if not is_html(headers, data[:512]):
            artifacts[final_url] = Artifact(final_url, url_filename(final_url))
            continue
        parser = LinkParser()
        try:
            parser.feed(data.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise DiscoveryError(f"cannot parse directory index {current}: {exc}") from exc
        for href in parser.links:
            joined = urljoin(final_url, href)
            parsed = urlparse(joined)
            if parsed.scheme not in {"http", "https"} or parsed.netloc != root.netloc:
                continue
            if parsed.query or parsed.fragment or not parsed.path.startswith(root_path):
                continue
            normalized = parsed._replace(query="", fragment="").geturl()
            if parsed.path.endswith("/"):
                if normalized not in visited:
                    pending.append(normalized)
            else:
                artifacts[normalized] = Artifact(normalized, url_filename(normalized))
                if len(artifacts) > max_files:
                    raise DiscoveryError(f"directory exceeds {max_files} files: {start_url}")
    if not artifacts:
        raise DiscoveryError(f"directory contains no downloadable files: {start_url}")
    return [artifacts[key] for key in sorted(artifacts)]


def geo_supplement_url(source_url: str) -> str | None:
    parsed = urlparse(source_url)
    if parsed.netloc.lower() != "www.ncbi.nlm.nih.gov" or parsed.path != "/geo/query/acc.cgi":
        return None
    accession = next((value for key, value in parse_qsl(parsed.query) if key == "acc"), "")
    match = re.fullmatch(r"(GSE|GSM)([0-9]+)", accession)
    if not match:
        return None
    prefix, digits = match.groups()
    bucket = f"{prefix}{digits[:-3]}nnn"
    category = "series" if prefix == "GSE" else "samples"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/{category}/{bucket}/{accession}/suppl/"


def resolve_figshare(url: str, timeout: float) -> list[Artifact] | None:
    parsed = urlparse(url)
    if not parsed.netloc.lower().endswith("figshare.com"):
        return None
    match = re.search(r"/([0-9]+)(?:/)?$", parsed.path)
    if not match:
        return None
    payload = request_json(f"https://api.figshare.com/v2/articles/{match.group(1)}", timeout)
    files = payload.get("files", []) if isinstance(payload, dict) else []
    artifacts = [
        Artifact(value["download_url"], safe_filename(value.get("name", "download.bin")))
        for value in files
        if isinstance(value, dict) and isinstance(value.get("download_url"), str)
    ]
    if not artifacts:
        raise DiscoveryError("Figshare record contains no downloadable files")
    return artifacts


def resolve_zenodo(url: str, timeout: float) -> list[Artifact] | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "zenodo.org":
        return None
    match = re.search(r"/(?:records?|record)/([0-9]+)(?:/)?$", parsed.path)
    if not match:
        return None
    payload = request_json(f"https://zenodo.org/api/records/{match.group(1)}", timeout)
    files = payload.get("files", []) if isinstance(payload, dict) else []
    artifacts = []
    for value in files:
        if not isinstance(value, dict):
            continue
        links = value.get("links", {})
        content_url = None
        if isinstance(links, dict):
            content_url = links.get("content") or links.get("self")
        if isinstance(content_url, str):
            artifacts.append(Artifact(content_url, safe_filename(value.get("key", "download.bin"))))
    if not artifacts:
        raise DiscoveryError("Zenodo record contains no downloadable files")
    return artifacts


def resolve_github(url: str) -> list[Artifact] | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    owner, repository = parts[:2]
    if len(parts) >= 5 and parts[2:4] == ["releases", "tag"]:
        ref_kind, ref = "tags", "/".join(parts[4:])
    elif len(parts) >= 4 and parts[2] == "tree":
        ref_kind, ref = "heads", parts[3]
    else:
        archive = f"https://github.com/{owner}/{repository}/archive/HEAD.zip"
        return [Artifact(archive, safe_filename(f"{repository}-HEAD.zip"))]
    archive = f"https://github.com/{owner}/{repository}/archive/refs/{ref_kind}/{ref}.zip"
    return [Artifact(archive, safe_filename(f"{repository}-{ref}.zip"))]


def resolve_known_resource(url: str) -> list[Artifact] | None:
    artifacts = KNOWN_RESOURCE_ARTIFACTS.get(url)
    return list(artifacts) if artifacts is not None else None


def resolve_resource(resource: Resource, timeout: float) -> list[Artifact]:
    url = resource.source_url
    known = resolve_known_resource(url)
    if known is not None:
        return known
    geo_url = geo_supplement_url(url)
    if geo_url is not None:
        return crawl_directory(geo_url, timeout)
    figshare = resolve_figshare(url, timeout)
    if figshare is not None:
        return figshare
    zenodo = resolve_zenodo(url, timeout)
    if zenodo is not None:
        return zenodo
    github = resolve_github(url)
    if github is not None:
        return github
    parsed = urlparse(url)
    if parsed.path.endswith("/") and parsed.netloc.lower() in {
        "ftp.cngb.org",
        "ftp.ncbi.nlm.nih.gov",
    }:
        return crawl_directory(url, timeout)
    if Path(parsed.path).suffix.lower() in DIRECT_SUFFIXES:
        return [Artifact(url, url_filename(url))]
    prefix, headers, final_url = request_bytes(url, timeout, limit=512)
    if not is_html(headers, prefix):
        return [Artifact(final_url, url_filename(final_url))]
    raise DiscoveryError("source URL is an HTML/resource-service entry point; resolver required")


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=True, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def path_relative_to_data_root(path: Path, data_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(data_root.resolve()).as_posix()
    except ValueError as exc:
        raise InventoryError(f"output path escapes data root: {path}") from exc


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--cases-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--run-id", default="foreground")
    parser.add_argument("--workers", type=positive_int, default=4)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument(
        "--resource-id",
        action="append",
        default=[],
        help="download only the specified inventory ID; may be repeated",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--discover-only", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_id):
        parser.error("--run-id must be filesystem-safe")
    if args.timeout <= 0 or args.retries < 0 or args.retry_backoff < 0:
        parser.error("timeout must be positive; retries and retry-backoff must be nonnegative")

    cases_root = args.cases_root or args.data_root / Path(*STOMICS_RELATIVE.parts) / "cases"
    output_root = (
        args.output_root
        or args.data_root / Path(*STOMICS_RELATIVE.parts) / "staging/round3_auxiliary_downloads"
    )
    try:
        output_root.resolve(strict=False).relative_to(args.data_root.resolve())
        all_resources = load_resources(cases_root)
        resources = select_resources(all_resources, args.resource_id)
    except (InventoryError, OSError) as exc:
        emit("inventory_invalid", error_type=type(exc).__name__, error=str(exc))
        return 2

    counts: dict[str, int] = defaultdict(int)
    for resource in resources:
        counts[resource.access_classification] += 1
    emit(
        "inventory_validated",
        accepted_case_count=len(FINAL_STDS_IDS),
        deduplicated_resource_count=len(resources),
        total_deduplicated_resource_count=len(all_resources),
        selected_resource_ids=[resource.inventory_id for resource in resources],
        access_classification_counts=dict(sorted(counts.items())),
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return 0

    pending: list[dict[str, str]] = []
    artifacts_by_url: dict[str, Artifact] = {}
    resource_artifact_urls: dict[str, list[str]] = defaultdict(list)
    for resource in resources:
        if not public_download_eligible(resource):
            pending.append(
                {
                    "inventory_id": resource.inventory_id,
                    "access_classification": resource.access_classification,
                    "reason": "automatic download is not authorized by a direct anonymous route",
                }
            )
            continue
        try:
            artifacts = resolve_resource(resource, args.timeout)
        except (DiscoveryError, OSError) as exc:
            pending.append(
                {
                    "inventory_id": resource.inventory_id,
                    "access_classification": resource.access_classification,
                    "reason": str(exc),
                }
            )
            emit(
                "resource_discovery_pending",
                inventory_id=resource.inventory_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            continue
        for artifact in artifacts:
            try:
                validate_public_url(artifact.source_url)
            except InventoryError as exc:
                pending.append(
                    {
                        "inventory_id": resource.inventory_id,
                        "access_classification": resource.access_classification,
                        "reason": str(exc),
                    }
                )
                continue
            artifacts_by_url.setdefault(artifact.source_url, artifact)
            resource_artifact_urls[resource.inventory_id].append(artifact.source_url)
        partial_reason = PARTIAL_KNOWN_RESOURCE_REASONS.get(resource.source_url)
        if partial_reason is not None:
            pending.append(
                {
                    "inventory_id": resource.inventory_id,
                    "access_classification": resource.access_classification,
                    "reason": partial_reason,
                }
            )
            emit(
                "resource_partially_discovered",
                inventory_id=resource.inventory_id,
                artifact_count=len(artifacts),
                pending_reason=partial_reason,
            )
        emit(
            "resource_discovered",
            inventory_id=resource.inventory_id,
            artifact_count=len(artifacts),
        )

    ordered_artifacts = [artifacts_by_url[url] for url in sorted(artifacts_by_url)]
    rows: list[PlanRow] = []
    artifact_records: list[dict[str, Any]] = []
    artifact_id_by_url: dict[str, str] = {}
    for index, artifact in enumerate(ordered_artifacts, 1):
        url_key = hashlib.sha256(artifact.source_url.encode("utf-8")).hexdigest()[:20]
        artifact_id = f"R3FILE_{url_key}"
        artifact_id_by_url[artifact.source_url] = artifact_id
        filename = safe_filename(artifact.suggested_name)
        target = output_root / "objects" / artifact_id / "artifacts" / filename
        relative = path_relative_to_data_root(target, args.data_root)
        rows.append(PlanRow(index + 1, artifact.source_url, relative, target))
        artifact_records.append(
            {
                "artifact_id": artifact_id,
                "source_url": artifact.source_url,
                "target_path": relative,
            }
        )

    run_root = output_root / "runs" / args.run_id
    inventory = {
        "run_id": args.run_id,
        "scope_stds_ids": list(FINAL_STDS_IDS),
        "selected_resource_ids": [resource.inventory_id for resource in resources],
        "resources": [
            {
                **resource.as_dict(),
                "artifact_ids": [
                    artifact_id_by_url[url]
                    for url in sorted(set(resource_artifact_urls[resource.inventory_id]))
                    if url in artifact_id_by_url
                ],
            }
            for resource in resources
        ],
        "artifacts": artifact_records,
        "pending": pending,
    }
    try:
        atomic_write_json(run_root / "inventory.json", inventory)
    except OSError as exc:
        emit("inventory_write_failed", error_type=type(exc).__name__, error=str(exc))
        return 2
    emit(
        "discovery_completed",
        artifact_count=len(rows),
        pending_resource_count=len(pending),
        inventory_path=str(run_root / "inventory.json"),
    )
    if args.discover_only:
        return 3 if pending else 0

    logger = JsonlLogger(sys.stdout)
    config = DownloadConfig(False, args.timeout, args.retries, args.retry_backoff)
    results: list[DownloadResult] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="round3-aux") as executor:
        futures: dict[Future[DownloadResult], PlanRow] = {
            executor.submit(download_row, row, config, logger): row for row in rows
        }
        for future in as_completed(futures):
            row = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures += 1
                logger.emit(
                    "download_failed",
                    level="error",
                    row=row,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
    status_counts: dict[str, int] = defaultdict(int)
    for result in results:
        status_counts[result.status] += 1
    emit(
        "auxiliary_run_completed",
        resource_count=len(resources),
        artifact_count=len(rows),
        completed_artifact_count=len(results),
        download_failure_count=failures,
        pending_resource_count=len(pending),
        status_counts=dict(sorted(status_counts.items())),
        inventory_path=str(run_root / "inventory.json"),
        all_resources_localized=not failures and not pending,
    )
    if failures:
        return 1
    return 3 if pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
