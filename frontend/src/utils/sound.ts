// 简单音效管理：浏览器自动播放限制下，首次用户交互后解锁
const cache: Record<string, HTMLAudioElement> = {};
let unlocked = false;

export function unlockAudio() {
  if (unlocked) return;
  unlocked = true;
  // 触发一次播放授权
  const a = new Audio('/sounds/bg_room.mp3');
  a.volume = 0;
  a.play().then(() => { a.pause(); a.volume = 1; }).catch(() => {});
}

export function playSound(name: 'deal' | 'end_win' | 'end_lose', volume = 0.7) {
  try {
    if (!cache[name]) cache[name] = new Audio(`/sounds/${name}.mp3`);
    const a = cache[name];
    a.currentTime = 0;
    a.volume = volume;
    a.play().catch(() => {});
  } catch { /* ignore */ }
}

let bgm: HTMLAudioElement | null = null;
export function startBgm(volume = 0.25) {
  if (bgm) return;
  bgm = new Audio('/sounds/bg_room.mp3');
  bgm.loop = true;
  bgm.volume = volume;
  bgm.play().catch(() => { bgm = null; });
}
export function stopBgm() {
  if (bgm) { bgm.pause(); bgm = null; }
}
