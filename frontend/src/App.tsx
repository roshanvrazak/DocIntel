import { FileText, Cpu, Search, MessageSquare } from 'lucide-react';
import { UploadZone } from './components/UploadZone';

function App() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg shadow-md shadow-blue-500/20 text-white">
              <FileText size={20} />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">DocIntel</h1>
          </div>
          
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#" className="text-sm font-semibold text-blue-600 border-b-2 border-blue-600 pb-5 mt-5">Dashboard</a>
            <a href="#" className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors">Documents</a>
            <a href="#" className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors">Insights</a>
          </nav>

          <div className="flex items-center space-x-4">
             <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors">
               <Search size={20} />
             </button>
             <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs border border-blue-200">
               RV
             </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          {/* Left Column: Hero & Upload */}
          <div className="lg:col-span-8 space-y-12">
            <div className="space-y-4">
              <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight sm:text-5xl">
                Analyze Research <span className="text-blue-600">at Scale.</span>
              </h2>
              <p className="text-xl text-slate-500 max-w-2xl leading-relaxed">
                Upload your research papers and let our agentic intelligence extract insights, 
                summarize complex data, and answer your questions in real-time.
              </p>
            </div>

            <UploadZone />
          </div>

          {/* Right Column: Features/Status */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
              <h3 className="text-lg font-bold text-slate-900">Platform Features</h3>
              
              <div className="space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="p-2 bg-purple-50 rounded-lg text-purple-600 mt-1">
                    <Cpu size={18} />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Semantic Parsing</h4>
                    <p className="text-xs text-slate-500 mt-1">Deep structural analysis of PDF layouts and scientific notation.</p>
                  </div>
                </div>

                <div className="flex items-start space-x-4">
                  <div className="p-2 bg-green-50 rounded-lg text-green-600 mt-1">
                    <Search size={18} />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Vector Retrieval</h4>
                    <p className="text-xs text-slate-500 mt-1">Hyper-accurate search across your entire document library.</p>
                  </div>
                </div>

                <div className="flex items-start space-x-4">
                  <div className="p-2 bg-blue-50 rounded-lg text-blue-600 mt-1">
                    <MessageSquare size={18} />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Agentic Chat</h4>
                    <p className="text-xs text-slate-500 mt-1">Multi-agent system to validate and summarize research findings.</p>
                  </div>
                </div>
              </div>

              <hr className="border-slate-100" />

              <div className="pt-2">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-slate-500 font-medium">System Status</span>
                  <span className="text-green-600 font-bold flex items-center">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500 mr-1.5 animate-pulse" />
                    Operational
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                  <div className="bg-green-500 h-full w-[95%]" />
                </div>
              </div>
            </div>

            <div className="bg-blue-600 rounded-2xl p-6 text-white shadow-lg shadow-blue-600/20">
              <h3 className="font-bold text-lg mb-2">Need help?</h3>
              <p className="text-blue-100 text-sm mb-4">Check out our documentation or reach out for support.</p>
              <button className="w-full bg-white text-blue-600 font-bold py-2 rounded-xl text-sm hover:bg-blue-50 transition-colors">
                View Docs
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-8">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center text-slate-400 text-sm">
          <p>© 2024 DocIntel Platform. All rights reserved.</p>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <a href="#" className="hover:text-slate-600">Privacy Policy</a>
            <a href="#" className="hover:text-slate-600">Terms of Service</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
