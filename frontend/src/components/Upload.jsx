import { useEffect, useState } from 'react'

function Dropzone({ label, hint, accept, required, file, onFile }) {
  const [drag, setDrag] = useState(false)
  return (
    <div
      className={`dropzone ${drag ? 'drag' : ''} ${file ? 'filled' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]) }}
    >
      <input type="file" accept={accept} onChange={(e) => onFile(e.target.files[0] || null)} aria-label={label} />
      <div className="dz-head">
        <span className="dz-title">{label}</span>
        <span className={`tag ${required ? 'tag-req' : 'tag-opt'}`}>{required ? 'Required' : 'Optional'}</span>
      </div>
      {file ? (
        <>
          <span className="dz-file">📄 {file.name}</span>
          <span className="muted small">{(file.size / 1024).toFixed(0)} KB</span>
          <button className="dz-clear" onClick={(e) => { e.preventDefault(); onFile(null) }}>Remove</button>
        </>
      ) : (
        <span className="muted small">{hint}</span>
      )}
    </div>
  )
}

export default function Upload({ health, healthError, onStart, error }) {
  const [memo, setMemo] = useState(null)
  const [financials, setFinancials] = useState(null)
  const [template, setTemplate] = useState(null)
  const [useSamples, setUseSamples] = useState(false)
  const keyReady = health?.api_key_configured
  const [mode, setMode] = useState('live')
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (health && !keyReady) setMode('demo') }, [health, keyReady])

  const canRun = !healthError && health && (useSamples || (memo && financials))

  async function submit() {
    setBusy(true)
    await onStart({ memo, financials, template, mode, useSamples })
    setBusy(false)
  }

  return (
    <>
      <div className="hero">
        <h2>Screen a new investment opportunity</h2>
        <p>
          Upload the company's investment memo and financial statements. OpenAI extracts the data, the rules engine
          checks every figure, and the TMS template comes back filled in, with a validation report and a source for each value.
        </p>
      </div>

      <div className="card">
        <div className="section-title">1 · Documents</div>
        <div className="grid grid-3">
          <Dropzone label="Investment memo" hint="Drop a PDF here or click to browse" accept=".pdf" required={!useSamples} file={memo} onFile={setMemo} />
          <Dropzone label="Financial statements" hint="Audited accounts + budget, PDF" accept=".pdf" required={!useSamples} file={financials} onFile={setFinancials} />
          <Dropzone label="Screening template" hint="Leave empty to use the standard TMS template (.xlsx)" accept=".xlsx" required={false} file={template} onFile={setTemplate} />
        </div>

        {health?.samples_available && (
          <label className="check" style={{ marginTop: 16 }}>
            <input type="checkbox" checked={useSamples} onChange={(e) => setUseSamples(e.target.checked)} />
            Use the sample AgriWave Ltd documents for any file not uploaded
          </label>
        )}

        <div className="section-title" style={{ marginTop: 26 }}>2 · Extraction mode</div>
        <div className="options">
          <div className="segmented" role="tablist">
            <button className={mode === 'live' ? 'active' : ''} disabled={!keyReady} onClick={() => setMode('live')}>
              Live · OpenAI reads the PDFs
            </button>
            <button className={mode === 'demo' ? 'active' : ''} onClick={() => setMode('demo')}>
              Demo · saved extraction
            </button>
          </div>
        </div>
        {mode === 'demo' && (
          <div className="notice">
            Demo mode skips the AI call and uses a saved, hand-checked extraction of the AgriWave documents, so the uploaded
            PDFs are <strong>not</strong> read. Validation, scoring and template population still run in full.
            {!keyReady && ' To enable live mode, add OPENAI_API_KEY to backend/.env and restart the backend.'}
          </div>
        )}
        {healthError && (
          <div className="notice error">Can't reach the backend. Start it with <code>uvicorn api:app --port 8000</code> in the backend folder.</div>
        )}
        {error && <div className="notice error">{error}</div>}

        <div className="actions">
          <button className="btn btn-primary" disabled={!canRun || busy} onClick={submit}>
            {busy ? <span className="spinner" /> : '▶'} Run screening
          </button>
          {!canRun && health && <span className="muted small">Upload the memo and financial statements, or tick the sample documents option.</span>}
        </div>
      </div>
    </>
  )
}
