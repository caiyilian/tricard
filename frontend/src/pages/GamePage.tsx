import { useState, useCallback, useRef, useEffect } from 'react';
import type { RoomStateMessage, CommentEvent } from '../utils/types';

interface Props {
  state: RoomStateMessage;
  comments: CommentEvent[];
  onPlay: (cards: number[]) => void;
  onPass: () => void;
  onBid: (action: string) => void;
}

function cardImg(label: string, i: number): string {
  if (label === 'BJ') return '/cards/Poker_Joker_B.png';
  if (label === 'CJ') return '/cards/Poker_Joker_R.png';
  return `/cards/Poker_S${label}.png`;
}

export default function GamePage({ state, comments, onPlay, onPass, onBid }: Props) {
  const room = state.room;
  const priv = state.private!;
  const hand = priv.hand || [];
  const handLabels = priv.hand_labels || [];
  const remaining = priv.remaining || [0, 0, 0];
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [timer, setTimer] = useState(30);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 倒计时：当 can_act 时开始 30s 倒计时
  useEffect(() => {
    if (priv.can_act && priv.status === 'playing') {
      setTimer(30);
      timerRef.current = setInterval(() => {
        setTimer(t => { if (t <= 1) { clearInterval(timerRef.current!); return 0; } return t - 1; });
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setTimer(30);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [priv.can_act, priv.turn, priv.status]);

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

  const handleBid = (action: string) => {
    onBid(action);
  };

  // 座位布局
  const seats = [
    { seat: 0, pos: 'bottom', label: '我' },
    { seat: 1, pos: 'left', label: '上家' },
    { seat: 2, pos: 'right', label: '下家' },
  ];

  // ---- 抢地主阶段 ----
  if (priv.status === 'bidding') {
    return (
      <div style={{ maxWidth: 600, margin: '60px auto', color: '#eee', textAlign: 'center' }}>
        <h2>抢地主</h2>
        <p style={{ margin: '20px 0', color: '#aaa' }}>
          底牌: {priv.bottom?.join(' ') || '???'}
        </p>
        {seats.map(s => (
          <div key={s.seat} style={{ margin: 8, padding: 10, background: s.seat === priv.bidding_seat ? '#16213e' : '#111', borderRadius: 8 }}>
            {room.seats[s.seat]?.nickname || '?'}
            {priv.bidders?.[s.seat] && <span style={{ marginLeft: 8, color: '#aaa' }}>(已叫)</span>}
          </div>
        ))}
        {priv.can_bid && (
          <div style={{ marginTop: 24, display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button onClick={() => handleBid('landlord')} style={{ padding: '12px 32px', backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>叫地主</button>
            <button onClick={() => handleBid('pass')} style={{ padding: '12px 32px', backgroundColor: '#333', color: '#eee', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>不叫</button>
          </div>
        )}
        {!priv.can_bid && priv.bidding_seat !== undefined && (
          <p style={{ marginTop: 20, color: '#888' }}>等待 {room.seats[priv.bidding_seat]?.nickname} 叫牌...</p>
        )}
      </div>
    );
  }

  // ---- 出牌阶段 ----
  const canBeatAny = priv.can_beat_any !== false;

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
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#4ecca3', marginTop: 4 }}>{s.seat === 0 ? hand.length : (remaining[s.seat] ?? 0)}</div>
            <div style={{ fontSize: 12, color: '#888' }}>张</div>
          </div>
        ))}
      </div>

      {/* 倒计时 */}
      {priv.can_act && (
        <div style={{ textAlign: 'center', margin: '4px 0' }}>
          <span style={{ display: 'inline-block', padding: '4px 16px', background: timer <= 10 ? '#e94560' : '#333', borderRadius: 12, fontSize: 14 }}>
            ⏱ {timer}s
          </span>
        </div>
      )}

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
        {!priv.last_play_labels.length && priv.status === 'playing' && (
          <div style={{ color: '#888', fontSize: 14 }}>你领出（你是本轮第一个出牌的人）</div>
        )}
      </div>

      {/* 出牌历史 */}
      {priv.history && priv.history.length > 0 && (
        <div style={{ maxHeight: 100, overflowY: 'auto', margin: '8px 40px', padding: 8, background: 'rgba(0,0,0,0.3)', borderRadius: 6, fontSize: 12 }}>
          {priv.history.slice(-10).map((e, i) => (
            <div key={i} style={{ color: '#999', marginBottom: 2 }}>
              <span style={{ color: '#666' }}>第{e.trick}轮</span> {room.seats[e.seat]?.nickname || '?'}:
              {e.action === 'pass' ? ' 过' : ` ${e.labels?.join(' ')}`}
            </div>
          ))}
        </div>
      )}

      {/* 手牌 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 4, padding: '12px 0' }}>
        {handLabels.map((l, i) => (
          <div key={i} onClick={() => toggle(i)} style={{
            cursor: priv.can_act && canBeatAny ? 'pointer' : 'default',
            transform: selected.has(i) ? 'translateY(-16px)' : 'none',
            transition: 'transform 0.12s',
            filter: !priv.can_act ? 'brightness(0.6)' : 'none',
            pointerEvents: priv.can_act && canBeatAny ? 'auto' : 'none' as React.CSSProperties['pointerEvents'],
          }}>
            <img src={cardImg(l, i)} style={{ width: 52, height: 72, borderRadius: 6, border: selected.has(i) ? '2px solid #e94560' : '2px solid transparent' }} />
          </div>
        ))}
      </div>

      {/* 操作按钮 */}
      {priv.can_act && (
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', padding: 12 }}>
          {canBeatAny ? (
            <>
              <button onClick={handlePlay} disabled={selected.size === 0} style={{
                padding: '10px 28px', backgroundColor: selected.size > 0 ? '#e94560' : '#333', color: selected.size > 0 ? '#fff' : '#666',
                border: 'none', borderRadius: 6, fontSize: 16, cursor: selected.size > 0 ? 'pointer' : 'not-allowed',
              }}>
                出牌
              </button>
              <button onClick={handlePass} style={{ padding: '10px 28px', backgroundColor: '#333', color: '#eee', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>
                不出
              </button>
            </>
          ) : (
            <>
              <button disabled style={{ padding: '10px 28px', backgroundColor: '#333', color: '#666', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'not-allowed' }}>
                出牌
              </button>
              <button onClick={handlePass} style={{ padding: '10px 28px', backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>
                不出（压不住）
              </button>
            </>
          )}
        </div>
      )}
      {!priv.can_act && priv.turn !== null && priv.status === 'playing' && (
        <div style={{ textAlign: 'center', padding: 12, color: '#888' }}>
          等待 {room.seats[priv.turn]?.nickname} 出牌...
        </div>
      )}

      {/* 评论（暂时隐藏）
      {comments.length > 0 && (
        <div style={{ position: 'fixed', bottom: 20, right: 20, maxWidth: 300, background: 'rgba(0,0,0,0.7)', borderRadius: 8, padding: 12 }}>
          {comments.slice(-3).reverse().map((c, i) => (
            <div key={i} style={{ fontSize: 13, marginBottom: 4, color: c.personality === 'savage' ? '#ff6b6b' : '#4ecca3' }}>
              <strong>{c.speaker}:</strong> {c.text}
            </div>
          ))}
        </div>
      )}
      */}
    </div>
  );
}