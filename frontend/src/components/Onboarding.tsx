import { useEffect, useState } from 'react';
import {
  fetchOnboardingQuestions,
  submitOnboarding,
  type Question,
  type OnboardingAnswer,
} from '../api/onboarding';

type Status = 'loading' | 'answering' | 'submitting' | 'error';

interface Props {
  studentId: string;
  onDone: () => void;
}

export function Onboarding({ studentId, onDone }: Props) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [qIdx, setQIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, OnboardingAnswer>>({});
  const [status, setStatus] = useState<Status>('loading');
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    fetchOnboardingQuestions()
      .then((qs) => {
        setQuestions(qs);
        setStatus('answering');
      })
      .catch(() => {
        setErrorMsg('问卷加载失败，请刷新重试');
        setStatus('error');
      });
  }, []);

  if (status === 'loading') {
    return <FullScreenShell><Center>加载中...</Center></FullScreenShell>;
  }

  if (status === 'error' && questions.length === 0) {
    return (
      <FullScreenShell>
        <Center>
          <ErrorText>{errorMsg}</ErrorText>
          <button onClick={() => location.reload()}>刷新</button>
        </Center>
      </FullScreenShell>
    );
  }

  const q = questions[qIdx];
  const ans = answers[q.id] ?? { question_id: q.id };
  const isLast = qIdx === questions.length - 1;
  const canNext = isAnswered(q, ans);

  function handleSingle(optId: string) {
    setAnswers((a) => ({
      ...a,
      [q.id]: { question_id: q.id, choice: optId },
    }));
  }

  function handleMulti(optId: string) {
    setAnswers((a) => {
      const cur = (a[q.id]?.choice as string[] | undefined) ?? [];
      const next = cur.includes(optId)
        ? cur.filter((x) => x !== optId)
        : [...cur, optId];
      return { ...a, [q.id]: { question_id: q.id, choice: next } };
    });
  }

  function handleOpen(text: string) {
    setAnswers((a) => ({
      ...a,
      [q.id]: { question_id: q.id, free_text: text },
    }));
  }

  async function handleSubmit() {
    setStatus('submitting');
    setErrorMsg('');
    try {
      const payload: OnboardingAnswer[] = questions.map((qq) => ({
        question_id: qq.id,
        choice: answers[qq.id]?.choice,
        free_text: answers[qq.id]?.free_text,
      }));
      await submitOnboarding(studentId, payload);
      onDone();
    } catch (e) {
      setErrorMsg(`提交失败：${String(e)}，请重试`);
      setStatus('error');
    }
  }

  return (
    <FullScreenShell>
      <Header>
        <Progress>
          问题 {qIdx + 1} / {questions.length}
        </Progress>
        <ProgressBar value={(qIdx + 1) / questions.length} />
      </Header>

      <QuestionCard>
        <Prompt>{q.prompt}</Prompt>

        {q.type === 'single' &&
          q.options?.map((opt) => (
            <Option
              key={opt.id}
              selected={ans.choice === opt.id}
              onClick={() => handleSingle(opt.id)}
            >
              <Radio checked={ans.choice === opt.id} />
              <span>{opt.label}</span>
            </Option>
          ))}

        {q.type === 'multi' &&
          q.options?.map((opt) => {
            const cur = (ans.choice as string[] | undefined) ?? [];
            const checked = cur.includes(opt.id);
            return (
              <Option
                key={opt.id}
                selected={checked}
                onClick={() => handleMulti(opt.id)}
              >
                <CheckBox checked={checked} />
                <span>{opt.label}</span>
              </Option>
            );
          })}

        {q.type === 'open' && (
          <OpenTextarea
            value={ans.free_text ?? ''}
            placeholder={q.placeholder ?? ''}
            onChange={(v) => handleOpen(v)}
          />
        )}
      </QuestionCard>

      {status === 'error' && (
        <ErrorText style={{ marginTop: 16 }}>{errorMsg}</ErrorText>
      )}

      <Footer>
        <Btn onClick={() => setQIdx((i) => Math.max(0, i - 1))} disabled={qIdx === 0}>
          上一题
        </Btn>
        {isLast ? (
          <Btn primary disabled={!canNext || status === 'submitting'} onClick={handleSubmit}>
            {status === 'submitting' ? 'AI 评估中...' : '提交'}
          </Btn>
        ) : (
          <Btn primary disabled={!canNext} onClick={() => setQIdx((i) => i + 1)}>
            下一题
          </Btn>
        )}
      </Footer>
    </FullScreenShell>
  );
}

// ---------- helpers ----------

function isAnswered(q: Question, a: OnboardingAnswer): boolean {
  if (q.type === 'single') return typeof a.choice === 'string' && a.choice.length > 0;
  if (q.type === 'multi') return Array.isArray(a.choice); // 允许多选 0 个（视为跳过）
  if (q.type === 'open') return typeof a.free_text === 'string' && a.free_text.trim().length >= 10;
  return false;
}

// ---------- inline style atoms ----------

const FullScreenShell: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: 'fixed',
      inset: 0,
      background: '#FBF7EC',
      fontFamily: 'HedvigLettersSerif, serif',
      zIndex: 10000,
      display: 'flex',
      flexDirection: 'column',
      padding: '40px 80px',
      overflowY: 'auto',
    }}
  >
    {children}
  </div>
);

const Center: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    {children}
  </div>
);

const Header: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ marginBottom: 24 }}>{children}</div>
);

const Progress: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 14, color: '#6B6B70', marginBottom: 8 }}>{children}</div>
);

const ProgressBar: React.FC<{ value: number }> = ({ value }) => (
  <div style={{ height: 4, background: '#E5E5E0', borderRadius: 2 }}>
    <div style={{ width: `${value * 100}%`, height: 4, background: '#1B3B6F', borderRadius: 2 }} />
  </div>
);

const QuestionCard: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ flex: 1, maxWidth: 720, margin: '0 auto', width: '100%' }}>{children}</div>
);

const Prompt: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2 style={{ fontSize: 24, color: '#1B3B6F', marginBottom: 24 }}>{children}</h2>
);

const Option: React.FC<{ selected: boolean; onClick: () => void; children: React.ReactNode }> = ({
  selected,
  onClick,
  children,
}) => (
  <div
    onClick={onClick}
    style={{
      padding: '16px 20px',
      border: `2px solid ${selected ? '#1B3B6F' : '#E5E5E0'}`,
      borderRadius: 8,
      marginBottom: 12,
      cursor: 'pointer',
      background: selected ? '#F0EBDF' : '#FFFFFF',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      fontSize: 15,
    }}
  >
    {children}
  </div>
);

const Radio: React.FC<{ checked: boolean }> = ({ checked }) => (
  <div
    style={{
      width: 18,
      height: 18,
      borderRadius: '50%',
      border: `2px solid ${checked ? '#1B3B6F' : '#9B9B9F'}`,
      flexShrink: 0,
    }}
  >
    {checked && (
      <div
        style={{
          width: 8,
          height: 8,
          background: '#1B3B6F',
          borderRadius: '50%',
          margin: '3px auto',
        }}
      />
    )}
  </div>
);

const CheckBox: React.FC<{ checked: boolean }> = ({ checked }) => (
  <div
    style={{
      width: 18,
      height: 18,
      border: `2px solid ${checked ? '#1B3B6F' : '#9B9B9F'}`,
      borderRadius: 4,
      background: checked ? '#1B3B6F' : 'transparent',
      flexShrink: 0,
    }}
  />
);

const OpenTextarea: React.FC<{ value: string; placeholder: string; onChange: (v: string) => void }> = ({
  value,
  placeholder,
  onChange,
}) => (
  <textarea
    value={value}
    placeholder={placeholder}
    onChange={(e) => onChange(e.target.value)}
    style={{
      width: '100%',
      minHeight: 120,
      padding: 16,
      fontSize: 15,
      fontFamily: 'HedvigLettersSerif, serif',
      border: '2px solid #E5E5E0',
      borderRadius: 8,
      resize: 'vertical',
      background: '#FFFFFF',
    }}
  />
);

const Footer: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32 }}>
    {children}
  </div>
);

const Btn: React.FC<{
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  primary?: boolean;
}> = ({ children, onClick, disabled, primary }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      padding: '12px 24px',
      fontSize: 14,
      fontFamily: 'HedvigLettersSerif, serif',
      background: primary ? '#1B3B6F' : '#FFFFFF',
      color: primary ? '#FBF7EC' : '#1B3B6F',
      border: `1px solid ${primary ? '#1B3B6F' : '#E5E5E0'}`,
      borderRadius: 6,
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
    }}
  >
    {children}
  </button>
);

const ErrorText: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => <div style={{ color: '#BC4749', fontSize: 14, ...style }}>{children}</div>;
