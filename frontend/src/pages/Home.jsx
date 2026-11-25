import { useEffect } from 'react'
import { Arrow, Chart, Check, Shield, Upload } from '../components/Icons'

const STEPS = [
  ['1. Upload the documents', 'Drop in the company’s investment memo and audited financial statements as PDFs. The standard TMS template is used unless you upload your own.'],
  ['2. AI extracts, rules verify', 'AI reads every figure and fact with its source. A rules engine then recomputes subtotals, ties the three statements together and tests every claim in the memo.'],
  ['3. Decide with confidence', 'You get a scored risk matrix, a ranked list of red flags and key DD questions, plus the completed TMS Excel ready for the deal-team meeting.'],
]

const TOOLS = [
  [<Upload key="u" />, 'Screen a Company', 'Upload a memo and financials and run the full screening in one click.', '#/screen'],
  [<Chart key="c" />, 'Results & Risk Matrix', 'TMS score, category weights and the rationale behind every criterion.', '#/results'],
  [<Shield key="s" />, 'Validation Report', 'Every arithmetic and consistency check, ranked by severity, with the gap shown.', '#/results?tab=flags'],
]

export default function Home({ scrollTo }) {
  useEffect(() => {
    if (scrollTo) document.getElementById(scrollTo)?.scrollIntoView({ behavior: 'smooth' })
    else window.scrollTo(0, 0)
  }, [scrollTo])

  return (
    <>
      <section className="hero">
        <div className="wrap hero-grid">
          <div>
            <h1>Screen deals in minutes, not days.</h1>
            <p>
              Investment teams in Africa spend hours copying figures from company memos and audited accounts into
              screening templates, and errors in those source documents slip through. This tool reads the documents,
              checks every number and fills in the TMS screen for you.
            </p>
            <p>
              Every opportunity gets a clear, evidence-backed verdict:{' '}
              <span className="g">actively cultivate</span>, <span className="a">monitor passively</span>, or{' '}
              <span className="r">do not proceed</span>.
            </p>
            <div className="hero-actions">
              <a className="btn btn-primary" href="#/screen">Screen a Company</a>
              <a className="btn btn-outline" href="#/how">See how it works</a>
            </div>
          </div>
          <div className="hero-media">
            <img src="/images/hero-analysis.jpg" alt="Illustration of a financial report with a bar chart, checkmarks and a magnifying glass on a phone" width="626" height="554" />
            <div className="hero-badge">
              <span className="badge-dot"><Check /></span>
            </div>
          </div>
        </div>
      </section>

      <section className="band" id="how">
        <div className="wrap section">
          <h2>How it works</h2>
          <p className="section-lead">From PDF to a validated screening template in three steps. AI does the reading; deterministic rules do the maths, so every number can be traced.</p>
          <div className="cards">
            {STEPS.map(([t, d]) => (
              <div className="tile" key={t}><h3>{t}</h3><p>{d}</p></div>
            ))}
          </div>
        </div>
      </section>

      <section className="wrap section" id="tools">
        <h2>Explore the tools</h2>
        <div className="cards">
          {TOOLS.map(([icon, t, d, href]) => (
            <a className="tile tool" key={t} href={href} style={{ textDecoration: 'none' }}>
              <span className="tool-icon">{icon}</span>
              <h3>{t}</h3>
              <p>{d}</p>
              <span className="tool-link">Open <Arrow /></span>
            </a>
          ))}
        </div>
      </section>
    </>
  )
}
