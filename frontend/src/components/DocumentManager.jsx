import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  RefreshCw,
  Cpu,
  HelpCircle,
  Clock,
  Eye
} from 'lucide-react';

export default function DocumentManager({
  ticker,
  formData,
  setFormData,
  setStatusMsg,
  setError,
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [reviewItems, setReviewItems] = useState([]);
  const [extractionSummary, setExtractionSummary] = useState(null);
  const fileInputRef = useRef(null);

  // Fetch documents and review queue for current ticker
  const refreshDocuments = async () => {
    if (!ticker) return;
    setLoading(true);
    try {
      const cleanTicker = ticker.trim().toUpperCase();
      const res = await fetch(`/api/tickers/${cleanTicker}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }

      // Also check review queue
      const revRes = await fetch(`/api/tickers/${cleanTicker}/review`);
      if (revRes.ok) {
        const revData = await revRes.json();
        setReviewItems(revData.items || []);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshDocuments();
  }, [ticker]);

  // Upload handler
  const handleUploadFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    if (!ticker) {
      setError('Please provide a company ticker symbol first');
      return;
    }

    const cleanTicker = ticker.trim().toUpperCase();
    const uploadForm = new FormData();
    for (let i = 0; i < fileList.length; i++) {
      uploadForm.append('files', fileList[i]);
    }
    uploadForm.append('basis', formData?.data_basis || 'CONSOLIDATED');

    setLoading(true);
    try {
      const res = await fetch(`/api/tickers/${cleanTicker}/documents`, {
        method: 'POST',
        body: uploadForm,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Document upload failed');
      }

      const data = await res.json();
      if (data.errors && data.errors.length > 0) {
        setError(`Upload Warnings: ${data.errors.map((e) => `${e.filename}: ${e.error}`).join('; ')}`);
      } else {
        setStatusMsg(`Successfully uploaded ${data.documents.length} Annual Report document(s) for ${cleanTicker}.`);
      }
      refreshDocuments();
    } catch (err) {
      setError(`PDF Upload Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Drag & drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUploadFiles(e.dataTransfer.files);
    }
  };

  // Update metadata (FY / Basis)
  const handleUpdateMeta = async (docId, newFy, newBasis) => {
    if (!ticker) return;
    try {
      const cleanTicker = ticker.trim().toUpperCase();
      const res = await fetch(`/api/tickers/${cleanTicker}/documents/${docId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fiscal_year: newFy,
          basis: newBasis,
        }),
      });
      if (res.ok) {
        refreshDocuments();
      }
    } catch (err) {
      setError(`Failed to update document metadata: ${err.message}`);
    }
  };

  // Delete document
  const handleDelete = async (docId) => {
    if (!ticker) return;
    try {
      const cleanTicker = ticker.trim().toUpperCase();
      const res = await fetch(`/api/tickers/${cleanTicker}/documents/${docId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setStatusMsg(`Deleted document ${docId}.`);
        refreshDocuments();
      }
    } catch (err) {
      setError(`Failed to delete document: ${err.message}`);
    }
  };

  // Trigger PDF extraction
  const handleExtractFromPdfs = async () => {
    if (!ticker || documents.length === 0) return;
    setExtracting(true);
    setError(null);
    setExtractionSummary(null);

    try {
      const cleanTicker = ticker.trim().toUpperCase();
      const res = await fetch(`/api/tickers/${cleanTicker}/documents/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          basis: formData?.data_basis || 'CONSOLIDATED',
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Extraction failed');
      }

      const data = await res.json();
      setExtractionSummary(data);

      // Merge extracted fields into formData so user immediately sees FCI form populate
      if (data.fields && data.fields.length > 0) {
        setFormData((prev) => {
          const updated = { ...(prev || {}) };
          const prov = { ...(updated.provenance || {}) };

          data.fields.forEach((f) => {
            // Only overwrite if existing field is empty or from lower-confidence source
            updated[f.field_name] = f.value;
            prov[f.field_name] = {
              field_name: f.field_name,
              source: f.source,
              period: f.period,
              basis: f.basis,
              confidence: f.confidence,
              page: f.page,
              document_id: f.document_id,
            };
          });

          updated.provenance = prov;
          return updated;
        });

        setStatusMsg(
          `Extracted ${data.fields_count} field(s) from ${data.documents_count} Annual Report PDF(s) with page citations.`
        );
      } else {
        setStatusMsg('No new fields extracted from uploaded PDFs.');
      }

      // Refresh review queue
      refreshDocuments();
    } catch (err) {
      setError(`PDF Extraction Error: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  // Resolve review queue item
  const handleResolveReview = async (itemId, val) => {
    try {
      const res = await fetch(`/api/review/${itemId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolved_value: val,
          reviewer: 'analyst',
        }),
      });
      if (res.ok) {
        setStatusMsg(`Resolved review item ${itemId}.`);
        refreshDocuments();
      }
    } catch (err) {
      setError(`Failed to resolve review item: ${err.message}`);
    }
  };

  return (
    <div
      style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '12px',
        padding: '18px',
        marginTop: '20px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '14px',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={18} color="var(--color-primary)" />
          <h3 style={{ fontSize: '15px', fontWeight: 600, margin: 0 }}>
            Annual Report PDFs (Phase D Multi-Report Ingestion)
          </h3>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '10px',
              background: 'rgba(99, 102, 241, 0.2)',
              color: '#a5b4fc',
            }}
          >
            {documents.length} Uploaded
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            id="extract-pdfs-btn"
            className="btn btn-primary btn-sm"
            onClick={handleExtractFromPdfs}
            disabled={extracting || documents.length === 0}
            title="Runs Tier 1 Narrative and Tier 2 Table extraction across all uploaded annual reports"
          >
            <Cpu size={14} />
            {extracting ? 'Extracting from PDFs...' : 'Extract from Annual Reports'}
          </button>

          <button
            id="upload-pdf-btn"
            className="btn btn-secondary btn-sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <UploadCloud size={14} /> Add PDF(s)
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleUploadFiles(e.target.files);
              }
            }}
          />
        </div>
      </div>

      {/* Multi-PDF Drag & Drop Zone */}
      <div
        className={`upload-dropzone ${dragActive ? 'dragging' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{ padding: '16px', marginBottom: '14px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
          <UploadCloud size={20} color="var(--color-primary)" />
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Drag & drop one or multiple Annual Report PDFs (e.g. FY24, FY23, FY22), up to 100 MB each.
          </span>
        </div>
      </div>

      {/* Document List Table */}
      {documents.length > 0 && (
        <div style={{ overflowX: 'auto', marginBottom: '14px' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '12px',
              textAlign: 'left',
            }}
          >
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px 6px' }}>Document Name</th>
                <th style={{ padding: '8px 6px' }}>Class</th>
                <th style={{ padding: '8px 6px' }}>Pages</th>
                <th style={{ padding: '8px 6px' }}>Fiscal Year</th>
                <th style={{ padding: '8px 6px' }}>Basis</th>
                <th style={{ padding: '8px 6px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                let badgeColor = '#10b981';
                let badgeBg = 'rgba(16, 185, 129, 0.15)';
                if (doc.pdf_class === 'HYBRID') {
                  badgeColor = '#f59e0b';
                  badgeBg = 'rgba(245, 158, 11, 0.15)';
                } else if (doc.pdf_class === 'SCANNED_IMAGE_ONLY') {
                  badgeColor = '#f43f5e';
                  badgeBg = 'rgba(244, 63, 94, 0.15)';
                }

                return (
                  <tr key={doc.doc_id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '8px 6px', maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span title={doc.filename} style={{ fontWeight: 500 }}>
                        {doc.filename}
                      </span>
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          padding: '2px 6px',
                          borderRadius: '6px',
                          background: badgeBg,
                          color: badgeColor,
                          fontWeight: 600,
                        }}
                      >
                        {doc.pdf_class}
                      </span>
                    </td>
                    <td style={{ padding: '8px 6px' }}>{doc.page_count}</td>
                    <td style={{ padding: '8px 6px' }}>
                      <select
                        value={doc.fiscal_year || ''}
                        onChange={(e) => handleUpdateMeta(doc.doc_id, e.target.value, doc.basis)}
                        style={{ padding: '3px 6px', fontSize: '11px', borderRadius: '6px' }}
                      >
                        <option value="">Auto / Unknown</option>
                        <option value="FY25">FY25</option>
                        <option value="FY24">FY24</option>
                        <option value="FY23">FY23</option>
                        <option value="FY22">FY22</option>
                        <option value="FY21">FY21</option>
                        <option value="FY20">FY20</option>
                      </select>
                    </td>
                    <td style={{ padding: '8px 6px' }}>
                      <select
                        value={doc.basis || 'CONSOLIDATED'}
                        onChange={(e) => handleUpdateMeta(doc.doc_id, doc.fiscal_year, e.target.value)}
                        style={{ padding: '3px 6px', fontSize: '11px', borderRadius: '6px' }}
                      >
                        <option value="CONSOLIDATED">Consolidated</option>
                        <option value="STANDALONE">Standalone</option>
                      </select>
                    </td>
                    <td style={{ padding: '8px 6px', textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '4px 8px', color: 'var(--color-danger)' }}
                        onClick={() => handleDelete(doc.doc_id)}
                        title="Remove document"
                      >
                        <Trash2 size={12} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Extraction Results Preview */}
      {extractionSummary && (
        <div
          style={{
            marginTop: '12px',
            padding: '12px',
            borderRadius: '8px',
            background: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            fontSize: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
            <FileCheck size={16} color="var(--color-primary)" />
            <span style={{ fontWeight: 600 }}>
              Extraction Preview ({extractionSummary.fields_count} fields extracted):
            </span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {extractionSummary.fields.map((f, idx) => (
              <span
                key={idx}
                style={{
                  padding: '4px 8px',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                }}
              >
                <strong>{f.field_name}</strong>: {String(f.value)}
                {f.page && <span style={{ opacity: 0.7, marginLeft: '4px' }}>[p.{f.page}]</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Pending Review Queue Items */}
      {reviewItems.length > 0 && (
        <div
          style={{
            marginTop: '14px',
            padding: '12px',
            borderRadius: '8px',
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            fontSize: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
            <AlertTriangle size={16} color="#f59e0b" />
            <span style={{ fontWeight: 600, color: '#fcd34d' }}>
              Pending Analyst Review ({reviewItems.length} items flagged):
            </span>
          </div>

          {reviewItems.map((item) => (
            <div
              key={item.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 0',
                borderBottom: '1px solid rgba(245, 158, 11, 0.15)',
              }}
            >
              <div>
                <strong>{item.field_name}</strong>: {item.description}
                {item.source_citation && (
                  <span style={{ opacity: 0.8, marginLeft: '6px' }}>({item.source_citation})</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                {item.candidates &&
                  item.candidates.map((cand, cIdx) => (
                    <button
                      key={cIdx}
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '3px 8px', fontSize: '11px' }}
                      onClick={() => handleResolveReview(item.id, cand.value)}
                    >
                      Accept {String(cand.value)}
                    </button>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
