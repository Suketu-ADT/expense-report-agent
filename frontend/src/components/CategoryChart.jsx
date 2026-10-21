import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieIcon } from 'lucide-react';
import Card from './ui/Card';
import EmptyState from './ui/EmptyState';
import { getRunCurrency, formatRunMoney } from '../utils/format';

// Restrained categorical palette: indigo accent first, then muted, distinguishable hues.
const COLORS = ['#635BFF', '#16845B', '#B7791F', '#C43D4B', '#0E7490', '#8B5CF6', '#64748B', '#BE185D'];

export default function CategoryChart({ data, isRunning }) {
  const totals = data?.totals || {};
  const currency = getRunCurrency(data);

  // Category subtotals only: the confirmed_total key is the overall figure, not a category.
  const chartData = Object.entries(totals)
    .filter(([key]) => key !== 'confirmed_total' && totals[key] > 0)
    .map(([name, value]) => ({ name, value }));

  const categorizedSum = chartData.reduce((s, d) => s + d.value, 0);

  return (
    <Card
      id="categories"
      title="Category breakdown"
      description={chartData.length ? 'Confirmed spend by category' : 'Confirmed spend, split by category.'}
      icon={PieIcon}
    >
      {chartData.length === 0 ? (
        <EmptyState icon={PieIcon} title={data ? 'No category data' : isRunning ? 'Waiting for totals…' : 'No data yet'}>
          {data
            ? 'No confirmed category totals were returned for this run.'
            : 'Category totals appear once the Calculation stage completes.'}
        </EmptyState>
      ) : (
        <div className="chart-layout">
          <div className="chart-box" role="img" aria-label={`Donut chart of ${chartData.length} spending categories`}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius="62%"
                  outerRadius="88%"
                  paddingAngle={2}
                  dataKey="value"
                  stroke="var(--surface-primary)"
                  strokeWidth={2}
                  isAnimationActive={false}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [formatRunMoney(value, currency), name]}
                  contentStyle={{
                    backgroundColor: 'var(--surface-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    boxShadow: 'var(--shadow-lg)',
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="chart-center" aria-hidden="true">
              <span className="chart-center-label">Categorised</span>
              <span className="chart-center-value">{formatRunMoney(categorizedSum, currency)}</span>
            </div>
          </div>

          <ul className="legend-list">
            {chartData.map((d, i) => (
              <li key={d.name}>
                <span className="legend-swatch" style={{ background: COLORS[i % COLORS.length] }} aria-hidden="true" />
                <span className="legend-name">{d.name}</span>
                <span className="legend-pct">{categorizedSum > 0 ? `${((d.value / categorizedSum) * 100).toFixed(0)}%` : ''}</span>
                <span className="legend-value">{formatRunMoney(d.value, currency)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
