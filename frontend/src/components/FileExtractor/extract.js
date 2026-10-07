export const ACCEPTED_EXTENSIONS = ['.xlsx', '.xls', '.csv', '.json']

function extensionOf(fileName) {
  const dot = fileName.lastIndexOf('.')
  return dot === -1 ? '' : fileName.slice(dot).toLowerCase()
}

function columnsOf(rows) {
  const columns = []
  const seen = new Set()
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!seen.has(key)) {
        seen.add(key)
        columns.push(key)
      }
    }
  }
  return columns
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function toRows(value) {
  if (Array.isArray(value)) {
    return value.map((item) => (isPlainObject(item) ? item : { value: item }))
  }
  if (isPlainObject(value)) return [value]
  return [{ value }]
}

function makeSheet(name, rows) {
  return { name, columns: columnsOf(rows), rows }
}

function extractJson(text) {
  const data = JSON.parse(text)

  // An object whose values are all arrays (e.g. { users: [...], orders: [...] }) becomes one sheet per key.
  if (isPlainObject(data)) {
    const entries = Object.entries(data)
    if (entries.length > 0 && entries.every(([, v]) => Array.isArray(v))) {
      return entries.map(([key, v]) => makeSheet(key, toRows(v)))
    }
  }
  return [makeSheet('data', toRows(data))]
}

async function extractWorkbook(buffer) {
  const XLSX = await import('xlsx')
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true })
  return workbook.SheetNames.map((name) => {
    const rows = XLSX.utils.sheet_to_json(workbook.Sheets[name], { defval: null, raw: true })
    return makeSheet(name, rows)
  })
}

/**
 * Parses an Excel/CSV/JSON file into `{ fileName, fileType, sheets: [{ name, columns, rows }] }`.
 */
export async function extractFile(file) {
  const ext = extensionOf(file.name)
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    throw new Error(`Unsupported file type "${ext || file.name}". Use ${ACCEPTED_EXTENSIONS.join(', ')}.`)
  }

  const sheets = ext === '.json' ? extractJson(await file.text()) : await extractWorkbook(await file.arrayBuffer())

  return { fileName: file.name, fileType: ext.slice(1), sheets }
}

export function formatCell(value) {
  if (value === null || value === undefined) return ''
  if (value instanceof Date) return value.toLocaleString()
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
