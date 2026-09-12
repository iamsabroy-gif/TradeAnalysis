import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  BarChart3,
  PieChart,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  ShieldCheck,
  Layers,
  Sparkles,
  FileText,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Play,
  Building2,
  Wallet,
  Landmark,
  ShieldAlert,
  HelpCircle,
  Copy,
  ExternalLink,
  Plus,
  Trash2,
  ArrowRight
} from 'lucide-react';

export function defaultPhase2Input(initialTicker = '', initialPhase1Id = null) {
  return {
    ticker: initialTicker || '',
    company_name: '',
    as_of_date: new Date().toISOString().slice(0, 10),
    data_basis: 'CONSOLIDATED',
    sector: 'STANDARD',
    regulated_contract_revenue_pct: null,
    is_cyclical: false,
    order_book_driven: false,
    financials: [
      { period: 'FY20', revenue: 100, ebitda: 22, ebit: 18, pat: 14, total_equity: 80, gross_debt: 10, cash_and_equivalents: 15, roce_pct: 18.0, gross_margin_pct: 45.0, ebitda_margin_pct: 22.0, net_margin_pct: 14.0, finance_cost: 1.0, cfo: 18.0 },
      { period: 'FY21', revenue: 125, ebitda: 28, ebit: 23, pat: 18, total_equity: 98, gross_debt: 10, cash_and_equivalents: 22, roce_pct: 19.5, gross_margin_pct: 46.0, ebitda_margin_pct: 22.4, net_margin_pct: 14.4, finance_cost: 1.0, cfo: 24.0 },
      { period: 'FY22', revenue: 155, ebitda: 36, ebit: 30, pat: 23, total_equity: 120, gross_debt: 12, cash_and_equivalents: 30, roce_pct: 20.2, gross_margin_pct: 46.5, ebitda_margin_pct: 23.2, net_margin_pct: 14.8, finance_cost: 1.2, cfo: 30.0 },
      { period: 'FY23', revenue: 190, ebitda: 45, ebit: 38, pat: 29, total_equity: 148, gross_debt: 14, cash_and_equivalents: 42, roce_pct: 21.0, gross_margin_pct: 47.0, ebitda_margin_pct: 23.7, net_margin_pct: 15.3, finance_cost: 1.5, cfo: 38.0 },
      { period: 'FY24', revenue: 235, ebitda: 58, ebit: 49, pat: 38, total_equity: 185, gross_debt: 15, cash_and_equivalents: 58, roce_pct: 22.1, gross_margin_pct: 47.5, ebitda_margin_pct: 24.7, net_margin_pct: 16.2, finance_cost: 1.5, cfo: 48.0 },
    ],
    working_capital: [
      { period: 'FY22', receivable_days: 48, inventory_days: 38, payable_days: 44 },
      { period: 'FY23', receivable_days: 50, inventory_days: 39, payable_days: 45 },
      { period: 'FY24', receivable_days: 49, inventory_days: 38, payable_days: 44 },
    ],
    segments: [],
    debt_refinancing: {
      short_term_borrowings: 5.0,
      long_term_borrowings: 10.0,
      principal_due_next_12m: 2.0,
      undrawn_committed_lines: 12.0,
      quarterly_operating_expenses: null,
    },
    credit_covenants: {
      credit_rating: 'AA',
      rating_outlook: 'STABLE',
      downgrades_last_3y_notches: 0,
      covenant_breach_disclosed: false,
      covenant_waiver_obtained: false,
      average_borrowing_cost_pct: 8.2,
      borrowing_cost_yoy_increase_bps: 0,
      unrated_with_material_debt: false,
      substantially_all_assets_pledged: false,
    },
    loans_given: {
      total_loans_advances_to_entities: 0.0,
      pct_of_net_worth: 0.0,
      is_non_interest_bearing_material: false,
      has_provisions_or_writeoffs: false,
      growing_faster_than_revenue: false,
    },
    guarantees: {
      total_guarantees: 0.0,
      pct_of_net_worth: 0.0,
      guarantees_for_non_subs_material: false,
      guarantee_invoked_or_paid: false,
      borrowed_from_group_undisclosed_terms: false,
    },
    moat: {
      claimed_moat_type: 'SWITCHING_COSTS',
      moat_description: 'High customer integration costs and sticky software ecosystem.',
      realisation_rising_vs_inflation: true,
      licence_subsidy_expiring_within_3y: false,
    },
    competition: {
      market_share_history: { FY22: 18.0, FY23: 19.5, FY24: 21.0 },
      revenue_trailed_industry_3y: false,
      largest_competitor_growing_materially_faster: false,
      disruptive_entrant_or_substitute: false,
      market_share_data_available: true,
    },
    pestle: {
      political: '',
      economic: '',
      social: '',
      technological: '',
      legal: '',
      environmental: '',
    },
    margin_driver_disclosed: true,
    margin_driver_explanation: '',
    provenance: {},
  };
}

export default function Phase2View({ initialTicker, initialPhase1Id, onSwitchToPhase1 }) {
  const [formData, setFormData] = useState(() => defaultPhase2Input(initialTicker, initialPhase1Id));
  const [phase1Id, setPhase1Id] = useState(initialPhase1Id || '');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingFixture, setLoadingFixture] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);
  const [activeTab, setActiveTab] = useState('investor'); // 'investor' | 'analyst' | 'checks'
  const [openSection, setOpenSection] = useState('all');

  // If initialTicker changes from parent
  useEffect(() => {
    if (initialTicker && !formData.ticker) {
      setFormData((prev) => ({ ...prev, ticker: initialTicker }));
    }
    if (initialPhase1Id) {
      setPhase1Id(initialPhase1Id);
    }
  }, [initialTicker, initialPhase1Id]);

  const handleLoadFixture = async (fixtureName) => {
    setLoadingFixture(true);
    setError(null);
    try {
      const res = await fetch(`/api/phase2/fixtures/${fixtureName}`);
      if (!res.ok) {
        throw new Error(`Failed to load fixture: ${res.statusText}`);
      }
      const data = await res.json();
      setFormData(data);
      setStatusMsg(`Loaded canonical fixture: ${fixtureName.toUpperCase()}`);
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingFixture(false);
    }
  };

  const handleRunEvaluation = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        company_input: formData,
        phase1_result_id: phase1Id ? phase1Id.trim() : null,
      };

      const res = await fetch('/api/phase2/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Phase 2 evaluation failed');
      }

      const data = await res.json();
      setEvaluation(data);
      setStatusMsg('Phase 2 Evaluation completed successfully!');
      setTimeout(() => setStatusMsg(null), 4000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFinancialChange = (index, field, value) => {
    const updated = [...formData.financials];
    updated[index] = { ...updated[index], [field]: value === '' ? null : Number(value) };
    setFormData((prev) => ({ ...prev, financials: updated }));
  };

  const handleWorkingCapitalChange = (index, field, value) => {
    const updated = [...formData.working_capital];
    updated[index] = { ...updated[index], [field]: value === '' ? null : Number(value) };
    setFormData((prev) => ({ ...prev, working_capital: updated }));
  };

  const getVerdictStyle = (verdict) => {
    switch (verdict) {
      case 'CLEARED TO PHASE 3':
        return { badge: 'badge-success', bg: 'rgba(16, 185, 129, 0.1)', border: '#10b981', text: '#10b981' };
      case 'REJECT AT PHASE 2':
        return { badge: 'badge-danger', bg: 'rgba(244, 63, 94, 0.1)', border: '#f43f5e', text: '#f43f5e' };
      case 'HOLD — WATCH LIST':
        return { badge: 'badge-warning', bg: 'rgba(245, 158, 11, 0.1)', border: '#f59e0b', text: '#f59e0b' };
      case 'HOLD — INCONCLUSIVE':
      default:
        return { badge: 'badge-secondary', bg: 'rgba(99, 102, 241, 0.1)', border: '#6366f1', text: '#818cf8' };
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PASS':
        return <span className="badge badge-success" style={{ fontSize: '11px' }}>PASS</span>;
      case 'FAIL':
        return <span className="badge badge-danger" style={{ fontSize: '11px' }}>FAIL</span>;
      case 'CONCERN':
        return <span className="badge badge-warning" style={{ fontSize: '11px' }}>CONCERN</span>;
      case 'INCONCLUSIVE':
      default:
        return <span className="badge badge-secondary" style={{ fontSize: '11px', background: 'rgba(148,163,184,0.2)', color: '#cbd5e1' }}>INCONCLUSIVE</span>;
    }
  };

  return (
    <div className="phase2-container" id="phase2-view-root">
      {/* Top Banner / Header */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span className="badge badge-primary" style={{ background: 'linear-gradient(135deg, #6366f1, #3b82f6)', color: '#fff', fontSize: '11px' }}>
                PHASE 2 ENGINE
              </span>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Business Quality, Moat & Capital Allocation (Checks 7–18)
              </span>
            </div>
            <h2 style={{ fontSize: '24px', margin: 0, color: 'var(--text-primary)' }}>
              Phase 2: Business Quality Check
            </h2>
            <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Evaluates <strong>What It Earns</strong>, <strong>What It Owes</strong>, <strong>How It Collects</strong>, and <strong>Why It Lasts</strong> against calibrated industry thresholds.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setFormData(defaultPhase2Input())}
              title="Reset fields to blank template"
            >
              <RotateCcw size={14} /> Reset Form
            </button>
            {onSwitchToPhase1 && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={onSwitchToPhase1}
                title="Go back to Phase 1 Gatekeeper"
              >
                ← Return to Phase 1
              </button>
            )}
          </div>
        </div>

        {/* Canonical Fixtures Quick-Load Bar */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={14} color="var(--color-primary)" />
            LOAD PRESET TEST FIXTURES (CANONICAL SCENARIOS):
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              id="fixture-btn-saas"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '12px', borderColor: 'rgba(16, 185, 129, 0.3)' }}
              onClick={() => handleLoadFixture('saas')}
              disabled={loadingFixture}
            >
              ⚡ SaaS (Asset-Light)
            </button>
            <button
              id="fixture-btn-utility"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '12px', borderColor: 'rgba(59, 130, 246, 0.3)' }}
              onClick={() => handleLoadFixture('utility')}
              disabled={loadingFixture}
            >
              ⚡ Regulated Utility (Infra)
            </button>
            <button
              id="fixture-btn-redflag"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '12px', borderColor: 'rgba(244, 63, 94, 0.3)', color: '#fda4af' }}
              onClick={() => handleLoadFixture('red_flag')}
              disabled={loadingFixture}
            >
              ⚡ Red Flag (Covenant Breach)
            </button>
            <button
              id="fixture-btn-cashhoarder"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '12px', borderColor: 'rgba(245, 158, 11, 0.3)', color: '#fef08a' }}
              onClick={() => handleLoadFixture('cash_hoarder')}
              disabled={loadingFixture}
            >
              ⚡ Cash Hoarder (Affiliate Loans)
            </button>
            <button
              id="fixture-btn-deteriorating"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '12px', borderColor: 'rgba(168, 85, 247, 0.3)' }}
              onClick={() => handleLoadFixture('deteriorating')}
              disabled={loadingFixture}
            >
              ⚡ Deteriorating Leverage
            </button>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {statusMsg && (
        <div style={{ marginBottom: '16px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)', color: '#c7d2fe', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <CheckCircle2 size={16} color="var(--color-primary)" />
          <span>{statusMsg}</span>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: '16px', padding: '12px 16px', borderRadius: '8px', background: 'var(--color-danger-bg)', border: '1px solid var(--color-danger-border)', color: 'var(--color-danger)', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
          <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13.5px' }}>{error}</div>
        </div>
      )}

      {/* Input Sections */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        {/* Section 1: Company & Sector Boundaries (§1) */}
        <div className="field-group">
          <div className="field-group-header">
            <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Building2 size={18} color="var(--color-primary)" />
              1. Company Profile & Sector Boundary Matrix (§1)
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Rules §1 Matrix Calibration</span>
          </div>

          <div className="grid-3" style={{ marginBottom: '14px' }}>
            <div>
              <label>Ticker Symbol *</label>
              <input
                id="p2-input-ticker"
                type="text"
                placeholder="e.g. SAASTECH"
                value={formData.ticker}
                onChange={(e) => setFormData((prev) => ({ ...prev, ticker: e.target.value.toUpperCase() }))}
              />
            </div>
            <div>
              <label>Company Name</label>
              <input
                id="p2-input-company-name"
                type="text"
                placeholder="e.g. CloudScale Software Ltd"
                value={formData.company_name || ''}
                onChange={(e) => setFormData((prev) => ({ ...prev, company_name: e.target.value }))}
              />
            </div>
            <div>
              <label>As of Date</label>
              <input
                id="p2-input-as-of-date"
                type="date"
                value={formData.as_of_date}
                onChange={(e) => setFormData((prev) => ({ ...prev, as_of_date: e.target.value }))}
              />
            </div>
          </div>

          <div className="grid-3" style={{ marginBottom: '14px' }}>
            <div>
              <label>Sector Category (Boundary Matrix)</label>
              <select
                id="p2-select-sector"
                value={formData.sector}
                onChange={(e) => setFormData((prev) => ({ ...prev, sector: e.target.value }))}
              >
                <option value="ASSET_LIGHT">ASSET_LIGHT (IT, Software, FMCG Asset-Light)</option>
                <option value="STANDARD">STANDARD (General Manufacturing, Auto, Retail)</option>
                <option value="CAPITAL_INTENSIVE">CAPITAL_INTENSIVE (Commodity, Real Estate, Cement)</option>
                <option value="REGULATED_UTILITY">REGULATED_UTILITY (Power Grid, Concessions, Utilities)</option>
              </select>
            </div>

            <div>
              <label>
                Regulated / Long-Term Contract Revenue %
                {Number(formData.regulated_contract_revenue_pct) >= 70 && (
                  <span style={{ color: '#38bdf8', fontSize: '11px', marginLeft: '6px' }}>
                    (Shift to Regulated Utility Active!)
                  </span>
                )}
              </label>
              <input
                id="p2-input-regulated-rev"
                type="number"
                placeholder="e.g. 75"
                min="0"
                max="100"
                value={formData.regulated_contract_revenue_pct ?? ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    regulated_contract_revenue_pct: e.target.value === '' ? null : parseFloat(e.target.value),
                  }))
                }
              />
            </div>

            <div>
              <label>Linked Phase 1 Result ID (Optional)</label>
              <input
                id="p2-input-phase1-id"
                type="text"
                placeholder="Leave blank or enter Phase 1 result_id"
                value={phase1Id}
                onChange={(e) => setPhase1Id(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginTop: '10px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                id="p2-check-cyclical"
                type="checkbox"
                style={{ width: 'auto' }}
                checked={formData.is_cyclical}
                onChange={(e) => setFormData((prev) => ({ ...prev, is_cyclical: e.target.checked }))}
              />
              <span>Cyclical Industry (applies 3-year trailing trend rule)</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                id="p2-check-orderbook"
                type="checkbox"
                style={{ width: 'auto' }}
                checked={formData.order_book_driven}
                onChange={(e) => setFormData((prev) => ({ ...prev, order_book_driven: e.target.checked }))}
              />
              <span>Order-Book Driven (applies execution cycle adjustments)</span>
            </label>
          </div>
        </div>

        {/* Section 2: Group A — What It Earns (Financials Table) */}
        <div className="field-group">
          <div className="field-group-header">
            <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={18} color="#10b981" />
              2. Group A — What It Earns (Financials Series FY20–FY24)
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Checks 7 (RoCE), 8 (Margin Trajectory), 9 (Reinvestment), 10 (Segments)</span>
          </div>

          <div style={{ overflowX: 'auto', marginBottom: '16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '8px 6px' }}>Period</th>
                  <th style={{ padding: '8px 6px' }}>Revenue (₹ Cr)</th>
                  <th style={{ padding: '8px 6px' }}>EBITDA (₹ Cr)</th>
                  <th style={{ padding: '8px 6px' }}>EBIT (₹ Cr)</th>
                  <th style={{ padding: '8px 6px' }}>PAT (₹ Cr)</th>
                  <th style={{ padding: '8px 6px' }}>RoCE %</th>
                  <th style={{ padding: '8px 6px' }}>Gross Mgn %</th>
                  <th style={{ padding: '8px 6px' }}>Equity (₹ Cr)</th>
                  <th style={{ padding: '8px 6px' }}>Debt (₹ Cr)</th>
                  <th style={{ padding: '8px 6px' }}>Cash (₹ Cr)</th>
                </tr>
              </thead>
              <tbody>
                {formData.financials.map((row, idx) => (
                  <tr key={row.period || idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '6px 4px', fontWeight: 600 }}>{row.period}</td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '70px' }}
                        value={row.revenue ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'revenue', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '60px' }}
                        value={row.ebitda ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'ebitda', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '60px' }}
                        value={row.ebit ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'ebit', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '60px' }}
                        value={row.pat ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'pat', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        step="0.1"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '55px', color: '#34d399' }}
                        value={row.roce_pct ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'roce_pct', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        step="0.1"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '55px' }}
                        value={row.gross_margin_pct ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'gross_margin_pct', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '65px' }}
                        value={row.total_equity ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'total_equity', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '60px' }}
                        value={row.gross_debt ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'gross_debt', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '6px 4px' }}>
                      <input
                        type="number"
                        style={{ padding: '4px 6px', fontSize: '12px', minWidth: '60px' }}
                        value={row.cash_and_equivalents ?? ''}
                        onChange={(e) => handleFinancialChange(idx, 'cash_and_equivalents', e.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 3: Group B — What It Owes (Debt, Liquidity, Covenants, Affiliate Loans) */}
        <div className="field-group">
          <div className="field-group-header">
            <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Landmark size={18} color="#f59e0b" />
              3. Group B — What It Owes (Debt, Covenants & Guarantees)
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Checks 11 (Debt/EBITDA), 12 (Refinancing), 13 (Covenants), 14 (Affiliate Loans), 15 (Guarantees)</span>
          </div>

          <div className="grid-3" style={{ marginBottom: '14px' }}>
            <div>
              <label>Short-Term Borrowings (₹ Cr)</label>
              <input
                id="p2-input-st-borrowings"
                type="number"
                value={formData.debt_refinancing?.short_term_borrowings ?? ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    debt_refinancing: {
                      ...prev.debt_refinancing,
                      short_term_borrowings: parseFloat(e.target.value) || 0,
                    },
                  }))
                }
              />
            </div>
            <div>
              <label>Principal Repayment Due Next 12m (₹ Cr)</label>
              <input
                id="p2-input-due-12m"
                type="number"
                value={formData.debt_refinancing?.principal_due_next_12m ?? ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    debt_refinancing: {
                      ...prev.debt_refinancing,
                      principal_due_next_12m: parseFloat(e.target.value) || 0,
                    },
                  }))
                }
              />
            </div>
            <div>
              <label>Credit Rating</label>
              <input
                id="p2-input-credit-rating"
                type="text"
                placeholder="e.g. AAA, AA+, BBB-, Unrated"
                value={formData.credit_covenants?.credit_rating || ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    credit_covenants: {
                      ...prev.credit_covenants,
                      credit_rating: e.target.value,
                    },
                  }))
                }
              />
            </div>
          </div>

          <div className="grid-3" style={{ marginBottom: '14px' }}>
            <div>
              <label>Covenant Breach Disclosed?</label>
              <select
                id="p2-select-covenant-breach"
                value={formData.credit_covenants?.covenant_breach_disclosed ? 'true' : 'false'}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    credit_covenants: {
                      ...prev.credit_covenants,
                      covenant_breach_disclosed: e.target.value === 'true',
                    },
                  }))
                }
              >
                <option value="false">No (Clean)</option>
                <option value="true">Yes (Breach Disclosed — Fail Check 13!)</option>
              </select>
            </div>

            <div>
              <label>Loans & Advances Given to Affiliates (₹ Cr)</label>
              <input
                id="p2-input-loans-given"
                type="number"
                placeholder="0"
                value={formData.loans_given?.total_loans_advances_to_entities ?? ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    loans_given: {
                      ...prev.loans_given,
                      total_loans_advances_to_entities: parseFloat(e.target.value) || 0,
                    },
                  }))
                }
              />
            </div>

            <div>
              <label>Total Guarantees Given (₹ Cr)</label>
              <input
                id="p2-input-guarantees"
                type="number"
                placeholder="0"
                value={formData.guarantees?.total_guarantees ?? ''}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    guarantees: {
                      ...prev.guarantees,
                      total_guarantees: parseFloat(e.target.value) || 0,
                    },
                  }))
                }
              />
            </div>
          </div>
        </div>

        {/* Section 4: Group C & Group D (Working Capital & Moat / Market Share) */}
        <div className="grid-2">
          {/* Group C: Working Capital */}
          <div className="field-group">
            <div className="field-group-header">
              <h3 style={{ fontSize: '15px', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={17} color="#38bdf8" />
                4. Group C — How It Collects (Check 16)
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Working Capital Days</span>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
              <thead>
                <tr style={{ color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '6px 4px' }}>Year</th>
                  <th style={{ padding: '6px 4px' }}>Receivable</th>
                  <th style={{ padding: '6px 4px' }}>Inventory</th>
                  <th style={{ padding: '6px 4px' }}>Payable</th>
                </tr>
              </thead>
              <tbody>
                {formData.working_capital.map((wc, idx) => (
                  <tr key={wc.period || idx}>
                    <td style={{ padding: '4px', fontWeight: 600 }}>{wc.period}</td>
                    <td style={{ padding: '4px' }}>
                      <input
                        type="number"
                        style={{ padding: '3px 6px', fontSize: '12px' }}
                        value={wc.receivable_days ?? ''}
                        onChange={(e) => handleWorkingCapitalChange(idx, 'receivable_days', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '4px' }}>
                      <input
                        type="number"
                        style={{ padding: '3px 6px', fontSize: '12px' }}
                        value={wc.inventory_days ?? ''}
                        onChange={(e) => handleWorkingCapitalChange(idx, 'inventory_days', e.target.value)}
                      />
                    </td>
                    <td style={{ padding: '4px' }}>
                      <input
                        type="number"
                        style={{ padding: '3px 6px', fontSize: '12px' }}
                        value={wc.payable_days ?? ''}
                        onChange={(e) => handleWorkingCapitalChange(idx, 'payable_days', e.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Group D: Moat & Longevity */}
          <div className="field-group">
            <div className="field-group-header">
              <h3 style={{ fontSize: '15px', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldCheck size={17} color="#a855f7" />
                5. Group D — Why It Lasts (Checks 17 & 18)
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Moat & Competition</span>
            </div>

            <div style={{ marginBottom: '10px' }}>
              <label>Claimed Moat Type</label>
              <select
                id="p2-select-moat"
                value={formData.moat?.claimed_moat_type || 'NONE'}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    moat: { ...prev.moat, claimed_moat_type: e.target.value },
                  }))
                }
              >
                <option value="NONE">NONE (No durable advantage)</option>
                <option value="SWITCHING_COSTS">SWITCHING_COSTS (High friction to leave)</option>
                <option value="NETWORK_EFFECTS">NETWORK_EFFECTS (Value grows with users)</option>
                <option value="COST_ADVANTAGE">COST_ADVANTAGE (Lowest structural cost)</option>
                <option value="INTANGIBLE_ASSETS">INTANGIBLE_ASSETS (Patents, Brand, Licences)</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '12.5px' }}>
                <input
                  type="checkbox"
                  style={{ width: 'auto' }}
                  checked={formData.moat?.realisation_rising_vs_inflation ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      moat: { ...prev.moat, realisation_rising_vs_inflation: e.target.checked },
                    }))
                  }
                />
                <span>Pricing Power (Realisation Beats Inflation)</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '12.5px' }}>
                <input
                  type="checkbox"
                  style={{ width: 'auto' }}
                  checked={formData.competition?.revenue_trailed_industry_3y ?? false}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      competition: { ...prev.competition, revenue_trailed_industry_3y: e.target.checked },
                    }))
                  }
                />
                <span>Trailed Industry Growth for 3y</span>
              </label>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
          <button
            id="p2-evaluate-btn"
            className="btn btn-primary"
            style={{ padding: '12px 24px', fontSize: '15px' }}
            onClick={handleRunEvaluation}
            disabled={loading || !formData.ticker}
          >
            <Play size={18} />
            {loading ? 'Evaluating Quality Checks 7–18...' : 'Run Phase 2 Quality Evaluation'}
          </button>
        </div>
      </div>

      {/* Evaluation Results View */}
      {evaluation && evaluation.result && (
        <div className="phase2-results" id="phase2-results-root">
          {/* Verdict Banner Card */}
          {(() => {
            const vStyle = getVerdictStyle(evaluation.result.verdict);
            return (
              <div
                className="glass-panel"
                style={{
                  padding: '24px',
                  marginBottom: '24px',
                  border: `2px solid ${vStyle.border}`,
                  background: vStyle.bg,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <span className={`badge ${vStyle.badge}`} style={{ fontSize: '13px', padding: '6px 14px' }}>
                        {evaluation.result.verdict}
                      </span>
                      <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                        Sector Treatment: <strong>{evaluation.result.sector}</strong>
                      </span>
                      {evaluation.result.phase1_cleared && (
                        <span style={{ fontSize: '12px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', padding: '2px 8px', borderRadius: '4px' }}>
                          Phase 1 Cleared
                        </span>
                      )}
                    </div>

                    <h2 style={{ fontSize: '24px', margin: '4px 0 8px 0', color: 'var(--text-primary)' }}>
                      {evaluation.result.company_name || evaluation.result.ticker}
                    </h2>
                    <p style={{ fontSize: '15px', color: '#e2e8f0', maxWidth: '850px', margin: 0 }}>
                      {evaluation.result.verdict_summary}
                    </p>
                  </div>

                  {/* Summary Metric Counters */}
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ textAlign: 'center', padding: '10px 16px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 700, color: '#10b981' }}>{evaluation.result.passes_count}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>PASSES</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '10px 16px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 700, color: '#f59e0b' }}>{evaluation.result.concerns_count}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CONCERNS</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '10px 16px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 700, color: '#f43f5e' }}>{evaluation.result.fails_count}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>FAILS</div>
                    </div>
                  </div>
                </div>

                {/* Why The Verdict */}
                {evaluation.result.why_the_verdict && evaluation.result.why_the_verdict.length > 0 && (
                  <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                      KEY VERDICT DRIVERS:
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13.5px', color: '#cbd5e1' }}>
                      {evaluation.result.why_the_verdict.map((reason, i) => (
                        <li key={i} style={{ marginBottom: '4px' }}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Results Tabs Switcher */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div className="tabs-nav">
              <button
                id="p2-tab-investor"
                className={`tab-btn ${activeTab === 'investor' ? 'active' : ''}`}
                onClick={() => setActiveTab('investor')}
              >
                <Sparkles size={15} /> Investor Narrative Prose
              </button>
              <button
                id="p2-tab-analyst"
                className={`tab-btn ${activeTab === 'analyst' ? 'active' : ''}`}
                onClick={() => setActiveTab('analyst')}
              >
                <FileText size={15} /> Analyst Deep-Dive Table (§4)
              </button>
              <button
                id="p2-tab-checks"
                className={`tab-btn ${activeTab === 'checks' ? 'active' : ''}`}
                onClick={() => setActiveTab('checks')}
              >
                <Layers size={15} /> 12 Quality Checks Breakdown
              </button>
            </div>
          </div>

          {/* Tab 1: Investor Narrative Prose */}
          {activeTab === 'investor' && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '18px', margin: 0, color: 'var(--text-primary)' }}>
                  Investor Narrative Report
                </h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Plain-English prose format with ₹100 analogy & statutory disclaimer
                </span>
              </div>
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  padding: '20px',
                  borderRadius: '10px',
                  fontSize: '14px',
                  lineHeight: '1.65',
                  color: '#e2e8f0',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                {evaluation.investor_report}
              </div>
            </div>
          )}

          {/* Tab 2: Analyst Technical Working Table */}
          {activeTab === 'analyst' && (
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '18px', margin: 0, color: 'var(--text-primary)' }}>
                  Analyst Internal Working Table (§4 Technical View)
                </h3>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '12px 10px', width: '50px' }}>#</th>
                      <th style={{ padding: '12px 10px', width: '220px' }}>Check</th>
                      <th style={{ padding: '12px 10px', width: '110px' }}>Status</th>
                      <th style={{ padding: '12px 10px' }}>Finding & Metric</th>
                      <th style={{ padding: '12px 10px', width: '180px' }}>Threshold Applied</th>
                      <th style={{ padding: '12px 10px', width: '100px' }}>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evaluation.result.checks.map((c) => (
                      <tr key={c.check_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '12px 10px', fontWeight: 700, color: 'var(--text-muted)' }}>
                          {c.q_number}
                        </td>
                        <td style={{ padding: '12px 10px', fontWeight: 600 }}>
                          {c.title}
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{c.group}</div>
                        </td>
                        <td style={{ padding: '12px 10px' }}>
                          {getStatusBadge(c.status)}
                          {c.trend_modifier_applied && (
                            <div style={{ fontSize: '10px', color: '#38bdf8', marginTop: '2px' }}>
                              Trend Mod. Applied
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>
                          {c.finding}
                          {c.inconclusive_reason && (
                            <div style={{ fontSize: '11.5px', color: 'var(--color-warning)', marginTop: '4px' }}>
                              Reason: {c.inconclusive_reason}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px 10px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                          {c.threshold_applied || '—'}
                        </td>
                        <td style={{ padding: '12px 10px', color: 'var(--text-muted)', fontSize: '12px' }}>
                          {c.source}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: Detailed 12 Checks Breakdown Cards */}
          {activeTab === 'checks' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '16px' }}>
              {evaluation.result.checks.map((c) => (
                <div
                  key={c.check_id}
                  className="glass-panel"
                  style={{
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-primary)' }}>
                        {c.q_number} • {c.group}
                      </span>
                      {getStatusBadge(c.status)}
                    </div>
                    <h4 style={{ fontSize: '15px', margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
                      {c.title}
                    </h4>
                    <p style={{ fontSize: '13px', color: '#cbd5e1', margin: '0 0 10px 0', lineHeight: '1.5' }}>
                      {c.finding}
                    </p>
                  </div>

                  <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                    <div><strong>Threshold:</strong> <code>{c.threshold_applied || 'N/A'}</code></div>
                    {c.what_would_clear && (
                      <div style={{ marginTop: '4px', color: '#93c5fd' }}>
                        <strong>What clears:</strong> {c.what_would_clear}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
