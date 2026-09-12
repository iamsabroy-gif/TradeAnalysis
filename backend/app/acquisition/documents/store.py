"""
Document store for Phase 1 Gatekeeper Annual Report PDFs.
Stores raw PDF bytes and JSON metadata sidecars under var/documents/{ticker}/.
Maps to implementpdf.md Stage 1 and Phase1-WebApp-Implementation-Plan.md §2.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from backend.app.acquisition.types import SourceDocument
from backend.app.models.enums import PdfClass, ReportingBasis


class DocumentStore:
    """File-backed local document store under var/documents/."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent / "var" / "documents"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _ticker_dir(self, ticker: str) -> Path:
        clean = ticker.strip().upper()
        tdir = self.base_dir / clean
        tdir.mkdir(parents=True, exist_ok=True)
        return tdir

    def _doc_to_dict(self, doc: SourceDocument) -> dict:
        return {
            "doc_id": doc.doc_id,
            "ticker": doc.ticker,
            "filename": doc.filename,
            "fiscal_year": doc.fiscal_year,
            "basis": doc.basis.value if isinstance(doc.basis, ReportingBasis) else doc.basis,
            "pdf_class": doc.pdf_class.value if isinstance(doc.pdf_class, PdfClass) else doc.pdf_class,
            "page_count": doc.page_count,
            "stored_path": doc.stored_path,
            "uploaded_at": doc.uploaded_at,
            "uploader": doc.uploader,
        }

    def _dict_to_doc(self, data: dict) -> SourceDocument:
        return SourceDocument(
            doc_id=data["doc_id"],
            ticker=data["ticker"],
            filename=data["filename"],
            fiscal_year=data.get("fiscal_year"),
            basis=ReportingBasis(data["basis"]) if "basis" in data else ReportingBasis.CONSOLIDATED,
            pdf_class=PdfClass(data["pdf_class"]) if "pdf_class" in data else PdfClass.NATIVE_TEXT,
            page_count=data.get("page_count", 0),
            stored_path=data.get("stored_path", ""),
            uploaded_at=data.get("uploaded_at", ""),
            uploader=data.get("uploader"),
        )

    def save(self, doc: SourceDocument, content_bytes: bytes) -> SourceDocument:
        tdir = self._ticker_dir(doc.ticker)
        pdf_path = tdir / f"{doc.doc_id}.pdf"
        meta_path = tdir / f"{doc.doc_id}.json"

        # Content-hash deduplication: write bytes if not already existing
        if not pdf_path.exists():
            with open(pdf_path, "wb") as f:
                f.write(content_bytes)

        # Update stored_path
        updated_doc = SourceDocument(
            doc_id=doc.doc_id,
            ticker=doc.ticker,
            filename=doc.filename,
            fiscal_year=doc.fiscal_year,
            basis=doc.basis,
            pdf_class=doc.pdf_class,
            page_count=doc.page_count,
            stored_path=str(pdf_path),
            uploaded_at=doc.uploaded_at,
            uploader=doc.uploader,
        )

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self._doc_to_dict(updated_doc), f, indent=2)

        return updated_doc

    def get(self, ticker: str, doc_id: str) -> Optional[SourceDocument]:
        tdir = self._ticker_dir(ticker)
        meta_path = tdir / f"{doc_id}.json"
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_doc(data)
        except Exception:
            return None

    def get_content(self, ticker: str, doc_id: str) -> Optional[bytes]:
        tdir = self._ticker_dir(ticker)
        pdf_path = tdir / f"{doc_id}.pdf"
        if not pdf_path.exists():
            return None
        with open(pdf_path, "rb") as f:
            return f.read()

    def list_for_ticker(self, ticker: str) -> List[SourceDocument]:
        tdir = self._ticker_dir(ticker)
        docs = []
        for meta_path in sorted(tdir.glob("*.json")):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                docs.append(self._dict_to_doc(data))
            except Exception:
                continue
        return docs

    def update(
        self,
        ticker: str,
        doc_id: str,
        fiscal_year: Optional[str] = None,
        basis: Optional[ReportingBasis] = None,
    ) -> Optional[SourceDocument]:
        doc = self.get(ticker, doc_id)
        if not doc:
            return None
        updated_doc = SourceDocument(
            doc_id=doc.doc_id,
            ticker=doc.ticker,
            filename=doc.filename,
            fiscal_year=fiscal_year if fiscal_year is not None else doc.fiscal_year,
            basis=basis if basis is not None else doc.basis,
            pdf_class=doc.pdf_class,
            page_count=doc.page_count,
            stored_path=doc.stored_path,
            uploaded_at=doc.uploaded_at,
            uploader=doc.uploader,
        )
        tdir = self._ticker_dir(ticker)
        meta_path = tdir / f"{doc_id}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self._doc_to_dict(updated_doc), f, indent=2)
        return updated_doc

    def delete(self, ticker: str, doc_id: str) -> bool:
        tdir = self._ticker_dir(ticker)
        pdf_path = tdir / f"{doc_id}.pdf"
        meta_path = tdir / f"{doc_id}.json"
        deleted = False
        if pdf_path.exists():
            pdf_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True
        return deleted

    def delete_all_for_ticker(self, ticker: str) -> int:
        """Removes every stored document (PDF + metadata sidecar) for a ticker. Returns the count deleted."""
        tdir = self._ticker_dir(ticker)
        count = 0
        for path in tdir.glob("*"):
            if path.is_file():
                path.unlink()
                count += 1
        return count // 2  # each document is a (pdf, json) pair


# Global instance
document_store = DocumentStore()
