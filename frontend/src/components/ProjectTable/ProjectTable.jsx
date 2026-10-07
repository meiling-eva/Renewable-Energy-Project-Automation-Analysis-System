import { useMemo, useState } from 'react'
import { PROJECT_COLUMNS } from './columns'
import './ProjectTable.css'

const PRODUCT_TYPE_LABELS = { pv: 'PV', pv_battery: 'PV + Battery' }

function display(col, value) {
  if (value === null || value === undefined || value === '') return '—'
  if (col.type === 'boolean' && typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (col.type === 'system_type') return String(value).replace(/_/g, '-')
  if (col.type === 'product_type') return PRODUCT_TYPE_LABELS[value] ?? String(value)
  if (col.type === 'segment') return String(value).charAt(0).toUpperCase() + String(value).slice(1)
  if (col.type === 'number' && typeof value === 'number') return value.toLocaleString()
  if (col.type === 'date') return new Date(value).toLocaleDateString()
  return String(value)
}

function compare(a, b) {
  if (a === b) return 0
  if (a === null || a === undefined || a === '') return 1
  if (b === null || b === undefined || b === '') return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

const hasKeys = (obj) => Object.keys(obj ?? {}).length > 0

/**
 * Shows cleaned project rows in a sortable, searchable grid.
 *
 * Props:
 *   projects  array of `{ row, data, errors, warnings }` (as returned by POST /api/import/projects)
 */
function ProjectTable({ projects }) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: null, dir: 1 })
  const [filter, setFilter] = useState('all')

  const invalidCount = projects.filter((p) => hasKeys(p.errors)).length
  const warningCount = projects.filter((p) => !hasKeys(p.errors) && hasKeys(p.warnings)).length

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    let rows = projects
    if (filter === 'errors') rows = rows.filter((p) => hasKeys(p.errors))
    if (filter === 'warnings') rows = rows.filter((p) => hasKeys(p.warnings))
    if (q) {
      rows = rows.filter((p) =>
        Object.values(p.data).some((v) => v !== null && String(v).toLowerCase().includes(q)),
      )
    }
    if (sort.key) {
      rows = [...rows].sort((a, b) => sort.dir * compare(a.data[sort.key], b.data[sort.key]))
    }
    return rows
  }, [projects, query, sort, filter])

  function toggleSort(key) {
    setSort((prev) =>
      prev.key !== key ? { key, dir: 1 } : prev.dir === 1 ? { key, dir: -1 } : { key: null, dir: 1 },
    )
  }

  return (
    <section className="project-table">
      <div className="pt-toolbar">
        <strong>{projects.length} project(s)</strong>
        {invalidCount > 0 && <span className="pt-badge pt-badge-error">{invalidCount} with errors</span>}
        {warningCount > 0 && <span className="pt-badge pt-badge-warn">{warningCount} with warnings</span>}
        {invalidCount === 0 && warningCount === 0 && <span className="pt-badge pt-badge-ok">All valid</span>}
        <span className="pt-spacer" />
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All rows</option>
          <option value="errors">Only errors</option>
          <option value="warnings">Only warnings</option>
        </select>
        <input
          className="pt-search"
          placeholder="Search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="pt-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row</th>
              {PROJECT_COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={col.type === 'number' ? 'pt-num pt-sortable' : 'pt-sortable'}
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                  {sort.key === col.key && (sort.dir === 1 ? ' ▲' : ' ▼')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((p) => (
              <tr key={p.row} className={hasKeys(p.errors) ? 'pt-row-error' : ''}>
                <td className="muted">{p.row}</td>
                {PROJECT_COLUMNS.map((col) => {
                  const error = p.errors?.[col.key]
                  const warning = p.warnings?.[col.key]
                  const classes = [
                    col.type === 'number' ? 'pt-num' : '',
                    error ? 'pt-cell-error' : warning ? 'pt-cell-warn' : '',
                  ].join(' ')
                  return (
                    <td key={col.key} className={classes} title={error ?? warning}>
                      {col.type === 'system_type' && !error && p.data[col.key] ? (
                        <span className={`pt-tag pt-tag-${p.data[col.key]}`}>
                          {display(col, p.data[col.key])}
                        </span>
                      ) : (
                        display(col, p.data[col.key])
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={PROJECT_COLUMNS.length + 1} className="muted pt-empty">
                  No matching projects.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default ProjectTable
