import { useState } from 'react';
import './Dock.css';

const items = [
  { ic: '◇', lb: 'Map' },
  { ic: '✦', lb: 'AI' },
  { ic: '□', lb: 'Doc' },
  { ic: '≡', lb: 'Ex' },
  { ic: '⌨', lb: 'Code' },
  { ic: '✎', lb: 'Note' },
  { ic: '◈', lb: 'Mind' },
  { ic: '❐', lb: 'Res' },
  { ic: '▣', lb: 'Dash' }
];

export function Dock() {
  const [active, setActive] = useState(0);
  return (
    <nav className="dock">
      {items.map((it, i) => (
        <button
          key={it.lb}
          className={`dock-item ${active === i ? 'active' : ''}`}
          onClick={() => setActive(i)}
        >
          <span className="ic">{it.ic}</span>
          <span className="lb">{it.lb}</span>
        </button>
      ))}
    </nav>
  );
}