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
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    if (!username || !password) { setMsg('请输入用户名和密码'); return; }
    try {
      setBusy(true);
      setMsg('');
      const res = tab === 'login'
        ? await api.login(username, password)
        : await api.register(username, password, nickname || username);
      localStorage.setItem('token', res.token);
      localStorage.setItem('username', (res.user as any).username || username);
      onLogin(res.token);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : '网络错误');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
      {/* 背景漂浮扑克 */}
      {['🂡', '🂾', '🃁', '🃎', '🃑'].map((c, i) => (
        <div key={i} style={{
          position: 'absolute', fontSize: 72, opacity: 0.07, color: '#fff',
          left: `${12 + i * 18}%`, top: `${15 + (i % 3) * 28}%`,
          animation: `floatY ${4 + i}s ease-in-out ${i * 0.7}s infinite`,
        }}>{c}</div>
      ))}
      <div className="tc-panel anim-popIn" style={{ width: 380, padding: 32 }}>
        <div style={{ textAlign: 'center', marginBottom: 26 }}>
          <div style={{ fontSize: 46, animation: 'floatY 3.5s ease-in-out infinite' }}>🃏</div>
          <h1 style={{
            fontSize: 30, fontWeight: 900, letterSpacing: 6,
            background: 'linear-gradient(180deg,#fff6c8,#ffd54a)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>Tricard 斗地主</h1>
          <div style={{ color: 'var(--ink-dim)', fontSize: 13, marginTop: 4 }}>局域网联机 · AI 同桌 · 欢乐豆结算</div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 18, background: 'rgba(0,0,0,.3)', borderRadius: 10, padding: 4 }}>
          {(['login', 'register'] as const).map(t => (
            <button key={t} onClick={() => { setTab(t); setMsg(''); }} style={{
              flex: 1, padding: 9, border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600,
              background: tab === t ? 'linear-gradient(180deg,#f0617c,#e94560)' : 'transparent',
              color: tab === t ? '#fff' : 'var(--ink-dim)', transition: 'all .2s',
            }}>{t === 'login' ? '登录' : '注册'}</button>
          ))}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input className="tc-input" placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)} />
          <input className="tc-input" type="password" placeholder="密码" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && handle()} />
          {tab === 'register' && <input className="tc-input" placeholder="昵称（可选）" value={nickname} onChange={e => setNickname(e.target.value)} />}
          <button className="tc-btn gold" style={{ padding: 13, fontSize: 16 }} onClick={handle} disabled={busy}>
            {busy ? '请稍候…' : tab === 'login' ? '进入牌桌' : '注册并进入'}
          </button>
        </div>
        {msg && <p className="anim-fadeUp" style={{ color: '#ff8a80', marginTop: 14, fontSize: 13, textAlign: 'center' }}>{msg}</p>}
      </div>
    </div>
  );
}
