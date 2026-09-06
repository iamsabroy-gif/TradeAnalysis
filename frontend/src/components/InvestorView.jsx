import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Printer, ExternalLink, ShieldAlert } from 'lucide-react';

export default function InvestorView({ report, resultId }) {
  if (!report) return null;

  const getStatusIcon = (badge) => {
    switch (badge) {
      case 'success':
        return <CheckCircle2 size={18} color="#10b981" />;
      case 'danger':
        return <XCircle size={18} color="#f43f5e" />;
      default:
        return <AlertTriangle size={18} color="#f59e0b" />;
    }
  };

  const handlePrint = () => {
    window.open(`/api/reports/${resultId}/html`, '_blank');
  };

  return (
    <div className="investor-view" id="investor-report-view">
      {/* Top Banner */}
      <div className={`glass-panel banner-box banner-${report.badge_color}`} style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <span className={`badge badge-${report.badge_color}`} id="verdict-badge">
                {report.badge_label}
              </span>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Revision #{report.revision}
              </span>
              {report.supersedes && (
                <span style={{ fontSize: '12px', color: 'var(--color-warning)', background: 'rgba(245,158,11,0.1)', padding: '2px 8px', borderRadius: '4px' }}>
                  Replaces previous evaluation
                </span>
              )}
            </div>
            <h2 style={{ fontSize: '24px', marginBottom: '8px', color: 'var(--text-primary)' }}>
              {report.headline}
            </h2>
            <p style={{ fontSize: '15px', color: '#cbd5e1', maxWidth: '850px' }}>
              {report.lead_story}
            </p>
          </div>
          <button
            id="print-pdf-button"
            className="btn btn-secondary btn-sm"
            onClick={handlePrint}
            title="Open printable HTML and PDF export"
          >
            <Printer size={15} /> Export / Print Report
          </button>
        </div>

        {/* Metadata tag bar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)', fontSize: '13px', color: 'var(--text-secondary)' }}>
          <div><strong>Ticker:</strong> <span style={{ color: '#fff' }}>{report.ticker}</span></div>
          <div><strong>As of Date:</strong> {report.as_of_date}</div>
          <div><strong>Financial Basis:</strong> {report.data_basis_label}</div>
          <div><strong>Evaluated:</strong> {new Date(report.generated_at).toLocaleString()}</div>
        </div>
      </div>

      {/* Sourcing warning if citation gaps exist */}
      {report.citation_gaps && report.citation_gaps.length > 0 && (
        <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '24px', borderColor: 'var(--color-warning-border)', background: 'rgba(245,158,11,0.08)' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <ShieldAlert size={22} color="var(--color-warning)" />
            <div>
              <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-warning)' }}>
                Sourcing Transparency Notice (Rule §7)
              </div>
              <div style={{ fontSize: '13px', color: '#e2e8f0', marginTop: '2px' }}>
                The evaluation used these fields, but their original filing sources were not fully recorded:
                <code style={{ marginLeft: '6px', color: '#fef08a' }}>{report.citation_gaps.join(', ')}</code>.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Checks Grid */}
      <h3 style={{ fontSize: '18px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        The Six Honesty Checks Explained Simply
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {report.checks.map((check) => (
          <div key={check.check_id} className="glass-panel check-item" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {getStatusIcon(check.status_badge)}
                <h4 style={{ fontSize: '16px', margin: 0 }}>{check.title}</h4>
              </div>
              <span className={`badge badge-${check.status_badge}`}>
                {check.status_label}
              </span>
            </div>

            {/* Everyday Analogy */}
            <div style={{ fontSize: '13.5px', fontStyle: 'italic', color: 'var(--text-secondary)', marginBottom: '12px', paddingLeft: '12px', borderLeft: '3px solid var(--border-subtle)' }}>
              💡 {check.analogy}
            </div>

            {/* Technical finding translated */}
            <div style={{ fontSize: '14px', color: '#e2e8f0', marginBottom: '10px' }}>
              <strong>What we found:</strong> {check.finding}
            </div>

            {check.missing_data && (
              <div style={{ fontSize: '13.5px', color: 'var(--color-warning)', marginBottom: '8px', background: 'rgba(245,158,11,0.1)', padding: '6px 10px', borderRadius: '6px' }}>
                ⚠️ <strong>Missing Information:</strong> {check.missing_data}
              </div>
            )}

            {/* "So what does this mean for me?" card */}
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '10px 14px', marginTop: '10px', fontSize: '13.5px', color: '#f1f5f9' }}>
              <strong>What this means for you:</strong> {check.so_what}
            </div>

            {/* Source citation */}
            {check.citation && (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>
                <strong>Source:</strong> {check.citation}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Mandatory SEBI Disclaimer */}
      <div style={{ marginTop: '40px', padding: '20px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center', fontSize: '12.5px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
        {report.sebi_disclaimer}
      </div>
    </div>
  );
}
