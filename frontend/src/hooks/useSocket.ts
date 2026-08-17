import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import type { RoomStateMessage, CommentEvent, GameEndEvent, ErrorEvent } from '../utils/types';

export function useSocket(token: string | null) {
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [roomState, setRoomState] = useState<RoomStateMessage | null>(null);
  const [comments, setComments] = useState<CommentEvent[]>([]);
  const [gameEnd, setGameEnd] = useState<GameEndEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [okAction, setOkAction] = useState<{ action: string } | null>(null);
  const [timedOut, setTimedOut] = useState<{ seat: number } | null>(null);

  const emit = useCallback(
    (event: string, data?: unknown) => {
      if (socketRef.current) socketRef.current.emit(event, data);
    },
    [],
  );

  useEffect(() => {
    if (!token) return;
    const s = io('/', { auth: { token }, transports: ['websocket', 'polling'] });
    socketRef.current = s;
    s.on('connect', () => setConnected(true));
    s.on('disconnect', () => setConnected(false));
    s.on('room_state', (d: RoomStateMessage) => setRoomState(d));
    s.on('comment', (d: CommentEvent) => setComments(p => [...p, d]));
    s.on('game_end', (d: GameEndEvent) => setGameEnd(d));
    s.on('error', (d: ErrorEvent) => setError(d.msg));
    s.on('ok', (d: { action: string }) => setOkAction(d));
    s.on('timed_out', (d: { seat: number }) => setTimedOut(d));
    s.on('redirect', (d: { to: string }) => { /* handled by App */ });
    return () => { s.disconnect(); socketRef.current = null; };
  }, [token]);

  const clearGameEnd = useCallback(() => setGameEnd(null), []);
  return { connected, roomState, comments, gameEnd, error, okAction, timedOut, emit, setError, setGameEnd, setComments, clearGameEnd };
}