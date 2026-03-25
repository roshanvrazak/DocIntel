import React, { useState } from 'react';
import { ExternalLink, Activity, Info, X, Zap, ChevronRight } from 'lucide-react';

export const TraceViewer: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Trigger Card */}
      <div 
        onClick={() => setIsOpen(true)}
        className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 overflow-hidden transition-all hover:shadow-md cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl group-hover:bg-indigo-600 group-hover:text-white transition-colors">
              <Activity size={18} />
            </div>
            <div>
              <h3 className="text-sm font-black text-slate-900 uppercase tracking-tight">Observability</h3>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Arize Phoenix</p>
            </div>
          </div>
          <div className="text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity">
            <ChevronRight size={18} />
          </div>
        </div>
        
        <div className="space-y-4">
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-start space-x-3">
            <Info size={16} className="text-slate-400 mt-0.5 shrink-0" />
            <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
              Click to view real-time agentic traces and LLM metrics.
            </p>
          </div>
          
          <div className="pt-2">
             <div className="flex items-center justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 px-1">
               <span>Status</span>
               <div className="flex items-center space-x-1.5">
                 <span className="flex h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                 <span className="text-green-600">Exporting</span>
               </div>
             </div>
             
             <div className="space-y-2">
               <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                 <div className="h-full bg-indigo-500 w-2/3 rounded-full" />
               </div>
               <div className="flex justify-between text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                 <span>Endpoint: phoenix:4317</span>
                 <span>v1.0.0-beta</span>
               </div>
             </div>
          </div>
        </div>
      </div>

      {/* Slide-over */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" onClick={() => setIsOpen(false)} />
          
          <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
            <div className="w-screen max-w-3xl transform transition-all animate-in slide-in-from-right duration-500 shadow-2xl">
              <div className="flex h-full flex-col bg-white">
                <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-lg shadow-indigo-600/20">
                      <Zap size={20} />
                    </div>
                    <div>
                      <h2 className="text-lg font-black text-slate-900 tracking-tight">System Trace Viewer</h2>
                      <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Powered by Arize Phoenix</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setIsOpen(false)}
                    className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-600"
                  >
                    <X size={20} />
                  </button>
                </div>
                
                <div className="flex-1 overflow-hidden relative bg-slate-50">
                   <iframe 
                     src="http://localhost:6006" 
                     className="w-full h-full border-none"
                     title="Arize Phoenix Trace Viewer"
                   />
                </div>
                
                <div className="p-6 bg-white border-t border-slate-100 flex items-center justify-between">
                   <div className="flex items-center space-x-3">
                     <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                     <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Collector Active: phoenix:4317</span>
                   </div>
                   <div className="flex items-center space-x-4">
                     <button 
                       onClick={() => window.open('http://localhost:6006', '_blank')}
                       className="flex items-center space-x-2 text-[10px] font-black text-indigo-600 hover:text-indigo-700 uppercase tracking-widest transition-colors"
                     >
                       <span>Open in full window</span>
                       <ExternalLink size={12} />
                     </button>
                   </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
