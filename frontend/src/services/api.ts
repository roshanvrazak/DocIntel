import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper for multipart/form-data (file uploads)
export const uploadClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// Document management helpers
export const documentsApi = {
  list: (page = 1, limit = 20) =>
    apiClient.get(`/api/documents?page=${page}&limit=${limit}`),
  delete: (id: string) =>
    apiClient.delete(`/api/documents/${id}`),
  reprocess: (id: string) =>
    apiClient.post(`/api/documents/${id}/reprocess`),
};
