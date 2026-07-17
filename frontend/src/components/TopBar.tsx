import './TopBar.css';
import { ModeToggle } from './ModeToggle';
import { LayoutIcons } from './LayoutIcons';
import { useSession } from '../store/session';

export function TopBar() {
  const studentId = useSession((s) => s.studentId);
  // 显示前 8 位 UUID，方便用户识别身份但又不占满 TopBar
  const shortId = studentId ? studentId.slice(0, 8) : '—';
  return (
    <header className="topbar">
      <span className="logo">◆ SelfLearn</span>
      <nav>
        <a href="#" className="active">Map</a>
        <a href="#">Today</a>
        <a href="#">Resources</a>
        <a href="#">Profile</a>
      </nav>
      <ModeToggle />
      <LayoutIcons />
      <div className="right">
        <span className="cmdk">⌘K</span>
        <span className="student-id" title={studentId}>ID · {shortId}</span>
      </div>
    </header>
  );
}