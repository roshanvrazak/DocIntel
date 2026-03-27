import React from 'react';
import { FileText, X } from 'lucide-react';
import { CitationData } from '../types';

interface CitationCardProps {
  citation: CitationData;
  onClose: () => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md transition-all animate-in fade-in duration-300">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-300 ring-1 ring-black/5">
        <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-blue-600 rounded-2xl text-white shadow-lg shadow-blue-600/20">
              <FileText size={22} />
            </div>
            <div>
              <h4 className="text-lg font-bold text-slate-900 truncate max-w-[340px]">
                {citation.filename}
              </h4>
              <div className="flex items-center space-x-2 mt-0.5">
                 <span className="text-[10px] font-extrabold text-blue-600 uppercase tracking-widest bg-blue-50 px-2 py-0.5 rounded-full">
                   Page {citation.page_number || '1'}
                 </span>
                 <span className="h-1 w-1 rounded-full bg-slate-300" />
                 <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                   Source Reference
                 </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close citation details"
            className="p-2.5 text-slate-400 hover:text-slate-900 hover:bg-slate-200/50 rounded-full transition-all"
          >
            <X size={24} />
          </button>
        </div>
        
        <div className="p-10 overflow-y-auto bg-white flex-1 custom-scrollbar">
          <div className="relative">
            <div className="absolute -left-6 top-0 bottom-0 w-1.5 bg-blue-100 rounded-full" />
            <p className="text-slate-800 leading-relaxed text-lg font-serif italic antialiased">
              "{citation.text}"
            </p>
          </div>
        </div>
        
        <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-8 py-3 bg-slate-900 text-white text-sm font-bold rounded-2xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/10 active:scale-95"
          >
            Close Source
          </button>
        </div>
      </div>
    </div>
  );
};
