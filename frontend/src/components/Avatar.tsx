import React from 'react';

const PALETTE = ['#e94560', '#4ecca3', '#ffd54a', '#7c83fd', '#ff8c42', '#00b8a9', '#f6416c', '#a3d2ca'];

export function Avatar({ nickname, avatar, size = 48, ring }: {
  nickname: string;
  avatar?: string | null;
  size?: number;
  ring?: string; // 高亮圈颜色
}) {
  const ch = (nickname || '?').slice(0, 1);
  const bg = PALETTE[(nickname || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % PALETTE.length];
  const ringStyle: React.CSSProperties = ring
    ? { boxShadow: `0 0 0 3px ${ring}, 0 0 14px ${ring}`, animation: 'glowPulse 1.2s ease-in-out infinite' }
    : { boxShadow: '0 0 0 2px rgba(255,255,255,.15)' };
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', overflow: 'hidden', flexShrink: 0,
      background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.44, fontWeight: 700, color: '#fff', textShadow: '0 1px 2px rgba(0,0,0,.5)',
      transition: 'box-shadow .2s', ...ringStyle,
    }}>
      {avatar ? <img src={avatar} alt={nickname} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : ch}
    </div>
  );
}
