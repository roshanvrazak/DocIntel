import React, { useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadClient } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { CheckCircle2, FileText, Loader2, XCircle, UploadCloud } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { UploadingFile } from '../types';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface UploadZoneProps {
  files: UploadingFile[];
  setFiles: React.Dispatch<React.SetStateAction<UploadingFile[]>>;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ files, setFiles }) => {
  // Extract all non-null doc IDs to subscribe to - memoized to prevent unnecessary WS re-renders
  const docIds = React.useMemo(() => 
    files
      .filter((f) => f.id !== undefined)
      .map((f) => f.id as string),
    [files]
  );
    
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
  }, [updates, setFiles]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // Add new files to the state with a temporary local ID for tracking
    const newFilesWithLocalId = acceptedFiles.map((file) => ({
      file,
      status: 'pending',
      progress: 0,
      localId: Math.random().toString(36).substring(7),
    }));

    setFiles((prev) => [...prev, ...newFilesWithLocalId]);

    // Upload files in parallel
    await Promise.all(
      newFilesWithLocalId.map(async (newFile) => {
        const formData = new FormData();
        formData.append('file', newFile.file);

        try {
          setFiles((prev) =>
            prev.map((f) =>
              f.localId === newFile.localId ? { ...f, status: 'uploading' } : f
            )
          );

          const response = await uploadClient.post('/api/upload', formData);
          const { id, status } = response.data;

          setFiles((prev) =>
            prev.map((f) =>
              f.localId === newFile.localId
                ? { ...f, id, status: status || 'uploaded', progress: 5 }
                : f
            )
          );
        } catch (error) {
          console.error('Upload failed', error);
          setFiles((prev) =>
            prev.map((f) =>
              f.localId === newFile.localId ? { ...f, status: 'error', progress: 0 } : f
            )
          );
        }
      })
    );
  }, [setFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
  });

  return (
    <div className="w-full space-y-8">
      <div
        {...getRootProps()}
        className={cn(
          'group relative border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer transition-all duration-300 ease-in-out',
          isDragActive
            ? 'border-blue-500 bg-blue-50/50 scale-[1.01]'
            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          <div className={cn(
            "p-5 rounded-2xl mb-5 transition-colors duration-300 shadow-sm",
            isDragActive ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-500 group-hover:bg-slate-200"
          )}>
            <UploadCloud className="h-10 w-10" />
          </div>
          <h3 className="text-xl font-extrabold text-slate-900 mb-2">
            {isDragActive ? 'Drop your PDFs' : 'Upload Research Papers'}
          </h3>
          <p className="text-slate-500 max-w-xs mx-auto text-sm font-medium leading-relaxed">
            Drag and drop multiple PDF files here, or click to browse your computer.
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden ring-1 ring-black/5">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h3 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
              Processing Queue
            </h3>
            <span className="bg-blue-600 text-white text-[10px] font-extrabold px-2.5 py-1 rounded-full shadow-lg shadow-blue-600/20">
              {files.length} {files.length === 1 ? 'File' : 'Files'}
            </span>
          </div>
          <ul className="divide-y divide-slate-100">
            {files.map((file) => (
              <li key={file.localId} className="px-6 py-5 hover:bg-slate-50/30 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-4">
                    <div className="p-2.5 bg-blue-50 rounded-xl text-blue-600">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-extrabold text-slate-900 truncate max-w-[200px] md:max-w-[300px]">
                        {file.file.name}
                      </p>
                      <div className="flex items-center mt-1">
                         <span className={cn(
                           "text-[9px] font-extrabold uppercase tracking-widest px-2 py-0.5 rounded-full",
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
                        <span className="text-[10px] font-extrabold hidden sm:inline uppercase tracking-widest">Ready</span>
                      </div>
                    ) : file.status.startsWith('error') ? (
                      <div className="flex items-center text-red-600 space-x-1">
                        <XCircle className="h-5 w-5" />
                        <span className="text-[10px] font-extrabold hidden sm:inline uppercase tracking-widest">Failed</span>
                      </div>
                    ) : (
                      <div className="flex items-center text-blue-600 space-x-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-xs font-extrabold tabular-nums">{file.progress}%</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {(!file.status.startsWith('error') && file.status !== 'ready') && (
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-blue-600 h-full transition-all duration-500 ease-out shadow-sm"
                      style={{ width: `${file.progress}%` }}
                    />
                  </div>
                )}
                
                {file.status.startsWith('error') && (
                  <p className="text-[10px] text-red-500 mt-1 font-bold uppercase tracking-tight">
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
