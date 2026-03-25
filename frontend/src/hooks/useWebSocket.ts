import { useEffect, useState } from 'react';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws/progress';

export interface ProgressUpdate {
  doc_id: string;
  status: string;
  progress: number;
}

export const useWebSocket = (docIds: string[]) => {
  const [updates, setUpdates] = useState<Record<string, ProgressUpdate>>({});

  useEffect(() => {
    if (docIds.length === 0) return;

    const sockets: Record<string, WebSocket> = {};

    docIds.forEach((docId) => {
      // Don't reconnect if already connected
      if (sockets[docId]) return;

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
      };

      sockets[docId] = socket;
    });

    return () => {
      Object.values(sockets).forEach((socket) => {
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
          socket.close();
        }
      });
    };
  }, [JSON.stringify(docIds)]); // Using JSON.stringify for deep comparison of docIds array

  return updates;
};
