import React, { useEffect, useState, useCallback } from 'react';
import { Trash2, RefreshCw, FileText, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { apiClient } from '../services/api';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface DocRecord {
  id: string;
  filename: string;
  status: string;
  created_at: string;
}

interface DocumentManagerProps {
  onDocumentsChange?: () => void;
}

export const DocumentManager: React.FC<DocumentManagerProps> = ({ onDocumentsChange }) => {
  const [docs, setDocs] = useState<DocRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const limit = 10;

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/api/documents?page=${page}&limit=${limit}`);
      setDocs(res.data.documents);
      setTotal(res.data.total);
    } catch {
      setError('Failed to load documents.');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this document and all its data?')) return;
    setActionInProgress(id);
    try {
      await apiClient.delete(`/api/documents/${id}`);
      await fetchDocs();
      onDocumentsChange?.();
    } catch {
      setError('Failed to delete document.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReprocess = async (id: string) => {
    setActionInProgress(id);
    try {
      await apiClient.post(`/api/documents/${id}/reprocess`);
      await fetchDocs();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Failed to reprocess document.');
    } finally {
      setActionInProgress(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const statusColor = (status: string) => {
    if (status === 'ready') return 'bg-green-100 text-green-700';
    if (status === 'error') return 'bg-red-100 text-red-700';
    return 'bg-blue-100 text-blue-700';
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <h3 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
          Document Library
        </h3>
        <button
          onClick={fetchDocs}
          className="p-1.5 text-slate-400 hover:text-blue-600 transition-colors rounded-lg hover:bg-blue-50"
          aria-label="Refresh document list"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {error && (
        <div className="mx-4 mt-4 flex items-center space-x-2 text-red-600 bg-red-50 px-4 py-3 rounded-xl text-xs font-bold">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={24} className="animate-spin text-blue-600" />
        </div>
      ) : docs.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">No documents yet</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {docs.map((doc) => (
            <li key={doc.id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50/40 transition-colors">
              <div className="flex items-center space-x-3 min-w-0">
                <div className="p-2 bg-blue-50 rounded-lg text-blue-600 shrink-0">
                  <FileText size={14} />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 truncate max-w-[180px]">{doc.filename}</p>
                  <div className="flex items-center space-x-2 mt-0.5">
                    <span className={cn('text-[9px] font-extrabold uppercase tracking-widest px-2 py-0.5 rounded-full', statusColor(doc.status))}>
                      {doc.status}
                    </span>
                    <span className="text-[9px] text-slate-400 font-medium">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0 ml-3">
                {doc.status === 'ready' && (
                  <CheckCircle2 size={14} className="text-green-500" />
                )}
                <button
                  onClick={() => handleReprocess(doc.id)}
                  disabled={actionInProgress === doc.id}
                  aria-label={`Reprocess ${doc.filename}`}
                  className="p-1.5 text-slate-400 hover:text-blue-600 transition-colors rounded-lg hover:bg-blue-50 disabled:opacity-40"
                >
                  {actionInProgress === doc.id
                    ? <Loader2 size={14} className="animate-spin" />
                    : <RefreshCw size={14} />}
                </button>
                <button
                  onClick={() => handleDelete(doc.id)}
                  disabled={actionInProgress === doc.id}
                  aria-label={`Delete ${doc.filename}`}
                  className="p-1.5 text-slate-400 hover:text-red-600 transition-colors rounded-lg hover:bg-red-50 disabled:opacity-40"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
            {total} documents · page {page}/{totalPages}
          </span>
          <div className="flex space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-[10px] font-extrabold text-slate-500 bg-slate-100 rounded-lg disabled:opacity-30 hover:bg-slate-200 transition-colors"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 text-[10px] font-extrabold text-slate-500 bg-slate-100 rounded-lg disabled:opacity-30 hover:bg-slate-200 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
