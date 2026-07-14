import './TopBar.css';
import { ModeToggle } from './ModeToggle';
import { LayoutIcons } from './LayoutIcons';
import { ResetButton } from '../reset/ResetButton';

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
        <ResetButton />
        <span className="avatar">林</span>
      </div>
    </header>
  );
}
