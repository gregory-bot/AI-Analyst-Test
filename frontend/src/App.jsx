import { useEffect, useRef, useState } from 'react'
import { createJob, getHealth, getJob } from './api'
import { Footer, Header } from './components/Layout'
import Upload from './components/Upload'
import Progress from './components/Progress'
import Results from './components/Results'
import Home from './pages/Home'
import { Chart } from './components/Icons'

// Minimal hash router: #/  #/how  #/screen  #/results?tab=flags
function parseHash() {
  const [path, query = ''] = window.location.hash.replace(/^#/, '').split('?')
  const page = { '/screen': 'screen', '/results': 'results', '/how': 'how' }[path] || 'home'
  return { page, tab: new URLSearchParams(query).get('tab') }
}

export default function App() {
  const [route, setRoute] = useState(parseHash)
  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState(false)
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const timer = useRef(null)

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    getHealth().then(setHealth).catch(() => setHealthError(true))
    return () => { window.removeEventListener('hashchange', onHash); clearInterval(timer.current) }
  }, [])

  useEffect(() => { if (route.page !== 'home' && route.page !== 'how') window.scrollTo(0, 0) }, [route.page])

  async function start(params) {
    setError('')
    try {
      const { job_id } = await createJob(params)
      setJob({ id: job_id, status: 'queued', step: 0, message: 'Queued', mode: params.mode })
      timer.current = setInterval(async () => {
        try {
          const j = await getJob(job_id)
          setJob(j)
          if (j.status === 'done') { clearInterval(timer.current); window.location.hash = '#/results' }
          if (j.status === 'error') clearInterval(timer.current)
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
    window.location.hash = '#/screen'
  }

  const running = job && job.status !== 'done'
  const done = job?.status === 'done'

  return (
    <>
      <Header route={route.page} />
      <main>
        {(route.page === 'home' || route.page === 'how') && <Home scrollTo={route.page === 'how' ? 'how' : null} />}

        {route.page === 'screen' && (
          <div className="wrap page">
            {running
              ? <Progress job={job} error={error} onReset={reset} />
              : <Upload health={health} healthError={healthError} onStart={start} error={error} lastDone={done} />}
          </div>
        )}

        {route.page === 'results' && (
          <div className="wrap page">
            {done ? <Results key={job.id} job={job} onReset={reset} initialTab={route.tab} /> : (
              <div className="card empty">
                <span className="tool-icon"><Chart /></span>
                <h2>{running ? 'Screening in progress' : 'No screening yet'}</h2>
                <p className="muted">
                  {running ? 'Your results will appear here as soon as the run finishes.'
                    : 'Upload an investment memo and financial statements to generate a TMS screen, risk matrix and validation report.'}
                </p>
                <a className="btn btn-primary" href="#/screen">{running ? 'View progress' : 'Screen a Company'}</a>
              </div>
            )}
          </div>
        )}
      </main>
      <Footer />
    </>
  )
}
