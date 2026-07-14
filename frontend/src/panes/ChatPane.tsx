import { Rnd } from 'react-rnd';

export function ChatPane({ onClose }: { onClose: () => void }) {
  // Stage 4 简化：AI 聊天占位
  return (
    <Rnd default={{ x: 300, y: 200, width: 400, height: 480 }}>
      <div style={{ background: '#fff', padding: 16, borderRadius: 8, border: '1px solid #E4E4E0', height: '100%', overflow: 'auto', fontFamily: 'HedvigLettersSerif, serif' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <h4 style={{ margin: 0, color: '#1B3B6F' }}>小书 · Always on</h4>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#BC4749' }}>×</button>
        </div>
        <p style={{ color: '#6B6B70', marginTop: 12 }}>AI 对话占位。Stage 5+ 接 LLM 流式输出。</p>
      </div>
    </Rnd>
  );
}