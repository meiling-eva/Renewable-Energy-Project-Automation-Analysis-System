const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

async function request(path, options = {}) {
  const isForm = options.body instanceof FormData
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: isForm ? {} : { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // non-JSON error body
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.status === 204 ? null : res.json()
}

function uploadTo(path, file, commit) {
  const body = new FormData()
  body.append('file', file)
  return request(`${path}?commit=${commit}`, { method: 'POST', body })
}

export const api = {
  health: () => request('/health'),
  listProjects: () => request('/projects'),
  createProject: (data) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id, data) =>
    request(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),
  importProjects: (file, commit = false) => uploadTo('/import/projects', file, commit),
  importComplianceChecks: (file, commit = false) =>
    uploadTo('/import/compliance-checks', file, commit),
}
