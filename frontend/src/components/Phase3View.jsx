import React, { useState, useEffect } from 'react';
import {
  Calculator,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Sparkles,
  Layers,
  RotateCcw,
  Play,
  Copy,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  HelpCircle,
  Building,
  Target,
  FileText,
  DollarSign,
  PieChart,
  Activity,
  Plus,
  Trash2,
  ArrowRight
} from 'lucide-react';

export function defaultPhase3Input(initialTicker = '', initialPhase2Id = null) {
  return {
    ticker: initialTicker || '',
    company_name: '',
    as_of_date: new Date().toISOString().slice(0, 10),
    current_price: 1450.0,
    current_pe: 24.5,
    five_yr_avg_pe: 26.0,
    peer_avg_pe: 28.0,
    current_ev_ebitda: 16.2,
    five_yr_avg_ev_ebitda: 17.5,
    peer_avg_ev_ebitda: 18.0,
    dividend_yield_pct: 1.8,
    historical_eps_growth_3y_cagr: 16.5,
    expected_pe_change_annualized_pct: 0.0,
    claimed_growth_narrative: 'Expanding market share in enterprise cloud services with steady 15-18% revenue CAGR.',
    story_contradictions: [],
    custom_narrative_notes: '',
  };
}

export default function Phase3View({ initialTicker, initialPhase2Id, onSwitchToPhase2 }) {
  const [formData, setFormData] = useState(() => defaultPhase3Input(initialTicker, initialPhase2Id));
  const [phase2Id, setPhase2Id] = useState(initialPhase2Id || '');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingFixture, setLoadingFixture] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);
  const [activeTab, setActiveTab] = useState('investor'); // 'investor' | 'analyst'
  const [copied, setCopied] = useState(false);

  // Common quick-toggle contradictions
  const [contradictionToggles, setContradictionToggles] = useState({
    EXPANSION_LIE: false,
    VENDOR_RISK: false,
    GUIDANCE_GAP: false,
    TONE_SHIFT: false,
  });

  useEffect(() => {
    if (initialTicker && !formData.ticker) {
      setFormData((prev) => ({ ...prev, ticker: initialTicker }));
    }
    if (initialPhase2Id) {
      setPhase2Id(initialPhase2Id);
    }
  }, [initialTicker, initialPhase2Id]);

  const handleLoadFixture = async (fixtureName) => {
    setLoadingFixture(true);
    setError(null);
    try {
      const res = await fetch(`/api/phase3/fixtures/${fixtureName}`);
      if (!res.ok) {
        throw new Error(`Failed to load fixture: ${res.statusText}`);
      }
      const data = await res.json();
      setFormData(data);

      // Sync quick toggles from loaded contradictions
      const toggles = {
        EXPANSION_LIE: false,
        VENDOR_RISK: false,
        GUIDANCE_GAP: false,
        TONE_SHIFT: false,
      };
      if (data.story_contradictions && Array.isArray(data.story_contradictions)) {
        data.story_contradictions.forEach((c) => {
          if (toggles.hasOwnProperty(c.contradiction_type)) {
            toggles[c.contradiction_type] = true;
          }
        });
      }
      setContradictionToggles(toggles);

      setStatusMsg(`Loaded canonical fixture: ${fixtureName.toUpperCase().replace(/_/g, ' ')}`);
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingFixture(false);
    }
  };

  const handleToggleContradiction = (type, title, defaultEvidence) => {
    const isCurrentlyActive = contradictionToggles[type];
    const newToggles = { ...contradictionToggles, [type]: !isCurrentlyActive };
    setContradictionToggles(newToggles);

    let currentContradictions = [...(formData.story_contradictions || [])];
    if (isCurrentlyActive) {
      // Remove it
      currentContradictions = currentContradictions.filter((c) => c.contradiction_type !== type);
    } else {
      // Add it
      currentContradictions.push({
        contradiction_type: type,
        claim_made: title,
        financial_reality: defaultEvidence,
        source_reference: 'Management Discussion & Annual Report Notes',
        severity: 'FATAL',
      });
    }

    setFormData((prev) => ({
      ...prev,
      story_contradictions: currentContradictions,
    }));
  };

  const handleRunEvaluation = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        company_input: formData,
        phase2_result_id: phase2Id ? phase2Id.trim() : null,
      };

      const res = await fetch('/api/phase3/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Phase 3 evaluation failed');
      }

      const data = await res.json();
      const resResult = data.result || data;
      setEvaluation({
        ...resResult,
        verdict: resResult.verdict || data.verdict,
        verdict_summary: resResult.verdict_summary || data.verdict_summary,
        valuation_analysis: resResult.valuation_analysis || data.valuation_analysis,
        return_path_analysis: resResult.return_path_analysis || data.return_path_analysis,
        story_scan_analysis: resResult.story_scan_analysis || data.story_scan_analysis,
        analyst_markdown: data.analyst_markdown || data.analyst_table,
        investor_report: data.investor_report,
      });
      setStatusMsg('Phase 3 Evaluation completed successfully!');
      setTimeout(() => {
        const el = document.getElementById('phase3-results-container');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyReport = () => {
    if (!evaluation) return;
    const reportText = activeTab === 'investor' ? evaluation.investor_report : evaluation.analyst_markdown;
    navigator.clipboard.writeText(reportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  // Helper for gap calculations
  const calcGap = (current, benchmark) => {
    if (!current || !benchmark) return null;
    return (((current - benchmark) / benchmark) * 100).toFixed(1);
  };

  const peGapVs5Yr = calcGap(formData.current_pe, formData.five_yr_avg_pe);
  const peGapVsPeer = calcGap(formData.current_pe, formData.peer_avg_pe);
  const evGapVs5Yr = calcGap(formData.current_ev_ebitda, formData.five_yr_avg_ev_ebitda);
  const evGapVsPeer = calcGap(formData.current_ev_ebitda, formData.peer_avg_ev_ebitda);

  // Live required EPS growth estimate
  // (1 + 0.20)^3 = 1.728. Target PAT multiplier = 1.728 / ((1 + pe_change/100)^3 * (1 + div/100)^3)
  const peMultiplier = Math.pow(1 + (formData.expected_pe_change_annualized_pct || 0) / 100, 3);
  const divMultiplier = Math.pow(1 + (formData.dividend_yield_pct || 0) / 100, 3);
  const reqEpsMultiplier = 1.728 / (peMultiplier * divMultiplier);
  const liveReqEpsCagr = (Math.pow(Math.max(0.01, reqEpsMultiplier), 1 / 3) - 1) * 100;

  const getVerdictStyle = (verdict) => {
    switch (verdict) {
      case 'BUY - HIGH CONVICTION':
        return { badge: 'badge-success', bg: 'rgba(16, 185, 129, 0.1)', border: '#10b981', text: '#10b981' };
      case 'BUY - SPECULATIVE':
        return { badge: 'badge-primary', bg: 'rgba(99, 102, 241, 0.12)', border: '#6366f1', text: '#818cf8' };
      case 'HOLD - FAIR VALUE':
        return { badge: 'badge-warning', bg: 'rgba(245, 158, 11, 0.1)', border: '#f59e0b', text: '#f59e0b' };
      case 'AVOID - OVERVALUED':
        return { badge: 'badge-danger', bg: 'rgba(244, 63, 94, 0.1)', border: '#f43f5e', text: '#f43f5e' };
      case 'AVOID - STORY CONTRADICTION':
      default:
        return { badge: 'badge-danger', bg: 'rgba(225, 29, 72, 0.15)', border: '#e11d48', text: '#fb7185' };
    }
  };

  return (
    <div className="phase3-container" id="phase3-view-root">
      {/* Top Banner / Header */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span className="badge badge-primary" style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', fontSize: '11px' }}>
                PHASE 3 GATEKEEPER
              </span>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Valuation Gap, 20% Hurdle Return Path & Story Contradiction Scan (Checks A–C)
              </span>
            </div>
            <h2 style={{ fontSize: '24px', margin: 0, color: 'var(--text-primary)' }}>
              Phase 3: Valuation & Story Confirmation
            </h2>
            <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Protects capital from paying euphoric prices and exposes fabricated management narratives. <em>"Never let a great company become an expensive mistake."</em>
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setFormData(defaultPhase3Input());
                setContradictionToggles({ EXPANSION_LIE: false, VENDOR_RISK: false, GUIDANCE_GAP: false, TONE_SHIFT: false });
                setEvaluation(null);
              }}
              title="Reset fields to blank template"
            >
              <RotateCcw size={14} /> Reset
            </button>

            <button
              id="btn-run-phase3-evaluation"
              className="btn btn-primary"
              onClick={handleRunEvaluation}
              disabled={loading}
              style={{ padding: '10px 22px', fontSize: '14px', background: 'linear-gradient(135deg, #10b981, #047857)' }}
            >
              {loading ? (
                <>Evaluating Phase 3...</>
              ) : (
                <>
                  <Play size={16} fill="currentColor" /> Run Phase 3 Engine
                </>
              )}
            </button>
          </div>
        </div>

        {/* Status / Error feedback */}
        {statusMsg && (
          <div className="alert alert-success" style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} /> {statusMsg}
          </div>
        )}
        {error && (
          <div className="alert alert-danger" style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {/* Canonical Fixture Quick-Loaders */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <Sparkles size={14} color="#10b981" />
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Load Canonical Test Case Fixtures:
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              id="btn-fixture-high-conviction"
              className="btn btn-secondary btn-xs"
              onClick={() => handleLoadFixture('high_conviction_buy')}
              disabled={loadingFixture}
              style={{ borderLeft: '3px solid #10b981' }}
            >
              🟢 BUY - High Conviction
            </button>
            <button
              id="btn-fixture-speculative"
              className="btn btn-secondary btn-xs"
              onClick={() => handleLoadFixture('speculative_buy')}
              disabled={loadingFixture}
              style={{ borderLeft: '3px solid #6366f1' }}
            >
              🔵 BUY - Speculative
            </button>
            <button
              id="btn-fixture-fair-value"
              className="btn btn-secondary btn-xs"
              onClick={() => handleLoadFixture('fair_value_hold')}
              disabled={loadingFixture}
              style={{ borderLeft: '3px solid #f59e0b' }}
            >
              🟡 HOLD - Fair Value
            </button>
            <button
              id="btn-fixture-overvalued"
              className="btn btn-secondary btn-xs"
              onClick={() => handleLoadFixture('overvalued_avoid')}
              disabled={loadingFixture}
              style={{ borderLeft: '3px solid #f43f5e' }}
            >
              🔴 AVOID - Overvalued
            </button>
            <button
              id="btn-fixture-contradiction"
              className="btn btn-secondary btn-xs"
              onClick={() => handleLoadFixture('story_contradiction_avoid')}
              disabled={loadingFixture}
              style={{ borderLeft: '3px solid #e11d48' }}
            >
              ⛔ AVOID - Story Contradiction
            </button>
          </div>
        </div>
      </div>

      {/* Target Config & Prerequisites Card */}
      <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '14px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Target size={16} color="var(--color-primary)" />
          Target Identification & Gatekeeper Clearance
        </h3>
        <div className="grid-3" style={{ gap: '16px' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>Company Ticker / Symbol</label>
            <input
              id="input-phase3-ticker"
              type="text"
              value={formData.ticker}
              onChange={(e) => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
              placeholder="e.g. INFY, TCS, TITAN"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>Company Legal Name</label>
            <input
              id="input-phase3-company-name"
              type="text"
              value={formData.company_name || ''}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              placeholder="e.g. Titan Company Ltd"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>
              Phase 2 Result ID (Prerequisite)
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                id="input-phase3-p2-id"
                type="text"
                value={phase2Id}
                onChange={(e) => setPhase2Id(e.target.value)}
                placeholder="Optional or valid P2 ID"
                style={{ flex: 1, padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
              />
              {onSwitchToPhase2 && (
                <button
                  type="button"
                  className="btn btn-secondary btn-xs"
                  onClick={onSwitchToPhase2}
                  title="Navigate back to Phase 2"
                >
                  <ArrowRight size={12} /> P2
                </button>
              )}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
              Must have achieved <strong>CLEARED TO PHASE 3</strong> in Phase 2 to be evaluated.
            </span>
          </div>
        </div>
      </div>

      {/* 3 Step Interactive Work Area */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', marginBottom: '28px' }}>
        
        {/* CHECK A: Valuation Gap Analysis */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Calculator size={18} color="#6366f1" />
              <h3 style={{ fontSize: '16px', margin: 0 }}>Check A: Valuation Gap</h3>
            </div>
            <span className="badge badge-secondary" style={{ fontSize: '11px' }}>Multiple Comparison</span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Compares Current P/E and EV/EBITDA against 5-Year Historical Medians and Peer Group averages.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Current Stock Price (₹)</label>
                <input
                  id="input-current-price"
                  type="number"
                  step="any"
                  value={formData.current_price ?? ''}
                  onChange={(e) => setFormData({ ...formData, current_price: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Current P/E Ratio</label>
                <input
                  id="input-current-pe"
                  type="number"
                  step="any"
                  value={formData.current_pe ?? ''}
                  onChange={(e) => setFormData({ ...formData, current_pe: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>5-Yr Avg P/E</label>
                <input
                  id="input-five-yr-pe"
                  type="number"
                  step="any"
                  value={formData.five_yr_avg_pe ?? ''}
                  onChange={(e) => setFormData({ ...formData, five_yr_avg_pe: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Peer Group Avg P/E</label>
                <input
                  id="input-peer-pe"
                  type="number"
                  step="any"
                  value={formData.peer_avg_pe ?? ''}
                  onChange={(e) => setFormData({ ...formData, peer_avg_pe: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>EV/EBITDA</label>
                <input
                  id="input-current-ev"
                  type="number"
                  step="any"
                  value={formData.current_ev_ebitda ?? ''}
                  onChange={(e) => setFormData({ ...formData, current_ev_ebitda: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>5Y EV/EBITDA</label>
                <input
                  id="input-five-yr-ev"
                  type="number"
                  step="any"
                  value={formData.five_yr_avg_ev_ebitda ?? ''}
                  onChange={(e) => setFormData({ ...formData, five_yr_avg_ev_ebitda: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Peer EV/EBITDA</label>
                <input
                  id="input-peer-ev"
                  type="number"
                  step="any"
                  value={formData.peer_avg_ev_ebitda ?? ''}
                  onChange={(e) => setFormData({ ...formData, peer_avg_ev_ebitda: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
            </div>

            {/* Live Gap Preview Box */}
            <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px dashed var(--border-subtle)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '8px', borderRadius: '8px' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>P/E Gap vs 5-Yr</span>
                <div style={{ fontSize: '14px', fontWeight: 600, color: peGapVs5Yr > 35 ? '#f43f5e' : peGapVs5Yr > 15 ? '#f59e0b' : '#10b981' }}>
                  {peGapVs5Yr !== null ? `${peGapVs5Yr > 0 ? '+' : ''}${peGapVs5Yr}%` : '—'}
                </div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '8px', borderRadius: '8px' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>P/E Gap vs Peer</span>
                <div style={{ fontSize: '14px', fontWeight: 600, color: peGapVsPeer > 35 ? '#f43f5e' : peGapVsPeer > 15 ? '#f59e0b' : '#10b981' }}>
                  {peGapVsPeer !== null ? `${peGapVsPeer > 0 ? '+' : ''}${peGapVsPeer}%` : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CHECK B: The 20% Hurdle Return Path */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={18} color="#10b981" />
              <h3 style={{ fontSize: '16px', margin: 0 }}>Check B: 20% Return Path</h3>
            </div>
            <span className="badge badge-success" style={{ fontSize: '11px' }}>3-Yr Hurdle</span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Tests if the company can realistically generate <strong>20% CAGR</strong> (+72.8% return) without requiring miraculous earnings growth.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Dividend Yield (%)</label>
                <input
                  id="input-div-yield"
                  type="number"
                  step="any"
                  value={formData.dividend_yield_pct ?? ''}
                  onChange={(e) => setFormData({ ...formData, dividend_yield_pct: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Historical 3-Yr EPS CAGR (%)</label>
                <input
                  id="input-hist-eps-cagr"
                  type="number"
                  step="any"
                  value={formData.historical_eps_growth_3y_cagr ?? ''}
                  onChange={(e) => setFormData({ ...formData, historical_eps_growth_3y_cagr: e.target.value === '' ? null : Number(e.target.value) })}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Expected Annualized P/E Re-rating (%)</label>
              <input
                id="input-pe-rerating"
                type="number"
                step="any"
                value={formData.expected_pe_change_annualized_pct ?? 0.0}
                onChange={(e) => setFormData({ ...formData, expected_pe_change_annualized_pct: e.target.value === '' ? 0 : Number(e.target.value) })}
                placeholder="0% = Multiple neutral; -5% = De-rating"
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
              />
              <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', display: 'block', marginTop: '3px' }}>
                Note: Rule prohibits relying on &gt;=20% multiple expansion.
              </span>
            </div>

            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Claimed Growth Narrative</label>
              <textarea
                id="input-growth-narrative"
                rows={2}
                value={formData.claimed_growth_narrative || ''}
                onChange={(e) => setFormData({ ...formData, claimed_growth_narrative: e.target.value })}
                placeholder="Management guidance / expansion story..."
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)', color: '#fff', fontSize: '12px' }}
              />
            </div>

            {/* Live Return Path Preview Box */}
            <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px dashed var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Estimated Required EPS CAGR</span>
                <div style={{ fontSize: '15px', fontWeight: 600, color: liveReqEpsCagr > 25 ? '#f43f5e' : liveReqEpsCagr > 18 ? '#f59e0b' : '#10b981' }}>
                  {isFinite(liveReqEpsCagr) ? `${liveReqEpsCagr.toFixed(1)}% / yr` : '—'}
                </div>
              </div>
              <span
                className={`badge ${
                  liveReqEpsCagr <= (formData.historical_eps_growth_3y_cagr || 0) + 3
                    ? 'badge-success'
                    : liveReqEpsCagr <= 25
                    ? 'badge-warning'
                    : 'badge-danger'
                }`}
                style={{ fontSize: '11px' }}
              >
                {liveReqEpsCagr <= (formData.historical_eps_growth_3y_cagr || 0) + 3
                  ? 'PROBABLE'
                  : liveReqEpsCagr <= 25
                  ? 'AGGRESSIVE'
                  : 'MIRACULOUS'}
              </span>
            </div>
          </div>
        </div>

        {/* CHECK C: The 4 Great Contradictions Scan */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={18} color="#f43f5e" />
              <h3 style={{ fontSize: '16px', margin: 0 }}>Check C: Story Contradictions</h3>
            </div>
            <span className="badge badge-danger" style={{ fontSize: '11px' }}>Integrity Scan</span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Uncovers disconnects between management narrative and verified audit/operational numbers.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
            {/* Contradiction 1: The Expansion Lie */}
            <div
              onClick={() =>
                handleToggleContradiction(
                  'EXPANSION_LIE',
                  'Claimed 50% capacity expansion',
                  'Fixed assets grew by only 2.1% and inventory holding days rose from 38 to 68 days.'
                )
              }
              style={{
                padding: '10px',
                borderRadius: '8px',
                border: `1px solid ${contradictionToggles.EXPANSION_LIE ? '#f43f5e' : 'var(--border-subtle)'}`,
                background: contradictionToggles.EXPANSION_LIE ? 'rgba(244, 63, 94, 0.12)' : 'rgba(255,255,255,0.02)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: contradictionToggles.EXPANSION_LIE ? '#f43f5e' : 'var(--text-primary)' }}>
                  1. The Expansion Lie
                </span>
                <span className={`badge ${contradictionToggles.EXPANSION_LIE ? 'badge-danger' : 'badge-secondary'}`} style={{ fontSize: '10px' }}>
                  {contradictionToggles.EXPANSION_LIE ? 'FLAGGED' : 'CLEAR'}
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                Capacity claimed without matching Fixed Asset growth and surging inventory days.
              </p>
            </div>

            {/* Contradiction 2: The Vendor Risk */}
            <div
              onClick={() =>
                handleToggleContradiction(
                  'VENDOR_RISK',
                  'Long-term sticky vendor partnership',
                  'Vendor contract in active litigation dispute; 35% of product volume exposed.'
                )
              }
              style={{
                padding: '10px',
                borderRadius: '8px',
                border: `1px solid ${contradictionToggles.VENDOR_RISK ? '#f43f5e' : 'var(--border-subtle)'}`,
                background: contradictionToggles.VENDOR_RISK ? 'rgba(244, 63, 94, 0.12)' : 'rgba(255,255,255,0.02)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: contradictionToggles.VENDOR_RISK ? '#f43f5e' : 'var(--text-primary)' }}>
                  2. The Vendor Risk
                </span>
                <span className={`badge ${contradictionToggles.VENDOR_RISK ? 'badge-danger' : 'badge-secondary'}`} style={{ fontSize: '10px' }}>
                  {contradictionToggles.VENDOR_RISK ? 'FLAGGED' : 'CLEAR'}
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                Silent cancellation or legal dispute with key exclusive customer or supplier.
              </p>
            </div>

            {/* Contradiction 3: The Guidance Gap */}
            <div
              onClick={() =>
                handleToggleContradiction(
                  'GUIDANCE_GAP',
                  'Management 25% revenue growth guidance',
                  'Actual delivered revenue grew only 9.4% in FY23 and 8.1% in FY24.'
                )
              }
              style={{
                padding: '10px',
                borderRadius: '8px',
                border: `1px solid ${contradictionToggles.GUIDANCE_GAP ? '#f43f5e' : 'var(--border-subtle)'}`,
                background: contradictionToggles.GUIDANCE_GAP ? 'rgba(244, 63, 94, 0.12)' : 'rgba(255,255,255,0.02)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: contradictionToggles.GUIDANCE_GAP ? '#f43f5e' : 'var(--text-primary)' }}>
                  3. The Guidance Gap
                </span>
                <span className={`badge ${contradictionToggles.GUIDANCE_GAP ? 'badge-danger' : 'badge-secondary'}`} style={{ fontSize: '10px' }}>
                  {contradictionToggles.GUIDANCE_GAP ? 'FLAGGED' : 'CLEAR'}
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                Management consistently missed stated guidance by &gt;10% for 2+ consecutive cycles.
              </p>
            </div>

            {/* Contradiction 4: The Tone Shift */}
            <div
              onClick={() =>
                handleToggleContradiction(
                  'TONE_SHIFT',
                  'Stable competitive moat',
                  'Abrupt tone shift in MD&A from product innovation to blaming industry headwinds and raw material inflation.'
                )
              }
              style={{
                padding: '10px',
                borderRadius: '8px',
                border: `1px solid ${contradictionToggles.TONE_SHIFT ? '#f43f5e' : 'var(--border-subtle)'}`,
                background: contradictionToggles.TONE_SHIFT ? 'rgba(244, 63, 94, 0.12)' : 'rgba(255,255,255,0.02)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: contradictionToggles.TONE_SHIFT ? '#f43f5e' : 'var(--text-primary)' }}>
                  4. The Tone Shift
                </span>
                <span className={`badge ${contradictionToggles.TONE_SHIFT ? 'badge-danger' : 'badge-secondary'}`} style={{ fontSize: '10px' }}>
                  {contradictionToggles.TONE_SHIFT ? 'FLAGGED' : 'CLEAR'}
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                Sudden shift in MD&A commentary from unit metrics to macro blame and regulatory excuses.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* EVALUATION RESULTS DISPLAY */}
      {evaluation && (
        <div className="glass-panel" id="phase3-results-container" style={{ padding: '24px', marginBottom: '32px' }}>
          {/* Hero Verdict Banner */}
          {(() => {
            const vStyle = getVerdictStyle(evaluation.verdict);
            return (
              <div
                style={{
                  background: vStyle.bg,
                  border: `2px solid ${vStyle.border}`,
                  borderRadius: '14px',
                  padding: '24px',
                  marginBottom: '24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  {evaluation.verdict.startsWith('BUY') ? (
                    <CheckCircle2 size={44} color={vStyle.text} />
                  ) : evaluation.verdict.startsWith('HOLD') ? (
                    <AlertTriangle size={44} color={vStyle.text} />
                  ) : (
                    <XCircle size={44} color={vStyle.text} />
                  )}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
                        PHASE 3 FINAL GATEKEEPER DECISION:
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        ID: {evaluation.result_id}
                      </span>
                    </div>
                    <h2 style={{ fontSize: '26px', margin: 0, color: vStyle.text, fontWeight: 800 }}>
                      {evaluation.verdict}
                    </h2>
                    <p style={{ fontSize: '14px', color: 'var(--text-primary)', margin: '6px 0 0', maxWidth: '780px' }}>
                      {evaluation.why_verdict || evaluation.verdict_summary}
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '180px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Check A (Valuation):</span>
                    <strong style={{ color: (evaluation.valuation?.overall_status || evaluation.valuation?.status) === 'FAIR' ? '#10b981' : '#f59e0b' }}>
                      {evaluation.valuation?.overall_status || evaluation.valuation?.status || 'N/A'}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Check B (20% Hurdle):</span>
                    <strong style={{ color: (evaluation.return_path?.probability || evaluation.return_path_analysis?.probability) === 'PROBABLE' ? '#10b981' : '#f43f5e' }}>
                      {evaluation.return_path?.probability || evaluation.return_path_analysis?.probability || 'N/A'}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Check C (Story Scan):</span>
                    <strong style={{ color: (evaluation.story_scan?.has_fatal_contradiction ?? evaluation.story_scan_analysis?.has_fatal_contradiction) ? '#f43f5e' : '#10b981' }}>
                      {(evaluation.story_scan?.has_fatal_contradiction ?? evaluation.story_scan_analysis?.has_fatal_contradiction) ? 'CONTRADICTION' : 'CLEARED'}
                    </strong>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Apartment Price Tag Analogy Box */}
          <div
            style={{
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              borderRadius: '12px',
              padding: '16px 20px',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '14px',
            }}
          >
            <Building size={24} color="#818cf8" style={{ marginTop: '2px', flexShrink: 0 }} />
            <div>
              <h4 style={{ fontSize: '14px', margin: '0 0 4px', color: '#a5b4fc', fontWeight: 600 }}>
                The "Apartment Price Tag" Analogy (Plain English for Investors)
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>
                {evaluation.valuation_analysis?.apartment_analogy ||
                  `Buying a magnificent luxury apartment at twice the neighborhood price is rarely a smart financial investment. Even if the building is immaculate (Phase 1 & Phase 2 cleared), your returns depend entirely on what price you pay today.`}
              </p>
            </div>
          </div>

          {/* Tab Switcher: Layman Investor vs Analyst Table */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <div className="tabs-nav" style={{ padding: '4px', gap: '4px' }}>
              <button
                className={`tab-btn ${activeTab === 'investor' ? 'active' : ''}`}
                onClick={() => setActiveTab('investor')}
                style={{ fontSize: '13px', padding: '6px 16px' }}
              >
                <FileText size={14} /> Investor Plain English (user.md)
              </button>
              <button
                className={`tab-btn ${activeTab === 'analyst' ? 'active' : ''}`}
                onClick={() => setActiveTab('analyst')}
                style={{ fontSize: '13px', padding: '6px 16px' }}
              >
                <Layers size={14} /> §4 Analyst Working Table
              </button>
            </div>

            <button
              className="btn btn-secondary btn-xs"
              onClick={handleCopyReport}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {copied ? <CheckCircle2 size={13} color="#10b981" /> : <Copy size={13} />}
              {copied ? 'Copied!' : 'Copy Markdown Report'}
            </button>
          </div>

          {/* Tab Content Display */}
          {activeTab === 'investor' ? (
            <div
              style={{
                background: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '10px',
                padding: '20px',
                fontSize: '13.5px',
                lineHeight: 1.6,
                color: 'var(--text-primary)',
                whiteSpace: 'pre-wrap',
                fontFamily: 'system-ui, -apple-system, sans-serif',
              }}
            >
              {evaluation.investor_report}
            </div>
          ) : (
            <div
              style={{
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '10px',
                padding: '20px',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                lineHeight: 1.5,
                color: '#e2e8f0',
                overflowX: 'auto',
                whiteSpace: 'pre-wrap',
              }}
            >
              {evaluation.analyst_markdown}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
