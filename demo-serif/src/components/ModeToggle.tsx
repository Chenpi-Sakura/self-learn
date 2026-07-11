import { motion } from 'framer-motion';
import { useWorkspace } from '../store/useWorkspace';
import './ModeToggle.css';

export function ModeToggle() {
  const mode = useWorkspace((s) => s.mode);
  const setMode = useWorkspace((s) => s.setMode);

  return (
    <div className="mode" role="tablist" aria-label="学习模式">
      {mode === 'proficiency' && (
        <motion.span
          layoutId="mode-pill"
          className="pill"
          initial={false}
          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
          style={{ left: 2, right: '50%' }}
        />
      )}
      {mode === 'exploration' && (
        <motion.span
          layoutId="mode-pill"
          className="pill"
          initial={false}
          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
          style={{ left: '50%', right: 2 }}
        />
      )}
      <button className={mode === 'proficiency' ? 'on' : ''} onClick={() => setMode('proficiency')}>🎯 精通</button>
      <button className={mode === 'exploration' ? 'on' : ''} onClick={() => setMode('exploration')}>🔭 探索</button>
    </div>
  );
}
