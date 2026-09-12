import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  Play,
  RotateCcw,
  Layers,
  Sparkles,
  AlertCircle,
  FileText,
  Globe,
  UploadCloud,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  HelpCircle,
  Database,
  Trash2,
  TrendingUp,
  ArrowRight,
  Sliders
} from 'lucide-react';
import InvestorView from './components/InvestorView.jsx';
import AnalystView from './components/AnalystView.jsx';
import CoverageModal from './components/CoverageModal.jsx';
import ProvenanceChip from './components/ProvenanceChip.jsx';
import UploadValidationModal from './components/UploadValidationModal.jsx';
import DocumentManager from './components/DocumentManager.jsx';
import Phase2View from './components/Phase2View.jsx';
import RulesConfigModal from './components/RulesConfigModal.jsx';

// A fully blank CompanyInput, mirroring backend/app/models/schemas.py field
// for field. Used by "Start New Company" so a cleared form is genuinely
// empty everywhere — not the demo fixture, not a prior ticker's leftovers.
function blankCompanyInput() {
  return {
    ticker: '',
    as_of_date: new Date().toISOString().slice(0, 10),
    company_type: null,
    data_basis: 'CONSOLIDATED',
    auditor_resigned_mid_tenure_last_3y: null,
    audit_opinion: null,
    regulatory_action: { active_or_past_5y: null, nature: null, retrieval_tier: null },
    legal_fees: null,
    audit_fees: null,
    legal_fees_prior_year: null,
    industry_sector: null,
    legal_fee_surge_explained: null,
    govt_shareholding_pct: null,
    promoter_holding_pct_of_company: null,
    pledged_pct_of_promoter_holding: null,
    pledged_pct_history_last_4q: null,
    pledged_pct_history_retrieval_tier: null,
    pledged_pct_of_total_shares: null,
    rpt_sales_plus_purchases: null,
    revenue: null,
    unusual_affiliate_dealings: null,
    net_worth: null,
    litigation_claims_exposure: null,
    routine_guarantee_exposure: null,
    contingent_liabilities: null,
    contingent_liabilities_breakdown_available: null,
    cfo_last_5y: null,
    pat_last_5y: null,
    working_capital_cycle_tier: null,
    revenue_last_5y: null,
    cumulative_working_capital_change_5y: null,
    liquid_cushion_first_year: null,
    liquid_cushion_last_year: null,
    years_5y_series_gap_checked: null,
    cfo_changes_last_3y: null,
    restatement_of_past_accounts: null,
    restatement_search_retrieval_tier: null,
    restatement_esg_only_excluded: null,
    years_of_track_record_available: null,
    provenance: {},
  };
}

export default function App() {
  const [formData, setFormData] = useState(blankCompanyInput());
  const [priorResultId, setPriorResultId] = useState(null);
  
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchingScreener, setFetchingScreener] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);
  const [activeTab, setActiveTab] = useState('investor');
  const [currentPhase, setCurrentPhase] = useState('phase1');
  
  // Modals & Upload State
  const [coverageOpen, setCoverageOpen] = useState(false);
  const [rulesModalOpen, setRulesModalOpen] = useState(false);
  const [rulesConfigInfo, setRulesConfigInfo] = useState({ source: 'DEFAULT', version: '1.0.0' });
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadResultData, setUploadResultData] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const refreshRulesInfo = () => {
    fetch('/api/rules/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.source) {
          setRulesConfigInfo({ source: data.source, version: data.version });
        }
      })
      .catch(() => {});
  };

  // Confirm the backend is reachable on mount and load initial rules engine info
  useEffect(() => {
    fetch('/api/health').catch(() => setError('Failed to connect to Phase 1 backend API'));
    refreshRulesInfo();
  }, []);

  // Discards every finding/reading/extraction for the current ticker —
  // deletes its uploaded Annual Report documents and pending review-queue
  // items server-side (not just hidden client-side), then resets the form
  // to a genuinely blank CompanyInput so the analyst can start a new
  // company from scratch.
  const handleStartNewCompany = async () => {
    const currentTicker = formData?.ticker?.trim();
    const confirmed = window.confirm(
      currentTicker
        ? `This will permanently delete all uploaded documents and pending review items for ${currentTicker.toUpperCase()}, and clear every field. Continue?`
        : 'This will clear every field on the form. Continue?'
    );
    if (!confirmed) return;

    setError(null);
    setStatusMsg(null);

    if (currentTicker) {
      try {
        const res = await fetch(`/api/tickers/${currentTicker.toUpperCase()}/reset`, {
          method: 'DELETE',
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Reset failed');
        }
      } catch (err) {
        setError(`Reset Error: ${err.message}`);
        return; // don't clear local state if the server-side wipe failed
      }
    }

    setFormData(blankCompanyInput());
    setEvaluation(null);
    setPriorResultId(null);
    setUploadResultData(null);
    setUploadModalOpen(false);
    setStatusMsg('Cleared. Ready for a new company.');
  };

  const handleInputChange = (field, value) => {
    setFormData((prev) => {
      if (!prev) return prev;
      const updated = { ...prev, [field]: value };
      // If manually changed, update provenance to MANUAL
      const prov = { ...(prev.provenance || {}) };
      prov[field] = {
        field_name: field,
        source: 'Manual UI Entry',
        period: 'Current',
        basis: prev.data_basis || 'CONSOLIDATED',
        confidence: 'MANUAL',
      };
      updated.provenance = prov;
      return updated;
    });
  };

  // Fetch live or cached data from Screener via Phase C pipeline
  const handleFetchScreener = async () => {
    if (!formData?.ticker) {
      setError('Please provide a company ticker symbol first');
      return;
    }
    setFetchingScreener(true);
    setError(null);
    setStatusMsg(null);

    try {
      const ticker = formData.ticker.trim().toUpperCase();
      const res = await fetch(`/api/tickers/${ticker}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          basis: formData.data_basis || 'CONSOLIDATED',
          as_of_date: formData.as_of_date || '2024-03-31',
          manual_overrides: null,
          prior_result_id: priorResultId,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Screener acquisition failed');
      }

      const data = await res.json();
      setFormData(data.company_input);
      setEvaluation({
        result: data.result,
        investor_report: data.investor_report,
        analyst_report: data.analyst_report,
      });
      setPriorResultId(data.result.result_id);

      if (data.adapter_errors && data.adapter_errors.length > 0) {
        setError(`Screener Warning: ${data.adapter_errors.join('; ')}`);
      } else {
        const emptyCount = data.empty_fields ? data.empty_fields.length : 0;
        setStatusMsg(
          `Successfully scraped Screener.in for ${ticker}! Extracted automated fields. (${emptyCount} Phase D fields awaiting PDF/Workbook input).`
        );
      }
    } catch (err) {
      setError(`Screener Fetch Error: ${err.message}`);
    } finally {
      setFetchingScreener(false);
    }
  };

  // Upload Excel or CSV analyst workbook
  const handleFileProcess = async (file) => {
    if (!file) return;
    setError(null);
    setStatusMsg(null);

    const ticker = formData?.ticker || 'UNKNOWN';
    const formUpload = new FormData();
    formUpload.append('file', file);

    try {
      const res = await fetch(`/api/tickers/${ticker}/uploads`, {
        method: 'POST',
        body: formUpload,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Workbook upload failed');
      }

      const uploadData = await res.json();
      setUploadResultData(uploadData);
      setUploadModalOpen(true);

      // Merge extracted fields into formData
      if (uploadData.fields && uploadData.fields.length > 0) {
        setFormData((prev) => {
          const updated = { ...(prev || {}) };
          const prov = { ...(updated.provenance || {}) };

          uploadData.fields.forEach((f) => {
            updated[f.field_name] = f.value;
            prov[f.field_name] = {
              field_name: f.field_name,
              source: `Workbook: ${uploadData.filename}`,
              period: f.period || 'FY24',
              basis: f.basis || 'CONSOLIDATED',
              confidence: f.confidence || 'MANUAL',
            };
          });

          updated.provenance = prov;
          return updated;
        });

        setStatusMsg(
          `Successfully loaded ${uploadData.fields_count} field(s) from ${uploadData.filename} (${uploadData.errors_count} warnings/errors).`
        );
      }
    } catch (err) {
      setError(`Workbook Upload Error: ${err.message}`);
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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const handleEvaluate = async (usePrior = false) => {
    if (!formData) return;
    setLoading(true);
    setError(null);

    try {
      const payload = {
        ...formData,
        prior_result_id: usePrior ? priorResultId : null,
      };

      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Evaluation failed');
      }

      const data = await res.json();
      setEvaluation(data);
      setPriorResultId(data.result.result_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Navbar Header */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              background: currentPhase === 'phase1' 
                ? 'linear-gradient(135deg, #6366f1, #3b82f6)' 
                : 'linear-gradient(135deg, #10b981, #06b6d4)',
              padding: '10px',
              borderRadius: '12px',
              display: 'flex',
            }}
          >
            {currentPhase === 'phase1' ? (
              <ShieldCheck size={28} color="#fff" />
            ) : (
              <TrendingUp size={28} color="#fff" />
            )}
          </div>
          <div>
            <h1 style={{ fontSize: '24px', margin: 0 }}>
              {currentPhase === 'phase1' ? 'Phase 1 Gatekeeper' : 'Phase 2 Quality Engine'}
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
              {currentPhase === 'phase1'
                ? 'Honesty, Integrity & Forensic Safety Engine (Checks 1–6)'
                : 'Business Quality, Moat & Capital Allocation Engine (Checks 7–18)'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            id="open-rules-config-btn"
            className="btn btn-secondary btn-sm"
            onClick={() => setRulesModalOpen(true)}
            title="Configure dynamic rules engine thresholds, boundary matrices, and sector mappings"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Sliders size={14} /> Rules Config
            <span
              style={{
                fontSize: '10.5px',
                padding: '2px 7px',
                borderRadius: '8px',
                fontWeight: 600,
                backgroundColor:
                  rulesConfigInfo.source === 'DEFAULT'
                    ? 'rgba(59, 130, 246, 0.15)'
                    : 'rgba(16, 185, 129, 0.2)',
                color: rulesConfigInfo.source === 'DEFAULT' ? '#60a5fa' : '#34d399',
                border: `1px solid ${
                  rulesConfigInfo.source === 'DEFAULT'
                    ? 'rgba(59, 130, 246, 0.3)'
                    : 'rgba(16, 185, 129, 0.4)'
                }`,
              }}
            >
              {rulesConfigInfo.source === 'DEFAULT' ? 'Default' : 'Custom'}
            </span>
          </button>

          <a
            id="download-template-link"
            href="/api/templates/workbook.xlsx"
            download="phase1_analyst_workbook.xlsx"
            className="btn btn-secondary btn-sm"
            title="Download the official Excel template derived from FIELD_COVERAGE_MATRIX"
          >
            <Download size={14} /> Analyst Template (.xlsx)
          </a>

          <button
            id="open-coverage-matrix-btn"
            className="btn btn-secondary btn-sm"
            onClick={() => setCoverageOpen(true)}
          >
            <Layers size={14} /> Field Matrix (§3)
          </button>
        </div>
      </header>

      {/* Top Phase Navigation Bar */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '28px' }}>
        <div className="tabs-nav" style={{ padding: '6px', gap: '8px' }}>
          <button
            id="tab-switch-phase1"
            className={`tab-btn ${currentPhase === 'phase1' ? 'active' : ''}`}
            style={{ fontSize: '14px', padding: '10px 22px', borderRadius: '10px' }}
            onClick={() => setCurrentPhase('phase1')}
          >
            <ShieldCheck size={18} /> Phase 1: Forensic Safety (Checks 1–6)
          </button>
          <button
            id="tab-switch-phase2"
            className={`tab-btn ${currentPhase === 'phase2' ? 'active' : ''}`}
            style={{ fontSize: '14px', padding: '10px 22px', borderRadius: '10px' }}
            onClick={() => setCurrentPhase('phase2')}
          >
            <TrendingUp size={18} /> Phase 2: Business Quality (Checks 7–18)
          </button>
        </div>
      </div>

      {/* Conditional Phase View */}
      {currentPhase === 'phase2' ? (
        <Phase2View
          initialTicker={formData.ticker}
          initialPhase1Id={evaluation?.result?.verdict === 'CLEARED TO PHASE 2' ? evaluation.result.result_id : null}
          onSwitchToPhase1={() => setCurrentPhase('phase1')}
        />
      ) : (
        <>
          {/* Main Control & Acquisition Card */}
          <section className="glass-panel" style={{ padding: '24px', marginBottom: '32px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color="var(--color-primary)" />
            <h2 style={{ fontSize: '18px', margin: 0 }}>Data Acquisition & Target Config</h2>
          </div>
        </div>

        {formData && (
          <div>
            {/* Primary Target & Action Bar */}
            <div className="grid-3" style={{ marginBottom: '16px' }}>
              <div>
                <label>Company Ticker / Symbol</label>
                <input
                  id="input-ticker"
                  type="text"
                  value={formData.ticker || ''}
                  onChange={(e) => handleInputChange('ticker', e.target.value.toUpperCase())}
                  placeholder="e.g. INFY, TCS, TATAMOTORS"
                />
              </div>

              <div>
                <label>As of Date</label>
                <input
                  id="input-as-of-date"
                  type="date"
                  value={formData.as_of_date || '2024-03-31'}
                  onChange={(e) => handleInputChange('as_of_date', e.target.value)}
                />
              </div>

              <div>
                <label>Reporting Basis</label>
                <select
                  id="select-data-basis"
                  value={formData.data_basis || 'CONSOLIDATED'}
                  onChange={(e) => handleInputChange('data_basis', e.target.value)}
                >
                  <option value="CONSOLIDATED">CONSOLIDATED</option>
                  <option value="STANDALONE">STANDALONE</option>
                </select>
              </div>
            </div>

            {/* Quick Actions & Upload Dropzone */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '20px' }}>
              <button
                id="fetch-screener-btn"
                className="btn btn-primary"
                onClick={handleFetchScreener}
                disabled={fetchingScreener || !formData.ticker}
                title="Fetches HTML tables from Screener.in, parses statements, and auto-populates fields"
              >
                <Globe size={16} />
                {fetchingScreener ? 'Scraping Screener.in...' : `Fetch from Screener (${formData.ticker || 'Ticker'})`}
              </button>

              <button
                id="upload-workbook-btn"
                className="btn btn-secondary"
                onClick={() => fileInputRef.current?.click()}
                title="Upload analyst Excel workbook or CSV export"
              >
                <UploadCloud size={16} /> Upload Analyst Workbook (.xlsx / .csv)
              </button>

              <button
                id="start-new-company-btn"
                className="btn btn-secondary"
                onClick={handleStartNewCompany}
                title="Deletes all uploaded documents, extracted fields, and review items for this ticker, and clears the form"
              >
                <Trash2 size={16} /> Start New Company
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileProcess(e.target.files[0]);
                  }
                }}
              />
            </div>

            {/* Drag & Drop Box */}
            <div
              className={`upload-dropzone ${dragActive ? 'dragging' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                <FileSpreadsheet size={22} color="var(--color-primary)" />
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Drag & drop analyst Excel (<code>.xlsx</code>) or CSV workbook here, or click to browse.
                </span>
              </div>
            </div>

            {/* Annual Report PDFs Manager (Phase D Multi-PDF Ingestion) */}
            <DocumentManager
              ticker={formData.ticker}
              formData={formData}
              setFormData={setFormData}
              setStatusMsg={setStatusMsg}
              setError={setError}
            />

            {/* Status Notification Banner */}
            {statusMsg && (
              <div
                style={{
                  marginTop: '16px',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  background: 'rgba(99, 102, 241, 0.1)',
                  border: '1px solid rgba(99, 102, 241, 0.25)',
                  color: '#c7d2fe',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '13px',
                }}
              >
                <CheckCircle2 size={16} color="var(--color-primary)" />
                <span>{statusMsg}</span>
              </div>
            )}

            {/* Error Notification Banner */}
            {error && (
              <div
                style={{
                  marginTop: '16px',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: 'var(--color-danger-bg)',
                  border: '1px solid var(--color-danger-border)',
                  color: 'var(--color-danger)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <div style={{ marginTop: '24px' }}>
              {/* Field Group 1: Automated Screener Financials (Phase C) */}
              <div className="field-group">
                <div className="field-group-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Globe size={16} color="var(--color-primary)" />
                    <h3 style={{ fontSize: '14.5px', margin: 0 }}>
                      Automated Screener Financials & Ratios (Phase C — Automated)
                    </h3>
                  </div>
                  <span className="badge badge-success" style={{ fontSize: '10px', padding: '2px 8px' }}>
                    Screener Tier 1
                  </span>
                </div>

                <div className="grid-3" style={{ marginBottom: '14px' }}>
                  <div>
                    <label>
                      Revenue from Operations (₹ Cr)
                      <ProvenanceChip prov={formData.provenance?.revenue} />
                    </label>
                    <input
                      id="input-revenue"
                      type="number"
                      step="1"
                      value={formData.revenue ?? ''}
                      placeholder="e.g. 153670"
                      onChange={(e) =>
                        handleInputChange('revenue', e.target.value ? parseFloat(e.target.value) : null)
                      }
                    />
                  </div>

                  <div>
                    <label>
                      Net Worth / Total Equity (₹ Cr)
                      <ProvenanceChip prov={formData.provenance?.net_worth} />
                    </label>
                    <input
                      id="input-net-worth"
                      type="number"
                      step="1"
                      value={formData.net_worth ?? ''}
                      placeholder="e.g. 85400"
                      onChange={(e) =>
                        handleInputChange('net_worth', e.target.value ? parseFloat(e.target.value) : null)
                      }
                    />
                  </div>

                  <div>
                    <label>
                      Contingent Liabilities (₹ Cr)
                      <ProvenanceChip prov={formData.provenance?.contingent_liabilities} />
                    </label>
                    <input
                      id="input-contingent-liabilities"
                      type="number"
                      step="1"
                      value={formData.contingent_liabilities ?? ''}
                      placeholder="e.g. 1200"
                      onChange={(e) =>
                        handleInputChange(
                          'contingent_liabilities',
                          e.target.value ? parseFloat(e.target.value) : null
                        )
                      }
                    />
                  </div>
                </div>

                <div className="grid-3" style={{ marginBottom: '14px' }}>
                  <div>
                    <label>
                      Promoter Holding %
                      <ProvenanceChip prov={formData.provenance?.promoter_holding_pct_of_company} />
                    </label>
                    <input
                      id="input-promoter-holding"
                      type="number"
                      step="0.01"
                      value={formData.promoter_holding_pct_of_company ?? ''}
                      placeholder="e.g. 52.4"
                      onChange={(e) =>
                        handleInputChange(
                          'promoter_holding_pct_of_company',
                          e.target.value ? parseFloat(e.target.value) : null
                        )
                      }
                    />
                  </div>

                  <div>
                    <label>
                      Pledged % of Promoter Holding
                      <ProvenanceChip prov={formData.provenance?.pledged_pct_of_promoter_holding} />
                    </label>
                    <input
                      id="input-pledge-pct"
                      type="number"
                      step="0.01"
                      value={formData.pledged_pct_of_promoter_holding ?? ''}
                      placeholder="e.g. 0.0 (<= 10% passes)"
                      onChange={(e) =>
                        handleInputChange(
                          'pledged_pct_of_promoter_holding',
                          e.target.value ? parseFloat(e.target.value) : null
                        )
                      }
                    />
                  </div>

                  <div>
                    <label>
                      Govt Shareholding %
                      <ProvenanceChip prov={formData.provenance?.govt_shareholding_pct} />
                    </label>
                    <input
                      id="input-govt-shareholding"
                      type="number"
                      step="0.01"
                      value={formData.govt_shareholding_pct ?? ''}
                      placeholder="e.g. 0.0 (>50% = PSU)"
                      onChange={(e) =>
                        handleInputChange(
                          'govt_shareholding_pct',
                          e.target.value ? parseFloat(e.target.value) : null
                        )
                      }
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <div>
                    <label>
                      CFO Last 5 Years (₹ Cr, comma-separated)
                      <ProvenanceChip prov={formData.provenance?.cfo_last_5y} />
                    </label>
                    <input
                      id="input-cfo-last-5y"
                      type="text"
                      value={formData.cfo_last_5y ? formData.cfo_last_5y.join(', ') : ''}
                      placeholder="e.g. 12000, 14000, 16000, 18000, 21000"
                      onChange={(e) => {
                        const vals = e.target.value
                          .split(',')
                          .map((s) => parseFloat(s.trim()))
                          .filter((n) => !isNaN(n));
                        handleInputChange('cfo_last_5y', vals.length > 0 ? vals : null);
                      }}
                    />
                  </div>

                  <div>
                    <label>
                      PAT Last 5 Years (₹ Cr, comma-separated)
                      <ProvenanceChip prov={formData.provenance?.pat_last_5y} />
                    </label>
                    <input
                      id="input-pat-last-5y"
                      type="text"
                      value={formData.pat_last_5y ? formData.pat_last_5y.join(', ') : ''}
                      placeholder="e.g. 10000, 12500, 14000, 16500, 19000"
                      onChange={(e) => {
                        const vals = e.target.value
                          .split(',')
                          .map((s) => parseFloat(s.trim()))
                          .filter((n) => !isNaN(n));
                        handleInputChange('pat_last_5y', vals.length > 0 ? vals : null);
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Field Group 2: Annual Report, Audit & Governance (Phase D: PDF Extract / Workbook) */}
              <div className="field-group">
                <div className="field-group-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={16} color="#a5b4fc" />
                    <h3 style={{ fontSize: '14.5px', margin: 0 }}>
                      Governance, Audit & Regulatory (Phase D — PDF Extract & Manual Review)
                    </h3>
                  </div>
                  <span className="badge badge-warning" style={{ fontSize: '10px', padding: '2px 8px' }}>
                    Phase D / Workbook
                  </span>
                </div>

                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                  These fields originate from the statutory Annual Report notes and regulatory filings. Fill them via
                  the analyst workbook upload (<code>.xlsx</code>) or manually below.
                </p>

                <div className="grid-3" style={{ marginBottom: '14px' }}>
                  <div>
                    <label>
                      Audit Opinion (Check 1)
                      <ProvenanceChip prov={formData.provenance?.audit_opinion} />
                    </label>
                    <select
                      id="select-audit-opinion"
                      value={formData.audit_opinion || 'UNQUALIFIED'}
                      onChange={(e) => handleInputChange('audit_opinion', e.target.value)}
                    >
                      <option value="UNQUALIFIED">UNQUALIFIED (Clean / Pass)</option>
                      <option value="QUALIFIED">QUALIFIED (Fail)</option>
                      <option value="ADVERSE">ADVERSE (Fail)</option>
                      <option value="DISCLAIMER_OF_OPINION">DISCLAIMER OF OPINION (Fail)</option>
                    </select>
                  </div>

                  <div>
                    <label>
                      Auditor Resigned Mid-Tenure (3Y)
                      <ProvenanceChip prov={formData.provenance?.auditor_resigned_mid_tenure_last_3y} />
                    </label>
                    <select
                      id="select-auditor-resigned"
                      value={
                        formData.auditor_resigned_mid_tenure_last_3y === null
                          ? ''
                          : formData.auditor_resigned_mid_tenure_last_3y
                          ? 'true'
                          : 'false'
                      }
                      onChange={(e) =>
                        handleInputChange(
                          'auditor_resigned_mid_tenure_last_3y',
                          e.target.value === '' ? null : e.target.value === 'true'
                        )
                      }
                    >
                      <option value="false">No (Clean)</option>
                      <option value="true">Yes (Fail Check 1)</option>
                      <option value="">Missing / Not Verified</option>
                    </select>
                  </div>

                  <div>
                    <label>
                      Regulatory Action / SEBI Enforcement
                      <ProvenanceChip prov={formData.provenance?.regulatory_action} />
                    </label>
                    <select
                      id="select-regulatory-action"
                      value={
                        // regulatory_action is a {active_or_past_5y, nature, retrieval_tier}
                        // object, not a bare boolean — a populated-but-clean object is
                        // truthy in JS, so it must never be tested directly (that was the
                        // bug: any non-null finding rendered as "Active Action").
                        !formData.regulatory_action ||
                        formData.regulatory_action.active_or_past_5y === null ||
                        formData.regulatory_action.active_or_past_5y === undefined
                          ? ''
                          : formData.regulatory_action.active_or_past_5y
                          ? 'true'
                          : 'false'
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        handleInputChange('regulatory_action', {
                          active_or_past_5y: v === '' ? null : v === 'true',
                          nature: v === '' ? null : v === 'true' ? null : 'NONE',
                          retrieval_tier: null,
                        });
                      }}
                    >
                      <option value="false">None / Clean</option>
                      <option value="true">Active Action (Fail Check 1)</option>
                      <option value="">Missing / Not Verified</option>
                    </select>
                  </div>
                </div>

                <div className="grid-3" style={{ marginBottom: '14px' }}>
                  <div>
                    <label>
                      RPT Sales + Purchases (₹ Cr, Check 3)
                      <ProvenanceChip prov={formData.provenance?.rpt_sales_plus_purchases} />
                    </label>
                    <input
                      id="input-rpt-sales-purchases"
                      type="number"
                      step="1"
                      value={formData.rpt_sales_plus_purchases ?? ''}
                      placeholder="e.g. 450 (<= 10% rev passes)"
                      onChange={(e) =>
                        handleInputChange(
                          'rpt_sales_plus_purchases',
                          e.target.value ? parseFloat(e.target.value) : null
                        )
                      }
                    />
                  </div>

                  <div>
                    <label>
                      Unusual Affiliate Dealings
                      <ProvenanceChip prov={formData.provenance?.unusual_affiliate_dealings} />
                    </label>
                    <select
                      id="select-unusual-affiliate"
                      value={
                        formData.unusual_affiliate_dealings === null
                          ? ''
                          : formData.unusual_affiliate_dealings
                          ? 'true'
                          : 'false'
                      }
                      onChange={(e) =>
                        handleInputChange(
                          'unusual_affiliate_dealings',
                          e.target.value === '' ? null : e.target.value === 'true'
                        )
                      }
                    >
                      <option value="false">No (Clean)</option>
                      <option value="true">Yes (Fail Check 3)</option>
                      <option value="">Missing / Not Verified</option>
                    </select>
                  </div>

                  <div>
                    <label>
                      CFO Changes in Last 3 Years (Check 6)
                      <ProvenanceChip prov={formData.provenance?.cfo_changes_last_3y} />
                    </label>
                    <input
                      id="input-cfo-changes"
                      type="number"
                      step="1"
                      min="0"
                      value={formData.cfo_changes_last_3y ?? ''}
                      placeholder="e.g. 0 (>= 2 fails)"
                      onChange={(e) =>
                        handleInputChange(
                          'cfo_changes_last_3y',
                          e.target.value ? parseInt(e.target.value, 10) : null
                        )
                      }
                    />
                  </div>
                </div>

                <div className="grid-3">
                  <div>
                    <label>
                      Restatement of Accounts (Check 6)
                      <ProvenanceChip prov={formData.provenance?.restatement_of_past_accounts} />
                    </label>
                    <select
                      id="select-restatements"
                      value={
                        formData.restatement_of_past_accounts === null
                          ? ''
                          : formData.restatement_of_past_accounts
                          ? 'true'
                          : 'false'
                      }
                      onChange={(e) =>
                        handleInputChange(
                          'restatement_of_past_accounts',
                          e.target.value === '' ? null : e.target.value === 'true'
                        )
                      }
                    >
                      <option value="false">No (Clean)</option>
                      <option value="true">Yes (Fail Check 6)</option>
                      <option value="">Missing / Not Verified</option>
                    </select>
                  </div>

                  <div>
                    <label>
                      Legal & Professional Fees (₹ Cr)
                      <ProvenanceChip prov={formData.provenance?.legal_fees} />
                    </label>
                    <input
                      id="input-legal-fees"
                      type="number"
                      step="0.1"
                      value={formData.legal_fees ?? ''}
                      placeholder="e.g. 45"
                      onChange={(e) =>
                        handleInputChange('legal_fees', e.target.value ? parseFloat(e.target.value) : null)
                      }
                    />
                  </div>

                  <div>
                    <label>
                      Payment to Auditors (₹ Cr)
                      <ProvenanceChip prov={formData.provenance?.audit_fees} />
                    </label>
                    <input
                      id="input-audit-fees"
                      type="number"
                      step="0.1"
                      value={formData.audit_fees ?? ''}
                      placeholder="e.g. 12"
                      onChange={(e) =>
                        handleInputChange('audit_fees', e.target.value ? parseFloat(e.target.value) : null)
                      }
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Run Engine Button Bar */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '16px' }}>
              <button
                id="evaluate-ticker-btn"
                className="btn btn-primary"
                onClick={() => handleEvaluate(false)}
                disabled={loading}
              >
                <Play size={16} /> {loading ? 'Running Checks...' : 'Run Phase 1 Evaluation'}
              </button>

              {priorResultId && (
                <button
                  id="re-evaluate-version-btn"
                  className="btn btn-secondary"
                  onClick={() => handleEvaluate(true)}
                  disabled={loading}
                  title="Simulate a re-run that increments revision and links supersedes pointer"
                >
                  <RotateCcw size={16} /> Re-evaluate (Revision {evaluation ? evaluation.result.revision + 1 : 2})
                </button>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Results View */}
      {evaluation && (
        <section>
          {/* Phase 2 Transition Callout if Cleared */}
          {evaluation.result?.verdict === 'CLEARED TO PHASE 2' && (
            <div
              className="glass-panel"
              style={{
                padding: '16px 20px',
                marginBottom: '20px',
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(99, 102, 241, 0.15))',
                border: '1px solid #10b981',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <CheckCircle2 size={28} color="#10b981" />
                <div>
                  <div style={{ fontWeight: 700, color: '#10b981', fontSize: '15px' }}>
                    GATEKEEPER VERDICT: CLEARED TO PHASE 2!
                  </div>
                  <div style={{ fontSize: '13px', color: '#cbd5e1' }}>
                    All 6 Forensic Safety Checks cleared. Ready for Operating Quality, Moat & Capital Allocation evaluation.
                  </div>
                </div>
              </div>
              <button
                id="proceed-to-phase2-btn"
                className="btn btn-primary"
                style={{ padding: '10px 18px', fontSize: '14px' }}
                onClick={() => setCurrentPhase('phase2')}
              >
                Proceed to Phase 2 Quality Check <ArrowRight size={16} />
              </button>
            </div>
          )}

          {/* View Mode Switcher */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px',
            }}
          >
            <div className="tabs-nav">
              <button
                id="tab-investor-view"
                className={`tab-btn ${activeTab === 'investor' ? 'active' : ''}`}
                onClick={() => setActiveTab('investor')}
              >
                <Sparkles size={15} /> Investor View (user.md Prose)
              </button>
              <button
                id="tab-analyst-view"
                className={`tab-btn ${activeTab === 'analyst' ? 'active' : ''}`}
                onClick={() => setActiveTab('analyst')}
              >
                <FileText size={15} /> Analyst Deep-Dive (§4 Table)
              </button>
            </div>
          </div>

          {activeTab === 'investor' ? (
            <InvestorView report={evaluation.investor_report} resultId={evaluation.result.result_id} />
          ) : (
            <AnalystView analystReport={evaluation.analyst_report} rawResult={evaluation.result} />
          )}
        </section>
      )}
    </>
  )}

      {/* Field Coverage Matrix Modal */}
      <CoverageModal isOpen={coverageOpen} onClose={() => setCoverageOpen(false)} />

      {/* Rules Engine Configuration Modal */}
      <RulesConfigModal
        isOpen={rulesModalOpen}
        onClose={() => setRulesModalOpen(false)}
        onConfigChanged={refreshRulesInfo}
      />

      {/* Upload Validation Modal */}
      <UploadValidationModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        uploadData={uploadResultData}
      />
    </div>
  );
}
