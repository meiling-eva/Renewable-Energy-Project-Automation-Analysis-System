import { useRef, useState } from 'react'
import { ACCEPTED_EXTENSIONS, extractFile, formatCell } from './extract'
import './FileExtractor.css'

/**
 * Upload an Excel (.xlsx/.xls/.csv) or JSON file and preview its contents as tables.
 *
 * Props:
 *   onExtract(result, file)  called with `{ fileName, fileType, sheets: [{ name, columns, rows }] }`
 *                            and the original File
 *   onClear()          called when the user clears the file
 *   maxPreviewRows     rows shown per sheet in the preview (default 100)
 */
function FileExtractor({ onExtract, onClear, maxPreviewRows = 100 }) {
  const inputRef = useRef(null)
  const [result, setResult] = useState(null)
  const [activeSheet, setActiveSheet] = useState(0)
  const [showData, setShowData] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleFile(file) {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const extracted = await extractFile(file)
      setResult(extracted)
      setActiveSheet(0)
      onExtract?.(extracted, file)
    } catch (e) {
      setResult(null)
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  function handleClear() {
    setResult(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
    onClear?.()
  }

  function handleDownloadJson() {
    const data = result.sheets.length === 1
      ? result.sheets[0].rows
      : Object.fromEntries(result.sheets.map((s) => [s.name, s.rows]))
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = result.fileName.replace(/\.[^.]+$/, '') + '.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  const sheet = result?.sheets[activeSheet]

  return (
    <section className="file-extractor">
      <div
        className={`fe-dropzone${dragging ? ' fe-dragging' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {busy ? 'Extracting…' : <>Drop an Excel or JSON file here, or <u>browse</u></>}
        <div className="fe-hint">{ACCEPTED_EXTENSIONS.join(', ')}</div>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="fe-result">
          <div className="fe-toolbar">
            <strong>{result.fileName}</strong>
            <span className="muted">
              {result.sheets.length} sheet(s) · {sheet.rows.length} row(s) · {sheet.columns.length} column(s)
            </span>
            <span className="fe-spacer" />
            <button type="button" onClick={() => setShowData((v) => !v)}>
              {showData ? 'Hide original data' : 'Show original data'}
            </button>
            <button type="button" onClick={handleDownloadJson}>Download JSON</button>
            <button type="button" className="danger" onClick={handleClear}>Clear</button>
          </div>

          {showData && result.sheets.length > 1 && (
            <div className="fe-tabs">
              {result.sheets.map((s, i) => (
                <button
                  key={s.name}
                  type="button"
                  className={i === activeSheet ? 'fe-tab fe-tab-active' : 'fe-tab'}
                  onClick={() => setActiveSheet(i)}
                >
                  {s.name}
                </button>
              ))}
            </div>
          )}

          {!showData ? null : sheet.rows.length === 0 ? (
            <p className="muted">This sheet is empty.</p>
          ) : (
            <div className="fe-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    {sheet.columns.map((c) => <th key={c}>{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {sheet.rows.slice(0, maxPreviewRows).map((row, i) => (
                    <tr key={i}>
                      <td className="muted">{i + 1}</td>
                      {sheet.columns.map((c) => <td key={c}>{formatCell(row[c])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
              {sheet.rows.length > maxPreviewRows && (
                <p className="muted">Showing first {maxPreviewRows} of {sheet.rows.length} rows.</p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default FileExtractor
