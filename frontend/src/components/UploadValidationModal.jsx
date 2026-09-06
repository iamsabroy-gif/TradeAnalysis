import React from 'react';
import { X, AlertTriangle, CheckCircle2, FileSpreadsheet } from 'lucide-react';

export default function UploadValidationModal({ isOpen, onClose, uploadData }) {
  if (!isOpen || !uploadData) return null;

  const hasErrors = uploadData.errors_count > 0;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '720px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: '#0f172a',
          border: '1px solid var(--border-subtle)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileSpreadsheet size={20} color="var(--color-primary)" />
            <h3 style={{ margin: 0, fontSize: '17px' }}>
              Workbook Upload: {uploadData.filename}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
            <div
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <CheckCircle2 size={20} color="var(--color-success)" />
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Parsed Fields</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-success)' }}>
                  {uploadData.fields_count}
                </div>
              </div>
            </div>

            <div
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: '8px',
                background: hasErrors ? 'rgba(244, 63, 94, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                border: hasErrors ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <AlertTriangle size={20} color={hasErrors ? 'var(--color-danger)' : 'var(--text-muted)'} />
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Validation Errors</div>
                <div
                  style={{
                    fontSize: '18px',
                    fontWeight: 700,
                    color: hasErrors ? 'var(--color-danger)' : 'var(--text-muted)',
                  }}
                >
                  {uploadData.errors_count}
                </div>
              </div>
            </div>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Content SHA-256: <code>{uploadData.content_hash}</code>
          </div>

          {hasErrors && (
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '14px', color: 'var(--color-danger)', marginBottom: '10px' }}>
                Rejected Rows & Validation Issues:
              </h4>
              <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                {uploadData.errors.map((err, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '8px 12px',
                      marginBottom: '6px',
                      borderRadius: '6px',
                      background: 'rgba(244, 63, 94, 0.08)',
                      border: '1px solid rgba(244, 63, 94, 0.2)',
                      fontSize: '12.5px',
                    }}
                  >
                    <span style={{ fontWeight: 600, color: '#fca5a5' }}>
                      {err.field_name || 'Global'}:
                    </span>{' '}
                    <span style={{ color: '#e2e8f0' }}>{err.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {uploadData.fields && uploadData.fields.length > 0 && (
            <div>
              <h4 style={{ fontSize: '14px', color: 'var(--text-primary)', marginBottom: '10px' }}>
                Extracted Fields Preview:
              </h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '8px' }}>Field</th>
                    <th style={{ padding: '8px' }}>Value</th>
                    <th style={{ padding: '8px' }}>Period</th>
                    <th style={{ padding: '8px' }}>Basis</th>
                    <th style={{ padding: '8px' }}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadData.fields.map((f, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px', fontWeight: 600, color: '#e0e7ff' }}>
                        <code>{f.field_name}</code>
                      </td>
                      <td style={{ padding: '8px' }}>{String(f.value)}</td>
                      <td style={{ padding: '8px' }}>{f.period || '—'}</td>
                      <td style={{ padding: '8px' }}>{f.basis}</td>
                      <td style={{ padding: '8px', color: 'var(--color-primary)' }}>{f.confidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
