import React from 'react';

const STR_RANKS = ['3','4','5','6','7','8','9','10','J','Q','K','A','2','BJ','CJ'];
const SUITS = ['S', 'H', 'D', 'C']; // 用于给无花色标签补确定性花色

/** 从后端 card int 解码图片路径（bit4-7 花色：1♠ 2♥ 4♦ 8♣，低4位点数） */
export function cardImgFromInt(c: number): string {
  const rank = c & 0xF;
  const suitBits = (c >> 4) & 0xF;
  const r = STR_RANKS[rank] || '3';
  if (r === 'BJ') return '/cards/Poker_Joker_B.png';
  if (r === 'CJ') return '/cards/Poker_Joker_R.png';
  const s = suitBits === 2 ? 'H' : suitBits === 4 ? 'D' : suitBits === 8 ? 'C' : 'S';
  return `/cards/Poker_${s}${r}.png`;
}

/** 从 rank-only 标签取图片路径；idx 用于确定性分配花色，避免全黑桃 */
export function cardImg(label: string, idx = 0): string {
  if (label === 'BJ') return '/cards/Poker_Joker_B.png';
  if (label === 'CJ') return '/cards/Poker_Joker_R.png';
  const s = SUITS[(label.charCodeAt(0) + label.length + idx) % 4];
  return `/cards/Poker_${s}${label}.png`;
}

interface CardProps {
  label: string;
  w?: number;
  style?: React.CSSProperties;
  onClick?: () => void;
  dim?: boolean;
  idx?: number;       // 无花色时的确定性花色种子
  src?: string;       // 直接指定图片（优先）
}

export const CARD_RATIO = 72 / 52; // h / w

export function Card({ label, w = 52, style, onClick, dim, idx = 0, src }: CardProps) {
  const h = Math.round(w * CARD_RATIO);
  return (
    <img
      src={src || cardImg(label, idx)}
      alt={label}
      draggable={false}
      onClick={onClick}
      style={{
        width: w, height: h, borderRadius: Math.max(3, w / 13),
        boxShadow: '0 2px 6px rgba(0,0,0,.45)',
        filter: dim ? 'brightness(.55)' : undefined,
        userSelect: 'none',
        ...style,
      }}
    />
  );
}

export function CardBack({ w = 40, style }: { w?: number; style?: React.CSSProperties }) {
  const h = Math.round(w * CARD_RATIO);
  return (
    <img
      src="/cards/pokerback.png"
      alt="back"
      draggable={false}
      style={{ width: w, height: h, borderRadius: Math.max(3, w / 13), boxShadow: '0 2px 6px rgba(0,0,0,.45)', userSelect: 'none', ...style }}
    />
  );
}
