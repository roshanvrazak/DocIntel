import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadClient } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { CheckCircle2, FileText, Loader2, XCircle, UploadCloud } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface UploadingFile {
  id?: string;
  file: File;
  status: string;
  progress: number;
}

export const UploadZone: React.FC = () => {
  const [files, setFiles] = useState<UploadingFile[]>([]);
  
  // Extract all non-null doc IDs to subscribe to
  const docIds = files
    .filter((f) => f.id !== undefined)
    .map((f) => f.id as string);
    
  const updates = useWebSocket(docIds);

  // Update file statuses when WebSocket messages arrive
  useEffect(() => {
    if (Object.keys(updates).length === 0) return;

    setFiles((prev) =>
      prev.map((f) => {
        if (f.id && updates[f.id]) {
          return {
            ...f,
            status: updates[f.id].status,
            progress: updates[f.id].progress,
          };
        }
        return f;
      })
    );
  }, [updates]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // Add new files to the state
    const newFiles = acceptedFiles.map((file) => ({
      file,
      status: 'pending',
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    // Upload each file
    for (const newFile of newFiles) {
      const formData = new FormData();
      formData.append('file', newFile.file);

      try {
        setFiles((prev) =>
          prev.map((f) =>
            f.file === newFile.file ? { ...f, status: 'uploading' } : f
          )
        );

        const response = await uploadClient.post('/api/upload', formData);
        const { id, status } = response.data;

        setFiles((prev) =>
          prev.map((f) =>
            f.file === newFile.file
              ? { ...f, id, status: status || 'uploaded', progress: 5 }
              : f
          )
        );
      } catch (error) {
        console.error('Upload failed', error);
        setFiles((prev) =>
          prev.map((f) =>
            f.file === newFile.file ? { ...f, status: 'error', progress: 0 } : f
          )
        );
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
  });

  return (
    <div className="w-full max-w-3xl mx-auto space-y-8 p-4">
      <div
        {...getRootProps()}
        className={cn(
          'group relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ease-in-out',
          isDragActive
            ? 'border-blue-500 bg-blue-50/50 scale-[1.01]'
            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          <div className={cn(
            "p-4 rounded-full mb-4 transition-colors duration-300",
            isDragActive ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-500 group-hover:bg-slate-200"
          )}>
            <UploadCloud className="h-10 w-10" />
          </div>
          <h3 className="text-xl font-semibold text-slate-900 mb-2">
            {isDragActive ? 'Drop your PDFs' : 'Upload Research Papers'}
          </h3>
          <p className="text-slate-500 max-w-xs mx-auto">
            Drag and drop multiple PDF files here, or click to browse your computer.
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Processing Queue
            </h3>
            <span className="bg-slate-200 text-slate-700 text-xs font-bold px-2 py-1 rounded-full">
              {files.length} {files.length === 1 ? 'File' : 'Files'}
            </span>
          </div>
          <ul className="divide-y divide-slate-100">
            {files.map((file, idx) => (
              <li key={file.id || idx} className="px-6 py-5 hover:bg-slate-50/30 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900 truncate max-w-[240px] md:max-w-[400px]">
                        {file.file.name}
                      </p>
                      <div className="flex items-center mt-1">
                         <span className={cn(
                           "text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded",
                           file.status === 'ready' ? "bg-green-100 text-green-700" :
                           file.status === 'error' ? "bg-red-100 text-red-700" :
                           "bg-blue-100 text-blue-700"
                         )}>
                           {file.status}
                         </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center ml-4">
                    {file.status === 'ready' ? (
                      <div className="flex items-center text-green-600 space-x-1">
                        <CheckCircle2 className="h-5 w-5" />
                        <span className="text-xs font-bold hidden sm:inline">Ready</span>
                      </div>
                    ) : file.status.startsWith('error') ? (
                      <div className="flex items-center text-red-600 space-x-1">
                        <XCircle className="h-5 w-5" />
                        <span className="text-xs font-bold hidden sm:inline">Failed</span>
                      </div>
                    ) : (
                      <div className="flex items-center text-blue-600 space-x-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-xs font-bold tabular-nums">{file.progress}%</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {(!file.status.startsWith('error') && file.status !== 'ready') && (
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-blue-600 h-full transition-all duration-500 ease-out"
                      style={{ width: `${file.progress}%` }}
                    />
                  </div>
                )}
                
                {file.status.startsWith('error') && (
                  <p className="text-[11px] text-red-500 mt-1 font-medium italic">
                    {file.status}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
