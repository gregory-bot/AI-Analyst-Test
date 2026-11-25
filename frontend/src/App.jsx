import { useEffect, useRef, useState } from 'react'
import { createJob, getHealth, getJob } from './api'
import Upload from './components/Upload'
import Progress from './components/Progress'
import Results from './components/Results'

export default function App() {
  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState(false)
  const [job, setJob] = useState(null)       // latest job status from the API
  const [error, setError] = useState('')
  const timer = useRef(null)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealthError(true))
    return () => clearInterval(timer.current)
  }, [])

  async function start(params) {
    setError('')
    try {
      const { job_id } = await createJob(params)
      setJob({ id: job_id, status: 'queued', step: 0, message: 'Queued', mode: params.mode })
      timer.current = setInterval(async () => {
        try {
          const j = await getJob(job_id)
          setJob(j)
          if (j.status === 'done' || j.status === 'error') clearInterval(timer.current)
        } catch (e) {
          clearInterval(timer.current)
          setError(e.message)
        }
      }, 1200)
    } catch (e) {
      setError(e.message)
    }
  }

  function reset() {
    clearInterval(timer.current)
    setJob(null)
    setError('')
  }

  const view = !job ? 'upload' : job.status === 'done' ? 'results' : 'progress'

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17l6-6 4 4 8-8" /><path d="M14 7h7v7" /></svg>
            </div>
            <div>
              <h1>TMS Screening Assistant</h1>
              <p>Investment memo + financials → validated screening template</p>
            </div>
          </div>
          <div className="health">
            {healthError && <span className="pill"><span className="dot bad" />Backend offline</span>}
            {health && (
              <>
                <span className="pill"><span className="dot ok" />API connected</span>
                <span className="pill">
                  <span className={`dot ${health.api_key_configured ? 'ok' : ''}`} />
                  {health.api_key_configured ? `Claude ready · ${health.model}` : 'No API key · demo mode only'}
                </span>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="container">
        {view === 'upload' && <Upload health={health} healthError={healthError} onStart={start} error={error} />}
        {view === 'progress' && <Progress job={job} error={error} onReset={reset} />}
        {view === 'results' && <Results job={job} onReset={reset} />}
      </main>
    </>
  )
}
