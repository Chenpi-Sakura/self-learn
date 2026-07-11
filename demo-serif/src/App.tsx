import './App.css';
import { Backdrop } from './components/Backdrop';
import { TopBar } from './components/TopBar';
import { Dock } from './components/Dock';
import { ChatFloat } from './components/ChatFloat';
import { Window } from './components/Window';
import { TreasureMap } from './components/TreasureMap';
import { TaskList } from './components/TaskList';
import { ProfileRadar } from './components/ProfileRadar';
import { Calendar } from './components/Calendar';
import { useWorkspace } from './store/useWorkspace';

export default function App() {
  const windows = useWorkspace((s) => s.windows);

  return (
    <div className="app">
      <Backdrop />
      <TopBar />
      <div className="windows-layer">
        <Window win={windows.map}      title="深度学习路径"  isKey><TreasureMap /></Window>
        <Window win={windows.today}    title="今日学习"><TaskList /></Window>
        <Window win={windows.profile}  title="六维画像"><ProfileRadar /></Window>
        <Window win={windows.calendar} title="本月打卡"><Calendar /></Window>
      </div>
      <Dock />
      <ChatFloat />
    </div>
  );
}