export const PROJECT_COLUMNS = [
  { key: 'project_name', label: 'Project Name', type: 'text' },
  { key: 'address', label: 'Address', type: 'text' },
  { key: 'city', label: 'City', type: 'text' },
  { key: 'state', label: 'State', type: 'text' },
  { key: 'system_type', label: 'System Type', type: 'system_type' },
  { key: 'segment', label: 'Segment', type: 'segment' },
  { key: 'product_type', label: 'Product Type', type: 'product_type' },
  { key: 'pv_capacity_kw', label: 'PV (kW)', type: 'number' },
  { key: 'battery_capacity_kwh', label: 'Battery (kWh)', type: 'number' },
  { key: 'inverter_capacity_kw', label: 'Inverter (kW)', type: 'number' },
  { key: 'grid_connected', label: 'Grid Connected', type: 'boolean' },
  { key: 'created_at', label: 'Created', type: 'date' },
  { key: 'updated_at', label: 'Updated', type: 'date' },
]

export const COLUMN_LABELS = Object.fromEntries(PROJECT_COLUMNS.map((c) => [c.key, c.label]))
