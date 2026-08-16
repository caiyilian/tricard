const BASE = '';

async function req<T>(method: string, path: string, data?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('token');
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => req<{ status: string }>('GET', '/api/health'),

  register: (username: string, password: string, nickname?: string) =>
    req<{ token: string; user: { id: number } }>('POST', '/api/auth/register', { username, password, nickname }),

  login: (username: string, password: string) =>
    req<{ token: string; user: { id: number } }>('POST', '/api/auth/login', { username, password }),

  getMe: () => req<{ username: string; nickname: string; joy_beans: number; wins: number; losses: number; games: number; win_rate: number | null; avatar: string | null }>('GET', '/api/users/me'),

  updateMe: (data: { nickname?: string }) => req<{ nickname: string }>('PUT', '/api/users/me', data),

  getRanking: (by = 'beans', limit = 50) =>
    req<{ by: string; items: { nickname: string; joy_beans: number; wins: number; win_rate: number | null }[] }>('GET', `/api/ranking?by=${by}&limit=${limit}`),

  listRooms: () => req<{ rooms: { code: string; base_bet: number; status: string; players: number }[] }>('GET', '/api/rooms'),

  uploadAvatar: async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    const token = localStorage.getItem('token');
    const res = await fetch(`${BASE}/api/users/avatar`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: 'upload failed' }))).detail);
    return res.json() as Promise<{ avatar: string }>;
  },
};