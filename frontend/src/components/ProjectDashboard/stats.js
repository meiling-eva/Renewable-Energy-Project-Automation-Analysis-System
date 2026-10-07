export const SYSTEM_TYPE_META = {
  on_grid: { label: 'On-grid', color: '#2563eb' },
  off_grid: { label: 'Off-grid', color: '#d97706' },
  hybrid: { label: 'Hybrid', color: '#7c3aed' },
}

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0)
const round = (v, digits = 2) => Math.round(v * 10 ** digits) / 10 ** digits

/** Aggregates cleaned project records (`data` objects) into chart-ready series. */
export function buildStats(projects) {
  const total = projects.length
  const pv = projects.reduce((s, p) => s + num(p.pv_capacity_kw), 0)
  const battery = projects.reduce((s, p) => s + num(p.battery_capacity_kwh), 0)
  const inverter = projects.reduce((s, p) => s + num(p.inverter_capacity_kw), 0)
  const gridConnected = projects.filter((p) => p.grid_connected === true).length

  const summary = {
    total,
    pv: round(pv),
    battery: round(battery),
    inverter: round(inverter),
    gridConnectedPct: total ? Math.round((gridConnected / total) * 100) : 0,
    dcAcRatio: inverter ? round(pv / inverter) : null,
  }

  const bySystemType = Object.entries(SYSTEM_TYPE_META)
    .map(([type, meta]) => {
      const items = projects.filter((p) => p.system_type === type)
      return {
        type,
        name: meta.label,
        value: items.length,
        pv: round(items.reduce((s, p) => s + num(p.pv_capacity_kw), 0)),
        fill: meta.color,
      }
    })
    .filter((d) => d.value > 0)

  const states = new Map()
  for (const p of projects) {
    const key = p.state?.trim().toUpperCase() || 'Unknown'
    const entry = states.get(key) ?? { state: key, count: 0, pv: 0, battery: 0, inverter: 0 }
    entry.count += 1
    entry.pv += num(p.pv_capacity_kw)
    entry.battery += num(p.battery_capacity_kwh)
    entry.inverter += num(p.inverter_capacity_kw)
    states.set(key, entry)
  }
  const byState = [...states.values()]
    .map((s) => ({ ...s, pv: round(s.pv), battery: round(s.battery), inverter: round(s.inverter) }))
    .sort((a, b) => b.pv - a.pv)

  const scatterByType = Object.entries(SYSTEM_TYPE_META)
    .map(([type, meta]) => ({
      type,
      name: meta.label,
      color: meta.color,
      points: projects
        .filter((p) => p.system_type === type && p.pv_capacity_kw != null)
        .map((p) => ({
          name: p.project_name,
          pv: num(p.pv_capacity_kw),
          battery: num(p.battery_capacity_kwh),
          inverter: num(p.inverter_capacity_kw),
        })),
    }))
    .filter((s) => s.points.length > 0)

  const months = new Map()
  for (const p of projects) {
    if (!p.created_at) continue
    const key = p.created_at.slice(0, 7) // YYYY-MM
    const entry = months.get(key) ?? { month: key, count: 0, pv: 0 }
    entry.count += 1
    entry.pv += num(p.pv_capacity_kw)
    months.set(key, entry)
  }
  const byMonth = [...months.values()]
    .map((m) => ({ ...m, pv: round(m.pv) }))
    .sort((a, b) => a.month.localeCompare(b.month))

  return { summary, bySystemType, byState, scatterByType, byMonth }
}
