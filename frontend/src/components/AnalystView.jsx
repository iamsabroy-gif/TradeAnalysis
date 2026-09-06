import React, { useState } from 'react';
import { Database, FileCode, CheckCircle2, XCircle, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';

export default function AnalystView({ analystReport, rawResult }) {
  const [activeTab, setActiveTab] = useState('table');

  if (!analystReport) return null;

  return (
    <div className="analyst-view" id="analyst-report-view">
      {/* Analyst Header & Digest */}
      <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 style={{ fontSize: '18px', margin: 0, color: 'var(--text-primary)' }}>
              Analyst Deep-Dive: {analystReport.ticker} (Revision {analystReport.revision})
            </h3>
            <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Input Digest: <code style={{ color: '#818cf8' }}>{analystReport.input_digest}</code> | Result ID: <code style={{ color: '#818cf8' }}>{analystReport.result_id}</code>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className={`btn btn-sm ${activeTab === 'table' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('table')}
            >
              Working Table
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'provenance' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('provenance')}
            >
              <Database size={14} /> Provenance ({analystReport.provenance_items.length})
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'json' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('json')}
            >
              <FileCode size={14} /> Raw JSON
            </button>
          </div>
        </div>
      </div>

      {/* Tab 1: Technical Working Table */}
      {activeTab === 'table' && (
        <div className="glass-panel" style={{ overflowX: 'auto', padding: '16px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '12px 10px', width: '40px' }}>#</th>
                <th style={{ padding: '12px 10px', width: '180px' }}>Check Name</th>
                <th style={{ padding: '12px 10px', width: '90px' }}>Status</th>
                <th style={{ padding: '12px 10px', width: '220px' }}>Finding / Value</th>
                <th style={{ padding: '12px 10px', width: '200px' }}>Threshold Limit</th>
                <th style={{ padding: '12px 10px' }}>Citation & Provenance</th>
              </tr>
            </thead>
            <tbody>
              {analystReport.rows.map((r) => {
                const isPass = r.status === 'PASS';
                const isFail = r.status === 'FAIL';
                return (
                  <tr key={r.check_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 600 }}>{r.check_id}</td>
                    <td style={{ padding: '12px 10px', fontWeight: 500 }}>
                      {r.name}
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{r.reason_code}</div>
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      <span className={`badge badge-${isPass ? 'success' : isFail ? 'danger' : 'warning'}`} style={{ fontSize: '11px', padding: '2px 8px' }}>
                        {r.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 10px', color: isFail ? 'var(--color-danger)' : '#e2e8f0' }}>
                      {r.finding}
                      {r.missing_data && (
                        <div style={{ color: 'var(--color-warning)', fontSize: '11.5px', marginTop: '4px' }}>
                          Missing: {r.missing_data}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 10px', color: 'var(--text-secondary)', fontSize: '12px' }}>
                      {r.threshold}
                    </td>
                    <td style={{ padding: '12px 10px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                      {r.citation}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Provenance Map Explorer */}
      {activeTab === 'provenance' && (
        <div className="glass-panel" style={{ overflowX: 'auto', padding: '16px' }}>
          <div style={{ marginBottom: '12px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            Every scalar fed to the Decision Engine carries audit provenance per <code>Phase1-Algorithms.md §0</code>.
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '10px' }}>Field Name</th>
                <th style={{ padding: '10px' }}>Source Document</th>
                <th style={{ padding: '10px' }}>Period</th>
                <th style={{ padding: '10px' }}>Reporting Basis</th>
                <th style={{ padding: '10px' }}>Page</th>
                <th style={{ padding: '10px' }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {analystReport.provenance_items.map((p) => (
                <tr key={p.field_name} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px', fontWeight: 600, color: '#e0e7ff' }}><code>{p.field_name}</code></td>
                  <td style={{ padding: '10px', color: '#cbd5e1' }}>{p.source}</td>
                  <td style={{ padding: '10px' }}>{p.period}</td>
                  <td style={{ padding: '10px' }}>
                    <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                      {p.basis}
                    </span>
                  </td>
                  <td style={{ padding: '10px' }}>{p.page ?? '—'}</td>
                  <td style={{ padding: '10px' }}>
                    <span style={{ fontWeight: 600, color: p.confidence === 'HIGH' ? 'var(--color-success)' : p.confidence === 'MEDIUM' ? 'var(--color-warning)' : '#818cf8' }}>
                      {p.confidence}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 3: Raw JSON Payload */}
      {activeTab === 'json' && (
        <div className="glass-panel" style={{ padding: '16px' }}>
          <pre style={{ maxHeight: '500px', overflowY: 'auto', background: '#020617', padding: '16px', borderRadius: '8px', fontSize: '12px', color: '#a5b4fc' }}>
            {JSON.stringify(rawResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
