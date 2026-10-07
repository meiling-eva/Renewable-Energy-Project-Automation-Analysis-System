import { lazy, Suspense, useMemo, useState } from 'react'
import { api } from './api'
import CleaningReport from './components/CleaningReport'
import FileExtractor from './components/FileExtractor'
import ProjectTable, { COLUMN_LABELS } from './components/ProjectTable'
import './App.css'

const ProjectDashboard = lazy(() => import('./components/ProjectDashboard'))

function App() {
  const [file, setFile] = useState(null)
  const [cleaned, setCleaned] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function clean(source, commit = false) {
    setBusy(true)
    setError('')
    try {
      const result = await api.importProjects(source, commit)
      if (commit) {
        setNotice(`Saved ${result.inserted} project(s) to the database.`)
        // Re-run the preview so saved rows now show as "already in database".
        setCleaned(await api.importProjects(source, false))
      } else {
        setCleaned(result)
      }
    } catch (e) {
      setError(`Cleaning failed: ${e.message}. Is the backend running on port 8000?`)
    } finally {
      setBusy(false)
    }
  }

  function handleExtract(_, source) {
    setFile(source)
    setCleaned(null)
    setNotice('')
    clean(source)
  }

  function handleClear() {
    setFile(null)
    setCleaned(null)
    setError('')
    setNotice('')
  }

  const canSave = cleaned?.report.database_checked && cleaned.report.valid_rows > 0
  const validProjects = useMemo(
    () => (cleaned?.rows ?? []).filter((r) => Object.keys(r.errors).length === 0).map((r) => r.data),
    [cleaned],
  )

  return (
    <main className="container">
      <h1>Renewable Energy Project Automation Analysis Tool</h1>

      <h2>Extract File</h2>
      <FileExtractor onExtract={handleExtract} onClear={handleClear} />

      {busy && <p className="muted">Cleaning data…</p>}
      {error && <p className="error">{error}</p>}
      {notice && <p className="notice">{notice}</p>}

      {cleaned && (
        <>
          <h2>Project Data</h2>
          <ProjectTable projects={cleaned.rows} ></ProjectTable>
          {/*<div className="section-header">*/}
          {/*  <h2>Cleaned Projects</h2>*/}
          {/*  <button type="button" disabled={!canSave || busy} onClick={() => clean(file, true)}>*/}
          {/*    Save {cleaned.report.valid_rows} valid row(s)*/}
          {/*  </button>*/}
          {/*</div>*/}
          {/*<CleaningReport report={cleaned.report} labels={COLUMN_LABELS} />*/}

          <h2>Dashboard</h2>
          <p className="muted">Based on {validProjects.length} valid project(s); rows with errors are excluded.</p>
          <Suspense fallback={<p className="muted">Loading charts…</p>}>
            <ProjectDashboard projects={validProjects} />
          </Suspense>
        </>
      )}
    </main>
  )
}

export default App
