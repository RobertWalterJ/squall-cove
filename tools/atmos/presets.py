"""
presets.py - the catalogue of steam, mist and fog types for tools/atmos.

Every preset has:
  family   steam | mist | fog
  kind     life   (start, sustained loop variants, fade / settle)
           shot   (one-shot clips: splashes)
           strip  (fog / mist strip: periodic in x, seamless loop, lifecycle clips)
           blobs  (fog patches, loops)
  sim      Air solver parameters (see fluid.py). Sizes are physical: grid * dx metres.
  spray    optional droplet emitters (see fluid.Spray)
  look     render settings: reff (effective droplet radius m, sets extinction), vref/erode/lump/gain (cloud-style shaping),
           ks, amb (sun attenuation and ambient light), bump, up (render upsampling in x and z), noise scales
  clip     frame counts and rates
  game     hints written to JSON: wind response, lighting, sensors

All numbers were tuned by eye against the look of real steam, spray and fog; physical scale is real, the optical
density scale (gain) is an art control.
"""
import numpy as np

S = lambda a, b, x: np.clip((np.asarray(x, float) - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((np.asarray(x, float) - a) / (b - a), 0, 1))

PRESETS = {}


def add(name, **kw):
    PRESETS[name] = kw
    return kw


# common lighting presets (tint multiplies the grey sprite, bright scales it, scatter = gain of the forward-scatter layer)
LIGHT_STEAM = dict(day=dict(tint=[1.0, 1.0, 1.0], brightness=1.0, scatter=0.6),
                   dusk=dict(tint=[1.0, 0.80, 0.66], brightness=0.75, scatter=1.0),
                   night=dict(tint=[0.50, 0.58, 0.78], brightness=0.22, scatter=0.25, note="steam is lit by fires and lamps only: add the local light colour"),
                   backlit=dict(tint=[1.0, 0.97, 0.92], brightness=1.0, scatter=1.6))
LIGHT_MIST = dict(day=dict(tint=[0.96, 0.98, 1.0], brightness=1.0, scatter=0.9),
                  dusk=dict(tint=[1.0, 0.82, 0.70], brightness=0.72, scatter=1.3),
                  night=dict(tint=[0.45, 0.55, 0.75], brightness=0.20, scatter=0.3, note="lit by lamps and moon only"),
                  backlit=dict(tint=[1.0, 0.98, 0.94], brightness=1.0, scatter=2.0))
LIGHT_FOG = dict(day=dict(tint=[0.90, 0.93, 0.97], brightness=0.95, scatter=0.5),
                 dusk=dict(tint=[0.95, 0.78, 0.70], brightness=0.65, scatter=0.9),
                 night=dict(tint=[0.38, 0.46, 0.64], brightness=0.18, scatter=0.25, note="fog glows only where lamps and headlights hit it"),
                 backlit=dict(tint=[1.0, 0.97, 0.92], brightness=1.0, scatter=1.5))

# ------------------------------------------------------------------------------------------------------------
# STEAM
# ------------------------------------------------------------------------------------------------------------
add("steam_pipe", family="steam", kind="life", title="Pipe / vent steam jet",
    size_note="vertical jet from a 0.2 m vent, plume 1.5 to 2 m tall, clear gap about 10 to 20 cm",
    sim=dict(grid=(32, 32, 48), dx=0.05, dt=1 / 48, T0=288.0, rh=0.5, drag=0.1, vc=0.6, diff=0.03, kt=0.22, tau_evap=0.8,
             vents=[dict(x=0, y=0, rx=0.10, z0=0.08, dz=0.08, w=6.0, th=60, qe=0.16, amp=1.0, flick=0.9, gate=True, freq=1.6, turb=0.5)]),
    look=dict(reff=5e-6, vref=1.5, erode=0.5, lump=0.25, gain=1.0, ks=1.0, amb=0.45, bump=0.12, up=(4, 4), top=(0.7, 0.99), gap=0.06),
    clip=dict(fps=24, n_loop=24, n_start=12, n_fade=12, stage_fps=12, warm=5.0, ramp=0.5, fade_s=0.6, scroll=1),
    heat=dict(th_ref=60.0, strength=0.9, shape="tall"),
    game=dict(wind=dict(drift_base=0.35, drift_top=0.85, lean_deg_per_mps=9, max_lean_deg=70, note="plume bends over: lean the quad about its anchor"),
              light=LIGHT_STEAM))
add("steam_pot", family="steam", kind="life", title="Boiling pot / kettle steam",
    size_note="soft wisps from a 10 cm pot, 0.3 to 0.4 m tall",
    sim=dict(grid=(32, 32, 48), dx=0.012, dt=1 / 48, T0=292.0, rh=0.45, drag=0.2, vc=0.5, diff=0.04, kt=0.25, tau_evap=0.6,
             vents=[dict(x=0, y=0, rx=0.055, z0=0.014, dz=0.014, w=0.6, th=50, qe=0.12, amp=1.0, flick=0.8, gate=True, freq=0.9, turb=0.6)]),
    look=dict(reff=4e-6, vref=0.6, erode=0.55, lump=0.30, gain=1.2, ks=0.9, amb=0.55, bump=0.08, up=(4, 4), top=(0.6, 0.95), gap=0.0, xw=0.3),
    clip=dict(fps=24, n_loop=24, n_start=12, n_fade=14, stage_fps=12, warm=3.0, ramp=0.6, fade_s=0.6, scroll=1),
    heat=dict(th_ref=45.0, strength=0.35, shape="default"),
    game=dict(wind=dict(drift_base=0.6, drift_top=1.0, lean_deg_per_mps=30, max_lean_deg=80, note="very light: strongly wind-driven"), light=LIGHT_STEAM))
add("steam_engine", family="steam", kind="life", title="Hot wreck / engine bay cooling steam",
    size_note="three leaking seams along a 1 m bonnet, intermittent puffs, about 2 m tall",
    sim=dict(grid=(32, 32, 48), dx=0.06, dt=1 / 48, T0=288.0, rh=0.5, drag=0.12, vc=0.55, diff=0.03, kt=0.2, tau_evap=0.8, wind=0.25,
             vents=[dict(x=-0.45, y=0, rx=0.13, ry=0.20, z0=0.10, dz=0.10, w=2.8, th=64, qe=0.15, amp=1.0, flick=1.0, gate=True, freq=1.0, turb=0.6, jit=0.05),
                    dict(x=0.05, y=0.1, rx=0.11, ry=0.2, z0=0.10, dz=0.10, w=2.4, th=60, qe=0.14, amp=0.9, flick=1.0, gate=True, freq=1.5, turb=0.6, jit=0.05),
                    dict(x=0.5, y=-0.1, rx=0.12, ry=0.2, z0=0.08, dz=0.10, w=2.6, th=62, qe=0.14, amp=0.8, flick=1.0, gate=True, freq=0.7, turb=0.6, jit=0.05)]),
    look=dict(reff=5e-6, vref=1.2, erode=0.6, lump=0.3, gain=1.0, ks=1.0, amb=0.45, bump=0.12, up=(4, 4), top=(0.65, 0.97), gap=0.05, xw=0.3),
    clip=dict(fps=24, n_loop=24, n_start=12, n_fade=12, stage_fps=12, warm=4.0, ramp=0.8, fade_s=1.0, scroll=1),
    heat=dict(th_ref=52.0, strength=0.8, shape="wide"),
    game=dict(wind=dict(drift_base=0.5, drift_top=1.0, lean_deg_per_mps=18, max_lean_deg=75, note="baked with a 0.4 m/s breeze (tail drifts to +x); mirror for the other side"), light=LIGHT_STEAM))
add("steam_burst", family="steam", kind="life", title="Water-on-fire steam burst",
    size_note="huge, brief and billowing: 8 m wide, 10 to 12 m tall, bursts in about a second, lingers for 6 s",
    sim=dict(grid=(32, 32, 48), dx=0.25, dt=1 / 24, T0=288.0, rh=0.4, drag=0.06, vc=0.7, diff=0.03, kt=0.12, tau_evap=1.0, dmax=0.3,
             vents=[dict(x=0, y=0, rx=1.0, ry=1.0, z0=0.6, dz=0.5, w=8.0, th=70, qe=0.17, amp=1.0, flick=0.7, freq=0.6, turb=0.7)]),
    look=dict(reff=5e-6, vref=1.0, erode=0.45, lump=0.3, gain=1.1, ks=0.5, amb=0.45, bump=0.06, up=(4, 4), top=(0.55, 0.93), gap=0.0, xw=0.36, yw=0.3),
    clip=dict(fps=12, n_loop=24, n_start=12, n_fade=14, stage_fps=12, warm=4.0, ramp=0.15, fade_s=1.2, scroll=1, punch=(0.8, 0.6)),
    heat=dict(th_ref=75.0, strength=1.0, shape="tall"),
    game=dict(wind=dict(drift_base=0.2, drift_top=0.8, lean_deg_per_mps=3, max_lean_deg=45, note="momentum-dominated: only the top drifts"), light=LIGHT_STEAM))
add("steam_geyser", family="steam", kind="life", title="Geyser / hot spring veil",
    size_note="a 2 m pool giving a soft rising veil, about 4 m tall (cold morning air)",
    sim=dict(grid=(32, 32, 48), dx=0.1, dt=1 / 48, T0=277.0, rh=0.7, drag=0.12, vc=0.5, diff=0.04, kt=0.10, tau_evap=1.2,
             vents=[dict(x=0, y=0, rx=0.55, ry=0.55, z0=0.1, dz=0.12, w=0.6, th=25, qe=0.02, amp=1.0, flick=0.9, freq=0.5, turb=1.2),
                    dict(x=0.2, y=-0.1, rx=0.3, ry=0.3, z0=0.1, dz=0.12, w=1.4, th=34, qe=0.03, amp=0.8, flick=1.0, gate=True, freq=0.4, turb=1.0)]),
    look=dict(reff=5e-6, vref=0.8, erode=0.6, lump=0.35, gain=0.8, ks=0.7, amb=0.55, bump=0.08, up=(4, 4), top=(0.7, 0.99), gap=0.0),
    clip=dict(fps=12, n_loop=24, n_start=12, n_fade=12, stage_fps=8, warm=6.0, ramp=2.0, fade_s=2.5, scroll=1),
    heat=dict(th_ref=36.0, strength=0.45, shape="wide"),
    game=dict(wind=dict(drift_base=0.5, drift_top=1.0, lean_deg_per_mps=20, max_lean_deg=80, note="light veil: moves with the breeze"), light=LIGHT_STEAM))
add("steam_lava", family="steam", kind="life", title="Lava hitting water: boiling steam",
    size_note="enormous white cloud, 14 m across and 20 m tall, boiling and rolling",
    sim=dict(grid=(32, 32, 48), dx=0.5, dt=1 / 16, T0=288.0, rh=0.5, drag=0.05, vc=0.8, diff=0.03, kt=0.10, tau_evap=1.5, dmax=0.3,
             vents=[dict(x=0, y=0, rx=2.2, ry=2.2, z0=1.0, dz=1.0, w=7.0, th=75, qe=0.2, amp=1.0, flick=0.6, freq=0.35, turb=0.8)]),
    look=dict(reff=5e-6, vref=1.2, erode=0.4, lump=0.2, gain=1.0, ks=0.3, amb=0.45, bump=0.03, up=(4, 4), top=(0.55, 0.93), gap=0.0, xw=0.36, yw=0.3),
    clip=dict(fps=8, n_loop=24, n_start=12, n_fade=14, stage_fps=8, warm=14.0, ramp=3.0, fade_s=4.0, scroll=1),
    heat=dict(th_ref=80.0, strength=1.0, shape="tall"),
    game=dict(wind=dict(drift_base=0.15, drift_top=0.6, lean_deg_per_mps=1.5, max_lean_deg=35, note="huge buoyant column: barely leans"), light=LIGHT_STEAM))

# ------------------------------------------------------------------------------------------------------------
# MIST (droplet spray)
# ------------------------------------------------------------------------------------------------------------
add("mist_bow", family="mist", kind="life", title="Sea spray off a bow or breaking wave",
    size_note="sheets thrown 3 to 4 m up and carried aft; x axis = aft direction, anchor = bow crest",
    sim=dict(grid=(32, 32, 48), dx=0.12, dt=1 / 48, T0=285.0, rh=0.85, drag=0.15, vc=0.4, diff=0.03, kt=0.12, tau_evap=1.0, wind=lambda z: 3.0 * np.clip(z / 3.0, 0.3, 1.0),
             churn=0.4, churn_h=2.5, noise_tc=0.4),
    spray=dict(rh=0.85, eddy=0.12, coupling=0.8, nmax=70000,
               emitters=[dict(pos=(-1.1, 0.0, 0.25), pos_sigma=(0.25, 0.10, 0.04), axis=(0.45, 0.0, 1.0), spread=(0.35, 0.55, 0.30), speed=(5.2, 1.6),
                              r=(70e-6, 0.8), flux=2.6, pps=4200)]),
    look=dict(reff=60e-6, vref=1.4, erode=0.25, lump=0.2, gain=1.0, ks=0.9, amb=0.5, bump=0.06, up=(4, 4), top=(0.75, 0.99), blur=(1.2, 0.6), trail=3),
    clip=dict(fps=24, n_loop=24, n_start=12, n_fade=24, stage_fps=16, warm=2.0, ramp=0.25, fade_s=0.4, scroll=1),
    game=dict(wind=dict(drift_base=0.6, drift_top=1.0, lean_deg_per_mps=12, max_lean_deg=60, note="baked with 3 m/s relative wind aft; scale the drift with the apparent wind"), light=LIGHT_MIST))
add("mist_surf", family="mist", kind="life", title="Waterfall / surf mist",
    size_note="soft rolling base mist, 10 m wide and 8 to 12 m tall, fine droplets that hang and roll",
    sim=dict(grid=(32, 32, 48), dx=0.35, dt=1 / 24, T0=284.0, rh=0.92, drag=0.08, vc=0.6, diff=0.04, kt=0.2, tau_evap=3.0, churn=0.9, churn_h=5.0, noise_tc=1.0, noise_sig=2.0,
             vents=[dict(x=0, y=0, rx=2.5, ry=2.0, z0=0.4, dz=0.4, w=0.5, th=0.6, amp=1.0, flick=0.8, freq=0.3, turb=0.8)]),
    spray=dict(rh=0.92, eddy=0.5, coupling=0.0, nmax=60000, rmin=4e-6,
               emitters=[dict(pos=(0.0, 0.0, 0.3), pos_sigma=(1.8, 1.2, 0.3), axis=(0.0, 0.0, 1.0), spread=(0.9, 0.9, 0.4), speed=(1.4, 0.8),
                              r=(14e-6, 0.5), flux=5.0, pps=3000)]),
    look=dict(reff=14e-6, vref=0.8, erode=0.5, lump=0.3, gain=1.0, ks=0.6, amb=0.55, bump=0.06, up=(4, 4), top=(0.72, 0.99), blur=(1.6, 0.8), trail=1),
    clip=dict(fps=12, n_loop=24, n_start=12, n_fade=12, stage_fps=8, warm=14.0, ramp=3.0, fade_s=3.0, scroll=1),
    game=dict(wind=dict(drift_base=0.8, drift_top=1.0, lean_deg_per_mps=25, max_lean_deg=75, note="fine droplets follow the wind almost exactly"), light=LIGHT_MIST))


def splash(name, title, L, dx, fps, n, mass, nb, size_note):
    g = 9.81
    v0 = float(np.sqrt(g * L))
    return add(name, family="mist", kind="shot", title=title, size_note=size_note,
               sim=dict(grid=(32, 32, 48), dx=dx, dt=1 / 48, T0=285.0, rh=0.8, drag=0.15, vc=0.4, diff=0.03, kt=0.1, tau_evap=1.0),
               spray=dict(rh=0.8, eddy=0.04 * L, coupling=0.6, nmax=60000,
                          emitters=[dict(pos=(0, 0, 0.02 * L), ring=0.22 * L, pos_sigma=(0.02 * L, 0.02 * L, 0.01 * L), radial=True, elev=(50, 14), speed=(2.1 * v0, 0.6 * v0),
                                         r=(0.0004 * (L / 0.3) ** 0.4, 0.75), flux=mass * 0.55 / nb, pps=14000 / nb, sched=lambda t, nb=nb: float(t < nb)),
                                    dict(pos=(0, 0, 0.02 * L), pos_sigma=(0.05 * L, 0.05 * L, 0.01 * L), axis=(0, 0, 1), spread=(0.22, 0.22, 0.05), speed=(1.8 * v0, 0.4 * v0),
                                         r=(0.0003 * (L / 0.3) ** 0.4, 0.7), flux=mass * 0.15 / nb, pps=3000 / nb, sched=lambda t, nb=nb: float(0.05 * nb < t < 1.8 * nb)),
                                    dict(pos=(0, 0, 0.05 * L), pos_sigma=(0.2 * L, 0.2 * L, 0.04 * L), radial=True, elev=(35, 25), speed=(1.0 * v0, 0.5 * v0),
                                         r=(35e-6, 0.5), flux=mass * 0.30 / nb, pps=7000 / nb, sched=lambda t, nb=nb: float(t < 1.5 * nb))]),
               look=dict(reff=80e-6, vref=1.2, erode=0.2, lump=0.15, gain=1.0, ks=0.9, amb=0.5, bump=0.05, up=(4, 4), top=(0.75, 0.99), blur=(1.2, 0.7), trail=3),
               clip=dict(fps=fps, n_shot=n, nvar=3, pulse=nb),
               game=dict(wind=dict(drift_base=0.5, drift_top=1.0, lean_deg_per_mps=10, max_lean_deg=60, note="the fine mist drifts; the coarse crown is ballistic"), light=LIGHT_MIST))


splash("splash_small", "Impact splash, small", 0.30, 0.02, 24, 30, 0.06, 0.05, "stone or bullet strike on water; crown 0.6 m wide, 0.5 m tall")
splash("splash_medium", "Impact splash, medium", 1.5, 0.10, 20, 36, 7.0, 0.12, "shell or large debris hit; crown 3 m wide, 3 m tall")
splash("splash_large", "Impact splash, large", 6.0, 0.40, 12, 40, 450.0, 0.25, "bomb or ship-scale impact; crown 12 m wide, 12 m tall")

add("spray_cone", family="mist", kind="life", title="Hose / nozzle spray cone",
    size_note="firefighting hose or water cannon, nozzle at the left edge, throws about 8 m, x axis = jet direction",
    sim=dict(grid=(48, 24, 24), dx=0.2, dt=1 / 48, T0=285.0, rh=0.7, drag=0.1, vc=0.4, diff=0.03, kt=0.1, tau_evap=1.0, wind=0.0),
    spray=dict(rh=0.7, eddy=0.1, coupling=1.0, nmax=70000,
               emitters=[dict(pos=(-4.4, 0.0, 1.4), pos_sigma=(0.03, 0.03, 0.03), axis=(1.0, 0.0, 0.28), spread=(0.0, 0.11, 0.11), speed=(17.0, 1.5),
                              r=(160e-6, 0.65), flux=3.0, pps=5000)]),
    look=dict(reff=100e-6, vref=1.3, erode=0.25, lump=0.2, gain=1.0, ks=0.6, amb=0.5, bump=0.05, up=(4, 4), top=(0.8, 0.99), blur=(1.2, 0.6), trail=3, win_x=0.12),
    clip=dict(fps=24, n_loop=24, n_start=12, n_fade=24, stage_fps=16, warm=1.5, ramp=0.1, fade_s=0.3, scroll=0),
    game=dict(wind=dict(drift_base=0.2, drift_top=0.7, lean_deg_per_mps=3, max_lean_deg=20, note="the jet core is ballistic; only the fine mist drifts"), light=LIGHT_MIST))

# ------------------------------------------------------------------------------------------------------------
# FOG / low mist strips: periodic in x. frame_px = grid * up. stages timeline in simulated seconds (time-lapse noted).
# ------------------------------------------------------------------------------------------------------------
STRIP_CLIP = dict(n_loop=24, n_linger=12, n_stage=8, fps=6, stage_fps=2, linger_fps=3)

add("fog_ground", family="fog", kind="strip", title="Ground fog",
    size_note="creeping fog 1 to 2 m deep; strip 16 m x 4 m (512x128), tileable",
    sim=dict(grid=(128, 20, 32), dx=0.125, dt=0.1, periodic=True, T0=284.0, rh=0.965, drag=0.25, vc=0.2, diff=0.06, kt=0.0, tau_evap=3.0, patch=3.0, patch_amp=0.5,
             force_h=0.7, churn=0.05, churn_h=1.8, noise_tc=3.0, noise_sig=2.2, vt=0.0, wind=lambda z: 0.25 * np.clip(z / 2.0, 0.2, 1.0), sponge_rate=1.5, slope=0.0),
    stages=dict(form=dict(cool=0.045, t=36.0, hold=0.012), drift=dict(t=40.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.05, t=30.0),
                fall=dict(force_h=1.6, vt=0.12, t=22.0, pre=dict(cool=0.05, t=40.0))),
    look=dict(reff=6e-6, vref=0.30, erode=0.45, lump=0.25, gain=1.0, ks=0.8, amb=0.55, bump=0.05, up=(4, 4), noise=((7, 2.5, 8), (3.5, 1.5, 4), (1.8, 0.9, 2)), noise_mode="boil",
              top=(0.62, 0.98), bottom=0.05, floor_fade=0.10, dither=True, u_ref=0.12),
    strip=dict(), clip=dict(STRIP_CLIP),
    game=dict(wind=dict(scroll_factor=[0.35, 0.6, 0.9], note="scroll layers at 35%, 60%, 90% of the wind speed (low to high)"), light=LIGHT_FOG, layer_heights_m=[0.0, 0.5, 1.0]))
add("fog_bank", family="fog", kind="strip", title="Rolling fog bank",
    size_note="advancing wall of fog 10 to 30 m tall; strip 160 m x 40 m (512x128), tileable",
    sim=dict(grid=(128, 24, 32), dx=1.25, dt=0.4, periodic=True, T0=284.0, rh=0.96, drag=0.04, vc=0.55, diff=0.04, kt=0.08, tau_evap=5.0, patch=3.0, patch_amp=0.6,
             force_h=12.0, churn=0.06, churn_h=26.0, noise_tc=8.0, noise_sig=2.0, wind=lambda z: 0.4 + 2.6 * np.clip(z / 28.0, 0, 1), sponge_rate=0.8, slope=0.0, th_amb=lambda z: 0.0 * z),
    stages=dict(form=dict(cool=0.06, t=60.0, hold=0.012), drift=dict(t=60.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.04, t=60.0),
                fall=dict(force_h=18.0, vt=0.5, t=40.0, pre=dict(cool=0.06, t=60.0))),
    look=dict(reff=7e-6, vref=0.10, erode=0.45, lump=0.3, gain=1.0, ks=0.12, amb=0.5, bump=0.06, up=(4, 4), noise=((7, 3, 8), (3.5, 1.5, 4), (1.8, 0.9, 2)), noise_mode="boil",
              top=(0.62, 0.98), bottom=0.05, floor_fade=0.08, dither=True, u_ref=1.4),
    strip=dict(), clip=dict(STRIP_CLIP, fps=6),
    game=dict(wind=dict(scroll_factor=[0.5, 0.8, 1.0], note="the bank front rolls with the upper wind; scroll the top layer fastest"), light=LIGHT_FOG, layer_heights_m=[0.0, 8.0, 18.0]))
add("fog_sea", family="fog", kind="strip", title="Harbour / sea fog",
    size_note="thick low fog 4 to 8 m deep drifting over water; strip 64 m x 16 m (512x128), tileable",
    sim=dict(grid=(128, 24, 32), dx=0.5, dt=0.25, periodic=True, T0=282.0, rh=0.97, drag=0.08, vc=0.45, diff=0.05, kt=0.05, tau_evap=4.0, patch=4.0, patch_amp=0.5,
             force_h=3.0, churn=0.08, churn_h=9.0, noise_tc=5.0, noise_sig=2.2, wind=lambda z: 0.6 + 1.8 * np.clip(z / 9.0, 0, 1), sponge_rate=1.0, slope=0.0),
    stages=dict(form=dict(cool=0.05, moist=3e-6, t=50.0, hold=0.014), drift=dict(t=50.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.05, t=45.0),
                fall=dict(force_h=6.0, vt=0.25, t=30.0, pre=dict(cool=0.05, t=50.0))),
    look=dict(reff=6e-6, vref=0.14, erode=0.5, lump=0.3, gain=1.0, ks=0.25, amb=0.5, bump=0.06, up=(4, 4), noise=((7, 3, 8), (3.5, 1.5, 4), (1.8, 0.9, 2)), noise_mode="boil",
              top=(0.62, 0.98), bottom=0.05, floor_fade=0.08, dither=True, u_ref=0.8),
    strip=dict(), clip=dict(STRIP_CLIP, fps=6),
    game=dict(wind=dict(scroll_factor=[0.5, 0.75, 1.0], note="harbour fog moves with the surface wind; upper layers faster"), light=LIGHT_FOG, layer_heights_m=[0.0, 2.0, 5.0]))
add("fog_valley", family="fog", kind="strip", title="Valley fog pooling",
    size_note="fog that has sunk to fill low ground under an inversion: flat top at 9 m, soft wisps above; strip 96 m x 24 m (512x128), tileable",
    sim=dict(grid=(128, 20, 32), dx=0.75, dt=0.5, periodic=True, T0=282.0, rh=lambda z: np.where(z < 10.0, 0.985, 0.55), th_amb=lambda z: 3.0 * S(9.0, 13.0, z) * 1.0 + 0.0 * z,
             drag=0.05, vc=0.4, diff=0.04, kt=0.04, tau_evap=4.0, patch=4.0, patch_amp=0.4, force_h=5.0, churn=0.05, churn_h=14.0, noise_tc=8.0, noise_sig=2.0,
             wind=lambda z: 0.3 + 0.9 * S(7.0, 12.0, z), sponge_rate=0.8, slope=0.04),
    stages=dict(form=dict(cool=0.05, t=70.0, hold=0.012), drift=dict(t=60.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.04, t=60.0),
                fall=dict(force_h=11.0, vt=0.45, t=50.0, pre=dict(cool=0.04, t=60.0))),
    look=dict(reff=6e-6, vref=0.10, erode=0.5, lump=0.3, gain=1.0, ks=0.12, amb=0.52, bump=0.06, up=(4, 4), noise=((7, 3, 8), (3.5, 1.5, 4), (1.8, 0.9, 2)), noise_mode="boil",
              top=(0.70, 0.99), bottom=0.05, floor_fade=0.08, dither=True, u_ref=0.5),
    strip=dict(), clip=dict(STRIP_CLIP, fps=5),
    game=dict(wind=dict(scroll_factor=[0.2, 0.4, 0.7], note="pooled fog barely moves: scroll slowly, wisps above faster"), light=LIGHT_FOG, layer_heights_m=[0.0, 4.0, 8.0]))
add("fog_wisps", family="fog", kind="strip", title="Fog wisp strips",
    size_note="thin curling strands, 32 m x 8 m (512x128), tileable; layer over fog for texture",
    sim=dict(grid=(128, 16, 32), dx=0.25, dt=0.15, periodic=True, T0=284.0, rh=0.93, drag=0.06, vc=0.9, diff=0.025, kt=0.03, tau_evap=3.0, patch=3.0, patch_amp=0.9,
             force_h=2.0, churn=0.04, churn_h=6.0, noise_tc=3.0, noise_sig=1.8, wind=lambda z: 0.2 + 1.4 * S(1.5, 5.5, z), sponge_rate=1.0, slope=0.0),
    stages=dict(form=dict(cool=0.04, t=40.0, hold=0.010), drift=dict(t=40.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.04, t=30.0),
                fall=dict(force_h=3.0, vt=0.2, t=25.0, pre=dict(cool=0.04, t=40.0))),
    look=dict(reff=5e-6, vref=0.10, erode=0.72, lump=0.3, gain=1.0, ks=0.2, amb=0.55, bump=0.05, up=(4, 4), noise=((5, 2.5, 6), (2.5, 1.2, 3), (1.4, 0.8, 1.6)), noise_mode="boil",
              top=(0.62, 0.98), bottom=0.05, floor_fade=0.05, dither=True, u_ref=0.5),
    strip=dict(), clip=dict(STRIP_CLIP, fps=6),
    game=dict(wind=dict(scroll_factor=[0.6, 0.85, 1.1], note="thin strands travel nearly with the wind"), light=LIGHT_FOG, layer_heights_m=[1.0, 3.0, 5.0]))
add("fog_forest", family="fog", kind="strip", title="Forest mist (vertical sheets)",
    size_note="mist rising in vertical sheets between trunks, 24 m x 12 m (512x256), tileable",
    sim=dict(grid=(128, 16, 64), dx=0.1875, dt=0.2, periodic=True, T0=282.0, rh=0.95, drag=0.1, vc=0.5, diff=0.03, kt=0.05, tau_evap=3.5, patch=2.0, patch_amp=0.5,
             force_h=3.5, churn=0.03, churn_h=12.0, noise_tc=4.0, noise_sig=1.6, wind=0.15, sponge_rate=1.0, slope=0.0,
             vents=[dict(x=-9.0 + 3.0 * k, y=0.0, rx=0.35, ry=1.1, z0=0.2, dz=0.3, w=0.35, th=0.4, qe=0.0008, amp=0.8 + 0.4 * ((k * 7) % 3) / 2.0, flick=0.7, freq=0.15 + 0.03 * k, turb=0.9)
                    for k in range(8)]),
    stages=dict(form=dict(cool=0.03, t=50.0, hold=0.008), drift=dict(t=50.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.03, t=40.0),
                fall=dict(force_h=6.0, vt=0.15, t=30.0, pre=dict(cool=0.03, t=50.0))),
    look=dict(reff=6e-6, vref=0.08, erode=0.55, lump=0.3, gain=1.0, ks=0.12, amb=0.55, bump=0.05, up=(4, 4), noise=((9, 2, 3), (4, 1.2, 1.8), (2, 0.8, 1.0)), noise_mode="boil",
              top=(0.70, 0.99), bottom=0.04, floor_fade=0.05, dither=True, u_ref=0.1),
    strip=dict(), clip=dict(STRIP_CLIP, fps=5),
    game=dict(wind=dict(scroll_factor=[0.3, 0.5, 0.7], note="forest mist is sheltered: scroll slowly"), light=LIGHT_FOG, layer_heights_m=[0.0, 3.0, 6.0]))
add("mist_dawn", family="mist", kind="strip", title="Dawn mist over water",
    size_note="very low, translucent, wispy mist (0.5 to 1 m) over still water; strip 19 m x 5 m (512x128), tileable",
    sim=dict(grid=(128, 16, 32), dx=0.15, dt=0.12, periodic=True, T0=283.0, rh=0.935, drag=0.1, vc=0.5, diff=0.04, kt=0.02, tau_evap=3.0, patch=3.5, patch_amp=0.9,
             force_h=0.4, churn=0.03, churn_h=1.2, noise_tc=3.0, noise_sig=2.0, wind=lambda z: 0.15 + 0.3 * np.clip(z / 1.5, 0, 1), sponge_rate=1.5, slope=0.0),
    stages=dict(form=dict(cool=0.03, t=30.0, hold=0.008), drift=dict(t=30.0, churn=1.0), linger=dict(churn=0.25), thin=dict(heat=0.04, t=25.0),
                fall=dict(force_h=0.8, vt=0.06, t=20.0, pre=dict(cool=0.03, t=30.0))),
    look=dict(reff=5e-6, vref=0.22, erode=0.66, lump=0.3, gain=0.8, ks=0.4, amb=0.6, bump=0.04, up=(4, 4), noise=((7, 2.5, 8), (3.5, 1.4, 4), (1.8, 0.8, 2)), noise_mode="boil",
              top=(0.62, 0.98), bottom=0.05, floor_fade=0.12, dither=True, u_ref=0.1),
    strip=dict(), clip=dict(STRIP_CLIP, fps=6),
    game=dict(wind=dict(scroll_factor=[0.4, 0.7, 1.0], note="lies on the water: scroll slowly"), light=LIGHT_FOG, layer_heights_m=[0.0, 0.3, 0.7]))

# blobs: soft irregular billboards (non periodic), loops
add("fog_blobs", family="fog", kind="blobs", title="Fog blob billboards",
    size_note="soft irregular patches: flat ground patch 10 m wide, round puff, tall column",
    sim=dict(grid=(40, 24, 32), dx=0.25, dt=0.2, T0=284.0, rh=0.95, drag=0.12, vc=0.4, diff=0.05, kt=0.04, tau_evap=3.0, force_h=3.0, noise_tc=3.0, noise_sig=1.8,
             churn=0.12, churn_h=8.0, wind=0.0),
    blobs=dict(types=dict(patch=dict(r=(3.4, 2.2, 0.55), z=0.6, amp=0.0014), puff=dict(r=(2.0, 1.8, 1.6), z=2.0, amp=0.0016), column=dict(r=(1.1, 1.0, 3.0), z=3.0, amp=0.0016)),
               nvar=2, n=12, fps=4),
    look=dict(reff=6e-6, vref=0.22, erode=0.55, lump=0.3, gain=1.0, ks=0.35, amb=0.55, bump=0.06, up=(4, 4), noise=((6, 3, 6), (3, 1.6, 3), (1.6, 0.9, 1.6)), noise_mode="boil",
              top=(0.65, 0.99), bottom=0.12, xw=0.3, yw=0.3, dither=True),
    clip=dict(fps=4),
    game=dict(wind=dict(scroll_factor=[1.0], note="blobs are free billboards: move them at the wind speed"), light=LIGHT_FOG))

ORDER = ["steam_pipe", "steam_pot", "steam_engine", "steam_burst", "steam_geyser", "steam_lava",
         "mist_bow", "mist_surf", "splash_small", "splash_medium", "splash_large", "spray_cone", "mist_dawn",
         "fog_ground", "fog_bank", "fog_sea", "fog_valley", "fog_wisps", "fog_forest", "fog_blobs"]
