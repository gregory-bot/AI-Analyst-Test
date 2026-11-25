const BASE = import.meta.env.VITE_API_URL || ''

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`)
  return body
}

export const getHealth = () => request('/api/health')
export const getJob = (id) => request(`/api/jobs/${id}`)
export const downloadUrl = (id) => `${BASE}/api/jobs/${id}/download`

export function createJob({ memo, financials, template, mode, useSamples }) {
  const form = new FormData()
  form.append('mode', mode)
  form.append('use_samples', useSamples ? 'true' : 'false')
  if (memo) form.append('memo', memo)
  if (financials) form.append('financials', financials)
  if (template) form.append('template', template)
  return request('/api/jobs', { method: 'POST', body: form })
}
