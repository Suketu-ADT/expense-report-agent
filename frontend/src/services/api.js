import axios from 'axios';

let API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
if (API_URL) {
    if (!API_URL.startsWith('http')) {
        API_URL = `https://${API_URL}`;
    }
    if (API_URL.endsWith('/')) {
        API_URL = API_URL.slice(0, -1);
    }
    if (!API_URL.endsWith('/api') && !API_URL.includes('localhost')) {
        API_URL = `${API_URL}/api`;
    }
}

export const api = {
    startRun: async (text) => {
        const response = await axios.post(`${API_URL}/run`, {
            request_text: text,
            user_id: "demo_user"
        });
        return response.data;
    },
    
    getRunStatus: async (runId) => {
        const response = await axios.get(`${API_URL}/run/${runId}`);
        return response.data;
    },
    
    getRunLogs: async (runId) => {
        const response = await axios.get(`${API_URL}/run/${runId}/logs`);
        return response.data;
    },
    
    uploadExpenses: async (file) => {
        const formData = new FormData();
        formData.append("file", file);
        const response = await axios.post(`${API_URL}/expenses/import`, formData, {
            headers: {
                "Content-Type": "multipart/form-data"
            }
        });
        return response.data;
    }
};
