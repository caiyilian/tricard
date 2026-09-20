import { useEffect, useRef, useState } from 'react';
import { api } from '../utils/api';
import { Avatar } from '../components/Avatar';

interface Props {
  onJoin: (code: string) => void;
  onCreate: (aiType: string) => void;
  onLogout: () => void;
}

interface Me { username: string; nickname: string; joy_beans: number; wins: number; losses: number; games: number; win_rate: number | null; avatar: string | null }
interface RankItem { nickname: string; joy_beans: number; wins: number; win_rate: number | null }

export default function LobbyPage({ onJoin, onCreate, onLogout }: Props) {
  const [rooms, setRooms] = useState<{ code: string; base_bet: number; status: string; players: number }[]>([]);
  const [searchCode, setSearchCode] = useState('');
  const [user, setUser] = useState<Me | null>(null);
  const [aiType, setAiType] = useState('basic');
  const [rankBy, setRankBy] = useState<'beans' | 'wins' | 'winrate'>('beans');
  const [rank, setRank] = useState<RankItem[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getMe().then(u => {
      setUser(u as Me);
      localStorage.setItem('username', (u as any).username || '');
    }).catch(() => {});
    const load = () => api.listRooms().then(r => setRooms(r.rooms)).catch(() => {});
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    api.getRanking(rankBy, 10).then(r => setRank(r.items as RankItem[])).catch(() => {});
  }, [rankBy]);

  const handleAvatar = async (f: File) => {
    try {
      await api.uploadAvatar(f);
      const u = await api.getMe();
      setUser(u as Me);
    } catch { /* ignore */ }
  };

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '22px 18px 40px' }}>
      {/* 顶栏 */}
      <div className="anim-fadeUp" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22 }}>
        <h1 style={{
          margin: 0, fontSize: 26, fontWeight: 900, letterSpacing: 3,
          background: 'linear-gradient(180deg,#fff6c8,#ffd54a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>🃏 Tricard 斗地主</h1>
        {user && (
          <div className="tc-panel" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '7px 16px 7px 8px' }}>
            <div style={{ position: 'relative', cursor: 'pointer' }} title="点击更换头像" onClick={() => fileRef.current?.click()}>
              <Avatar nickname={user.nickname} avatar={user.avatar} size={42} />
              <div style={{ position: 'absolute', right: -2, bottom: -2, fontSize: 11, background: '#26344a', borderRadius: '50%', width: 17, height: 17, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✎</div>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => e.target.files?.[0] && handleAvatar(e.target.files[0])} />
            </div>
            <div style={{ fontSize: 13 }}>
              <div style={{ fontWeight: 700 }}>{user.nickname}</div>
              <div style={{ color: 'var(--ink-dim)', fontSize: 12 }}>
                <span style={{ color: 'var(--gold)', fontWeight: 700 }}>🫘 {user.joy_beans}</span>
                {' · '}胜 {user.wins} / 负 {user.losses}
              </div>
            </div>
            <button className="tc-btn secondary" style={{ padding: '5px 12px', fontSize: 12 }}
              onClick={() => { localStorage.removeItem('token'); onLogout(); }}>退出</button>
          </div>
        )}
      </div>

      {/* 操作栏 */}
      <div className="tc-panel anim-fadeUp" style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center', padding: 16, animationDelay: '.08s' }}>
        <button className="tc-btn gold" onClick={() => onCreate(aiType)}>➕ 创建房间</button>
        <select value={aiType} onChange={e => setAiType(e.target.value)} className="tc-input" style={{ cursor: 'pointer' }}>
          <option value="basic">AI：规则AI（新手）</option>
          <option value="douzero">AI：DouZero（职业）</option>
          <option value="llm">AI：LLM（人性化）</option>
        </select>
        <div style={{ display: 'flex', gap: 8, flex: 1, minWidth: 220 }}>
          <input className="tc-input" placeholder="输入房号搜索" value={searchCode}
            onChange={e => setSearchCode(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchCode.trim() && onJoin(searchCode.trim())}
            style={{ flex: 1 }} />
          <button className="tc-btn" onClick={() => searchCode.trim() && onJoin(searchCode.trim())}>搜索</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* 房间列表 */}
        <div className="tc-panel anim-fadeUp" style={{ flex: 1, minWidth: 320, padding: 18, animationDelay: '.16s' }}>
          <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>🏠 房间列表</h3>
          {rooms.length === 0 && (
            <div style={{ textAlign: 'center', padding: '34px 0', color: 'var(--ink-dim)' }}>
              <div style={{ fontSize: 42, marginBottom: 8, animation: 'floatY 3s ease-in-out infinite' }}>🎴</div>
              暂无房间，创建一局吧
            </div>
          )}
          {rooms.map((r, i) => (
            <div key={r.code} className="anim-fadeUp" style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '12px 14px', marginBottom: 8, borderRadius: 10,
              background: 'rgba(255,255,255,.045)', border: '1px solid rgba(255,255,255,.07)',
              animationDelay: `${0.2 + i * 0.06}s`, transition: 'background .2s',
            }}>
              <div>
                <span style={{ fontWeight: 800, marginRight: 10, color: 'var(--gold)' }}>#{r.code}</span>
                <span style={{
                  fontSize: 12, padding: '2px 8px', borderRadius: 99,
                  background: r.status === 'waiting' ? 'rgba(78,204,163,.15)' : 'rgba(233,69,96,.15)',
                  color: r.status === 'waiting' ? 'var(--green)' : 'var(--accent)',
                }}>{r.status === 'waiting' ? '等待中' : '游戏中'}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ color: 'var(--ink-dim)', fontSize: 13 }}>{r.players}/3 人 · {r.base_bet} 豆</span>
                <button className="tc-btn" style={{ padding: '6px 16px', fontSize: 13 }} onClick={() => onJoin(r.code)}>加入</button>
              </div>
            </div>
          ))}
        </div>

        {/* 排行榜 */}
        <div className="tc-panel anim-fadeUp" style={{ width: 300, padding: 18, animationDelay: '.24s' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16 }}>🏆 排行榜</h3>
            <div style={{ display: 'flex', gap: 4 }}>
              {([['beans', '豆'], ['wins', '胜场'], ['winrate', '胜率']] as const).map(([k, label]) => (
                <button key={k} onClick={() => setRankBy(k)} style={{
                  padding: '3px 10px', fontSize: 12, border: 'none', borderRadius: 99, cursor: 'pointer',
                  background: rankBy === k ? 'var(--gold)' : 'rgba(255,255,255,.08)',
                  color: rankBy === k ? '#5a3a00' : 'var(--ink-dim)', fontWeight: 600,
                }}>{label}</button>
              ))}
            </div>
          </div>
          {rank.length === 0 && <p style={{ color: 'var(--ink-dim)', fontSize: 13 }}>暂无数据</p>}
          {rank.map((p, i) => (
            <div key={i} className="anim-fadeUp" style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '7px 6px',
              borderBottom: '1px solid rgba(255,255,255,.06)', animationDelay: `${0.3 + i * 0.05}s`,
            }}>
              <span style={{
                width: 22, textAlign: 'center', fontWeight: 800, fontSize: 14,
                color: i === 0 ? '#ffd54a' : i === 1 ? '#cfd8dc' : i === 2 ? '#d08c4e' : 'var(--ink-dim)',
              }}>{i + 1}</span>
              <Avatar nickname={p.nickname} size={30} />
              <span style={{ flex: 1, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.nickname}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--gold)' }}>
                {rankBy === 'beans' ? `🫘${p.joy_beans}` : rankBy === 'wins' ? `${p.wins}胜` : p.win_rate != null ? `${(p.win_rate * 100).toFixed(0)}%` : '-'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
