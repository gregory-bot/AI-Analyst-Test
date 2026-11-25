import { useEffect, useState } from 'react'

const STEPS = [
  ['Extract', 'OpenAI reads the memo and financial statements into structured data'],
  ['Validate', 'Recompute subtotals, tie the three statements together, test memo claims'],
  ['Score', 'Apply TMS thresholds to the quantitative criteria'],
  ['Populate', 'Write the screening template and audit sheets'],
]

export default function Progress({ job, error, onReset }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [])
  const failed = job.status === 'error'

  return (
    <div className="card">
      <div className="cat-head">
        <div>
          <h2 style={{ fontSize: 20, color: 'var(--red-900)' }}>{failed ? 'Screening failed' : 'Screening in progress…'}</h2>
          <p className="muted small" style={{ marginTop: 4 }}>
            {job.mode === 'live' ? 'Live extraction usually takes 1–2 minutes.' : 'Demo mode finishes in a few seconds.'} · {elapsed}s elapsed
          </p>
        </div>
      </div>
      <div className="steps" style={{ marginTop: 18 }}>
        {STEPS.map(([name, desc], i) => {
          const state = job.status === 'done' || i < job.step ? 'done' : i === job.step && !failed ? 'active' : ''
          return (
            <div className={`step ${state}`} key={name}>
              <div className="step-icon">{state === 'done' ? '✓' : state === 'active' ? <span className="spinner" /> : i + 1}</div>
              <div>
                <strong>{name}</strong>
                <div className="muted small">{i === job.step && job.status === 'running' ? job.message : desc}</div>
              </div>
            </div>
          )
        })}
      </div>
      {(failed || error) && (
        <>
          <div className="notice error">{job.error || error}</div>
          <div className="actions"><button className="btn btn-ghost" onClick={onReset}>← Back</button></div>
        </>
      )}
    </div>
  )
}
