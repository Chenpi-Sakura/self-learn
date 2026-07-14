import { useSession } from '../store/session';

export function ResetButton() {
  const reset = useSession((s) => s.reset);
  return (
    <button
      onClick={reset}
      style={{
        position: 'absolute', top: 16, right: 16, zIndex: 9999,
        padding: '6px 10px', background: '#BC4749', color: '#fff',
        border: 'none', borderRadius: 4, cursor: 'pointer',
        fontFamily: 'HedvigLettersSerif, serif', fontSize: 12,
      }}
    >
      重置 demo
    </button>
  );
}