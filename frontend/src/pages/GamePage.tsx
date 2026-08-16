import { useState, useCallback, useRef, useEffect } from 'react';
import type { RoomStateMessage, GameEndEvent } from '../utils/types';

interface Props {
  state: RoomStateMessage;
  gameEnd: GameEndEvent | null;
  onPlay: (cards: number[]) => void;
  onPass: () => void;
  onBid: (action: string) => void;
  onLeave: () => void;
}

function cardImg(label: string): string {
  if (label === 'BJ') return '/cards/Poker_Joker_B.png';
  if (label === 'CJ') return '/cards/Poker_Joker_R.png';
  return `/cards/Poker_S${label}.png`;
}

export default function GamePage({ state, gameEnd, onPlay, onPass, onBid, onLeave }: Props) {
  const room = state.room;
  const priv = state.private!;
  const hand = priv.hand || [];
  const handLabels = priv.hand_labels || [];
  const remaining = priv.remaining || [0, 0, 0];
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [timer, setTimer] = useState(30);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (priv.status === 'playing' && priv.turn !== null) {
      setTimer(30);
      timerRef.current = setInterval(() => {
        setTimer(t => { if (t <= 1) { clearInterval(timerRef.current!); return 0; } return t - 1; });
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setTimer(30);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [priv.turn, priv.status]);

  useEffect(() => { if (gameEnd) setShowResult(true); }, [gameEnd]);

  const toggle = useCallback((idx: number) => {
    setSelected(s => { const n = new Set(s); n.has(idx) ? n.delete(idx) : n.add(idx); return n; });
  }, []);

  const handlePlay = () => {
    const cards = Array.from(selected).map(i => hand[i]);
    if (cards.length === 0) return;
    onPlay(cards);
    setSelected(new Set());
  };

  const handlePass = () => { onPass(); setSelected(new Set()); };
  const handleBid = (action: string) => onBid(action);
  const handleLeave = () => { setShowResult(false); onLeave(); };

  // 每座最近一手出牌
  const lastPlays: Record<number, string[]> = {};
  if (priv.history) {
    for (const e of priv.history.slice().reverse()) {
      if (e.action === 'play' && e.labels?.length && !lastPlays[e.seat]) {
        lastPlays[e.seat] = e.labels;
      }
    }
  }

  const canBeatAny = priv.can_beat_any !== false;

  // ---- 结算窗口 ----
  if (showResult && gameEnd) {
    const r = gameEnd.result;
    return (
      <div style={{ maxWidth: 500, margin: '60px auto', padding: 24, background: '#1a1a2e', borderRadius: 12, color: '#eee', textAlign: 'center' }}>
        <h2 style={{ marginBottom: 20, color: r.winner_team === 'landlord' ? '#e94560' : '#4ecca3' }}>
          {r.winner_team === 'landlord' ? '地主获胜' : '农民获胜'}
        </h2>
        <div style={{ background: '#16213e', borderRadius: 8, padding: 16, marginBottom: 20 }}>
          {Object.values(r.per_seat as any).map((s: any, i: number) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: i < 2 ? '1px solid #333' : 'none' }}>
              <span>{s.nickname} {s.team === 'landlord' ? '(地主)' : '(农民)'}</span>
              <span style={{ color: s.won ? '#4ecca3' : '#e94560', fontWeight: 'bold' }}>{s.delta > 0 ? '+' : ''}{s.delta}</span>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 14, color: '#aaa', marginBottom: 20 }}>💣 {r.bombs} 个 · {r.spring ? '春天翻倍' : '无春天'}</div>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button onClick={() => setShowResult(false)} style={{ padding: '12px 28px', backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>再来一局</button>
          <button onClick={handleLeave} style={{ padding: '12px 28px', backgroundColor: '#333', color: '#eee', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>返回大厅</button>
        </div>
      </div>
    );
  }

  // ---- 抢地主阶段 ----
  if (priv.status === 'bidding') {
    return (
      <div style={{ maxWidth: 600, margin: '60px auto', color: '#eee', textAlign: 'center' }}>
        <h2>抢地主</h2>
        <p style={{ margin: '20px 0', color: '#aaa' }}>底牌: {priv.bottom?.join(' ') || '???'}</p>
        {[0,1,2].map(s => (
          <div key={s} style={{ margin: 8, padding: 10, background: s === priv.bidding_seat ? '#16213e' : '#111', borderRadius: 8 }}>
            {room.seats[s]?.nickname || '?'}
            {priv.bidders?.[s] && <span style={{ marginLeft: 8, color: '#aaa' }}>(已叫)</span>}
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
  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', color: '#eee', minHeight: '100vh', padding: '0 12px' }}>
      {/* 顶栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#1a1a2e', borderRadius: '0 0 10px 10px', fontSize: 13 }}>
        <span>房间 #{room.code} · 底分 {room.base_bet}</span>
        <span>💣 {priv.bomb_count} · 轮次 {priv.trick}</span>
        {priv.landlord_seat !== null && <span>{priv.landlord_seat === 0 ? '我是地主' : '我是农民'}</span>}
      </div>

      {/* 顶部：上家 | 底牌 | 下家 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '16px 20px 0' }}>
        {/* 上家 */}
        <div style={{ minWidth: 100 }}>
          <div style={{ background: '#16213e', padding: '8px 16px', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 14 }}>{room.seats[1]?.nickname}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{room.seats[1]?.is_ai ? 'AI' : '真人'}</div>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#4ecca3' }}>{remaining[1]}</div>
            <div style={{ fontSize: 11, color: '#888' }}>张</div>
          </div>
          {/* 上家出牌区：轮到则显示时钟，否则显示上一次出的牌 */}
          <div style={{ marginTop: 4, display: 'flex', justifyContent: 'flex-start', alignItems: 'center', minHeight: 56 }}>
            {priv.turn === 1 ? (
              <div style={{ padding: '4px 12px', background: timer <= 10 ? '#e94560' : '#333', borderRadius: 8, fontSize: 16, fontWeight: 'bold' }}>
                ⏱ {timer}s
              </div>
            ) : (
              lastPlays[1]?.map((l, i) => (
                <img key={i} src={cardImg(l)} style={{ width: 36, height: 52, borderRadius: 3, marginLeft: i > 0 ? -8 : 0 }} />
              ))
            )}
          </div>
        </div>

        {/* 底牌 */}
        {priv.bottom && priv.bottom.length > 0 && (
          <div style={{ textAlign: 'center', paddingTop: 8 }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>底牌</div>
            <div style={{ display: 'flex', gap: 3, justifyContent: 'center' }}>
              {priv.bottom.map((l, i) => (
                <img key={i} src={cardImg(l)} style={{ width: 36, height: 52, borderRadius: 3 }} />
              ))}
            </div>
          </div>
        )}

        {/* 下家 */}
        <div style={{ minWidth: 100 }}>
          <div style={{ background: '#16213e', padding: '8px 16px', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 14 }}>{room.seats[2]?.nickname}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{room.seats[2]?.is_ai ? 'AI' : '真人'}</div>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#4ecca3' }}>{remaining[2]}</div>
            <div style={{ fontSize: 11, color: '#888' }}>张</div>
          </div>
          {/* 下家出牌区：轮到则显示时钟，否则显示上一次出的牌 */}
          <div style={{ marginTop: 4, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', minHeight: 56 }}>
            {priv.turn === 2 ? (
              <div style={{ padding: '4px 12px', background: timer <= 10 ? '#e94560' : '#333', borderRadius: 8, fontSize: 16, fontWeight: 'bold' }}>
                ⏱ {timer}s
              </div>
            ) : (
              lastPlays[2]?.map((l, i) => (
                <img key={i} src={cardImg(l)} style={{ width: 36, height: 52, borderRadius: 3, marginLeft: i > 0 ? -8 : 0 }} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* 自己的出牌区：轮到则显示时钟，否则显示上一次出的牌 */}
      <div style={{ textAlign: 'center', minHeight: 64, padding: '8px 0', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        {priv.turn === 0 ? (
          <div style={{ padding: '6px 20px', background: timer <= 10 ? '#e94560' : '#333', borderRadius: 12, fontSize: 22, fontWeight: 'bold' }}>
            ⏱ {timer}s
          </div>
        ) : (
          <>
            {lastPlays[0]?.map((l, i) => (
              <img key={i} src={cardImg(l)} style={{ width: 42, height: 60, borderRadius: 4, marginLeft: i > 0 ? -10 : 0 }} />
            ))}
            {!lastPlays[0] && priv.last_play_labels.length > 0 && (
              priv.last_play_labels.map((l, i) => <img key={i} src={cardImg(l)} style={{ width: 42, height: 60, borderRadius: 4, marginLeft: i > 0 ? -10 : 0 }} />)
            )}
          </>
        )}
      </div>

      {/* 手牌 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 4, padding: '8px 0' }}>
        {handLabels.map((l, i) => (
          <div key={i} onClick={() => toggle(i)} style={{
            cursor: priv.can_act && canBeatAny ? 'pointer' : 'default',
            transform: selected.has(i) ? 'translateY(-16px)' : 'none',
            transition: 'transform 0.12s',
            filter: !priv.can_act ? 'brightness(0.6)' : 'none',
            pointerEvents: priv.can_act && canBeatAny ? 'auto' : 'none' as React.CSSProperties['pointerEvents'],
          }}>
            <img src={cardImg(l)} style={{ width: 52, height: 72, borderRadius: 6, border: selected.has(i) ? '2px solid #e94560' : '2px solid transparent' }} />
          </div>
        ))}
      </div>

      {/* 操作按钮 */}
      {priv.can_act && (
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', padding: '8px 0' }}>
          {canBeatAny ? (
            <>
              <button onClick={handlePlay} disabled={selected.size === 0} style={{ padding: '10px 28px', backgroundColor: selected.size > 0 ? '#e94560' : '#333', color: selected.size > 0 ? '#fff' : '#666', border: 'none', borderRadius: 6, fontSize: 16, cursor: selected.size > 0 ? 'pointer' : 'not-allowed' }}>出牌</button>
              <button onClick={handlePass} style={{ padding: '10px 28px', backgroundColor: '#333', color: '#eee', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>不出</button>
            </>
          ) : (
            <>
              <button disabled style={{ padding: '10px 28px', backgroundColor: '#333', color: '#666', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'not-allowed' }}>出牌</button>
              <button onClick={handlePass} style={{ padding: '10px 28px', backgroundColor: '#e94560', color: '#fff', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }}>不出（压不住）</button>
            </>
          )}
        </div>
      )}
      {!priv.can_act && priv.turn !== null && priv.status === 'playing' && (
        <div style={{ textAlign: 'center', padding: 8, color: '#888', fontSize: 13 }}>等待 {room.seats[priv.turn]?.nickname} 出牌...</div>
      )}
    </div>
  );
}