import { useEffect, useState } from 'react'
import { downloadUrl } from '../api'

const usd = (v) => (v == null ? '–' : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}m` : `$${Math.round(v / 1e3)}k`)
const k = (v) => (v == null ? '–' : `$${(v / 1000).toFixed(1)}m`) // statements are in USD '000
const pct = (v, d = 0) => (v == null ? '–' : `${(v * 100).toFixed(d)}%`)
const verdictClass = (v) => (v?.startsWith('Yes') ? 'v-yes' : v === 'No' ? 'v-no' : 'v-maybe')
const bandClass = (o) => (o > 0.7 ? 'band-high' : o >= 0.5 ? 'band-mid' : 'band-low')

function Gauge({ value, band }) {
  const r = 54, c = 2 * Math.PI * r
  return (
    <div className="gauge">
      <svg width="150" height="150" viewBox="0 0 140 140" role="img" aria-label={`Overall score ${pct(value)}`}>
        <defs>
          <linearGradient id="g" x1="0" x2="1"><stop offset="0" stopColor="#2563eb" /><stop offset="1" stopColor="#60a5fa" /></linearGradient>
        </defs>
        <circle cx="70" cy="70" r={r} fill="none" stroke="#eaf1fe" strokeWidth="14" />
        <circle cx="70" cy="70" r={r} fill="none" stroke="url(#g)" strokeWidth="14" strokeLinecap="round"
          strokeDasharray={`${c * value} ${c}`} transform="rotate(-90 70 70)" />
        <text x="70" y="72" textAnchor="middle" fontSize="30" fontWeight="700" fill="#0b1220">{pct(value)}</text>
        <text x="70" y="92" textAnchor="middle" fontSize="11" fill="#64748b">TMS score</text>
      </svg>
      <div className={`gauge-label ${bandClass(value)}`}>{band}</div>
    </div>
  )
}

function Dots({ score }) {
  if (score == null) return <span className="score-dots na">No info</span>
  return <span className="score-dots" aria-label={`${score} of 3`}>{[1, 2, 3].map((i) => <i key={i} className={i <= score ? 'on' : ''} />)}</span>
}

function Overview({ r }) {
  const s = r.screen
  const cards = [
    ['Impact theory of change', s.impact_toc, s.impact_rationale],
    ['Climate', s.climate, s.climate_rationale],
    ['2X gender alignment', s.two_x, s.two_x_rationale],
    ['Local founder', s.local_founder, s.local_founder_rationale],
    ['Workable security', s.security, s.security_rationale],
  ]
  return (
    <div className="grid" style={{ gap: 20 }}>
      <div className="card">
        <div className="section-title">Business</div>
        <p>{r.company.description}</p>
        <div className="grid grid-2" style={{ marginTop: 18 }}>
          <div>
            <div className="section-title" style={{ fontSize: 13 }}>Management</div>
            {r.company.management.map((p) => (
              <div key={p.name} className="small" style={{ marginBottom: 8 }}>
                <strong>{p.name}</strong> · {p.role}<div className="muted">{p.experience}; {p.prior_employers}</div>
              </div>
            ))}
          </div>
          <div>
            <div className="section-title" style={{ fontSize: 13 }}>Use of proceeds ({usd(r.funding.total)})</div>
            {r.funding.use_of_proceeds.map((u, i) => (
              <div key={i} className="small" style={{ marginBottom: 8 }}>
                <strong>{usd(u.usd)}</strong> <span className={`method ${u.instrument === 'equity' ? 'm-ai' : 'm-rule'}`} style={{ marginLeft: 6 }}>{u.instrument.replaceAll('_', ' ')}</span>
                <div className="muted">{u.purpose}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="grid grid-3">
        {cards.map(([title, v, why]) => (
          <div className="screen-card" key={title}>
            <div className="screen-head"><h4>{title}</h4><span className={`verdict ${verdictClass(v)}`}>{v}</span></div>
            <p className="small muted">{why}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function RiskMatrix({ r }) {
  return (
    <div className="grid" style={{ gap: 20 }}>
      {r.categories.map((cat) => (
        <div className="card" key={cat.name}>
          <div className="cat-head">
            <div>
              <div className="section-title" style={{ margin: 0 }}>{cat.name}</div>
              <span className="muted small">Weight {pct(cat.weight)} · {cat.points}/{cat.max} points</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="bar"><span style={{ width: pct(cat.pct) }} /></div><strong>{pct(cat.pct)}</strong>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th style={{ width: 170 }}>Criterion</th><th style={{ width: 90 }}>Score</th><th style={{ width: 110 }}>Method</th><th>Rationale</th></tr></thead>
              <tbody>
                {r.scores.filter((s) => s.category === cat.name).map((s) => (
                  <tr key={s.criterion}>
                    <td><strong>{s.label}</strong></td>
                    <td><Dots score={s.score} /></td>
                    <td><span className={`method ${s.method === 'Rule-based' ? 'm-rule' : 'm-ai'}`}>{s.method}</span></td>
                    <td>
                      {s.rationale}
                      <div className="muted small" style={{ marginTop: 4 }}>Source: {s.evidence}</div>
                      {s.dd && <div className="dd">DD: {s.dd}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}

function Flags({ r }) {
  const [sev, setSev] = useState('HIGH')
  const shown = r.flags.filter((f) => sev === 'ALL' || f.severity === sev)
  const label = { HIGH: 'High', MEDIUM: 'Medium', INFO: 'Passed', ALL: 'All' }
  return (
    <div>
      <div className="filters">
        {['HIGH', 'MEDIUM', 'INFO', 'ALL'].map((s) => (
          <button key={s} className={`filter ${sev === s ? 'active' : ''}`} onClick={() => setSev(s)}>
            {label[s]} ({s === 'ALL' ? r.flags.length : r.flag_counts[s] || 0})
          </button>
        ))}
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Severity</th><th>Area</th><th>Check</th><th>Year</th><th className="num">Expected</th><th className="num">Reported</th><th>Note</th></tr></thead>
          <tbody>
            {shown.map((f, i) => (
              <tr key={i}>
                <td><span className={`sev sev-${f.severity}`}>{label[f.severity]}</span></td>
                <td className="small">{f.area}</td>
                <td>{f.check}</td>
                <td className="small">{f.year}</td>
                <td className="num small">{String(f.expected ?? '–')}</td>
                <td className="num small">{String(f.reported ?? '–')}</td>
                <td className="small muted">{f.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Financials({ r }) {
  const rows = [
    ['Revenue', (m) => k(m.revenue)], ['Gross margin', (m) => pct(m.gross_margin)],
    ['EBITDA (reported)', (m) => k(m.ebitda_reported)], ['Net profit (reported)', (m) => k(m.pat_reported)],
    ['Loan book', (m) => k(m.loan_book)], ['Borrowings', (m) => k(m.debt)], ['Equity', (m) => k(m.equity)],
    ['Debt : Equity', (m) => (m.debt_to_equity == null ? '–' : `${m.debt_to_equity.toFixed(2)}x`)],
  ]
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>USD</th>{r.metrics.map((m) => <th className="num" key={m.year}>{m.year === '2025F' ? '2025 Budget' : m.year}</th>)}</tr></thead>
        <tbody>
          {rows.map(([name, fn]) => (
            <tr key={name}><td><strong>{name}</strong></td>{r.metrics.map((m) => <td className="num" key={m.year}>{fn(m)}</td>)}</tr>
          ))}
        </tbody>
      </table>
      <p className="muted small" style={{ padding: 12 }}>Figures as reported. The template recalculates subtotals from line items; see Validation for the differences.</p>
    </div>
  )
}

function Notes({ r }) {
  return (
    <div className="grid grid-2">
      <div className="card">
        <div className="section-title">Key due-diligence areas</div>
        <ol className="dd-list">{r.key_dd_areas.map((d, i) => <li key={i}>{d}</li>)}</ol>
      </div>
      <div className="card">
        <div className="section-title">Template fixes applied</div>
        <ol className="dd-list">{r.template_fixes.map((d, i) => <li key={i} className="small">{d}</li>)}</ol>
        <div className="section-title" style={{ marginTop: 20 }}>Run details</div>
        <p className="small muted">
          {r.run.timestamp} · mode: {r.run.mode}{r.run.model ? ` · ${r.run.model}` : ''}
          {r.run.input_tokens ? ` · ${r.run.input_tokens.toLocaleString()} in / ${r.run.output_tokens.toLocaleString()} out tokens` : ''}
        </p>
      </div>
    </div>
  )
}

export default function Results({ job, onReset, initialTab }) {
  const r = job.result
  const [tab, setTab] = useState(initialTab || 'overview')
  useEffect(() => { if (initialTab) setTab(initialTab) }, [initialTab])
  const tabs = [
    ['overview', 'Overview'], ['matrix', 'Risk matrix'],
    ['flags', 'Validation', r.flag_counts.HIGH], ['financials', 'Financials'], ['notes', 'DD & notes'],
  ]
  return (
    <>
      <div className="card">
        <div className="summary">
          <div>
            <span className="muted small">Screening result{job.mode === 'demo' ? ' · demo mode' : ''}</span>
            <div className="company-name">{r.company.name}</div>
            <div className="chips">
              <span className="chip soft">{r.company.sector}</span>
              {r.company.countries.map((c) => (
                <span key={c.name} className={`chip ${c.status === 'Planned' ? 'soft' : ''}`}>{c.name} · {c.tier}{c.status === 'Planned' ? ' (planned)' : ''}</span>
              ))}
            </div>
            <div className="kpis">
              <div className="kpi"><div className="kpi-label">AHL debt ask</div><div className="kpi-value">{usd(r.funding.debt_ask)}</div></div>
              <div className="kpi"><div className="kpi-label">Total raise</div><div className="kpi-value">{usd(r.funding.total)}</div></div>
              <div className="kpi"><div className="kpi-label">High-severity flags</div><div className="kpi-value">{r.flag_counts.HIGH || 0}</div></div>
              <div className="kpi"><div className="kpi-label">Checks passed</div><div className="kpi-value">{r.flag_counts.INFO || 0}/{r.flags.length}</div></div>
            </div>
            <div className="result-actions">
              <a className="btn btn-primary" href={downloadUrl(job.id)}>⬇ Download TMS Excel</a>
              <button className="btn btn-outline" onClick={onReset}>New screening</button>
            </div>
          </div>
          <Gauge value={r.overall} band={r.band} />
        </div>
      </div>

      <div className="tabs" role="tablist">
        {tabs.map(([id, name, count]) => (
          <button key={id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>
            {name}{count ? <span className="count">{count}</span> : null}
          </button>
        ))}
      </div>

      {tab === 'overview' && <Overview r={r} />}
      {tab === 'matrix' && <RiskMatrix r={r} />}
      {tab === 'flags' && <Flags r={r} />}
      {tab === 'financials' && <Financials r={r} />}
      {tab === 'notes' && <Notes r={r} />}
    </>
  )
}
