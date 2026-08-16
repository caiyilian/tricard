import { useState, useCallback } from 'react';
import { useSocket } from './hooks/useSocket';
import LoginPage from './pages/LoginPage';
import LobbyPage from './pages/LobbyPage';
import RoomPage from './pages/RoomPage';
import GamePage from './pages/GamePage';

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [page, setPage] = useState<'lobby' | 'room' | 'game'>('lobby');
  const [myCode, setMyCode] = useState<string | null>(null);

  const s = useSocket(token);

  const handleLogin = useCallback((t: string) => {
    setToken(t);
    setPage('lobby');
  }, []);

  const handleCreate = useCallback(() => {
    s.emit('create_room', { base_bet: 200, ai_type: 'basic' });
    setPage('room');
  }, [s]);

  const handleJoin = useCallback((code: string) => {
    s.emit('join_room', { code });
    setMyCode(code);
    setPage('room');
  }, [s]);

  const handleLeave = useCallback(() => {
    s.emit('leave_room');
    setPage('lobby');
  }, [s]);

  const handleReady = useCallback(() => {
    s.emit('set_ready', { ready: true });
  }, [s]);

  const handleStart = useCallback(() => {
    s.emit('start', {});
  }, [s]);

  const handlePlay = useCallback((cards: number[]) => {
    s.emit('play', { hand: cards });
  }, [s]);

  const handlePass = useCallback(() => {
    s.emit('pass', {});
  }, [s]);

  const handleBid = useCallback((action: string) => {
    s.emit('bid', { action });
  }, [s]);

  // 当 room_state 的 status 变为 playing → 进入游戏页；gameEnd 时留在游戏页显示结算
  const roomStatus = s.roomState?.room?.status;
  const gameStatus = s.roomState?.private?.status;
  const hasGameEnd = s.gameEnd !== null;
  const nextPage = (roomStatus === 'playing' || gameStatus === 'bidding' || hasGameEnd) ? 'game' : (roomStatus === 'waiting' ? 'room' : 'lobby');

  return (
    <div style={{ background: '#0f3460', minHeight: '100vh', overflow: 'auto' }}>
      {!token ? (
        <LoginPage onLogin={handleLogin} />
      ) : nextPage === 'lobby' ? (
        <LobbyPage onJoin={handleJoin} onCreate={handleCreate} />
      ) : nextPage === 'room' ? (
        s.roomState ? (
          <RoomPage state={s.roomState} onReady={handleReady} onStart={handleStart} onLeave={handleLeave} />
        ) : (
          <div style={{ color: '#eee', textAlign: 'center', padding: 40 }}>加入房间中...</div>
        )
      ) : (
        <GamePage state={s.roomState!} gameEnd={s.gameEnd} onPlay={handlePlay} onPass={handlePass} onBid={handleBid} onLeave={handleLeave} />
      )}
    </div>
  );
}