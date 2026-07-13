import { useWorkspace } from '../store/useWorkspace';
import './TaskList.css';

const STATUS_LABEL: Record<string, string> = { doing: '进行中', todo: '待办', done: '完成' };

export function TaskList() {
  const tasks = useWorkspace((s) => s.tasks);
  const toggleTask = useWorkspace((s) => s.toggleTask);

  return (
    <div className="tl">
      <div className="tl-head">
        <div className="h">今日学习</div>
        <div className="s">{tasks.filter((t) => t.status !== 'done').length} 项未完成</div>
      </div>
      <div className="tl-list">
        {tasks.map((t) => (
          <div key={t.id} className={`tl-row ${t.status}`}>
            <button className="ck" onClick={() => toggleTask(t.id)} aria-label={t.title}>
              {t.status !== 'todo' ? '✓' : ''}
            </button>
            <span className="ttl">{t.title}</span>
            <span className="m">{t.minutes} min · {STATUS_LABEL[t.status]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
