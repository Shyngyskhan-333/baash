import unittest

from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.evidence.packet_service import EvidencePacketService
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.canonical_service import CanonicalSearchService


def _bundle(doc_id: str, title: str, paragraph: str):
    html = f"""
    <html>
      <head><title>{title}</title></head>
      <body>
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. {paragraph}</p>
        </section>
      </body>
    </html>
    """
    fetched = FetchedSourceContent(
        source_id="adilet",
        url=f"https://adilet.zan.kz/rus/docs/{doc_id}",
        content=html,
        raw_content_uri=f"data/raw/{doc_id}.html",
    )
    return EvidenceIngestionService().ingest_fetched(fetched)


class CanonicalSearchServiceTests(unittest.TestCase):
    def test_search_returns_evidence_packet_compatible_results(self):
        repository = InMemoryEvidenceRepository()
        bundle = _bundle("K000000024", "Canonical Search Law", "Банк обязан хранить документы.")
        repository.add_ingestion_bundle(bundle)

        response = CanonicalSearchService.from_repository(repository).search("банк документы")

        self.assertEqual(len(response["results"]), 1)
        result = response["results"][0]
        self.assertEqual(result["doc_id"], "K000000024")
        self.assertEqual(result["citation_id"], bundle.citations[0].id)
        self.assertEqual(result["document_version_id"], bundle.version.id)
        self.assertEqual(result["source_snapshot_id"], bundle.snapshot.id)

        packet_bundle = EvidencePacketService().build_from_search_results(
            title="Packet",
            purpose="canonical search test",
            results=response["results"],
        )
        self.assertEqual(packet_bundle.packet.citation_ids, (bundle.citations[0].id,))

    def test_search_supports_document_filtering(self):
        repository = InMemoryEvidenceRepository()
        first = _bundle("K000000025", "First Law", "Банк хранит документы.")
        second = _bundle("K000000026", "Second Law", "Банк хранит документы.")
        repository.add_ingestion_bundle(first)
        repository.add_ingestion_bundle(second)

        response = CanonicalSearchService.from_repository(repository).search(
            "банк документы",
            doc_ids=[second.document.id],
        )

        self.assertEqual([result["document_id"] for result in response["results"]], [second.document.id])

    def test_search_returns_empty_results_when_no_chunks_match(self):
        repository = InMemoryEvidenceRepository()
        repository.add_ingestion_bundle(_bundle("K000000027", "No Match Law", "Банк хранит документы."))

        response = CanonicalSearchService.from_repository(repository).search("энергетика", top_k=5)

        self.assertEqual(response, {"results": []})


if __name__ == "__main__":
    unittest.main()
