import { useEffect, useState, useRef } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws/progress';

export interface ProgressUpdate {
  doc_id: string;
  status: string;
  progress: number;
}

export const useWebSocket = (docIds: string[]) => {
  const [updates, setUpdates] = useState<Record<string, ProgressUpdate>>({});
  const socketsRef = useRef<Record<string, WebSocket>>({});
  const docIdsRef = useRef<string[]>(docIds);

  // Keep docIdsRef up to date
  useEffect(() => {
    docIdsRef.current = docIds;
  }, [docIds]);

  useEffect(() => {
    const currentDocIds = new Set(docIds);
    const activeDocIds = new Set(Object.keys(socketsRef.current));

    // 1. Close sockets for docIds that are no longer in the list
    activeDocIds.forEach((docId) => {
      if (!currentDocIds.has(docId)) {
        console.log(`Closing WS for ${docId}`);
        if (socketsRef.current[docId]) {
          socketsRef.current[docId].close();
          delete socketsRef.current[docId];
        }
      }
    });

    // 2. Open sockets for new docIds
    docIds.forEach((docId) => {
      if (!socketsRef.current[docId]) {
        const connect = () => {
          // If the docId was removed while we were trying to connect, don't proceed
          if (!new Set(docIdsRef.current).has(docId)) return;

          console.log(`Connecting to WS for ${docId}`);
          const url = `${WS_BASE_URL}/${docId}`;
          const socket = new WebSocket(url);

          socket.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data) as ProgressUpdate;
              setUpdates((prev) => ({
                ...prev,
                [docId]: data,
              }));
            } catch (err) {
              console.error(`Failed to parse WebSocket message for ${docId}`, err);
            }
          };

          socket.onopen = () => console.log(`Connected to WS for ${docId}`);
          socket.onerror = (err) => console.error(`WS error for ${docId}`, err);
          
          socket.onclose = () => {
            console.log(`WS closed for ${docId}`);
            // Simple retry logic if it's still in the list and wasn't closed by us
            if (socketsRef.current[docId] === socket && new Set(docIdsRef.current).has(docId)) {
               setTimeout(connect, 3000);
            }
          };

          socketsRef.current[docId] = socket;
        };

        connect();
      }
    });
  }, [docIds]);

  // Full cleanup on unmount
  useEffect(() => {
    return () => {
      Object.values(socketsRef.current).forEach((socket) => {
        socket.close();
      });
      socketsRef.current = {};
    };
  }, []);

  return updates;
};
