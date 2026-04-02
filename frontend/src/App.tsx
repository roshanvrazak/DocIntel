import { useState } from 'react';
import { FileText, Cpu, Search, LayoutDashboard, Database, BarChart3, Settings } from 'lucide-react';
import { UploadZone } from './components/UploadZone';
import { ActionPanel, ActionType } from './components/ActionPanel';
import { ChatInterface } from './components/ChatInterface';
import { TraceViewer } from './components/TraceViewer';
import { DocumentManager } from './components/DocumentManager';
import { UploadingFile } from './types';

function App() {
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const [selectedAction, setSelectedAction] = useState<ActionType>('summarize');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex">
      {/* Sidebar */}
      <aside className="w-20 lg:w-64 bg-white border-r border-slate-200 flex flex-col transition-all duration-300">
        <div className="p-6 flex items-center space-x-3">
          <div className="p-2.5 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20 text-white shrink-0">
            <FileText size={22} />
          </div>
          <h1 className="text-xl font-black text-slate-900 tracking-tighter hidden lg:block">DocIntel</h1>
        </div>

        <nav className="flex-1 px-4 mt-6 space-y-2">
           {[
             { icon: <LayoutDashboard size={20} />, label: 'Dashboard', active: true },
             { icon: <Database size={20} />, label: 'Documents', active: false },
             { icon: <BarChart3 size={20} />, label: 'Analytics', active: false },
             { icon: <Settings size={20} />, label: 'Settings', active: false },
           ].map((item, i) => (
             <a
               key={i}
               href="#"
               className={`flex items-center space-x-3 p-3 rounded-xl transition-all ${
                 item.active 
                   ? 'bg-blue-50 text-blue-600 font-bold' 
                   : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50 font-medium'
               }`}
             >
               <span className="shrink-0">{item.icon}</span>
               <span className="hidden lg:block text-sm">{item.label}</span>
             </a>
           ))}
        </nav>

        <div className="p-6 mt-auto">
           <div className="bg-slate-900 rounded-2xl p-4 text-white hidden lg:block overflow-hidden relative">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                 <Cpu size={64} />
              </div>
              <h4 className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-1">Pro Plan</h4>
              <p className="text-[11px] text-slate-400 mb-3">Unlimited agentic analysis and vector storage.</p>
              <button className="w-full bg-blue-600 py-2 rounded-lg text-xs font-bold hover:bg-blue-500 transition-colors">
                Upgrade
              </button>
           </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-10 px-8 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm text-slate-400 font-medium">
             <span>Workspace</span>
             <span>/</span>
             <span className="text-slate-900 font-bold uppercase tracking-widest text-[11px]">Research Analysis</span>
          </div>
          
          <div className="flex items-center space-x-6">
             <div className="relative hidden md:block">
               <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
               <input 
                 type="text" 
                 placeholder="Search documents..." 
                 className="pl-10 pr-4 py-2 bg-slate-100 border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 rounded-xl text-xs font-bold transition-all w-64"
               />
             </div>
             <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-xs shadow-lg shadow-blue-500/20 border border-white/20">
               RV
             </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-[#F8FAFC]">
          <div className="max-w-7xl mx-auto px-8 py-10">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
              {/* Left Column: Upload & Actions */}
              <div className="lg:col-span-5 space-y-10">
                <section className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-black text-slate-900 tracking-tight">Ingestion</h2>
                      <p className="text-sm text-slate-500 font-medium">Upload research PDFs for agentic processing.</p>
                    </div>
                    <div className="bg-white px-3 py-1 rounded-full border border-slate-200 shadow-sm">
                       <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                         {files.length} Files
                       </span>
                    </div>
                  </div>
                  <UploadZone files={files} setFiles={setFiles} />
                </section>

                <section className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">Agent Actions</h2>
                    <p className="text-sm text-slate-500 font-medium">Configure analysis parameters.</p>
                  </div>
                  <ActionPanel 
                    documents={files}
                    selectedAction={selectedAction}
                    onActionChange={setSelectedAction}
                    selectedDocIds={selectedDocIds}
                    onDocSelectionChange={setSelectedDocIds}
                  />
                </section>

                <section className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">Documents</h2>
                    <p className="text-sm text-slate-500 font-medium">Manage processed document library.</p>
                  </div>
                  <DocumentManager onDocumentsChange={() => {}} />
                </section>

                <section className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">Observability</h2>
                    <p className="text-sm text-slate-500 font-medium">Trace system execution and performance.</p>
                  </div>
                  <TraceViewer />
                </section>
              </div>

              {/* Right Column: Chat Interface */}
              <div className="lg:col-span-7 space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">Intelligence</h2>
                    <p className="text-sm text-slate-500 font-medium">Real-time multi-agent conversation.</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">System Active</span>
                  </div>
                </div>
                <ChatInterface 
                  selectedAction={selectedAction}
                  selectedDocIds={selectedDocIds}
                />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
