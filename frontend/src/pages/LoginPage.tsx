import { useState } from 'react';
import { api } from '../utils/api';

interface Props {
  onLogin: (token: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [msg, setMsg] = useState('');

  const handle = async () => {
    try {
      setMsg('');
      const res = tab === 'login'
        ? await api.login(username, password)
        : await api.register(username, password, nickname || username);
      localStorage.setItem('token', res.token);
      localStorage.setItem('username', (res.user as any).username || username);
      onLogin(res.token);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : '网络错误');
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '80px auto', padding: 24, background: '#1a1a2e', borderRadius: 12, color: '#eee' }}>
      <h1 style={{ textAlign: 'center', marginBottom: 24 }}>🃏 Tricard</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button onClick={() => setTab('login')} style={{ flex: 1, padding: 8, backgroundColor: tab === 'login' ? '#e94560' : '#16213e', color: '#eee', border: 'none', borderRadius: 6 }}>登录</button>
        <button onClick={() => setTab('register')} style={{ flex: 1, padding: 8, backgroundColor: tab === 'register' ? '#e94560' : '#16213e', color: '#eee', border: 'none', borderRadius: 6 }}>注册</button>
      </div>
      <input placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)} style={inputStyle} />
      <input type="password" placeholder="密码" value={password} onChange={e => setPassword(e.target.value)} style={inputStyle} />
      {tab === 'register' && <input placeholder="昵称（可选）" value={nickname} onChange={e => setNickname(e.target.value)} style={inputStyle} />}
      <button onClick={handle} style={{ width: '100%', padding: 12, backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>
        {tab === 'login' ? '登录' : '注册'}
      </button>
      {msg && <p style={{ color: '#ff6b6b', marginTop: 12 }}>{msg}</p>}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: 10,
  marginBottom: 12,
  borderRadius: 6,
  border: '1px solid #0f3460',
  background: '#16213e',
  color: '#eee',
  fontSize: 14,
  boxSizing: 'border-box',
};