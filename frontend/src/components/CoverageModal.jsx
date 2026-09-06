import React, { useEffect, useState } from 'react';
import { X, Layers } from 'lucide-react';

export default function CoverageModal({ isOpen, onClose }) {
  const [coverageData, setCoverageData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      fetch('/api/coverage')
        .then((res) => res.json())
        .then((data) => {
          setCoverageData(data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

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
          maxWidth: '960px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: '#0f172a',
          border: '1px solid var(--border-subtle)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers size={20} color="var(--color-primary)" />
            <h3 style={{ margin: 0, fontSize: '18px' }}>
              Phase 1 Field Coverage Matrix (§3)
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

        {/* Modal Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto' }}>
          <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            This matrix is the contract between data acquisition (scrapers/PDF extractors) and the Decision Engine.
            Every field of <code>CompanyInput</code> appears here with a declared owner and confidence floor.
          </p>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading matrix...</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px 8px' }}>Field</th>
                  <th style={{ padding: '10px 8px' }}>Check</th>
                  <th style={{ padding: '10px 8px' }}>Assigned Source</th>
                  <th style={{ padding: '10px 8px' }}>Owner (Phase)</th>
                  <th style={{ padding: '10px 8px' }}>Basis Required</th>
                  <th style={{ padding: '10px 8px' }}>Floor</th>
                </tr>
              </thead>
              <tbody>
                {coverageData &&
                  Object.entries(coverageData.matrix).map(([field, meta]) => (
                    <tr key={field} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '10px 8px', fontWeight: 600, color: '#e0e7ff' }}>
                        <code>{field}</code>
                      </td>
                      <td style={{ padding: '10px 8px' }}>{meta.check ? `Check ${meta.check}` : 'Structural'}</td>
                      <td style={{ padding: '10px 8px', color: '#cbd5e1' }}>{meta.source}</td>
                      <td style={{ padding: '10px 8px', color: '#a5b4fc' }}>{meta.owner}</td>
                      <td style={{ padding: '10px 8px' }}>{meta.basis_required ? 'Yes' : 'No'}</td>
                      <td style={{ padding: '10px 8px' }}>
                        <span style={{ fontWeight: 600, color: meta.confidence_floor === 'HIGH' ? 'var(--color-success)' : 'var(--color-warning)' }}>
                          {meta.confidence_floor}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
