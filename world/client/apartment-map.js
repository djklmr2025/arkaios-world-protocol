/*
 * ARKAIOS · Departamento de Cancún en pixel art (mapa vivo de la novela).
 * The story AI says where each character is ("ubicacion"); they walk there and the camera zooms
 * into that room. All art is drawn procedurally (no external images) at 8 px per tile.
 *
 * API: ApartmentMap.mount(el) · ApartmentMap.update(sceneData, playerText) · ApartmentMap.restore(loc)
 *      window.APARTMENT_PROMPT (appended to the story system prompt)
 */
(function () {
  const T = 8;               // logical pixels per tile
  const COLS = 28, ROWS = 20;
  const WALK_TILES_PER_SEC = 4.5;

  // Rooms: tile rects (inclusive). spots = where each character stands/sits by default.
  const ROOMS = {
    recamara:      { name: 'Recámara',            x: 1,  y: 1,  w: 8,  h: 6, floor: 'wood',     spots: { yukiho: [3, 4], jugador: [6, 5] } },
    bano_recamara: { name: 'Baño de la recámara', x: 10, y: 1,  w: 4,  h: 6, floor: 'tile',     spots: { yukiho: [11, 4], jugador: [12, 5] } },
    bano_tina:     { name: 'Baño con tina',       x: 15, y: 1,  w: 5,  h: 6, floor: 'tileBlue', spots: { yukiho: [16, 5], jugador: [18, 5] } },
    azotehuela:    { name: 'Azotehuela',          x: 21, y: 1,  w: 6,  h: 6, floor: 'concrete', spots: { yukiho: [23, 4], jugador: [25, 5] } },
    sala:          { name: 'Sala-comedor',        x: 1,  y: 8,  w: 19, h: 6, floor: 'woodDark', spots: { yukiho: [5, 9], jugador: [7, 9] } },
    cocina:        { name: 'Cocina',              x: 21, y: 8,  w: 6,  h: 6, floor: 'tileCream', spots: { yukiho: [23, 11], jugador: [25, 11] } },
    terraza:       { name: 'Terraza',             x: 1,  y: 15, w: 26, h: 4, floor: 'stone',    spots: { yukiho: [8, 16], jugador: [10, 16] } },
  };
  // Door tiles that open the wall grid between rooms.
  const DOORS = [[9, 3], [4, 7], [17, 7], [23, 7], [20, 10], [6, 14], [7, 14], [8, 14]];

  const PAL = {
    wall: '#2b2238', wallTop: '#4a3b5e', door: '#8a5a3b', glass: '#7fb2c9',
    wood: ['#9b6a43', '#8d5f3b'], woodDark: ['#6e4a33', '#64432e'], tile: ['#d9e3ea', '#c3d0d9'],
    tileBlue: ['#a9c9dc', '#94b8cf'], tileCream: ['#e8dcc2', '#dccdae'], concrete: ['#8b8f96', '#7f838a'],
    stone: ['#5f6a72', '#566069'], outline: '#1a1424',
  };

  window.APARTMENT_PROMPT = `
[ESCENARIO FÍSICO DEL DEPARTAMENTO (mapa en pixel art visible para el jugador)]:
Espacios: recamara (cama, buró, clóset; tiene su propio baño completo), bano_recamara (regadera, WC, lavabo),
bano_tina (tina, regadera y WC), sala (sofá, mesa de centro, comedor; aquí empezó la historia con el té),
cocina (estufa, refrigerador, tetera), terraza (frontal, con plantas y la lluvia), azotehuela (lavadora y lavadero).
Agrega SIEMPRE al JSON el campo "ubicacion": {"yukiho": "<espacio>", "jugador": "<espacio>"} ("jugador" es el personaje del humano) usando exactamente esos nombres.
Solo cambia de espacio cuando la historia lo justifique y narra el traslado. Por defecto ambos están en "sala".`;

  const KEYWORDS = [
    ['bano_recamara', /baño de (la|tu|su) rec[aá]mara|baño privado|baño de la habitaci/i],
    ['bano_tina', /\btina\b|bañera|regadera|ducha|\bbaño\b/i],
    ['recamara', /rec[aá]mara|habitaci[oó]n|dormitorio|\bcama\b|dormir|acostar/i],
    ['azotehuela', /azotehuela|lavadora|lavadero|tender la ropa|ropa mojada/i],
    ['cocina', /cocina|estufa|refrigerador|cocinar|preparar (la )?cena|tetera/i],
    ['terraza', /terraza|balc[oó]n|barandal/i],
    ['sala', /\bsala\b|sof[aá]|sill[oó]n|comedor/i],
  ];

  // ---------- grid ----------
  const grid = [];          // 'wall' | room id
  const blocked = new Set(); // furniture tiles "x,y"
  function buildGrid() {
    for (let y = 0; y < ROWS; y++) { grid[y] = []; for (let x = 0; x < COLS; x++) grid[y][x] = 'wall'; }
    for (const [id, r] of Object.entries(ROOMS)) for (let y = r.y; y < r.y + r.h; y++) for (let x = r.x; x < r.x + r.w; x++) grid[y][x] = id;
    for (const [x, y] of DOORS) grid[y][x] = 'door';
  }

  // ---------- furniture (tile coords; each fn draws in logical px) ----------
  const FURNITURE = [];
  function put(x, y, w, h, draw, solid = true) {
    FURNITURE.push({ x, y, w, h, draw });
    if (solid) for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) blocked.add(`${i},${j}`);
  }
  function box(c, px, py, w, h, fill, edge = PAL.outline) { c.fillStyle = edge; c.fillRect(px, py, w, h); c.fillStyle = fill; c.fillRect(px + 1, py + 1, w - 2, h - 2); }

  function furnish() {
    // Recámara
    put(1, 1, 2, 3, (c, x, y) => { box(c, x, y, 16, 24, '#5b3b6e'); box(c, x + 2, y + 2, 12, 5, '#f1ece4'); c.fillStyle = '#7b54a0'; c.fillRect(x + 1, y + 9, 14, 14); c.fillStyle = '#9a74c0'; c.fillRect(x + 1, y + 9, 14, 2); });
    put(3, 1, 1, 1, (c, x, y) => { box(c, x, y + 2, 8, 6, '#7a5232'); c.fillStyle = '#ffd98a'; c.fillRect(x + 3, y, 3, 3); });
    put(7, 1, 2, 1, (c, x, y) => { box(c, x, y, 16, 8, '#6b4a30'); c.fillStyle = '#3a2618'; c.fillRect(x + 7, y + 2, 1, 5); });
    put(6, 5, 2, 1, (c, x, y) => { c.fillStyle = '#c7a6d8'; c.fillRect(x, y + 1, 16, 6); }, false);
    // Baño recámara (completo)
    put(10, 1, 2, 2, (c, x, y) => { box(c, x, y, 16, 16, '#cfe6f2'); c.fillStyle = 'rgba(160,210,235,.6)'; c.fillRect(x + 2, y + 2, 12, 12); c.fillStyle = '#9aa'; c.fillRect(x + 7, y + 2, 2, 2); });
    put(13, 1, 1, 1, (c, x, y) => { box(c, x + 1, y, 6, 4, '#f4f4f4'); box(c, x + 1, y + 3, 6, 5, '#ffffff'); });
    put(13, 3, 1, 1, (c, x, y) => { box(c, x, y + 1, 8, 6, '#ffffff'); c.fillStyle = '#9bc'; c.fillRect(x + 2, y + 3, 4, 2); });
    // Baño con tina
    put(15, 1, 3, 2, (c, x, y) => { box(c, x, y, 24, 14, '#ffffff'); c.fillStyle = '#8ec8e8'; c.fillRect(x + 2, y + 2, 20, 9); c.fillStyle = '#c8e8f8'; c.fillRect(x + 3, y + 3, 6, 2); });
    put(19, 1, 1, 1, (c, x, y) => { box(c, x + 1, y, 6, 4, '#f4f4f4'); box(c, x + 1, y + 3, 6, 5, '#ffffff'); });
    put(19, 3, 1, 1, (c, x, y) => { box(c, x, y + 1, 8, 6, '#ffffff'); c.fillStyle = '#9bc'; c.fillRect(x + 2, y + 3, 4, 2); });
    put(15, 3, 1, 1, (c, x, y) => { c.fillStyle = '#b0b8c0'; c.fillRect(x + 3, y, 2, 6); c.fillRect(x + 1, y, 6, 2); }, false);
    // Azotehuela
    put(21, 1, 1, 2, (c, x, y) => { box(c, x, y, 8, 15, '#eef2f4'); c.fillStyle = '#3c4a55'; c.fillRect(x + 2, y + 5, 4, 4); c.fillStyle = '#8fb5cc'; c.fillRect(x + 3, y + 6, 2, 2); });
    put(23, 1, 2, 1, (c, x, y) => { box(c, x, y, 16, 8, '#b9c1c6'); c.fillStyle = '#7d98aa'; c.fillRect(x + 2, y + 2, 12, 4); });
    put(22, 4, 5, 1, (c, x, y) => { c.fillStyle = '#ddd'; c.fillRect(x, y + 1, 40, 1); const cl = ['#e86f6f', '#f2c14e', '#6fb3e8']; cl.forEach((k, i) => { c.fillStyle = k; c.fillRect(x + 4 + i * 12, y + 2, 6, 5); }); }, false);
    // Sala-comedor
    put(2, 12, 4, 1, (c, x, y) => { box(c, x, y - 2, 32, 10, '#3f6d73'); c.fillStyle = '#5a9098'; c.fillRect(x + 2, y, 28, 3); }, true);
    put(3, 10, 2, 1, (c, x, y) => { box(c, x, y + 1, 16, 6, '#7a5232'); c.fillStyle = '#f5f0e6'; c.fillRect(x + 6, y + 2, 3, 3); }, true);
    put(2, 9, 5, 2, (c, x, y) => { c.fillStyle = '#8a3f4f'; c.fillRect(x, y + 2, 40, 12); c.fillStyle = '#a5566a'; c.fillRect(x + 2, y + 4, 36, 8); }, false);
    put(1, 8, 1, 1, (c, x, y) => { c.fillStyle = '#2f6b3a'; c.fillRect(x + 1, y, 6, 5); c.fillStyle = '#8a5a3b'; c.fillRect(x + 2, y + 5, 4, 3); });
    put(8, 8, 3, 1, (c, x, y) => { box(c, x, y, 24, 7, '#222'); c.fillStyle = '#3b5f8a'; c.fillRect(x + 2, y + 1, 20, 4); });
    put(13, 10, 3, 2, (c, x, y) => { box(c, x + 2, y + 2, 20, 12, '#8d6440'); }, true);
    put(12, 10, 1, 2, (c, x, y) => { box(c, x + 2, y + 4, 5, 6, '#5a3d28'); }, false);
    put(16, 10, 1, 2, (c, x, y) => { box(c, x + 1, y + 4, 5, 6, '#5a3d28'); }, false);
    put(19, 8, 1, 1, (c, x, y) => { c.fillStyle = '#ffd98a'; c.fillRect(x + 3, y, 3, 3); c.fillStyle = '#555'; c.fillRect(x + 4, y + 3, 1, 5); });
    // Cocina
    put(21, 8, 6, 1, (c, x, y) => { box(c, x, y, 48, 8, '#c9b48e'); c.fillStyle = '#333'; [10, 18].forEach(o => c.fillRect(x + o, y + 2, 4, 4)); c.fillStyle = '#9bc'; c.fillRect(x + 30, y + 2, 8, 4); });
    put(26, 9, 1, 2, (c, x, y) => { box(c, x, y, 8, 16, '#e9eef0'); c.fillStyle = '#aab'; c.fillRect(x + 6, y + 3, 1, 4); c.fillRect(x + 6, y + 10, 1, 4); });
    put(22, 8, 1, 1, (c, x, y) => { c.fillStyle = '#b5402f'; c.fillRect(x + 2, y + 1, 4, 3); c.fillStyle = '#ddd'; c.fillRect(x + 3, y - 1, 2, 1); }, false);
    // Terraza
    put(1, 18, 26, 1, (c, x, y) => { c.fillStyle = '#c9ccd1'; c.fillRect(x, y + 2, 208, 1); for (let i = 0; i < 208; i += 4) c.fillRect(x + i, y + 2, 1, 5); }, true);
    [2, 13, 24].forEach(px => put(px, 15, 1, 1, (c, x, y) => { c.fillStyle = '#2f7a3f'; c.fillRect(x + 1, y, 6, 5); c.fillStyle = '#e46a8a'; c.fillRect(x + 3, y + 1, 2, 2); c.fillStyle = '#9a5b36'; c.fillRect(x + 2, y + 5, 4, 3); }));
    put(17, 16, 1, 1, (c, x, y) => { box(c, x + 1, y + 2, 6, 5, '#d9d4c5'); });
    put(19, 16, 1, 1, (c, x, y) => { box(c, x + 1, y + 2, 6, 5, '#d9d4c5'); });
  }

  // ---------- characters ----------
  const CHARS = {
    yukiho: { name: 'Yukiho', hair: '#14101a', skin: '#f2d5c2', shirt: '#f4f1ea', legs: '#4a5a7a', eye: '#3fbf7f', longHair: true },
    jugador: { name: 'Jugador', hair: '#3a2416', skin: '#c99a74', shirt: '#2f4a7a', legs: '#2b2b33', eye: '#3a2a1a', longHair: false },
  };
  const actors = {};
  function placeActor(id, room) {
    const [x, y] = freeSpot(ROOMS[room].spots[id], id);
    actors[id] = { id, room, x: x * T, y: y * T, path: [], frame: 0 };
  }
  function freeSpot([sx, sy]) { return blocked.has(`${sx},${sy}`) ? [sx, sy + 1] : [sx, sy]; }

  function drawActor(c, a, time) {
    const s = CHARS[a.id];
    const moving = a.path.length > 0;
    const bob = moving ? (Math.floor(time / 120) % 2) : (Math.floor(time / 600) % 2 === 0 ? 0 : 0);
    const x = Math.round(a.x), y = Math.round(a.y) - 5 - bob;
    c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(x + 1, Math.round(a.y) + 6, 6, 2);
    c.fillStyle = s.legs; c.fillRect(x + 2, y + 9, 1, 3); c.fillRect(x + 5, y + 9, 1, 3);
    if (moving && Math.floor(time / 120) % 2) { c.fillRect(x + 2, y + 11, 2, 1); } else { c.fillRect(x + 5, y + 11, 2, 1); }
    c.fillStyle = s.shirt; c.fillRect(x + 1, y + 5, 6, 5);
    c.fillStyle = s.skin; c.fillRect(x + 2, y + 1, 4, 4); c.fillRect(x, y + 6, 1, 3); c.fillRect(x + 7, y + 6, 1, 3);
    c.fillStyle = s.hair; c.fillRect(x + 1, y, 6, 2); c.fillRect(x + 1, y + 1, 1, 2); c.fillRect(x + 6, y + 1, 1, 2);
    if (s.longHair) { c.fillRect(x + 1, y + 2, 1, 6); c.fillRect(x + 6, y + 2, 1, 6); }
    c.fillStyle = s.eye; c.fillRect(x + 3, y + 3, 1, 1); c.fillRect(x + 5, y + 3, 1, 1);
  }

  // BFS over walkable tiles (rooms + doors, not furniture) -> list of tile centers
  function findPath(fx, fy, tx, ty) {
    const key = (x, y) => `${x},${y}`;
    const ok = (x, y) => x >= 0 && y >= 0 && x < COLS && y < ROWS && grid[y][x] !== 'wall' && (!blocked.has(key(x, y)) || (x === tx && y === ty));
    const prev = new Map([[key(fx, fy), null]]);
    const q = [[fx, fy]];
    while (q.length) {
      const [x, y] = q.shift();
      if (x === tx && y === ty) break;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (ok(nx, ny) && !prev.has(key(nx, ny))) { prev.set(key(nx, ny), [x, y]); q.push([nx, ny]); }
      }
    }
    if (!prev.has(key(tx, ty))) return [[tx, ty]];
    const path = [];
    for (let p = [tx, ty]; p; p = prev.get(key(p[0], p[1]))) path.unshift(p);
    return path.slice(1);
  }

  function moveActor(id, room) {
    const a = actors[id];
    if (!a || !ROOMS[room] || a.room === room) return;
    const [tx, ty] = freeSpot(ROOMS[room].spots[id]);
    a.path = findPath(Math.round(a.x / T), Math.round(a.y / T), tx, ty);
    a.room = room;
  }

  // ---------- render ----------
  let world, wctx, view, vctx, label, toggleBtn, focusRoom = 'sala', showAll = false;
  const cam = { x: 0, y: 0, w: COLS * T, h: ROWS * T };
  const drops = Array.from({ length: 90 }, () => ({ x: Math.random() * COLS * T, y: Math.random() * ROWS * T, s: 60 + Math.random() * 60 }));

  function drawFloor(c) {
    for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) {
      const cell = grid[y][x];
      if (cell === 'wall') {
        c.fillStyle = PAL.wall; c.fillRect(x * T, y * T, T, T);
        c.fillStyle = PAL.wallTop; c.fillRect(x * T, y * T, T, 2);
        continue;
      }
      const roomId = cell === 'door' ? nearestRoom(x, y) : cell;
      const tones = PAL[ROOMS[roomId].floor];
      c.fillStyle = tones[(x + y) % 2]; c.fillRect(x * T, y * T, T, T);
      if (cell === 'door') { c.fillStyle = y === 14 ? PAL.glass : PAL.door; c.fillRect(x * T + (y === 14 ? 0 : 1), y * T + (y === 14 ? 3 : 1), y === 14 ? T : T - 2, y === 14 ? 2 : T - 2); }
    }
    // windows on the outer top wall and glass wall to the terrace
    [[4, 0], [5, 0], [11, 0], [17, 0], [24, 0]].forEach(([x, y]) => { c.fillStyle = PAL.glass; c.fillRect(x * T + 1, y * T + 2, T - 2, 4); });
    for (let x = 1; x < 20; x++) if (grid[14][x] === 'wall') { c.fillStyle = 'rgba(127,178,201,.55)'; c.fillRect(x * T, 14 * T + 3, T, 2); }
  }
  function nearestRoom(x, y) {
    for (const [dx, dy] of [[0, 1], [1, 0], [0, -1], [-1, 0]]) { const g = grid[y + dy]?.[x + dx]; if (g && ROOMS[g]) return g; }
    return 'sala';
  }

  function drawRain(c, dt) {
    c.strokeStyle = 'rgba(170,200,255,.55)';
    for (const d of drops) {
      d.y += d.s * dt; d.x -= d.s * dt * 0.15;
      if (d.y > ROWS * T) { d.y = 15 * T - 4; d.x = Math.random() * COLS * T; }
      const ty = Math.floor(d.y / T), tx = Math.floor(d.x / T);
      if (ty >= 15 && grid[ty]?.[tx] && grid[ty][tx] !== 'wall') { c.fillStyle = 'rgba(170,200,255,.6)'; c.fillRect(Math.round(d.x), Math.round(d.y), 1, 3); }
    }
  }

  function drawNight(c, time) {
    c.fillStyle = 'rgba(10,8,30,.28)'; c.fillRect(0, 0, COLS * T, ROWS * T);
    const flicker = 0.85 + Math.sin(time / 400) * 0.05;
    [[3.5, 1.2, 26], [19.5, 8.2, 30], [12, 3, 18]].forEach(([x, y, r]) => {
      const g = c.createRadialGradient(x * T, y * T, 1, x * T, y * T, r);
      g.addColorStop(0, `rgba(255,214,140,${0.28 * flicker})`); g.addColorStop(1, 'rgba(255,214,140,0)');
      c.fillStyle = g; c.fillRect(x * T - r, y * T - r, r * 2, r * 2);
    });
    if (Math.random() < 0.002) { c.fillStyle = 'rgba(220,230,255,.35)'; c.fillRect(0, 15 * T, COLS * T, 5 * T); } // lightning
  }

  function targetCamera() {
    if (showAll) return { x: 0, y: 0, w: COLS * T, h: ROWS * T };
    const rooms = new Set([actors.yukiho?.room, actors.jugador?.room, focusRoom].filter(Boolean));
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const id of rooms) { const r = ROOMS[id]; x0 = Math.min(x0, r.x); y0 = Math.min(y0, r.y); x1 = Math.max(x1, r.x + r.w); y1 = Math.max(y1, r.y + r.h); }
    let x = (x0 - 1) * T, y = (y0 - 1) * T, w = (x1 - x0 + 2) * T, h = (y1 - y0 + 2) * T;
    const aspect = (COLS * T) / (ROWS * T);
    if (w / h < aspect) { const nw = h * aspect; x -= (nw - w) / 2; w = nw; } else { const nh = w / aspect; y -= (nh - h) / 2; h = nh; }
    w = Math.min(w, COLS * T); h = Math.min(h, ROWS * T);
    x = Math.max(0, Math.min(x, COLS * T - w)); y = Math.max(0, Math.min(y, ROWS * T - h));
    return { x, y, w, h };
  }

  let last = 0;
  function frame(time) {
    const dt = Math.min(0.05, (time - last) / 1000 || 0); last = time;
    for (const a of Object.values(actors)) {
      if (!a.path.length) continue;
      const [tx, ty] = a.path[0];
      const step = WALK_TILES_PER_SEC * T * dt;
      const dx = tx * T - a.x, dy = ty * T - a.y, dist = Math.hypot(dx, dy);
      if (dist <= step) { a.x = tx * T; a.y = ty * T; a.path.shift(); } else { a.x += dx / dist * step; a.y += dy / dist * step; }
    }
    wctx.clearRect(0, 0, COLS * T, ROWS * T);
    drawFloor(wctx);
    for (const f of FURNITURE) f.draw(wctx, f.x * T, f.y * T, time);
    Object.values(actors).sort((a, b) => a.y - b.y).forEach(a => drawActor(wctx, a, time));
    drawRain(wctx, dt);
    drawNight(wctx, time);

    const t = targetCamera(), k = 1 - Math.pow(0.0005, dt);
    for (const p of ['x', 'y', 'w', 'h']) cam[p] += (t[p] - cam[p]) * k;
    vctx.imageSmoothingEnabled = false;
    vctx.fillStyle = '#0d0a16'; vctx.fillRect(0, 0, view.width, view.height);
    vctx.drawImage(world, cam.x, cam.y, cam.w, cam.h, 0, 0, view.width, view.height);
    requestAnimationFrame(frame);
  }

  function updateLabel() {
    const y = actors.yukiho?.room, s = actors.jugador?.room;
    const where = y === s ? `Yukiho y ${playerName()} · ${ROOMS[y].name}` : `Yukiho · ${ROOMS[y].name}  |  ${playerName()} · ${ROOMS[s].name}`;
    label.textContent = showAll ? 'Departamento completo' : where;
  }
  function playerName() { try { return (typeof getProtagonistName === 'function' && getProtagonistName()) || 'Jugador'; } catch (e) { return 'Jugador'; } }

  function mount(el) {
    if (!el || view) return;
    buildGrid(); furnish();
    world = document.createElement('canvas'); world.width = COLS * T; world.height = ROWS * T; wctx = world.getContext('2d');
    el.innerHTML = `<div class="apt-head"><span class="apt-title">🏠 Departamento · Cancún</span>
      <button type="button" class="apt-toggle">🗺️ Ver todo</button></div>
      <canvas class="apt-view" width="448" height="320" aria-label="Mapa en pixel art del departamento"></canvas>
      <div class="apt-label" aria-live="polite"></div>`;
    view = el.querySelector('.apt-view'); vctx = view.getContext('2d');
    label = el.querySelector('.apt-label'); toggleBtn = el.querySelector('.apt-toggle');
    toggleBtn.onclick = () => { showAll = !showAll; toggleBtn.textContent = showAll ? '🔍 Acercar' : '🗺️ Ver todo'; updateLabel(); };
    placeActor('yukiho', 'sala'); placeActor('jugador', 'sala');
    updateLabel();
    requestAnimationFrame(frame);
  }

  function detect(text) {
    for (const [room, re] of KEYWORDS) if (re.test(text)) return room;
    return null;
  }
  function normalize(v) {
    if (!v) return null;
    const k = String(v).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '_');
    if (ROOMS[k]) return k;
    if (k.includes('tina')) return 'bano_tina';
    if (k.includes('bano')) return k.includes('recamara') ? 'bano_recamara' : 'bano_tina';
    return detect(k.replace(/_/g, ' '));
  }

  // Called after every story turn. Prefers the AI's "ubicacion"; falls back to keywords in the narration.
  function update(data, playerText) {
    if (!view) return null;
    const u = data && (data.ubicacion || data.location) || {};
    let y = normalize(u.yukiho), s = normalize(u.jugador || u.player || u.saul || u.saúl);
    if (!y && !s) { const guess = detect(`${data?.narration || ''} ${playerText || ''}`); y = s = guess; }
    if (y) moveActor('yukiho', y);
    if (s) moveActor('jugador', s);
    focusRoom = actors.yukiho.room;
    updateLabel();
    return { yukiho: actors.yukiho.room, jugador: actors.jugador.room };
  }

  function restore(loc) {
    if (!view || !loc) return;
    const saved = { yukiho: loc.yukiho, jugador: loc.jugador || loc.saul };  // older saves used "saul"
    for (const id of ['yukiho', 'jugador']) if (ROOMS[saved[id]]) placeActor(id, saved[id]);
    focusRoom = actors.yukiho.room;
    updateLabel();
  }

  // Field-by-field recovery of the story JSON when the model's output is malformed.
  function salvageJson(raw) {
    const text = String(raw || '');
    const str = (key) => {
      const m = text.match(new RegExp(`"?${key}"?\\s*:?\\s*"((?:[^"\\\\]|\\\\.)*)"`));
      if (!m) return null;
      try { return JSON.parse(`"${m[1]}"`); } catch (e) { return m[1]; }
    };
    const narration = str('narration');
    const dialogue = str('dialogue');
    if (!narration || !dialogue) return null;
    const bond = text.match(/"?bond_change"?\s*:?\s*(-?\d+)/);
    const opts = text.match(/"?options"?\s*:?\s*\[([\s\S]*?)\]/);
    const options = opts ? [...opts[1].matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => m[1]).slice(0, 3) : [];
    const ubic = text.match(/"?ubicacion"?\s*:?\s*\{([^}]*)\}/);
    const loc = {};
    if (ubic) for (const m of ubic[1].matchAll(/"?(yukiho|jugador|player|saul|saúl)"?\s*:\s*"([^"]+)"/gi)) loc[/yukiho/i.test(m[1]) ? 'yukiho' : 'jugador'] = m[2];
    return {
      narration, dialogue,
      bond_change: bond ? Number(bond[1]) : 5,
      status_text: str('status_text') || 'Contigo',
      options: options.length === 3 ? options : ['Escucharla con calma.', 'Ofrecerle algo caliente.', 'Preguntarle cómo se siente.'],
      ubicacion: loc,
    };
  }

  // The model sometimes echoes the schema placeholders ("Opción 1 de respuesta…") as options.
  const DEFAULT_OPTIONS = ['Quedarte a su lado en silencio, escuchando la lluvia.', 'Ofrecerle algo caliente de la cocina.', 'Preguntarle con suavidad qué está pensando.'];
  function cleanScene(data) {
    if (!data || typeof data !== 'object') return data;
    const opts = Array.isArray(data.options) ? data.options.filter((o) => typeof o === 'string' && o.trim() && !/^opci[oó]n \d/i.test(o.trim())) : [];
    return { ...data, options: opts.length >= 2 ? opts.slice(0, 3) : DEFAULT_OPTIONS };
  }

  const css = document.createElement('style');
  css.textContent = `
    .apt-card{background:var(--bg-card,#141020);border:1px solid var(--border-color,#2a2238);border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:6px}
    .apt-head{display:flex;justify-content:space-between;align-items:center}
    .apt-title{font-size:12px;font-weight:700;color:var(--accent-teal,#2dd4bf)}
    .apt-toggle{font-size:11px;background:transparent;color:var(--text-muted,#aaa);border:1px solid var(--border-color,#333);border-radius:8px;padding:3px 8px;cursor:pointer}
    .apt-toggle:hover{color:#fff;border-color:var(--accent-teal,#2dd4bf)}
    .apt-view{width:100%;height:auto;aspect-ratio:7/5;image-rendering:pixelated;border-radius:10px;background:#0d0a16;display:block}
    .apt-label{font-size:11px;color:var(--text-muted,#aaa);text-align:center;min-height:14px}`;
  document.head.appendChild(css);

  window.ApartmentMap = { mount, update, restore, salvageJson, cleanScene, rooms: ROOMS };
})();
