const LOCAL_API_BASE = 'http://127.0.0.1:8000/api/v1';
const PROD_API_BASE = 'https://rural-ai-doctor.onrender.com/api/v1';
const API_PORT = 8000;

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return LOCAL_API_BASE;
    }
    // 局域网访问（如 http://192.168.x.x:3000）：后端与本机同主机、跑在 8000 端口。
    return `http://${host}:${API_PORT}/api/v1`;
  }

  return PROD_API_BASE;
}
