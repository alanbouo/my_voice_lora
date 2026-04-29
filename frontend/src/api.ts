import axios from 'axios';

const API_BASE = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api`;
// Production: VITE_API_URL=https://api.voicelora.alanbouo.com:8443

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

export interface Stats {
  total_examples: number;
  golden_examples: number;
  total_ratings: number;
  average_rating: number;
}

export interface Style {
  value: string;
  label: string;
}

export interface GenerateRequest {
  prompt: string;
  style: string;
  context?: string;
}

export interface GenerateResponse {
  text: string;
  generation_id: string;
  examples_used: number;
  style: string;
}

export interface Example {
  id: string;
  response: string;
  context: string | null;
  style: string;
  is_golden: boolean;
}

export interface Config {
  your_name: string;
  your_emails: string[];
  slack_folder: string | null;
  whatsapp_folder: string | null;
  email_folder: string | null;
}

export const getStats = () => api.get<Stats>('/stats').then(r => r.data);
export const getStyles = () => api.get<Style[]>('/styles').then(r => r.data);
export const getConfig = () => api.get<Config>('/config').then(r => r.data);

export const generate = (req: GenerateRequest) => 
  api.post<GenerateResponse>('/generate', req).then(r => r.data);

export const rateGeneration = (generation_id: string, rating: number, feedback?: string) =>
  api.post('/rate', { generation_id, rating, feedback }).then(r => r.data);

export const getExamples = (params?: { style?: string; limit?: number; golden_only?: boolean }) =>
  api.get<Example[]>('/examples', { params }).then(r => r.data);

export const toggleGolden = (id: string, is_golden: boolean) =>
  api.post(`/examples/${id}/golden`, null, { params: { is_golden } }).then(r => r.data);

export const deleteExample = (id: string) =>
  api.delete(`/examples/${id}`).then(r => r.data);

export const importData = (source: 'slack' | 'whatsapp' | 'email') =>
  api.post(`/import/${source}`).then(r => r.data);

export const clearDatabase = () => api.post('/clear').then(r => r.data);

export const exportForFinetune = () => api.post('/export/finetune').then(r => r.data);
