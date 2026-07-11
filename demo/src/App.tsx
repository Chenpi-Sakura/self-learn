import { useWorkspace } from './store/useWorkspace';
import { TopBar } from './components/TopBar';
import { TreasureMap } from './components/TreasureMap';
import { ProfileRadar } from './components/ProfileRadar';
import { Calendar } from './components/Calendar';
import { FloatingWindow } from './components/FloatingWindow';
import { DocContent, ExContent, NoteContent, MindContent } from './components/WindowContents';
import { ChatFloat } from './components/ChatFloat';
import { Dock } from './components/Dock';

export function App() {
  const windows = useWorkspace((s) => s.windows);
  const mode = useWorkspace((s) => s.mode);

  // 视口尺寸（demo 锁定 1440×900 起步，超出时让内层 grid 处理）
  return (
    <div className="app" data-mode={mode}>
      <TopBar />

      <main className="desktop">
        {/* 左 1/3：藏宝图 + 画像 */}
        <section className="left-pane">
          <div className="pane-block pane-map">
            <TreasureMap />
          </div>
          <div className="pane-divider" />
          <div className="pane-block pane-radar">
            <ProfileRadar />
          </div>
        </section>

        {/* 右 2/3：日历 */}
        <section className="right-pane">
          <Calendar />
        </section>

        {/* 浮动窗口：根据 store.windows 渲染 */}
        <div className="window-layer">
          {windows.map((w) => (
            <FloatingWindow
              key={w.appId}
              appId={w.appId}
              x={w.x}
              y={w.y}
              w={w.w}
              h={w.h}
              z={w.z}
              title={
                w.appId === 'doc'  ? '讲义 · 自注意力机制' :
                w.appId === 'ex'   ? '习题 · 第 3 / 12 题' :
                w.appId === 'note' ? '笔记本' :
                w.appId === 'mind' ? '思维导图' :
                w.appId === 'code' ? '代码实验室' :
                w.appId === 'res'  ? '我的资源库' :
                w.appId === 'dash' ? '学习仪表盘' :
                w.appId === 'ai'   ? 'AI 对话' : ''
              }
              subtitle={
                w.appId === 'doc'  ? '第三章 / 共七章' :
                w.appId === 'ex'   ? '剩 23:14' :
                undefined
              }
              badge={
                w.appId === 'ex' ? '5/12' :
                w.appId === 'note' ? '·' :
                undefined
              }
            >
              {w.appId === 'doc'  && <DocContent />}
              {w.appId === 'ex'   && <ExContent />}
              {w.appId === 'note' && <NoteContent />}
              {w.appId === 'mind' && <MindContent />}
            </FloatingWindow>
          ))}
        </div>

        <ChatFloat />
      </main>

      <Dock />

      <style>{`
        .app {
          display: flex;
          flex-direction: column;
          height: 100vh;
          min-width: 1280px;
        }
        .desktop {
          flex: 1;
          display: grid;
          grid-template-columns: minmax(320px, 1fr) minmax(420px, 2fr);
          gap: 12px;
          padding: 12px;
          padding-bottom: calc(var(--dock-h) + 12px);
          min-height: 0;
          position: relative;
        }
        .left-pane {
          display: grid;
          grid-template-rows: 1.8fr 1fr;
          gap: 0;
          min-height: 0;
          background: var(--paper-card);
          border: var(--border);
          position: relative;
        }
        .pane-block {
          min-height: 0;
          overflow: hidden;
        }
        .pane-divider {
          position: absolute;
          left: 0;
          right: 0;
          top: 64%;          /* 对应 1.8fr / (1.8+1) ≈ 64% */
          height: 1px;
          background: var(--ink-line);
          z-index: 2;
        }
        .pane-divider::before {
          content: '';
          position: absolute;
          left: 50%;
          top: -3px;
          width: 16px;
          height: 7px;
          margin-left: -8px;
          background: var(--paper-card);
          border: var(--border-fade);
        }
        .pane-map > .treasure-card,
        .pane-radar > .radar-card {
          border: none;
        }
        .right-pane {
          min-height: 0;
        }
        .window-layer {
          position: absolute;
          inset: 0;
          pointer-events: none;
        }
        .window-layer > .fwin {
          pointer-events: auto;
        }
      `}</style>
    </div>
  );
}