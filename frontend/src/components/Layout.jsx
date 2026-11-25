import { useState } from 'react'
import { Close, Logo, Menu } from './Icons'

const LINKS = [
  ['home', 'Home', '#/'],
  ['how', 'How it works', '#/how'],
  ['screen', 'Screen a Company', '#/screen'],
  ['results', 'Results', '#/results'],
]

export function Header({ route }) {
  const [open, setOpen] = useState(false)
  return (
    <header className="header">
      <div className="wrap header-inner">
        <a className="logo" href="#/" onClick={() => setOpen(false)}>
          <span className="logo-mark"><Logo /></span>
          <span>
            <div className="logo-name">TMS Screening</div>
            <div className="logo-sub">AI Investment Analyst</div>
          </span>
        </a>
        <nav className={`nav ${open ? 'open' : ''}`} aria-label="Main">
          {LINKS.map(([id, label, href]) => (
            <a key={id} href={href} className={route === id ? 'active' : ''} onClick={() => setOpen(false)}>{label}</a>
          ))}
        </nav>
        <button className="menu-btn" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? <Close /> : <Menu />}
        </button>
      </div>
    </header>
  )
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <span>© 2026 TMS Screening Assistant · AHL AI Analyst case study</span>
        <strong>Designed by Kipngeno Gregory, Data Scientist</strong>
        <span>All data is fictitious.</span>
      </div>
    </footer>
  )
}
