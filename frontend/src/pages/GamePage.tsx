import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import type { RoomStateMessage, GameEndEvent, CommentEvent } from '../utils/types';
import { Card, CardBack, cardImg, cardImgFromInt } from '../components/Card';
import { Avatar } from '../components/Avatar';
import { playSound, unlockAudio, startBgm } from '../utils/sound';

interface Props {
  state: RoomStateMessage;
  gameEnd: GameEndEvent | null;
  hintResult: { cards: number[]; label: string } | null;
  comments: CommentEvent[];
  onHint: (type: string) => void;
  onPlay: (cards: number[]) => void;
  onPass: () => void;
  onBid: (action: string) => void;
  onLeave: () => void;
}

/* ---------- 牌型特效探测 ---------- */
type Fx = 'bomb' | 'rocket' | 'plane' | null;
function detectFx(labels: string[]): Fx {
  if (labels.length === 2 && labels.includes('BJ') && labels.includes('CJ')) return 'rocket';
  if (labels.length === 4 && new Set(labels).size === 1) return 'bomb';
  if (labels.length >= 6) {
    const cnt: Record<string, number> = {};
    labels.forEach(l => { cnt[l] = (cnt[l] || 0) + 1; });
    const triples = Object.values(cnt).filter(n => n >= 3).length;
    if (triples >= 2) return 'plane';
  }
  return null;
}

/* ---------- 环形倒计时 ---------- */
function TimerRing({ seconds, size = 64, warn }: { seconds: number; size?: number; warn: boolean }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, seconds / 30);
  const color = warn ? '#ff5252' : '#ffd54a';
  return (
    <div style={{ position: 'absolute', inset: -(size - 48) / 2 - 4, pointerEvents: 'none' }}>
      <svg width={size + 8} height={size + 8} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={(size + 8) / 2} cy={(size + 8) / 2} r={r} fill="none" stroke="rgba(255,255,255,.15)" strokeWidth={4} />
        <circle cx={(size + 8) / 2} cy={(size + 8) / 2} r={r} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset .9s linear, stroke .3s' }} />
      </svg>
    </div>
  );
}

/* ---------- 弹幕 ---------- */
function Danmaku({ comments }: { comments: CommentEvent[] }) {
  const items = useMemo(() => comments.slice(-6).map((c, i) => ({
    ...c, key: `${comments.length - 6 + i}-${c.text}`,
    top: 8 + ((comments.length - 6 + i) % 5) * 34,
    dur: 9 + ((comments.length - i) % 4),
  })), [comments]);
  return (
    <div className="danmaku-layer">
      {items.map(it => (
        <div key={it.key} className="danmaku-item" style={{ top: `${it.top}%`, animationDuration: `${it.dur}s` }}>
          {it.speaker}：{it.text}
        </div>
      ))}
    </div>
  );
}

/* ---------- 对手信息卡 ---------- */
function OppPanel({ seat, state, timer, side }: {
  seat: number; state: RoomStateMessage; timer: number; side: 'left' | 'right';
}) {
  const room = state.room;
  const priv = state.private!;
  const s = room.seats[seat];
  const remaining = priv.remaining?.[seat] ?? 0;
  const isTurn = priv.turn === seat;
  const isLandlord = priv.landlord_seat === seat;
  if (!s) return null;
  return (
    <div style={{
      position: 'absolute', top: '34%', [side]: 22, display: 'flex', flexDirection: 'column',
      alignItems: side === 'left' ? 'flex-start' : 'flex-end', gap: 8, zIndex: 5,
    } as React.CSSProperties}>
      <div style={{ position: 'relative' }}>
        <Avatar nickname={s.nickname} avatar={s.avatar} size={58} ring={isTurn ? (timer <= 10 ? '#ff5252' : '#ffd54a') : undefined} />
        {isTurn && <TimerRing seconds={timer} size={58} warn={timer <= 10} />}
        {isLandlord && (
          <div className="anim-popIn" style={{
            position: 'absolute', top: -10, [side]: -10, background: 'linear-gradient(180deg,#ffe082,#e8a900)',
            color: '#5a3a00', fontSize: 11, fontWeight: 800, padding: '2px 7px', borderRadius: 8,
            boxShadow: '0 2px 6px rgba(0,0,0,.4)',
          } as React.CSSProperties}>地主</div>
        )}
      </div>
      <div className="tc-panel" style={{ padding: '5px 12px', textAlign: side === 'left' ? 'left' : 'right', fontSize: 13 }}>
        <div style={{ fontWeight: 600 }}>{s.nickname}</div>
        <div style={{ fontSize: 11, color: 'var(--ink-dim)' }}>
          {s.is_ai ? (s.ai_type === 'douzero' ? '🤖 DouZero' : s.ai_type === 'llm' ? '🧠 LLM' : '🤖 AI') : '真人'}
        </div>
      </div>
      {/* 剩余牌：背面小扇形 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ display: 'flex' }}>
          {Array.from({ length: Math.min(remaining, 8) }).map((_, i) => (
            <CardBack key={i} w={20} style={{ marginLeft: i ? -12 : 0 }} />
          ))}
        </div>
        <span style={{
          fontSize: 20, fontWeight: 800, color: remaining <= 2 ? '#ff5252' : 'var(--gold)',
          textShadow: '0 2px 4px rgba(0,0,0,.6)',
          animation: remaining <= 2 ? 'floatY 1s ease-in-out infinite' : undefined,
        }}>{remaining}</span>
      </div>
    </div>
  );
}

/* ---------- 出牌区 ---------- */
function PlayedZone({ labels, from, w = 44 }: { labels: string[]; from: 'me' | 'left' | 'right'; w?: number }) {
  const anim = from === 'me' ? 'playFly' : from === 'left' ? 'playFlyLeft' : 'playFlyRight';
  return (
    <div key={labels.join(',')} style={{ display: 'flex', justifyContent: 'center', animation: `${anim} .35s cubic-bezier(.2,.9,.3,1.2) both` }}>
      {labels.map((l, i) => (
        <img key={i} src={cardImg(l, i)} style={{
          width: w, height: Math.round(w * 72 / 52), borderRadius: 4,
          marginLeft: i ? -w * 0.45 : 0, boxShadow: '0 3px 8px rgba(0,0,0,.5)',
        }} />
      ))}
    </div>
  );
}

function PassBubble({ text = '不出' }: { text?: string }) {
  return (
    <div className="anim-popIn" style={{
      padding: '6px 18px', borderRadius: 999, fontWeight: 700, fontSize: 15,
      background: 'rgba(0,0,0,.6)', border: '1px solid rgba(255,255,255,.25)', color: '#cfd8dc',
      boxShadow: '0 4px 10px rgba(0,0,0,.4)',
    }}>{text}</div>
  );
}

/* ================================================================ */
export default function GamePage({ state, gameEnd, hintResult, comments, onPlay, onPass, onBid, onLeave, onHint }: Props) {
  const room = state.room;
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const selectedRef = useRef<Set<number>>(new Set());
  const [timer, setTimer] = useState(30);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [fx, setFx] = useState<{ type: Fx; key: number }>({ type: null, key: 0 });
  const [dealing, setDealing] = useState(false);
  const [shake, setShake] = useState(0);

  const priv = state.private;
  const hand = priv?.hand || [];
  const handLabels = priv?.hand_labels || [];

  /* 发牌动画 + 音效：手牌从 0 → 17/20 时触发 */
  const prevHandLen = useRef(0);
  useEffect(() => {
    if (hand.length > 0 && prevHandLen.current === 0) {
      setDealing(true);
      playSound('deal', 0.8);
      const t = setTimeout(() => setDealing(false), 1200 + hand.length * 40);
      return () => clearTimeout(t);
    }
    prevHandLen.current = hand.length;
  }, [hand.length]);

  /* 倒计时 */
  useEffect(() => {
    if (priv?.status === 'playing' && priv.turn !== null) {
      setTimer(30);
      timerRef.current = setInterval(() => {
        setTimer(t => {
          if (t <= 1) {
            clearInterval(timerRef.current!);
            const cards = Array.from(selectedRef.current).map(i => hand[i]);
            if (cards.length > 0) { onPlay(cards); } else { onPass(); }
            setSelected(new Set());
            selectedRef.current = new Set();
            return 0;
          }
          return t - 1;
        });
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setTimer(30);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [priv?.turn, priv?.status]);

  /* 结算：音效 */
  useEffect(() => {
    if (gameEnd) {
      setShowResult(true);
      const mine = gameEnd.result.per_seat?.[0] ?? Object.values(gameEnd.result.per_seat)[0];
      playSound(mine?.won ? 'end_win' : 'end_lose', 0.8);
    }
  }, [gameEnd]);

  /* 提示 */
  useEffect(() => {
    if (hintResult && hintResult.cards && hintResult.cards.length > 0) {
      const hintSet = new Set(hintResult.cards.map(c => hand.indexOf(c)).filter(i => i >= 0));
      if (hintSet.size > 0) {
        setSelected(hintSet);
        selectedRef.current = hintSet;
      }
    }
  }, [hintResult]);

  /* 每座本回合最后动作 */
  const lastAction: Record<number, { type: string; labels: string[] }> = {};
  if (priv?.history) {
    const ct = priv.trick;
    for (const e of priv.history) {
      if (e.trick !== ct) continue;
      if (e.action === 'play') lastAction[e.seat] = { type: 'play', labels: e.labels || [] };
      else if (e.action === 'pass') lastAction[e.seat] = { type: 'pass', labels: [] };
    }
  }

  /* 炸弹/飞机特效：监听本回合最新出牌 */
  const fxKeyRef = useRef('');
  useEffect(() => {
    if (!priv?.history?.length) return;
    const last = priv.history[priv.history.length - 1];
    if (last.action !== 'play') return;
    const key = `${priv.trick}-${last.seat}-${(last.labels || []).join('')}`;
    if (key === fxKeyRef.current) return;
    fxKeyRef.current = key;
    const f = detectFx(last.labels || []);
    if (f) {
      setFx({ type: f, key: Date.now() });
      setShake(k => k + 1);
      setTimeout(() => setFx(cur => ({ ...cur, type: null })), 1400);
    }
  }, [priv?.history, priv?.trick]);

  const toggle = useCallback((idx: number) => {
    unlockAudio(); startBgm();
    setSelected(s => {
      const n = new Set(s);
      n.has(idx) ? n.delete(idx) : n.add(idx);
      selectedRef.current = n;
      return n;
    });
  }, []);

  const handlePlay = () => {
    const cards = Array.from(selected).sort((a, b) => a - b).map(i => hand[i]);
    if (cards.length === 0) return;
    onPlay(cards);
    setSelected(new Set());
    selectedRef.current = new Set();
  };
  const handlePass = () => { onPass(); setSelected(new Set()); selectedRef.current = new Set(); };
  const handleLeave = () => { setShowResult(false); onLeave(); };

  /* ---------- 房间已重置 ---------- */
  if (!priv && !gameEnd) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="tc-panel anim-popIn" style={{ maxWidth: 440, padding: 32, textAlign: 'center' }}>
          <h2 style={{ marginBottom: 20 }}>本局已结束</h2>
          <button className="tc-btn" onClick={onLeave}>返回大厅</button>
        </div>
      </div>
    );
  }

  /* ---------- 结算 ---------- */
  if (showResult && gameEnd) {
    const r = gameEnd.result;
    const mine = r.per_seat?.[0] ?? Object.values(r.per_seat)[0];
    const iWon = mine?.won;
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(5,10,18,.75)', backdropFilter: 'blur(4px)', position: 'relative', overflow: 'hidden',
      }}>
        {/* 金币雨 */}
        {iWon && Array.from({ length: 24 }).map((_, i) => (
          <div key={i} style={{
            position: 'absolute', left: `${(i * 41) % 100}%`, bottom: -30, fontSize: 26,
            animation: `coinFly ${2.2 + (i % 5) * 0.35}s ease-in ${(i % 8) * 0.18}s both`,
          }}>🪙</div>
        ))}
        {r.spring && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
            <div style={{ fontSize: 90, animation: 'springBloom 2s ease both' }}>🌸 春天 🌸</div>
          </div>
        )}
        <div className="tc-panel anim-popIn" style={{ width: 460, padding: 30, textAlign: 'center', zIndex: 2 }}>
          <div style={{
            fontSize: 40, fontWeight: 900, marginBottom: 6, letterSpacing: 4,
            background: iWon ? 'linear-gradient(180deg,#fff6c8,#ffd54a)' : 'linear-gradient(180deg,#e0e0e0,#9e9e9e)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            textShadow: iWon ? '0 4px 18px rgba(255,213,74,.35)' : 'none',
          }}>{iWon ? '胜利' : '失败'}</div>
          <div style={{ color: 'var(--ink-dim)', marginBottom: 18, fontSize: 14 }}>
            {r.winner_team === 'landlord' ? '地主阵营获胜' : '农民阵营获胜'}
            {' · '}💣×{r.bombs}{r.spring ? ' · 春天×2' : ''} · 倍数 {r.multiplier}
          </div>
          <div style={{ background: 'rgba(0,0,0,.3)', borderRadius: 10, padding: '6px 16px', marginBottom: 20 }}>
            {Object.values(r.per_seat).map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: i < 2 ? '1px solid rgba(255,255,255,.08)' : 'none', fontSize: 15 }}>
                <span>{s.nickname} <span style={{ fontSize: 12, color: 'var(--ink-dim)' }}>{s.team === 'landlord' ? '👑地主' : '🌾农民'}</span></span>
                <span className="anim-popIn" style={{ color: s.delta > 0 ? 'var(--gold)' : '#90a4ae', fontWeight: 800, animationDelay: `${0.3 + i * 0.25}s` }}>
                  {s.delta > 0 ? '+' : ''}{s.delta}
                </span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button className="tc-btn gold" onClick={() => setShowResult(false)}>再来一局</button>
            <button className="tc-btn secondary" onClick={handleLeave}>返回大厅</button>
          </div>
        </div>
      </div>
    );
  }

  /* ---------- 抢地主阶段 ---------- */
  if (priv!.status === 'bidding') {
    return (
      <div style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden' }} onClick={() => { unlockAudio(); startBgm(); }}>
        <div className="table-felt" />
        <div style={{ position: 'relative', zIndex: 2, textAlign: 'center', paddingTop: '12vh' }}>
          <h2 className="anim-fadeUp" style={{ fontSize: 34, letterSpacing: 8, color: 'var(--gold)', textShadow: '0 3px 10px rgba(0,0,0,.6)' }}>抢地主</h2>
          <div style={{ margin: '26px 0', display: 'flex', gap: 10, justifyContent: 'center' }}>
            {[0, 1, 2].map(i => (
              <CardBack key={i} w={44} style={{ animation: `dealCard .5s ${i * 0.15}s both` }} />
            ))}
          </div>
          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', marginBottom: 26 }}>
            {[0, 1, 2].map(s => (
              <div key={s} className="tc-panel" style={{
                padding: '12px 22px', display: 'flex', alignItems: 'center', gap: 10,
                borderColor: s === priv!.bidding_seat ? 'var(--gold)' : 'var(--panel-border)',
                boxShadow: s === priv!.bidding_seat ? '0 0 18px rgba(255,213,74,.35)' : undefined,
              }}>
                <Avatar nickname={room.seats[s]?.nickname || '?'} avatar={room.seats[s]?.avatar} size={40} ring={s === priv!.bidding_seat ? '#ffd54a' : undefined} />
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontWeight: 600 }}>{room.seats[s]?.nickname || '?'}</div>
                  <div style={{ fontSize: 12, color: 'var(--ink-dim)' }}>{priv!.bidders?.[s] ? '已叫牌' : s === priv!.bidding_seat ? '思考中…' : '等待'}</div>
                </div>
              </div>
            ))}
          </div>
          {priv!.can_bid ? (
            <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }} className="anim-fadeUp">
              <button className="tc-btn gold" style={{ fontSize: 18, padding: '14px 40px' }} onClick={() => onBid('landlord')}>叫地主</button>
              <button className="tc-btn secondary" style={{ fontSize: 18, padding: '14px 40px' }} onClick={() => onBid('pass')}>不叫</button>
            </div>
          ) : (
            <p style={{ color: 'var(--ink-dim)' }}>等待 {room.seats[priv!.bidding_seat ?? 0]?.nickname} 叫牌…</p>
          )}
        </div>
        {/* 抢地主阶段也展示自己的手牌 */}
        <div style={{ position: 'absolute', bottom: 20, left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 9 }}>
          <div style={{ display: 'flex' }}>
            {handLabels.map((l, i) => (
              <div key={`bid-${i}-${l}`} style={{ marginLeft: i ? -26 : 0, animation: dealing ? `dealCard .4s ${i * 0.045}s both` : undefined, zIndex: i, position: 'relative' }}>
                <Card label={l} w={60} src={cardImgFromInt(hand[i])} />
              </div>
            ))}
          </div>
        </div>
        <Danmaku comments={comments} />
      </div>
    );
  }

  /* ---------- 出牌阶段 ---------- */
  const canBeatAny = priv!.can_beat_any !== false;
  const multiplier = Math.pow(2, priv!.bomb_count || 0);
  const myTurn = priv!.turn === 0;

  return (
    <div key={shake} className={shake ? 'anim-shake' : ''} style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden' }}
      onClick={() => { unlockAudio(); startBgm(); }}>
      <div className="table-felt" />
      <Danmaku comments={comments} />

      {/* 炸弹/飞机全屏特效 */}
      {fx.type && (
        <div key={fx.key} style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none', zIndex: 50 }}>
          {fx.type === 'plane' ? (
            <div style={{ fontSize: 70, animation: 'planeFly 1.4s linear both' }}>✈️</div>
          ) : (
            <>
              <div style={{
                position: 'absolute', width: 320, height: 320, borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(255,180,60,.9), rgba(255,80,40,.5) 45%, transparent 70%)',
                animation: 'bombGlow 1.1s ease-out both',
              }} />
              <div style={{
                fontSize: 84, fontWeight: 900, letterSpacing: 6,
                background: 'linear-gradient(180deg,#fff3b0,#ff9800 55%,#f44336)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                filter: 'drop-shadow(0 6px 16px rgba(255,80,0,.6))',
                animation: 'bombFlash 1.3s ease both',
              }}>{fx.type === 'rocket' ? '🚀 王炸' : '💥 炸弹'}</div>
            </>
          )}
        </div>
      )}

      {/* 顶栏 */}
      <div style={{ position: 'relative', zIndex: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 18px' }}>
        <div className="tc-panel" style={{ padding: '6px 16px', fontSize: 13, color: 'var(--ink-dim)' }}>
          房间 #{room.code} · 底分 {room.base_bet}
        </div>
        {/* 底牌 */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--ink-dim)', marginBottom: 3 }}>底牌</div>
          <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
            {(priv!.bottom || []).map((l, i) => (
              <img key={i} src={cardImg(l, i)} style={{ width: 36, height: 50, borderRadius: 3, boxShadow: '0 2px 6px rgba(0,0,0,.5)', animation: `dealCard .5s ${i * .12}s both` }} />
            ))}
          </div>
        </div>
        <div className="tc-panel" style={{ padding: '6px 16px', fontSize: 13 }}>
          💣 {priv!.bomb_count} · <span key={priv!.bomb_count} style={{ display: 'inline-block', color: 'var(--gold)', fontWeight: 800, animation: 'multiplierPulse .5s ease' }}>倍数 ×{multiplier}</span>
          {' · '}{priv!.landlord_seat === 0 ? '👑 我是地主' : '🌾 我是农民'}
          {' '}<button onClick={onLeave} style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--ink-dim)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline' }}>退出</button>
        </div>
      </div>

      {/* 左右对手 */}
      <OppPanel seat={1} state={state} timer={timer} side="left" />
      <OppPanel seat={2} state={state} timer={timer} side="right" />

      {/* 对手出牌区 */}
      <div style={{ position: 'absolute', top: '44%', left: 150, right: 150, display: 'flex', justifyContent: 'space-between', zIndex: 4, pointerEvents: 'none' }}>
        {[1, 2].map(seat => (
          <div key={seat} style={{ minWidth: 120, display: 'flex', justifyContent: 'center' }}>
            {lastAction[seat]?.type === 'play' && <PlayedZone labels={lastAction[seat].labels} from={seat === 1 ? 'left' : 'right'} w={40} />}
            {lastAction[seat]?.type === 'pass' && priv!.turn !== seat && <PassBubble />}
          </div>
        ))}
      </div>

      {/* 我的出牌区 */}
      <div style={{ position: 'absolute', bottom: '31%', left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 4, pointerEvents: 'none' }}>
        {lastAction[0]?.type === 'play' && <PlayedZone labels={lastAction[0].labels} from="me" w={48} />}
        {lastAction[0]?.type === 'pass' && !myTurn && <PassBubble text="不出" />}
      </div>

      {/* 我自己 */}
      <div style={{ position: 'absolute', bottom: 14, left: 22, display: 'flex', alignItems: 'center', gap: 10, zIndex: 10 }}>
        <div style={{ position: 'relative' }}>
          <Avatar nickname={room.seats[0]?.nickname || '我'} avatar={room.seats[0]?.avatar} size={52} ring={myTurn ? (timer <= 10 ? '#ff5252' : '#ffd54a') : undefined} />
          {myTurn && <TimerRing seconds={timer} size={52} warn={timer <= 10} />}
          {priv!.landlord_seat === 0 && (
            <div className="anim-popIn" style={{ position: 'absolute', top: -10, left: -10, background: 'linear-gradient(180deg,#ffe082,#e8a900)', color: '#5a3a00', fontSize: 11, fontWeight: 800, padding: '2px 7px', borderRadius: 8 }}>地主</div>
          )}
        </div>
        <div className="tc-panel" style={{ padding: '4px 12px', fontSize: 13 }}>
          <div style={{ fontWeight: 600 }}>{room.seats[0]?.nickname}</div>
          <div style={{ fontSize: 12, color: myTurn && timer <= 10 ? '#ff5252' : 'var(--ink-dim)' }}>
            {myTurn ? `⏱ ${timer}s` : `剩余 ${priv!.remaining?.[0] ?? hand.length} 张`}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div style={{ position: 'absolute', bottom: 196, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 14, zIndex: 10, height: 46 }}>
        {priv!.can_act && canBeatAny && (
          <>
            <button className="tc-btn secondary" onClick={() => onHint('free')}>提示</button>
            <button className="tc-btn secondary" title="DouZero 职业提示，100 欢乐豆" onClick={() => onHint('paid')}>神算子·100豆</button>
            <button className="tc-btn gold" style={{ fontSize: 17, padding: '10px 40px' }} onClick={handlePlay} disabled={selected.size === 0}>出牌</button>
            <button className="tc-btn secondary" onClick={handlePass}>不出</button>
          </>
        )}
        {priv!.can_act && !canBeatAny && (
          <button className="tc-btn" onClick={handlePass}>不出（压不住）</button>
        )}
        {!priv!.can_act && priv!.turn !== null && priv!.status === 'playing' && (
          <div className="tc-panel" style={{ padding: '8px 20px', color: 'var(--ink-dim)', fontSize: 14, display: 'flex', alignItems: 'center' }}>
            等待 {room.seats[priv!.turn]?.nickname} 出牌…
          </div>
        )}
      </div>

      {/* 手牌（扇形叠加 + 发牌动画） */}
      <div style={{ position: 'absolute', bottom: 20, left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 9, paddingLeft: 120 }}>
        <div style={{ display: 'flex' }}>
          {handLabels.map((l, i) => {
            const isSel = selected.has(i);
            return (
              <div key={`${i}-${l}`} onClick={() => priv!.can_act && canBeatAny && toggle(i)} style={{
                marginLeft: i ? -26 : 0,
                transform: isSel ? 'translateY(-18px)' : 'none',
                transition: 'transform .13s ease, filter .2s',
                cursor: priv!.can_act && canBeatAny ? 'pointer' : 'default',
                filter: !priv!.can_act ? 'brightness(.65)' : 'none',
                animation: dealing ? `dealCard .4s ${i * 0.045}s both` : undefined,
                zIndex: isSel ? 10 : i,
                position: 'relative',
              }}
                onMouseEnter={e => { if (priv!.can_act && canBeatAny && !isSel) (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-8px)'; }}
                onMouseLeave={e => { if (!isSel) (e.currentTarget as HTMLDivElement).style.transform = 'none'; }}
              >
                <Card label={l} w={64} src={cardImgFromInt(hand[i])} style={{
                  border: isSel ? '2px solid var(--gold)' : '2px solid transparent',
                  boxShadow: isSel ? '0 6px 16px rgba(255,213,74,.4)' : '0 2px 6px rgba(0,0,0,.45)',
                }} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
