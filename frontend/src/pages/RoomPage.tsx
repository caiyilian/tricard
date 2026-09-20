import type { RoomStateMessage } from '../utils/types';
import { Avatar } from '../components/Avatar';

interface Props {
  state: RoomStateMessage;
  onReady: () => void;
  onStart: () => void;
  onLeave: () => void;
}

const AI_LABEL: Record<string, string> = { douzero: '🤖 DouZero', llm: '🧠 LLM', basic: '🤖 规则AI' };

export default function RoomPage({ state, onReady, onStart, onLeave }: Props) {
  const room = state.room;
  const myUsername = localStorage.getItem('username') || '';
  const mySeat = room.seats.findIndex(s => s?.username === myUsername);
  const mySeatInfo = mySeat >= 0 ? room.seats[mySeat] : null;
  const isHost = mySeat === room.host_seat;
  const nonHostHumans = room.seats.filter((s, i) => s && !s.is_ai && i !== room.host_seat);
  const allReady = nonHostHumans.every(s => s!.ready);

  return (
    <div style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="table-felt" />
      <div className="tc-panel anim-popIn" style={{ width: 560, padding: 26, position: 'relative', zIndex: 2 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <h2 style={{ margin: 0, fontSize: 22 }}>房间 <span style={{ color: 'var(--gold)' }}>#{room.code}</span></h2>
          <button className="tc-btn secondary" style={{ padding: '6px 16px', fontSize: 13 }} onClick={onLeave}>退出房间</button>
        </div>
        <p style={{ color: 'var(--ink-dim)', marginBottom: 18, fontSize: 13 }}>底分 {room.base_bet} 豆 · 把房号告诉局域网好友即可加入</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {room.seats.map((s, i) => (
            <div key={i} className="anim-fadeUp" style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '12px 16px', borderRadius: 12, animationDelay: `${i * 0.08}s`,
              background: s ? 'rgba(255,255,255,.05)' : 'rgba(255,255,255,.02)',
              border: `1px dashed ${s ? 'rgba(255,213,74,.25)' : 'rgba(255,255,255,.12)'}`,
            }}>
              {s ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Avatar nickname={s.nickname} avatar={s.avatar} size={44} ring={s.ready && !s.is_ai ? '#4ecca3' : undefined} />
                  <div>
                    <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
                      {s.nickname}
                      {i === room.host_seat && <span style={{ fontSize: 11, background: 'linear-gradient(180deg,#ffe082,#e8a900)', color: '#5a3a00', padding: '1px 7px', borderRadius: 6, fontWeight: 800 }}>房主</span>}
                      {s.is_ai && <span style={{ fontSize: 11, background: 'rgba(124,131,253,.2)', color: '#aab2ff', padding: '1px 7px', borderRadius: 6 }}>{AI_LABEL[s.ai_type || 'basic']}</span>}
                      <span style={{ fontSize: 12, color: s.connected ? 'var(--green)' : '#666' }}>{s.connected ? '● 在线' : '○ 离线'}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--ink-dim)', marginTop: 2 }}>
                      胜率 {(s as any).win_rate != null ? `${((s as any).win_rate * 100).toFixed(1)}%` : '-'} · 欢乐豆 {(s as any).joy_beans ?? '?'}
                    </div>
                  </div>
                </div>
              ) : (
                <span style={{ color: 'var(--ink-dim)', padding: '10px 0' }}>等待玩家加入…</span>
              )}
              <div style={{ fontSize: 13, fontWeight: 600, color: s?.ready ? 'var(--green)' : 'var(--ink-dim)' }}>
                {s?.ready ? '✓ 已准备' : (s && !s.is_ai && i !== room.host_seat ? '未准备' : '')}
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 22 }}>
          {isHost ? (
            <button className="tc-btn gold" onClick={onStart} disabled={!allReady} style={{ flex: 1, padding: 13, fontSize: 16 }}>
              {allReady ? '开始游戏' : '等待所有玩家准备…'}
            </button>
          ) : (
            <button className={mySeatInfo?.ready ? 'tc-btn secondary' : 'tc-btn'} onClick={onReady} style={{ flex: 1, padding: 13, fontSize: 16 }}>
              {mySeatInfo?.ready ? '取消准备' : '准备'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
