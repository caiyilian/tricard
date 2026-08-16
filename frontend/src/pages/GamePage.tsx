import { useState, useCallback } from 'react';
import type { RoomStateMessage, CommentEvent } from '../utils/types';

interface Props {
  state: RoomStateMessage;
  comments: CommentEvent[];
  onPlay: (cards: number[]) => void;
  onPass: () => void;
}

function cardImg(label: string, i: number): string {
  if (label === 'BJ') return '/cards/Poker_Joker_B.png';
  if (label === 'CJ') return '/cards/Poker_Joker_R.png';
  return `/cards/Poker_S${label}.png`; // 统一用黑桃
}

export default function GamePage({ state, comments, onPlay, onPass }: Props) {
  const room = state.room;
  const priv = state.private!;
  const hand = priv.hand || [];
  const handLabels = priv.hand_labels || [];
  const remaining = priv.remaining || [0, 0, 0];
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [showResult, setShowResult] = useState(false);

  const toggle = useCallback((idx: number) => {
    setSelected(s => { const n = new Set(s); n.has(idx) ? n.delete(idx) : n.add(idx); return n; });
  }, []);

  const handlePlay = () => {
    const cards = Array.from(selected).map(i => hand[i]);
    if (cards.length === 0) return;
    onPlay(cards);
    setSelected(new Set());
  };

  const handlePass = () => {
    onPass();
    setSelected(new Set());
  };

  // 结算面板
  if (showResult && state.room.status === 'finished') {
    // We'll handle game_end via parent
  }

  // 判断座位位置
  const seats = [
    { seat: 0, pos: 'bottom', label: '我', remaining: remaining[0] },
    { seat: 1, pos: 'left', label: '上家', remaining: remaining[1] },
    { seat: 2, pos: 'right', label: '下家', remaining: remaining[2] },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', color: '#eee', position: 'relative', minHeight: '100vh' }}>
      {/* 顶栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: 12, background: '#1a1a2e', borderRadius: '0 0 12px 12px' }}>
        <span>房间 #{room.code} · 底分 {room.base_bet}</span>
        <span>炸弹 {priv.bomb_count} · 轮次 {priv.trick}</span>
        {priv.landlord_seat !== null && <span>{priv.landlord_seat === 0 ? '我是地主' : '我是农民'}</span>}
      </div>

      {/* 对手信息 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '20px 40px' }}>
        {seats.filter(s => s.pos !== 'bottom').map(s => (
          <div key={s.seat} style={{ textAlign: 'center', background: '#16213e', padding: '12px 20px', borderRadius: 8, minWidth: 100 }}>
            <div>{room.seats[s.seat]?.nickname || '等待'}</div>
            <div style={{ fontSize: 12, color: '#aaa' }}>{room.seats[s.seat]?.is_ai ? 'AI' : '真人'}</div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#4ecca3', marginTop: 4 }}>{s.remaining}</div>
            <div style={{ fontSize: 12, color: '#888' }}>张</div>
          </div>
        ))}
      </div>

      {/* 出牌区 */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 100, margin: '12px 0' }}>
        {priv.last_play_labels.length > 0 && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>上一手 {room.seats[priv.last_play_by]?.nickname}</div>
            <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
              {priv.last_play_labels.map((l, i) => (
                <img key={i} src={cardImg(l, i)} style={{ width: 48, height: 68, borderRadius: 4 }} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 手牌 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 4, padding: '12px 0' }}>
        {handLabels.map((l, i) => (
          <div key={i} onClick={() => toggle(i)} style={{
            cursor: 'pointer',
            transform: selected.has(i) ? 'translateY(-16px)' : 'none',
            transition: 'transform 0.12s',
            filter: !priv.can_act ? 'brightness(0.6)' : 'none',
            pointerEvents: priv.can_act ? 'auto' : 'none' as React.CSSProperties['pointerEvents'],
          }}>
            <img src={cardImg(l, i)} style={{ width: 52, height: 72, borderRadius: 6, border: selected.has(i) ? '2px solid #e94560' : '2px solid transparent' }} />
          </div>
        ))}
      </div>

      {/* 操作按钮 */}
      {priv.can_act && (
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', padding: 12 }}>
          <button onClick={handlePlay} style={{ padding: '10px 28px', backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>
            出牌
          </button>
          <button onClick={handlePass} style={{ padding: '10px 28px', backgroundColor: '#333', color: '#eee', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>
            不出
          </button>
        </div>
      )}
      {!priv.can_act && priv.turn !== null && (
        <div style={{ textAlign: 'center', padding: 12, color: '#888' }}>
          等待 {room.seats[priv.turn]?.nickname} 出牌...
        </div>
      )}

      {/* 评论 / 聊天 */}
      {comments.length > 0 && (
        <div style={{ position: 'fixed', bottom: 20, right: 20, maxWidth: 300, background: 'rgba(0,0,0,0.7)', borderRadius: 8, padding: 12 }}>
          {comments.slice(-3).reverse().map((c, i) => (
            <div key={i} style={{ fontSize: 13, marginBottom: 4, color: c.personality === 'savage' ? '#ff6b6b' : '#4ecca3' }}>
              <strong>{c.speaker}:</strong> {c.text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}