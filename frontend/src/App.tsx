import { FileText } from 'lucide-react'

function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="flex justify-center">
          <div className="p-4 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20">
            <FileText size={48} className="text-white" />
          </div>
        </div>
        
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">DocIntel</h1>
          <p className="text-slate-400 text-lg">
            Agentic Document Intelligence Platform
          </p>
        </div>

        <div className="p-6 bg-slate-800 rounded-xl border border-slate-700">
          <p className="text-slate-300">
            Frontend successfully scaffolded with Vite, React, and Tailwind CSS.
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
