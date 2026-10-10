// Shared helpers for the fire checks and shots (FW branch): boots the Port battle map in first person on a free port, one headless Chrome.
import fs from 'fs'; import path from 'path';
import { ROOT, sleep, startServer, launch, loadGame, clickText, PROFILES } from './harness.mjs';
export { ROOT, sleep, PROFILES };
export const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
export async function boot(profile = 'desktop', extra = '') {
  const P = PROFILES[profile], srv = await startServer(), b = await launch(P);
  const ok = await loadGame(b, `http://127.0.0.1:${srv.port}/index.html?map=port&nointro=1&gov=best&edition=${P.ed}${extra}`); if (!ok) throw new Error('no load');
  await b.ev("(document.getElementById('help')||{}).hidden=true;1", true);
  await b.ev("__sc.openCommand();1"); await sleep(500);
  await b.ev("document.getElementById('tablet').hidden=true; __sc.openBattleSetup(); 1"); await sleep(700);
  await b.ev(clickText('#bSetup button', 'Begin battle')); await sleep(6000);
  await b.ev("__sc.CHEAT.god=true; 1", true); await b.ev("__sc.playBattle('blue');1"); await sleep(3000);
  await b.ev(`(()=>{ const sc=__sc; try{ document.getElementById('fpHint').style.display='none'; }catch(e){} if (sc.fp.p && sc.fp.p.state === 'rag') sc.fpJumpOrGetUp(); sc.CHEAT.fly = true; return 1 })()`);
  await b.ev(`window.__fxFind = (surf) => { const sc = __sc; for (let r = 0; r < 6000; r++) { const x = (Math.random() * 2 - 1) * 330, z = (Math.random() * 2 - 1) * 330; const h0 = sc.heightAt(x, z); if (h0 < 0.5) continue; if (sc.surfaceAt(x, z) !== surf) continue; let ok = true; for (let i = 0; i <= 3 && ok; i++) for (let j = -2; j <= 2; j++) if (sc.surfaceAt(x + j * 3, z + i * 6) !== surf || sc.heightAt(x + j * 3, z + i * 6) < 0.5) ok = false; if (ok) return [x, z]; } return null; };
    window.__fxGo = (x, z, yaw, pitch, h) => { const sc = __sc, p = sc.fp.p; p.x = x; p.z = z; p.y = Math.max(sc.heightAt(x, z), 0) + h; sc.fp.yaw = yaw; sc.fp.pitch = pitch; sc.fp.vx = sc.fp.vz = 0; sc.CHEAT.fly = true; return 1; }; 1`);
  return { b, srv, P, close: async () => { await b.close(); await srv.close(); } };
}
export async function render(b, file) { await b.ev("__sc.renderer.render(__sc.scene,__sc.camera);1", true); if (file) await b.shot(file); }
