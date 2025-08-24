import React, { useEffect, useState } from 'react';
import config from '../config';
import { computeProjectCompletion } from '../utils/toolCompletion';

export default function ToolProgressSidebar() {
  const [items, setItems] = useState([]);
  const token = localStorage.getItem('token');

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${config.API_BASE_URL}/tools/overview`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const d = await r.json();
        if (r.ok) setItems(d.items || []);
      } catch (e) {
        // no-op
      }
    })();
  }, []);

  const total = computeProjectCompletion(items);

  return (
    <aside className="tool-progress-side">
      <div className="hdr">Project Completeness: {total}%</div>
      <ul className="lst">
        {items.map(it => (
          <li key={it.tool} className="row">
            <span className="name">{it.tool}</span>
            <span className="pct">{it.percentage || 0}%</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}