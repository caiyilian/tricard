// Server message types matching backend

export interface SeatInfo {
  nickname: string;
  username: string;
  avatar: string | null;
  is_ai: boolean;
  ai_type: string | null;
  personality: string | null;
  ready: boolean;
  connected: boolean;
}

export interface RoomSnapshot {
  code: string;
  host_seat: number;
  base_bet: number;
  status: 'waiting' | 'playing' | 'finished';
  seats: (SeatInfo | null)[];
  players: number;
  those_ready: string[];
}

export interface PrivateSnapshot {
  turn: number | null;
  last_play: number[];
  last_play_labels: string[];
  last_play_by: number | null;
  trick: number;
  bomb_count: number;
  hand: number[];
  hand_labels: string[];
  remaining: number[];
  landlord_seat: number | null;
  bottom: string[];
  can_act: boolean;
}

export interface RoomStateMessage {
  room: RoomSnapshot;
  private: PrivateSnapshot | null;
}

export interface UserInfo {
  id: number;
  username: string;
  nickname: string;
  avatar: string | null;
  is_ai: boolean;
  joy_beans: number;
  wins: number;
  losses: number;
  games: number;
  win_rate: number | null;
}

export interface AuthResponse {
  token: string;
  user: UserInfo;
}

export interface SettlementResult {
  winner_team: string;
  winner_seat: number;
  bombs: number;
  spring: boolean;
  multiplier: number;
  per_seat: Record<number, { nickname: string; delta: number; won: boolean; team: string }>;
}

export interface RankingItem extends UserInfo {}

export interface RankingResponse {
  by: string;
  items: RankingItem[];
}

export interface RoomListItem {
  code: string;
  host_seat: number;
  base_bet: number;
  status: string;
  players: number;
}

export interface RoomsListResponse {
  rooms: RoomListItem[];
}

export interface CommentEvent {
  type: 'comment';
  seat: number;
  speaker: string;
  personality: string;
  text: string;
  archetype: string;
}

export interface GameEndEvent {
  result: SettlementResult;
}

export interface ErrorEvent {
  msg: string;
}