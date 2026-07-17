import { apiGet, apiPost } from './client';

export interface QuestionOption {
  id: string;
  label: string;
}

export interface Question {
  id: string;
  dimension_hint?: string;
  type: 'single' | 'multi' | 'open';
  prompt: string;
  options?: QuestionOption[];
  placeholder?: string;
}

export interface OnboardingAnswer {
  question_id: string;
  choice?: string | string[];
  free_text?: string;
}

export interface OnboardingSubmitResponse {
  dimensions: Record<string, number>;
  reasoning: string;
  snapshot_id: number;
}

export async function fetchOnboardingQuestions(): Promise<Question[]> {
  const res = await apiGet<{ questions: Question[] }>('/api/onboarding/questions');
  return res.questions;
}

export async function submitOnboarding(
  studentId: string,
  answers: OnboardingAnswer[]
): Promise<OnboardingSubmitResponse> {
  return apiPost<OnboardingSubmitResponse>('/api/onboarding/submit', {
    student_id: studentId,
    answers,
  });
}
