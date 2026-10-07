import { useMemo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { buildStats } from './stats'
import './ProjectDashboard.css'

const fmt = (v, unit) => `${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit ? ` ${unit}` : ''}`

function formatMonth(key) {
  const [year, month] = key.split('-').map(Number)
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}

function KpiCard({ label, value, hint }) {
  return (
    <div className="pd-kpi">
      <div className="pd-kpi-value">{value}</div>
      <div className="pd-kpi-label">{label}</div>
      {hint && <div className="pd-kpi-hint">{hint}</div>}
    </div>
  )
}

function ChartCard({ title, children, wide = false }) {
  return (
    <div className={`pd-card${wide ? ' pd-wide' : ''}`}>
      <h3>{title}</h3>
      {children}
    </div>
  )
}

function ScatterTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="pd-tooltip">
      <strong>{p.name}</strong>
      <div>PV: {fmt(p.pv, 'kW')}</div>
      <div>Battery: {fmt(p.battery, 'kWh')}</div>
      <div>Inverter: {fmt(p.inverter, 'kW')}</div>
    </div>
  )
}

/**
 * Charts and KPIs for cleaned project records.
 *
 * Props:
 *   projects  array of project `data` objects (only valid rows should be passed)
 */
function ProjectDashboard({ projects }) {
  const { summary, bySystemType, byState, scatterByType, byMonth } = useMemo(
    () => buildStats(projects),
    [projects],
  )

  if (projects.length === 0) {
    return <p className="muted">No valid projects to chart yet.</p>
  }

  return (
    <section className="project-dashboard">
      <div className="pd-kpis">
        <KpiCard label="Projects" value={summary.total} />
        <KpiCard label="Total PV" value={fmt(summary.pv, 'kW')} />
        <KpiCard label="Total battery" value={fmt(summary.battery, 'kWh')} />
        <KpiCard label="Total inverter" value={fmt(summary.inverter, 'kW')} />
        <KpiCard label="Grid connected" value={`${summary.gridConnectedPct}%`} />
        <KpiCard
          label="DC/AC ratio"
          value={summary.dcAcRatio ?? '—'}
          hint="Total PV ÷ total inverter"
        />
      </div>

      <div className="pd-grid">
        <ChartCard title="Projects by system type">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={bySystemType}
                dataKey="value"
                nameKey="name"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                label={({ name, value }) => `${name}: ${value}`}
              />
              <Tooltip
                formatter={(value, name, item) => [
                  `${value} project(s), ${fmt((value / summary.total) * 100)}%, ${fmt(item.payload.pv, 'kW')} PV`,
                  name,
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Capacity by state">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={byState} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="state" />
              <YAxis />
              <Tooltip
                formatter={(value, name) => [fmt(value, name.includes('Battery') ? 'kWh' : 'kW'), name]}
              />
              <Legend />
              <Bar dataKey="pv" name="PV (kW)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="inverter" name="Inverter (kW)" fill="#2563eb" radius={[4, 4, 0, 0]} />
              <Bar dataKey="battery" name="Battery (kWh)" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="PV vs battery capacity">
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="pv" name="PV" unit=" kW" />
              <YAxis type="number" dataKey="battery" name="Battery" unit=" kWh" />
              <ZAxis range={[60, 60]} />
              <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              {scatterByType.map((s) => (
                <Scatter key={s.type} name={s.name} data={s.points} fill={s.color} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Projects created per month">
          {byMonth.length === 0 ? (
            <p className="muted pd-empty">No created dates in this file.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={byMonth} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tickFormatter={formatMonth} />
                <YAxis allowDecimals={false} />
                <Tooltip
                  labelFormatter={formatMonth}
                  formatter={(value, _, item) => [`${value} (${fmt(item.payload.pv, 'kW')} PV)`, 'Projects']}
                />
                <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>
    </section>
  )
}

export default ProjectDashboard
