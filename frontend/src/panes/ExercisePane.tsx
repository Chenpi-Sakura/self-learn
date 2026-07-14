import { useEffect, useState } from 'react';
import { getLevel, submitLevel } from '../api/level';
import type { ExerciseResponse } from '../api/types';

export function ExercisePane({ levelId, onClose }: { levelId: string; onClose: () => void }) {
  const [exercises, setExercises] = useState<ExerciseResponse[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    if (!levelId) return;
    getLevel(levelId)
      .then((lv) => setExercises(lv.exercises))
      .catch(() => setExercises([]));
  }, [levelId]);

  const onSubmit = async () => {
    if (!levelId) return;
    try {
      const r = await submitLevel(levelId, answers);
      setResult(`已提交：score=${r.score}`);
    } catch (e) {
      setResult(`提交失败：${String(e)}`);
    }
  };

  return (
    <div style={{ background: '#fff', padding: 16, borderRadius: 8, border: '1px solid #E4E4E0', height: '100%', overflow: 'auto', fontFamily: 'HedvigLettersSerif, serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h4 style={{ margin: 0, color: '#1B3B6F' }}>习题</h4>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
      </div>
      {exercises.length === 0 ? (
        <p style={{ color: '#6B6B70' }}>请先启动关卡</p>
      ) : (
        <ol style={{ paddingLeft: 20 }}>
          {exercises.map((ex) => (
            <li key={ex.exercise_id} style={{ marginBottom: 12 }}>
              <div>{ex.prompt}</div>
              {ex.options && ex.options.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  {ex.options.map((opt) => (
                    <label key={opt} style={{ display: 'block' }}>
                      <input
                        type="radio"
                        name={ex.exercise_id}
                        value={opt}
                        onChange={(e) => setAnswers({ ...answers, [ex.exercise_id]: e.target.value })}
                      />{' '}
                      {opt}
                    </label>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      <button onClick={onSubmit} style={{ marginTop: 8, padding: '6px 12px', background: '#1B3B6F', color: '#fff', border: 'none', borderRadius: 4 }}>
        提交
      </button>
      {result && <p style={{ marginTop: 8, color: '#6B6B70' }}>{result}</p>}
    </div>
  );
}