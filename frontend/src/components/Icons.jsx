const base = { width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }

export const Logo = (p) => <svg {...base} {...p}><path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 15l3.5-4 3 3L20 7" /></svg>
export const Upload = (p) => <svg {...base} {...p}><path d="M12 15V3" /><path d="M7 8l5-5 5 5" /><path d="M20 15v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4" /></svg>
export const Chart = (p) => <svg {...base} {...p}><path d="M3 3v18h18" /><path d="M8 17v-5" /><path d="M13 17V8" /><path d="M18 17v-3" /></svg>
export const Shield = (p) => <svg {...base} {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>
export const Doc = (p) => <svg {...base} {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M8 13h8" /><path d="M8 17h5" /></svg>
export const Arrow = (p) => <svg {...base} width={18} height={18} {...p}><path d="M5 12h14" /><path d="M13 6l6 6-6 6" /></svg>
export const Menu = (p) => <svg {...base} {...p}><path d="M4 7h16" /><path d="M4 12h16" /><path d="M4 17h16" /></svg>
export const Close = (p) => <svg {...base} {...p}><path d="M6 6l12 12" /><path d="M18 6L6 18" /></svg>
export const Check = (p) => <svg {...base} {...p}><path d="M5 12l5 5 9-10" /></svg>
