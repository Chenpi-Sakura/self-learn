import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Onboarding } from '../Onboarding';
import * as api from '../../api/onboarding';

vi.mock('../../api/onboarding');

const MOCK_QUESTIONS = [
  {
    id: 'q1_kb',
    dimension_hint: 'kb',
    type: 'single' as const,
    prompt: '遇到新概念？',
    options: [
      { id: 'a', label: '查定义' },
      { id: 'b', label: '看例子' },
      { id: 'c', label: '试一下' },
    ],
  },
  {
    id: 'q8_open',
    type: 'open' as const,
    prompt: '你的学习方式？',
    placeholder: '...',
  },
];

describe('Onboarding', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('渲染第 1 题', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);

    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('遇到新概念？')).toBeInTheDocument());
    expect(screen.getByText('问题 1 / 2')).toBeInTheDocument();
  });

  it('选 single 选项 → 下一题可点', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    const nextBtn = screen.getByText('下一题') as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(false);
  });

  it('open 题提交按钮 disabled 当文本 < 10 字', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    fireEvent.click(screen.getByText('下一题'));

    const textarea = screen.getByPlaceholderText('...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '短文本' } });

    const submitBtn = screen.getByText('提交') as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it('提交成功 → onDone 被调', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    vi.mocked(api.submitOnboarding).mockResolvedValue({
      dimensions: { kb: 0.7, vp: 0.5, as: 0.5, ge: 0.5, ept: 0.5, fd: 0.5 },
      reasoning: 'ok',
      snapshot_id: 1,
    });
    const onDone = vi.fn();

    render(<Onboarding studentId="sid" onDone={onDone} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    fireEvent.click(screen.getByText('下一题'));

    const textarea = screen.getByPlaceholderText('...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '我喜欢先看图再看例子' } });

    fireEvent.click(screen.getByText('提交'));

    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(api.submitOnboarding).toHaveBeenCalledWith(
      'sid',
      expect.arrayContaining([
        { question_id: 'q1_kb', choice: 'a', free_text: undefined },
        { question_id: 'q8_open', choice: undefined, free_text: '我喜欢先看图再看例子' },
      ]),
    );
  });

  it('提交失败 → 显示错误', async () => {
    vi.mocked(api.fetchOnboardingQuestions).mockResolvedValue(MOCK_QUESTIONS);
    vi.mocked(api.submitOnboarding).mockRejectedValue(new Error('网络错误'));

    render(<Onboarding studentId="sid" onDone={vi.fn()} />);
    await waitFor(() => screen.getByText('查定义'));

    fireEvent.click(screen.getByText('查定义'));
    fireEvent.click(screen.getByText('下一题'));

    const textarea = screen.getByPlaceholderText('...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '我喜欢先看图再看例子' } });
    fireEvent.click(screen.getByText('提交'));

    await waitFor(() => expect(screen.getByText(/提交失败/)).toBeInTheDocument());
  });
});
