import './CleaningReport.css'

const sum = (obj) => Object.values(obj ?? {}).reduce((a, b) => a + b, 0)

function CountList({ title, counts, labels }) {
  const entries = Object.entries(counts ?? {})
  if (entries.length === 0) return null
  return (
    <div>
      <h4>{title}</h4>
      <ul>
        {entries.map(([field, count]) => (
          <li key={field}>
            {labels[field] ?? field}: <strong>{count}</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * Summarises what the backend cleaning step did (the `report` from POST /api/import/*).
 *
 * Props:
 *   report  cleaning report object
 *   labels  optional `{ field: label }` used to display field names
 */
function CleaningReport({ report, labels = {} }) {
  const stats = [
    { label: 'Rows in file', value: report.total_rows },
    { label: 'Empty rows removed', value: report.empty_rows_removed },
    { label: 'Duplicates removed', value: report.duplicates_removed },
    { label: 'Missing values filled', value: sum(report.filled_values) },
    { label: 'Units converted', value: sum(report.units_converted) },
    { label: 'Invalid dates', value: report.invalid_dates, tone: report.invalid_dates ? 'bad' : '' },
    { label: 'Valid rows', value: report.valid_rows, tone: 'good' },
    { label: 'Rows with errors', value: report.invalid_rows, tone: report.invalid_rows ? 'bad' : '' },
  ]

  return (
    <section className="cleaning-report">
      <div className="cr-stats">
        {stats.map((s) => (
          <div key={s.label} className={`cr-stat ${s.tone ? `cr-${s.tone}` : ''}`}>
            <div className="cr-value">{s.value}</div>
            <div className="cr-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="cr-details">
        {report.duplicates?.length > 0 && (
          <div>
            <h4>Duplicates removed</h4>
            <ul>
              {report.duplicates.map((d) => (
                <li key={d.row}>
                  Row {d.row}: {d.reason}
                  {d.duplicate_of ? ` (row ${d.duplicate_of})` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
        <CountList title="Missing values" counts={report.missing_values} labels={labels} />
        <CountList title="Filled / inferred" counts={report.filled_values} labels={labels} />
        <CountList title="Units converted" counts={report.units_converted} labels={labels} />
        {report.unmapped_fields?.length > 0 && (
          <div>
            <h4>Columns not found in file</h4>
            <p className="muted">{report.unmapped_fields.map((f) => labels[f] ?? f).join(', ')}</p>
          </div>
        )}
      </div>

      {report.database_checked === false && (
        <p className="muted cr-note">
          Database unavailable: records already in the database were not checked, and saving is disabled.
        </p>
      )}
    </section>
  )
}

export default CleaningReport
