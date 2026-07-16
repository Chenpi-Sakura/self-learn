export type Stage = 'profile' | 'plan' | 'director' | 'exercise' | 'review';

export type ProfileDimensions = {
  kb: number; vp: number; as: number; ge: number; ept: number; fd: number;
};

export interface ProfileResponse {
  student_id: string;
  dimensions: ProfileDimensions;
  tags: string[];
  snapshot_count: number;
  last_updated_at: string | null;
}

export interface MapNode {
  node_id: string;
  kp_id: string;
  title: string;
  position: { x: number; y: number };
  status: string;
}

export interface MapNodesResponse { nodes: MapNode[]; }

export interface ExerciseResponse {
  exercise_id: string;
  prompt: string;
  options: string[] | null;
  type: string;  // 'single_choice' | 'fill_blank' | 'short_answer' | 'code'
}

export interface LevelDetail {
  level_id: string;
  node_id: string;
  status: string;
  exercises: ExerciseResponse[];
  lecture_html: string | null;  // NULL 时显示"该关卡尚无讲义"
}

export interface ProfileHistoryEntry {
  profile: ProfileDimensions;
  trigger: string;
  created_at: string;
}

export interface ProfileHistoryResponse {
  student_id: string;
  snapshots: ProfileHistoryEntry[];
}

export type SSEEventData =
  | { stage: Stage; status: string; payload: Record<string, unknown> }
  | { status: 'completed'; payload: Record<string, unknown> }
  | { status: 'failed'; payload: { code: string; message: string } };

export interface SSEEvent {
  event: 'progress' | 'completed' | 'error';
  data: SSEEventData;
}