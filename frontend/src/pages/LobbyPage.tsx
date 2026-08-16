import { useEffect, useState } from 'react';
import { api } from '../utils/api';

interface Props {
  onJoin: (code: string) => void;
  onCreate: () => void;
}

export default function LobbyPage({ onJoin, onCreate }: Props) {
  const [rooms, setRooms] = useState<{ code: string; base_bet: number; status: string; players: number }[]>([]);
  const [searchCode, setSearchCode] = useState('');
  const [user, setUser] = useState<{ nickname: string; joy_beans: number; wins: number } | null>(null);

  useEffect(() => {
    api.getMe().then(setUser).catch(() => {});
    const id = setInterval(() => api.listRooms().then(r => setRooms(r.rooms)).catch(() => {}), 3000);
    return () => clearInterval(id);
  }, []);

  const handleSearch = () => {
    if (searchCode.trim()) onJoin(searchCode.trim());
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 20, color: '#eee' }}>
      {/* 顶栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>🃏 Tricard</h2>
        {user && (
          <div style={{ fontSize: 14, color: '#aaa' }}>
            {user.nickname} · 欢乐豆 <span style={{ color: '#ffd700' }}>{user.joy_beans}</span> · 胜场 {user.wins}
          </div>
        )}
      </div>

      {/* 操作栏 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <button onClick={onCreate} style={btnStyle}>➕ 创建房间</button>
        <div style={{ display: 'flex', gap: 4, flex: 1 }}>
          <input placeholder="输入房号搜索" value={searchCode} onChange={e => setSearchCode(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
            style={{ flex: 1, padding: 8, borderRadius: 6, border: '1px solid #0f3460', background: '#16213e', color: '#eee' }} />
          <button onClick={handleSearch} style={btnStyle}>搜索</button>
        </div>
      </div>

      {/* 房间列表 */}
      <div style={{ background: '#1a1a2e', borderRadius: 10, padding: 16 }}>
        <h3 style={{ margin: '0 0 12px' }}>房间列表</h3>
        {rooms.length === 0 && <p style={{ color: '#666' }}>暂无房间，创建一局吧</p>}
        {rooms.map(r => (
          <div key={r.code} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', marginBottom: 6, background: '#16213e', borderRadius: 8 }}>
            <div>
              <span style={{ fontWeight: 'bold', marginRight: 12 }}>#{r.code}</span>
              <span style={{ color: '#aaa' }}>{r.status === 'waiting' ? '等待中' : '游戏中'}</span>
            </div>
            <div>
              <span style={{ color: '#aaa', marginRight: 12 }}>{r.players}/3 人 · {r.base_bet} 豆</span>
              <button onClick={() => onJoin(r.code)} style={smallBtn}>加入</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = { padding: '8px 16px', backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', whiteSpace: 'nowrap' };
const smallBtn: React.CSSProperties = { ...btnStyle, padding: '4px 12px', fontSize: 12 };