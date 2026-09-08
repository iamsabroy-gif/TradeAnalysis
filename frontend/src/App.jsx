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
  Database
} from 'lucide-react';
import InvestorView from './components/InvestorView';
import AnalystView from './components/AnalystView';
import CoverageModal from './components/CoverageModal';
import ProvenanceChip from './components/ProvenanceChip';
import UploadValidationModal from './components/UploadValidationModal';
import DocumentManager from './components/DocumentManager';

export default function App() {
  const [fixtures, setFixtures] = useState([]);
  const [selectedFixtureId, setSelectedFixtureId] = useState('fixture_1_clean');
  const [formData, setFormData] = useState(null);
  const [priorResultId, setPriorResultId] = useState(null);
  
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchingScreener, setFetchingScreener] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);
  const [activeTab, setActiveTab] = useState('investor');
  
  // Modals & Upload State
  const [coverageOpen, setCoverageOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadResultData, setUploadResultData] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Load fixtures on mount
  useEffect(() => {
    fetch('/api/fixtures')
      .then((res) => res.json())
      .then((data) => {
        setFixtures(data.fixtures);
        if (data.fixtures.length > 0) {
          setFormData(data.fixtures[0].data);
        }
      })
      .catch((err) => setError('Failed to connect to Phase 1 backend API'));
  }, []);

  // Handle fixture selection
  const handleSelectFixture = (e) => {
    const fId = e.target.value;
    setSelectedFixtureId(fId);
    const found = fixtures.find((f) => f.id === fId);
    if (found) {
      setFormData(found.data);
      setPriorResultId(null);
      setStatusMsg(`Loaded test fixture: ${found.label}`);
    }
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
          marginBottom: '28px',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              background: 'linear-gradient(135deg, #6366f1, #3b82f6)',
              padding: '10px',
              borderRadius: '12px',
              display: 'flex',
            }}
          >
            <ShieldCheck size={28} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '24px', margin: 0 }}>Phase 1 Gatekeeper</h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
              Honesty, Integrity & Forensic Safety Engine (Phase C Scraper & Upload Pipeline Active)
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '300px' }}>
            <label style={{ margin: 0, whiteSpace: 'nowrap', fontSize: '13px' }}>Preset Fixture:</label>
            <select
              id="fixture-select-dropdown"
              value={selectedFixtureId}
              onChange={handleSelectFixture}
              style={{ padding: '6px 10px', fontSize: '13px' }}
            >
              {fixtures.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label} → [{f.expected}]
                </option>
              ))}
            </select>
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
                        formData.regulatory_action === null
                          ? ''
                          : formData.regulatory_action
                          ? 'true'
                          : 'false'
                      }
                      onChange={(e) =>
                        handleInputChange(
                          'regulatory_action',
                          e.target.value === '' ? null : e.target.value === 'true'
                        )
                      }
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

      {/* Field Coverage Matrix Modal */}
      <CoverageModal isOpen={coverageOpen} onClose={() => setCoverageOpen(false)} />

      {/* Upload Validation Modal */}
      <UploadValidationModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        uploadData={uploadResultData}
      />
    </div>
  );
}
