import React, { useState, useEffect } from 'react';
import {
  X,
  Sliders,
  Download,
  UploadCloud,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Search,
  Layers,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  FileSpreadsheet,
  Info
} from 'lucide-react';

export default function RulesConfigModal({ isOpen, onClose, onConfigChanged }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('phase1');
  const [uploading, setUploading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Keyword test tool state
  const [testKeyword, setTestKeyword] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testingKeyword, setTestingKeyword] = useState(false);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/rules/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (err) {
      console.error('Failed to fetch rules config:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchConfig();
      setNotification(null);
      setTestResult(null);
    }
  }, [isOpen]);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setNotification(null);
    try {
      const res = await fetch('/api/rules/config/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.status === 'SUCCESS') {
        setNotification({
          type: 'success',
          message: `Successfully loaded custom rules from ${data.file_name}! (Phase 1: ${data.loaded_counts?.phase1_rules_count || 10} thresholds, Phase 2: ${data.loaded_counts?.phase2_sectors_count || 4} sectors, Mappings: ${data.loaded_counts?.sector_keywords_count || 0} keywords)`,
        });
        await fetchConfig();
        if (onConfigChanged) onConfigChanged();
      } else {
        setNotification({
          type: 'error',
          message: data.detail || 'Failed to parse uploaded rules workbook.',
        });
      }
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Upload request failed: ' + err.message,
      });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all rules thresholds, boundary matrices, and sector mappings to standard baseline defaults?')) {
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/rules/config/reset', { method: 'POST' });
      if (res.ok) {
        setNotification({
          type: 'success',
          message: 'Rules successfully reset to standard baseline defaults.',
        });
        await fetchConfig();
        if (onConfigChanged) onConfigChanged();
      }
    } catch (err) {
      setNotification({
        type: 'error',
        message: 'Failed to reset rules: ' + err.message,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestKeyword = async (e) => {
    e?.preventDefault();
    if (!testKeyword.trim()) return;
    setTestingKeyword(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/rules/resolve-sector', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: testKeyword.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        setTestResult(data);
      }
    } catch (err) {
      console.error('Keyword test error:', err);
    } finally {
      setTestingKeyword(false);
    }
  };

  if (!isOpen) return null;

  const filteredMappings = config?.sector_mappings?.filter((m) => {
    const q = searchTerm.toLowerCase();
    return (
      m.keyword.toLowerCase().includes(q) ||
      m.sector.toLowerCase().includes(q) ||
      (m.notes && m.notes.toLowerCase().includes(q))
    );
  }) || [];

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
          maxWidth: '1040px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: '#0f172a',
          border: '1px solid var(--border-subtle)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(15, 23, 42, 0.95)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                padding: '10px',
                borderRadius: '10px',
                display: 'flex',
              }}
            >
              <Sliders size={22} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>
                  Rule Engine Configuration
                </h3>
                {config && (
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '3px 8px',
                      borderRadius: '12px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      backgroundColor:
                        config.source === 'DEFAULT'
                          ? 'rgba(59, 130, 246, 0.15)'
                          : 'rgba(16, 185, 129, 0.2)',
                      color: config.source === 'DEFAULT' ? '#60a5fa' : '#34d399',
                      border: `1px solid ${
                        config.source === 'DEFAULT'
                          ? 'rgba(59, 130, 246, 0.3)'
                          : 'rgba(16, 185, 129, 0.4)'
                      }`,
                    }}
                  >
                    {config.source === 'DEFAULT' ? 'Built-in Baseline' : 'Custom Excel Config'}
                  </span>
                )}
              </div>
              <p style={{ margin: '4px 0 0', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                Decoupled Triple-Input Model: [Stock Data] + [Rules Config] + [Sector Mapping] → Engine → [Verdict]
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Action Toolbar */}
        <div
          style={{
            padding: '14px 24px',
            backgroundColor: 'rgba(30, 41, 59, 0.4)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <a
              id="download-rules-config-btn"
              href="/api/rules/config/download"
              download="Rules_Config.xlsx"
              className="btn btn-secondary btn-sm"
              title="Download editable 3-sheet Excel workbook (Phase1_Thresholds, Phase2_Matrix, Sector_Mapping)"
            >
              <Download size={15} /> Download Rules_Config.xlsx
            </a>

            <label
              htmlFor="upload-rules-config-input"
              className={`btn btn-primary btn-sm ${uploading ? 'opacity-50' : ''}`}
              style={{ cursor: uploading ? 'wait' : 'pointer' }}
              title="Upload modified Rules_Config.xlsx to dynamically alter engine thresholds"
            >
              <UploadCloud size={15} /> {uploading ? 'Parsing...' : 'Upload Custom Config'}
              <input
                id="upload-rules-config-input"
                type="file"
                accept=".xlsx"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
                disabled={uploading}
              />
            </label>

            {config?.source !== 'DEFAULT' && (
              <button
                id="reset-rules-config-btn"
                onClick={handleReset}
                className="btn btn-secondary btn-sm"
                title="Reset active configuration to baseline defaults"
                style={{ color: 'var(--color-danger)' }}
              >
                <RotateCcw size={14} /> Reset Defaults
              </button>
            )}
          </div>

          {/* Quick Stats Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <span>Version: <strong style={{ color: 'var(--text-primary)' }}>{config?.version || '1.0.0'}</strong></span>
            <span>•</span>
            <span>Last Updated: <strong style={{ color: 'var(--text-primary)' }}>{config?.updated_at ? new Date(config.updated_at).toLocaleTimeString() : 'Baseline'}</strong></span>
          </div>
        </div>

        {/* Notifications / Feedback */}
        {notification && (
          <div
            style={{
              padding: '12px 24px',
              backgroundColor:
                notification.type === 'success'
                  ? 'rgba(16, 185, 129, 0.15)'
                  : 'rgba(239, 68, 68, 0.15)',
              borderBottom: '1px solid var(--border-subtle)',
              color: notification.type === 'success' ? '#34d399' : '#f87171',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            {notification.type === 'success' ? (
              <CheckCircle2 size={16} />
            ) : (
              <AlertTriangle size={16} />
            )}
            <span>{notification.message}</span>
          </div>
        )}

        {/* Keyword Resolver Tester Bar */}
        <div
          style={{
            padding: '12px 24px',
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
            ⚡ Keyword Resolver Test:
          </span>
          <form
            onSubmit={handleTestKeyword}
            style={{ display: 'flex', gap: '8px', flex: 1, maxWidth: '440px' }}
          >
            <input
              type="text"
              placeholder="e.g. SaaS software, Auto components, Mining, EPC..."
              value={testKeyword}
              onChange={(e) => setTestKeyword(e.target.value)}
              className="input-field"
              style={{
                fontSize: '12.5px',
                padding: '6px 12px',
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                color: '#fff',
                width: '100%',
              }}
            />
            <button
              type="submit"
              disabled={testingKeyword || !testKeyword.trim()}
              className="btn btn-secondary btn-sm"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              Resolve
            </button>
          </form>

          {testResult && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                padding: '4px 10px',
                borderRadius: '8px',
                color: '#a5b4fc',
              }}
            >
              <span>Sector: <strong style={{ color: '#fff' }}>{testResult.resolved_sector}</strong></span>
              <span>•</span>
              <span style={{ fontStyle: 'italic', opacity: 0.85 }}>{testResult.reason}</span>
            </div>
          )}
        </div>

        {/* Modal Navigation Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(15, 23, 42, 0.95)',
            padding: '0 24px',
          }}
        >
          <button
            className={`tab-btn ${activeTab === 'phase1' ? 'active' : ''}`}
            onClick={() => setActiveTab('phase1')}
            style={{ padding: '12px 16px', fontSize: '13.5px' }}
          >
            Phase 1 Thresholds (Forensic Safety)
          </button>
          <button
            className={`tab-btn ${activeTab === 'phase2' ? 'active' : ''}`}
            onClick={() => setActiveTab('phase2')}
            style={{ padding: '12px 16px', fontSize: '13.5px' }}
          >
            Phase 2 Boundary Matrix (Quality & Capital)
          </button>
          <button
            className={`tab-btn ${activeTab === 'mappings' ? 'active' : ''}`}
            onClick={() => setActiveTab('mappings')}
            style={{ padding: '12px 16px', fontSize: '13.5px' }}
          >
            Sector Keyword Mappings ({config?.sector_mappings?.length || 0})
          </button>
        </div>

        {/* Modal Body Content */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '50px', color: 'var(--text-secondary)' }}>
              Loading active configuration...
            </div>
          ) : (
            <>
              {/* TAB 1: PHASE 1 THRESHOLDS */}
              {activeTab === 'phase1' && (
                <div>
                  <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
                      Sheet: <code>Phase1_Thresholds</code>. Decouples strict forensic ceilings and failure triggers for Checks 1–6.
                    </p>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      All percentages expressed as whole numbers (e.g. 10.0 = 10%)
                    </span>
                  </div>

                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                        <th style={{ padding: '10px 12px' }}>Parameter Name</th>
                        <th style={{ padding: '10px 12px' }}>Check ID</th>
                        <th style={{ padding: '10px 12px' }}>Active Threshold</th>
                        <th style={{ padding: '10px 12px' }}>Rule Impact</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Promoter Pledge Fail Ceiling</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 3</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#f87171', fontWeight: 700 }}>
                            {config?.phase1?.promoter_pledge_fail_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Triggers immediate FAIL if promoter pledged shares exceed this threshold
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Low Holding Promoter Pledge Floor</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 3</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#fbbf24', fontWeight: 700 }}>
                            {config?.phase1?.promoter_pledge_low_holding_fail_pct}% (when holding &lt; {config?.phase1?.promoter_pledge_low_holding_floor_pct}%)
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Stricter fail threshold for low-promoter-holding firms
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Pledged % of Total Shares Cap</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 3</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#f87171', fontWeight: 700 }}>
                            {config?.phase1?.promoter_pledge_total_shares_fail_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Direct company-wide total share pledge limit
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>RPT Sales + Purchases Ceiling</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 4</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#f87171', fontWeight: 700 }}>
                            {config?.phase1?.rpt_sales_purchases_fail_pct}% of Revenue
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Related Party Transactions exceeding this ratio trigger forensic FAIL
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Contingent Liabilities / Net Worth</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 4</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#f87171', fontWeight: 700 }}>
                            {config?.phase1?.contingent_liabilities_net_worth_fail_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Overall contingent liabilities exposure cap vs net worth
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Litigation Claims / Net Worth</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 4</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#f87171', fontWeight: 700 }}>
                            {config?.phase1?.litigation_claims_net_worth_fail_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Direct legal claim exposure cap (§8.4-F sub-check limit)
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>CFO / PAT Ratio Floor</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 5</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#34d399', fontWeight: 700 }}>
                            {(config?.phase1?.cfo_pat_ratio_fail_floor * 100).toFixed(0)}% ({config?.phase1?.cfo_pat_ratio_fail_floor}x)
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Minimum 5-year operating cash conversion floor vs net profit
                        </td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Legal Fee Surge Ceiling</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 2</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#fbbf24', fontWeight: 700 }}>
                            {config?.phase1?.legal_fee_surge_fail_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Year-on-year legal fee surge threshold requiring explicit explanation
                        </td>
                      </tr>
                      <tr>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>Legal to Audit Fee Ratio</td>
                        <td style={{ padding: '10px 12px' }}><span className="badge badge-neutral">Check 2</span></td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: '#fbbf24', fontWeight: 700 }}>
                            {config?.phase1?.legal_to_audit_fee_multiplier}x
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                          Threshold for legal expense surge relative to statutory audit fee
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}

              {/* TAB 2: PHASE 2 BOUNDARY MATRIX */}
              {activeTab === 'phase2' && (
                <div>
                  <div style={{ marginBottom: '16px' }}>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
                      Sheet: <code>Phase2_Matrix</code>. Sector-calibrated boundaries for Return on Capital (Check 7), Leverage (Check 8), and Cash Conversion (Check 9).
                    </p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
                    {config?.phase2_matrix &&
                      Object.entries(config.phase2_matrix).map(([secKey, secCfg]) => (
                        <div
                          key={secKey}
                          style={{
                            backgroundColor: 'rgba(30, 41, 59, 0.5)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '12px',
                            padding: '16px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                            <h4 style={{ margin: 0, fontSize: '14.5px', color: '#60a5fa' }}>{secKey}</h4>
                            <span style={{ fontSize: '10px', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                              Profile
                            </span>
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
                            <div>
                              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Check 7: RoCE (%)</div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
                                <span style={{ color: '#34d399' }}>Pass: ≥{secCfg.roce_pass_floor}%</span>
                                <span style={{ color: '#f87171' }}>Fail: &lt;{secCfg.roce_fail_ceiling}%</span>
                              </div>
                            </div>

                            <div>
                              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Check 8: Net Debt / EBITDA</div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
                                <span style={{ color: '#34d399' }}>Pass: ≤{secCfg.net_debt_ebitda_pass_ceiling}x</span>
                                <span style={{ color: '#f87171' }}>Fail: &gt;{secCfg.net_debt_ebitda_fail_floor}x</span>
                              </div>
                            </div>

                            <div>
                              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Check 8: Interest Coverage</div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px' }}>
                                <span style={{ color: '#34d399' }}>Pass: ≥{secCfg.interest_coverage_pass_floor}x</span>
                                <span style={{ color: '#f87171' }}>Fail: &lt;{secCfg.interest_coverage_fail_ceiling}x</span>
                              </div>
                            </div>

                            <div>
                              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Check 8: Max Short-Term Debt</div>
                              <div style={{ color: '#fbbf24', marginTop: '2px' }}>
                                Concern if &gt;{secCfg.max_st_debt_concern_pct}%
                              </div>
                            </div>

                            <div>
                              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Check 9: Working Capital Limits</div>
                              <div style={{ marginTop: '2px', color: 'var(--text-primary)' }}>
                                CCC Surge: &gt;{secCfg.ccc_deterioration_fail_days}d | Recv: &gt;{secCfg.max_receivable_days_critical_cap}d
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* TAB 3: SECTOR KEYWORD MAPPINGS */}
              {activeTab === 'mappings' && (
                <div>
                  <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
                      Sheet: <code>Sector_Mapping</code>. Automatically resolves company business descriptions and industry tags to target Sector Profiles.
                    </p>
                    <div style={{ position: 'relative', width: '260px' }}>
                      <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
                      <input
                        type="text"
                        placeholder="Search keywords..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '6px 10px 6px 30px',
                          fontSize: '12.5px',
                          background: 'rgba(30, 41, 59, 0.6)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '8px',
                          color: '#fff',
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ maxHeight: '420px', overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px', textAlign: 'left' }}>
                      <thead>
                        <tr style={{ borderBottom: '2px solid var(--border-subtle)', backgroundColor: 'rgba(15, 23, 42, 0.95)', color: 'var(--text-secondary)', position: 'sticky', top: 0 }}>
                          <th style={{ padding: '10px 12px' }}>Keyword / Pattern</th>
                          <th style={{ padding: '10px 12px' }}>Target Sector Profile</th>
                          <th style={{ padding: '10px 12px' }}>Notes & Classification Context</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredMappings.map((m, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {m.keyword}
                            </td>
                            <td style={{ padding: '8px 12px' }}>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '3px 8px',
                                  borderRadius: '6px',
                                  fontWeight: 600,
                                  backgroundColor:
                                    m.sector === 'ASSET_LIGHT'
                                      ? 'rgba(16, 185, 129, 0.15)'
                                      : m.sector === 'STANDARD'
                                      ? 'rgba(59, 130, 246, 0.15)'
                                      : m.sector === 'CAP_INTENSIVE'
                                      ? 'rgba(245, 158, 11, 0.15)'
                                      : 'rgba(168, 85, 247, 0.15)',
                                  color:
                                    m.sector === 'ASSET_LIGHT'
                                      ? '#34d399'
                                      : m.sector === 'STANDARD'
                                      ? '#60a5fa'
                                      : m.sector === 'CAP_INTENSIVE'
                                      ? '#fbbf24'
                                      : '#c084fc',
                                }}
                              >
                                {m.sector}
                              </span>
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                              {m.notes || '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
