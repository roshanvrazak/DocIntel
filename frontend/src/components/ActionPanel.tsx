import React from 'react';
import { LayoutGrid, FileText, GitCompare, MessageSquare, Search, Sparkles } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { UploadingFile } from '../types';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type ActionType = 'summarize' | 'compare' | 'qa' | 'extract' | 'search';

interface Action {
  id: ActionType;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

const ACTIONS: Action[] = [
  {
    id: 'summarize',
    label: 'Summarize',
    description: 'Get a concise summary of your research papers.',
    icon: <FileText className="h-5 w-5" />,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: 'compare',
    label: 'Compare',
    description: 'Find similarities and differences between documents.',
    icon: <GitCompare className="h-5 w-5" />,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: 'qa',
    label: 'Q&A',
    description: 'Ask specific questions about the content.',
    icon: <MessageSquare className="h-5 w-5" />,
    color: 'bg-green-100 text-green-600',
  },
  {
    id: 'extract',
    label: 'Extract',
    description: 'Extract entities, metrics, and key findings.',
    icon: <Sparkles className="h-5 w-5" />,
    color: 'bg-amber-100 text-amber-600',
  },
  {
    id: 'search',
    label: 'Semantic Search',
    description: 'Find relevant sections across all documents.',
    icon: <Search className="h-5 w-5" />,
    color: 'bg-slate-100 text-slate-600',
  },
];

interface ActionPanelProps {
  documents: UploadingFile[];
  selectedAction: ActionType;
  onActionChange: (action: ActionType) => void;
  selectedDocIds: string[];
  onDocSelectionChange: (docIds: string[]) => void;
}

export const ActionPanel: React.FC<ActionPanelProps> = ({
  documents,
  selectedAction,
  onActionChange,
  selectedDocIds,
  onDocSelectionChange,
}) => {
  const readyDocs = documents.filter((doc) => doc.status === 'ready' && doc.id);

  const toggleDoc = (id: string) => {
    if (selectedDocIds.includes(id)) {
      onDocSelectionChange(selectedDocIds.filter((docId) => docId !== id));
    } else {
      onDocSelectionChange([...selectedDocIds, id]);
    }
  };

  const selectAll = () => {
    onDocSelectionChange(readyDocs.map((doc) => doc.id as string));
  };

  const selectNone = () => {
    onDocSelectionChange([]);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-6 border-b border-slate-100 bg-slate-50/30">
        <h3 className="text-lg font-bold text-slate-900 flex items-center">
          <LayoutGrid className="h-5 w-5 mr-2.5 text-blue-600" />
          Agent Actions
        </h3>
        <p className="text-xs text-slate-500 font-medium mt-1 uppercase tracking-wider">
          Intelligence task & Document Scope
        </p>
      </div>

      <div className="p-8 space-y-10">
        {/* Actions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ACTIONS.map((action) => (
            <button
              key={action.id}
              onClick={() => onActionChange(action.id)}
              aria-label={`Select ${action.label} action`}
              aria-pressed={selectedAction === action.id}
              className={cn(
                "flex items-start p-5 rounded-2xl border-2 transition-all text-left group active:scale-[0.98]",
                selectedAction === action.id
                  ? "border-blue-600 bg-blue-50/40 ring-1 ring-blue-600"
                  : "border-slate-100 hover:border-slate-200 bg-white"
              )}
            >
              <div className={cn(
                "p-3 rounded-xl mr-5 transition-transform group-hover:scale-110 duration-300 shadow-sm", 
                action.color
              )}>
                {action.icon}
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-extrabold text-slate-900">{action.label}</h4>
                <p className="text-[11px] text-slate-500 mt-1 font-medium leading-relaxed">{action.description}</p>
              </div>
            </button>
          ))}
        </div>

        {/* Document Selection */}
        <div className="space-y-5 bg-slate-50/50 p-6 rounded-2xl border border-slate-100">
          <div className="flex items-center justify-between">
            <h4 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-[0.2em]">Document Scope</h4>
            <div className="flex space-x-4">
              <button
                onClick={selectAll}
                disabled={readyDocs.length === 0}
                aria-label="Select all documents"
                className="text-[10px] font-extrabold text-blue-600 hover:text-blue-700 uppercase tracking-widest disabled:opacity-30"
              >
                Select All
              </button>
              <button
                onClick={selectNone}
                aria-label="Clear document selection"
                className="text-[10px] font-extrabold text-slate-400 hover:text-slate-500 uppercase tracking-widest"
              >
                Clear
              </button>
            </div>
          </div>

          {readyDocs.length === 0 ? (
            <div className="py-10 border-2 border-dashed border-slate-200 rounded-2xl text-center bg-white/50">
              <p className="text-xs text-slate-400 font-bold uppercase tracking-widest italic">
                No processed documents available
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2.5">
              {readyDocs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => toggleDoc(doc.id as string)}
                  aria-label={`Toggle selection for ${doc.file.name}`}
                  aria-pressed={selectedDocIds.includes(doc.id as string)}
                  className={cn(
                    "px-4 py-2 rounded-xl text-[11px] font-bold border transition-all active:scale-95 shadow-sm",
                    selectedDocIds.includes(doc.id as string)
                      ? "bg-blue-600 border-blue-600 text-white shadow-blue-500/25"
                      : "bg-white border-slate-200 text-slate-600 hover:border-slate-300"
                  )}
                >
                  {doc.file.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
