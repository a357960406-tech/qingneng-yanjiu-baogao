export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  status: string;
  chunk_count: number;
  char_count: number;
  error_reason: string | null;
  created_at: string;
}

export interface ReportItem {
  id: number;
  title: string;
  target_words: number;
  status: string;
  outline_confirmed: boolean;
  user_requirements: string | null;
  created_at: string;
}
