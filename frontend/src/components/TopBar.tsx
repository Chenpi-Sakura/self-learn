import './TopBar.css';
import { ModeToggle } from './ModeToggle';
import { LayoutIcons } from './LayoutIcons';

export function TopBar() {
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
        <span className="avatar">林</span>
      </div>
    </header>
  );
}
