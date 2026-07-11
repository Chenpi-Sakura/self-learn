import './Backdrop.css';

export function Backdrop() {
  return (
    <div className="backdrop" aria-hidden>
      <div className="backdrop-grid" />
      <svg className="backdrop-mountain" viewBox="0 0 540 220" preserveAspectRatio="none">
        <path d="M0 200 L120 90 L200 150 L300 60 L420 140 L540 100 L540 220 L0 220 Z"
              fill="var(--indigo)" opacity="0.5" />
        <path d="M0 220 L80 170 L180 190 L300 160 L420 195 L540 175 L540 220 L0 220 Z"
              fill="var(--indigo)" opacity="0.7" />
      </svg>
      <div className="backdrop-seal">藏 宝 图</div>
    </div>
  );
}