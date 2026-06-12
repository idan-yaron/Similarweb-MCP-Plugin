import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

// Inlined from Call 1 + Call 2 of sw-channel-mix execution.
// percent_share derived client-side per sw-channel-mix Step 5.
const data = [
  { channel: 'Direct',         current: 24.3, prior: 22.0 },
  { channel: 'Organic Search', current: 33.6, prior: 38.2 },
  { channel: 'Paid Search',    current: 15.4, prior: 12.1 },
  { channel: 'Paid Social',    current:  0.0, prior:  0.0 },
  { channel: 'Organic Social', current:  3.2, prior:  2.8 },
  { channel: 'Display Ads',    current:  9.4, prior:  6.1 },
  { channel: 'Mail',           current:  4.5, prior:  4.7 },
  { channel: 'Affiliates',     current:  6.6, prior:  7.2 },
  { channel: 'Referrals',      current:  2.4, prior:  6.4 },
  { channel: 'Gen AI',         current:  0.6, prior:  0.5 }
];

const enriched = data.map(d => {
  const deltaPp = d.current - d.prior;
  const pctChange = d.prior === 0 ? null : ((d.current - d.prior) / d.prior) * 100;
  let verdict = 'WITHIN NOISE';
  if (pctChange !== null) {
    const abs = Math.abs(pctChange);
    if (abs >= 15) verdict = 'MAJOR';
    else if (abs >= 5) verdict = 'MATERIAL';
  }
  return { ...d, deltaPp, pctChange, verdict };
});

const colorFor = d => (d.deltaPp >= 1.0 ? '#10b981' : d.deltaPp <= -1.0 ? '#ef4444' : '#9ca3af');

function TipBody({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{ background: '#fff', border: '1px solid #d1d5db', padding: 8, fontFamily: 'system-ui', fontSize: 12 }}>
      <div style={{ fontWeight: 600 }}>{row.channel}</div>
      <div>current: {row.current.toFixed(1)}%</div>
      <div>prior:   {row.prior.toFixed(1)}%</div>
      <div>delta:   {row.deltaPp >= 0 ? '+' : ''}{row.deltaPp.toFixed(1)} pp</div>
      <div>change:  {row.pctChange === null ? 'n/a' : `${row.pctChange >= 0 ? '+' : ''}${row.pctChange.toFixed(1)}%`}</div>
      <div style={{ marginTop: 4, fontWeight: 600 }}>{row.verdict}</div>
    </div>
  );
}

export default function Panel() {
  return (
    <div style={{ padding: 16, background: '#fff', color: '#111', fontFamily: 'system-ui' }}>
      <h2 style={{ fontSize: 16, marginBottom: 8 }}>Channel mix: current vs prior period</h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={enriched}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="channel" angle={-30} textAnchor="end" interval={0} height={70} />
          <YAxis label={{ value: 'Share %', angle: -90, position: 'insideLeft' }} />
          <Tooltip content={<TipBody />} />
          <Legend />
          <Bar dataKey="prior"   fill="#9ca3af" name="Prior" />
          <Bar dataKey="current" name="Current">
            {enriched.map((d, i) => <Cell key={i} fill={colorFor(d)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
