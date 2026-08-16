import { useCallback } from 'react';
import type { RoomStateMessage } from '../utils/types';

interface Props {
  state: RoomStateMessage;
  onReady: () => void;
  onStart: () => void;
  onLeave: () => void;
}

export default function RoomPage({ state, onReady, onStart, onLeave }: Props) {
  const room = state.room;
  const myUsername = localStorage.getItem('username') || '';
  const mySeat = room.seats.findIndex(s => s?.username === myUsername);
  const mySeatInfo = mySeat >= 0 ? room.seats[mySeat] : null;
  const isHost = mySeat === room.host_seat;
  const humans = room.seats.filter(s => s && !s.is_ai);
  const allReady = humans.length > 0 && humans.every(s => s.ready);

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 20, color: '#eee' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>房间 #{room.code}</h2>
        <button onClick={onLeave} style={{ padding: '6px 14px', backgroundColor: '#333', color: '#eee', border: 'none', borderRadius: 6, cursor: 'pointer' }}>退出</button>
      </div>
      <p style={{ color: '#aaa', marginBottom: 16 }}>底分: {room.base_bet} 豆</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {room.seats.map((s, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: '#16213e', borderRadius: 8 }}>
            <div>
              {s ? (
                <>
                  <span style={{ fontWeight: 'bold' }}>{s.nickname}</span>
                  {i === room.host_seat && <span style={{ marginLeft: 6, fontSize: 11, color: '#ffd700', background: '#333', padding: '1px 5px', borderRadius: 3 }}>房主</span>}
                  {s.is_ai && <span style={{ marginLeft: 8, fontSize: 12, color: '#aaa', background: '#0f3460', padding: '2px 6px', borderRadius: 4 }}>AI</span>}
                  {s.connected && <span style={{ marginLeft: 8, fontSize: 12, color: '#4ecca3' }}>●</span>}
                  {!s.connected && <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>○</span>}
                </>
              ) : <span style={{ color: '#555' }}>等待玩家...</span>}
            </div>
            <div style={{ fontSize: 12, color: s?.ready ? '#4ecca3' : '#666' }}>
              {s?.ready ? '已准备' : (s && !s.is_ai ? '未准备' : '')}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        {isHost ? (
          <button onClick={onStart} disabled={!allReady} style={{
            flex: 1, padding: 12, border: 'none', borderRadius: 6, fontSize: 16, cursor: allReady ? 'pointer' : 'not-allowed',
            backgroundColor: allReady ? '#e94560' : '#333', color: allReady ? '#fff' : '#666',
          }}>
            开始游戏
          </button>
        ) : (
          <button onClick={onReady} style={{
            flex: 1, padding: 12, border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer',
            backgroundColor: mySeatInfo?.ready ? '#666' : '#4ecca3', color: '#fff',
          }}>
            {mySeatInfo?.ready ? '取消准备' : '准备'}
          </button>
        )}
      </div>
    </div>
  );
}