import { useWorkspace, type LayoutId } from '../store/useWorkspace';
import { readingLayout, practiceLayout, codingLayout } from '../lib/layouts';
import './LayoutIcons.css';

const opts: { id: LayoutId; ic: string; label: string; fn: () => ReturnType<typeof readingLayout> }[] = [
  { id: 'reading',  ic: '📖', label: '阅读', fn: readingLayout },
  { id: 'practice', ic: '✏️', label: '习题', fn: practiceLayout },
  { id: 'coding',   ic: '💻', label: '代码', fn: codingLayout }
];

export function LayoutIcons() {
  const layout = useWorkspace((s) => s.layout);
  const setLayout = useWorkspace((s) => s.setLayout);

  return (
    <div className="layout-icons" role="group" aria-label="布局">
      {opts.map((o) => (
        <button
          key={o.id}
          className={layout === o.id ? 'on' : ''}
          title={o.label}
          onClick={() => setLayout(o.id, o.fn())}
        >
          {o.ic}
        </button>
      ))}
    </div>
  );
}
