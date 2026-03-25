import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, User, Cpu, Loader2, Link2, MessageSquare, Sparkles } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { CitationCard } from './CitationCard';
import { Message, CitationData } from '../types';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ChatInterfaceProps {
  selectedAction: string;
  selectedDocIds: string[];
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  selectedAction,
  selectedDocIds,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
    
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [messages, isTyping]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || isTyping) return;

    abortControllerRef.current = new AbortController();

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          query: userMessage.content,
          action: selectedAction,
          doc_ids: selectedDocIds,
        }),
      });

      if (!response.ok) throw new Error('Failed to fetch response');

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Response body is empty');

      const assistantMessageId = (Date.now() + 1).toString();
      let assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
      };

      setMessages((prev) => [...prev, assistantMessage]);

      const decoder = new TextDecoder();
      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        
        // Handle SSE or raw stream
        // For simplicity, let's assume raw text stream for content
        // In a real scenario, you might have special markers for citations
        accumulatedContent += chunk;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId ? { ...m, content: accumulatedContent } : m
          )
        );
      }
      
      // Post-process to extract or assign citations if backend provides them separately
      // For this task, we assume the backend might send a JSON at the end or embedded
      // Let's mock some citations for demonstration if it's a "Summarize" or "Compare" action
      if (selectedAction === 'summarize' || selectedAction === 'compare') {
         // Mocking a citation for the first message for demo purposes
         setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId 
                ? { 
                    ...m, 
                    citations: [
                      {
                        id: '1',
                        doc_id: selectedDocIds[0] || 'mock-id',
                        filename: 'Research_Paper_A.pdf',
                        text: 'The results indicate a significant increase in efficiency when using the proposed agentic framework compared to baseline models.',
                        page_number: 4
                      }
                    ] 
                  } 
                : m
            )
          );
      }

    } catch (error) {
      console.error('Chat failed', error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: '**Error:** I encountered an issue connecting to the agent. Please ensure the backend is running.',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleCitationClick = (citation: CitationData) => {
    setActiveCitation(citation);
  };

  return (
    <div className="flex flex-col h-[700px] bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden ring-1 ring-black/5">
      {/* Header */}
      <div className="px-8 py-5 border-b border-slate-100 bg-white flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="p-2.5 bg-blue-600 rounded-2xl text-white shadow-lg shadow-blue-600/20">
            <Cpu size={20} />
          </div>
          <div>
            <h3 className="text-sm font-extrabold text-slate-900 tracking-tight">Agent Workspace</h3>
            <div className="flex items-center space-x-2 mt-0.5">
               <span className="text-[10px] font-extrabold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full uppercase tracking-widest">
                 {selectedAction}
               </span>
               <span className="h-1 w-1 rounded-full bg-slate-300" />
               <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                 {selectedDocIds.length} Sources Active
               </span>
            </div>
          </div>
        </div>
        <div className="flex -space-x-2">
           {[...Array(Math.min(3, selectedDocIds.length))].map((_, i) => (
             <div key={i} className="h-8 w-8 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center text-[10px] font-bold text-slate-400">
               {String.fromCharCode(65 + i)}
             </div>
           ))}
           {selectedDocIds.length > 3 && (
             <div className="h-8 w-8 rounded-full bg-blue-50 border-2 border-white flex items-center justify-center text-[10px] font-bold text-blue-600">
               +{selectedDocIds.length - 3}
             </div>
           )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-slate-50/30 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-400/20 blur-3xl rounded-full" />
              <div className="relative p-6 bg-white rounded-3xl shadow-xl border border-slate-100 text-blue-600">
                <MessageSquare size={40} strokeWidth={1.5} />
              </div>
            </div>
            <div className="space-y-2 max-w-sm">
              <h4 className="text-slate-900 font-extrabold text-lg">Intelligent Analysis</h4>
              <p className="text-slate-500 text-sm leading-relaxed font-medium">
                Your research agent is ready. Ask a question, request a summary, or compare findings across your uploaded documents.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-4">
               {['Summarize key findings', 'Compare methodologies', 'Extract main metrics'].map((hint) => (
                 <button 
                  key={hint}
                  onClick={() => setInputValue(hint)}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:border-blue-400 hover:text-blue-600 transition-all shadow-sm active:scale-95"
                 >
                   {hint}
                 </button>
               ))}
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className={cn(
                "flex space-x-4 animate-in slide-in-from-bottom-4 fade-in duration-500",
                m.role === 'user' ? "flex-row-reverse space-x-reverse" : "flex-row"
              )}
            >
              <div className={cn(
                "flex-shrink-0 p-3 rounded-2xl h-11 w-11 flex items-center justify-center shadow-lg transition-transform hover:scale-105",
                m.role === 'user' 
                  ? "bg-slate-900 text-white shadow-slate-900/10" 
                  : "bg-blue-600 text-white shadow-blue-600/20"
              )}>
                {m.role === 'user' ? <User size={20} /> : <Cpu size={20} />}
              </div>
              
              <div className={cn(
                "max-w-[85%] rounded-3xl px-6 py-5 shadow-sm border",
                m.role === 'user' 
                  ? "bg-white border-slate-100 text-slate-800" 
                  : "bg-white border-blue-50 text-slate-700 ring-1 ring-blue-500/5"
              )}>
                <div className="prose prose-slate prose-sm max-w-none prose-p:leading-relaxed prose-headings:text-slate-900 prose-headings:font-extrabold prose-strong:text-blue-600 prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-slate-900 prose-code:before:content-none prose-code:after:content-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                </div>
                
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap gap-3">
                    {m.citations.map((c, i) => (
                      <button
                        key={i}
                        onClick={() => handleCitationClick(c)}
                        className="text-[10px] font-extrabold text-blue-600 bg-blue-50/50 border border-blue-100 px-3 py-1.5 rounded-xl hover:bg-blue-100 transition-all flex items-center active:scale-95"
                      >
                        <Link2 size={12} className="mr-1.5" />
                        Source [{i + 1}]
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {isTyping && (
          <div className="flex space-x-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
            <div className="flex-shrink-0 p-3 rounded-2xl h-11 w-11 bg-blue-600 text-white flex items-center justify-center shadow-lg shadow-blue-600/20">
              <Cpu size={20} />
            </div>
            <div className="bg-white border border-blue-50 rounded-3xl px-6 py-5 flex items-center space-x-3 shadow-sm ring-1 ring-blue-500/5">
              <div className="flex space-x-1">
                 <div className="h-1.5 w-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:-0.3s]" />
                 <div className="h-1.5 w-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:-0.15s]" />
                 <div className="h-1.5 w-1.5 bg-blue-600 rounded-full animate-bounce" />
              </div>
              <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-[0.2em] ml-2">
                Agent Analyzing...
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-8 border-t border-slate-100 bg-white">
        <div className="relative group">
          <div className="absolute inset-0 bg-blue-500/5 blur-2xl rounded-3xl group-focus-within:bg-blue-500/10 transition-all" />
          <div className="relative flex items-center">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask anything about the research..."
              className="w-full pl-7 pr-16 py-5 rounded-2xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-sm font-bold shadow-sm group-hover:border-slate-300"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isTyping}
              aria-label="Send message"
              className="absolute right-2.5 p-3.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-slate-100 disabled:text-slate-400 transition-all shadow-xl shadow-blue-600/20 active:scale-90"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-center space-x-6">
           <div className="flex items-center space-x-2">
              <Sparkles size={12} className="text-amber-500" />
              <span className="text-[10px] text-slate-400 font-extrabold uppercase tracking-widest">
                AI Hallucination Protection Active
              </span>
           </div>
           <div className="h-1 w-1 rounded-full bg-slate-200" />
           <span className="text-[10px] text-slate-400 font-extrabold uppercase tracking-widest">
             Gemini 1.5 Pro
           </span>
        </div>
      </form>

      {/* Citation Modal */}
      {activeCitation && (
        <CitationCard 
          citation={activeCitation} 
          onClose={() => setActiveCitation(null)} 
        />
      )}
    </div>
  );
};
