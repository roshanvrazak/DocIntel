export interface Document {
  id: string;
  filename: string;
  status: string;
  progress: number;
}

export interface UploadingFile {
  id?: string;
  localId: string;
  file: File;
  status: string;
  progress: number;
}

export interface CitationData {
  id: string;
  text: string;
  doc_id: string;
  filename: string;
  page_number?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationData[];
}
