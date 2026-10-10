"""Step 2: roster of synthetic Chatterbox voices, line inventory and generation loop.

Imported by make_expressive.py (`roster` command). Every voice is an identity defined by a SYNTHETIC Kokoro
reference clip (tools/voices/make_refs.py), never a real person. Accents are limited to what the Kokoro
references carry (US or UK English); Chatterbox copies the reference timbre, pace and accent.
"""
import os, re, json, time
import numpy as np
import soundfile as sf

# ----------------------------------------------------------------------------- voices
# id: (reference id, role label, description, shout exaggeration, shout cfg, radio exaggeration, radio cfg)
VOICES = {
    "michael": dict(ref="michael", role="gun_crew",   desc="US male, mid 30s, gun crew (approved Kokoro Michael timbre)", sx=1.0, sc=0.28, rx=0.6, rc=0.4),
    "lewis":   dict(ref="lewis",   role="squad",      desc="UK male, 20s, rifleman (approved Kokoro Lewis timbre)",       sx=1.0, sc=0.28, rx=0.65, rc=0.4),
    "echo":    dict(ref="echo",    role="squad",      desc="US male, young, rifleman",                                    sx=1.05, sc=0.25, rx=0.65, rc=0.4),
    "nicole":  dict(ref="nicole",  role="squad",      desc="US female, 20s, rifleman",                                    sx=1.0, sc=0.28, rx=0.65, rc=0.4),
    "daniel":  dict(ref="daniel",  role="squad_leader", desc="UK male, 40s, squad leader, gruff and steady",              sx=0.95, sc=0.3, rx=0.55, rc=0.45),
    "fable":   dict(ref="fable",   role="commander",  desc="UK male, 50s, platoon commander, calm and authoritative",     sx=0.8, sc=0.4, rx=0.45, rc=0.5),
    "emma":    dict(ref="emma",    role="hq",         desc="UK female, 30s, company HQ officer on the radio",             sx=0.8, sc=0.4, rx=0.45, rc=0.5),
    "sarah":   dict(ref="sarah",   role="medic",      desc="US female, 30s, combat medic",                                sx=0.95, sc=0.3, rx=0.6, rc=0.45),
    "fenrir":  dict(ref="fenrir",  role="pilot",      desc="US male, 30s, pilot and aircrew",                             sx=0.9, sc=0.3, rx=0.55, rc=0.45),
    "george":  dict(ref="george",  role="enemy",      desc="UK-accented male, 40s, enemy soldier A",                      sx=1.05, sc=0.25, rx=0.7, rc=0.4),
    "adam":    dict(ref="adam",    role="enemy",      desc="US-accented male, 30s, enemy soldier B",                      sx=1.05, sc=0.25, rx=0.7, rc=0.4),
}

# ----------------------------------------------------------------------------- line catalogue
# VLINES keys with their plain strings (no {placeholders}); (key, text, priority) where priority 1 = urgent/combat
def L(key, *texts, hot=False): return [(key, t, hot) for t in texts]

SQUAD_ALL = (
    L("contact", "Contact front!", "Contact left!", "Contact right!", "Contact rear!", hot=True) +
    L("taking_fire", "Taking fire!", "We are taking fire!", "Under fire!", "They are shooting at us!", hot=True) +
    L("pinned", "Pinned down!", "I cannot move!", "Heads down, we are pinned!", hot=True) +
    L("moving", "Moving!", "On the move!", "Go go go!", "Moving up!") +
    L("covering", "Covering!", "I have you covered!", "Covering fire!") +
    L("reload", "Reloading!", "Changing mag!", "Reloading, cover me!", "Cover me!") +
    L("low_ammo", "Low on ammo!", "Almost dry!", "Running low!") +
    L("grenade", "Grenade out!", "Frag!", "Grenade!", "Fire in the hole!", hot=True) +
    L("medic_call", "Medic!", "I need a medic!", "Man hit, medic!", hot=True) +
    L("medic_coming", "Medic coming!", "Hold on, I am coming!", "On my way!") +
    L("patched", "Patched up.", "You are good.", "All fixed.") +
    L("thanks", "Thanks, medic.", "Thanks!", "Good as new.") +
    L("man_down", "Man down!", "He is down!", "They got him!", hot=True) +
    L("kill", "Got one.", "Target down.", "He is down.", "Hostile down.") +
    L("flag_secured", "Flag secured.", "The point is ours.", "We hold the point.") +
    L("losing_point", "We are losing the point!", "They are taking the point!", "The point is slipping!", hot=True) +
    L("defend", "Defend the point!", "Holding the point.", "We hold here.") +
    L("ack_follow", "Roger, following.", "On you.", "Following you.", "Right behind you.") +
    L("ack_hold", "Holding here.", "Roger, holding.", "Staying put.") +
    L("ack_move", "Moving to your mark.", "Roger, moving.", "On the way.") +
    L("ack_attack", "Attacking!", "Roger, going in.", "Engaging!", "Moving to engage.") +
    L("ack_defend", "Defending the point.", "Roger, we hold it.", "Digging in.") +
    L("ack_cover", "Taking cover.", "Getting down.", "Roger, cover.") +
    L("ack_fall", "Falling back!", "Pulling back!", "Roger, back we go.") +
    L("ack_suppress", "Suppressing!", "Laying down fire!", "Keeping their heads down.") +
    L("ack_ping", "Marked.", "Got it.", "I see it.") +
    L("ack_holdfire", "Holding fire.", "Weapons tight.", "Fire held.") +
    L("ack_freefire", "Free to fire.", "Weapons free.", "Fire at will.") +
    L("ack_mount", "Mounting up.", "Getting in.", "Roger, mounting.") +
    L("idle", "Waiting for orders.", "All quiet.", "Standing by.") +
    L("regroup", "On you!", "Regroup!", "Catching up!", "Coming to you!") +
    L("mount", "In!") +
    L("dismount", "Dismounting.", "Out!", "Getting out.") +
    L("full", "No room!", "It is full.", "No seat for me.") +
    L("bail", "Vehicle on fire, bail out!", "Bail out, it is burning!", "Everybody out!", hot=True) +
    L("climbing", "Climbing.", "Going up.", "On the ladder.") +
    L("in_position", "In position.", "Set up top.", "I have the high ground.") +
    L("retreat", "Fall back!", "Back, back!", "Get out of here!", "Pull back!", hot=True) +
    L("cannot_hold", "We cannot hold!", "We are being overrun!", "It is too much!", hot=True) +
    L("clear", "Clear.", "Area clear.", "All clear.") +
    L("aircraft", "Aircraft inbound!", "Helicopter overhead!", "Aircraft, take cover!", hot=True) +
    L("fm_shot", "Shot, over") + L("fm_splash", "Splash")
)
# keys that exist in index.html VLINES (the others are new groups: commander, crew, aircrew, leader, misc enemy)
VLINES_KEYS = set("contact taking_fire pinned moving covering reload low_ammo grenade medic_call medic_coming patched thanks man_down kill flag_secured losing_point defend ack_follow ack_hold ack_move ack_attack ack_defend ack_cover ack_fall ack_suppress ack_ping ack_holdfire ack_freefire ack_mount idle regroup mount dismount full bail climbing in_position retreat cannot_hold clear aircraft vehicle e_contact e_fire e_grenade e_down fm_start fm_shot fm_splash fm_destroyed fm_cease".split())
SQUAD_KEYS_SKIP_FOR_VOICE_B = {"mount", "full", "climbing", "in_position", "ack_mount"}   # vehicle chatter: one squad voice is enough

def pick(lines, per_key, skip=()):
    out, seen = [], {}
    for k, t, hot in lines:
        if k in skip: continue
        seen[k] = seen.get(k, 0) + 1
        if seen[k] <= per_key: out.append((k, t, hot))
    return out

CREW = (
    L("crew_up", "Up!") + L("crew_weaponup", "Weapon up!") + L("crew_ready", "Ready!") + L("crew_readytofire", "Ready to fire!") +
    L("crew_loaded", "Loaded!") + L("crew_roundup", "Round up!") + L("crew_standingby", "Standing by!") + L("crew_gunready", "Gun ready!") +
    L("crew_shotout", "Shot out!") + L("crew_reloading", "Reloading!") + L("crew_onTarget", "On target!") + L("crew_checkfire", "Check fire!") +
    L("fm_shot", "Shot, over!") + L("fm_splash", "Splash!") + L("crew_ceasefire", "Cease fire!") + L("crew_roundsaway", "Rounds away!")
)
COMMANDER = (
    L("cmd_attack", "Attack the quay.", "All units, advance.", "Push forward.", "Counterattack now.") +
    L("cmd_hold", "Hold the line.", "Hold your positions.", "Defend the point.") +
    L("cmd_fall", "Fall back.", "Break contact.", "Regroup at the rally point.") +
    L("cmd_reinf", "Reinforcements inbound.", "Reinforcements are on their way.") +
    L("cmd_medevac", "Medevac inbound.", "Medevac is two minutes out.") +
    L("cmd_supply", "Supplies dropping.", "Resupply is inbound.") +
    L("cmd_gunship", "Gunship on station.", "Air support is on station.", "Requesting air support.") +
    L("fm_start", "Fire mission, on your mark.", "Fire mission, danger close.") +
    L("fm_cease", "Cease fire.", "Cease fire, cease fire.") +
    L("fm_destroyed", "Target destroyed.") +
    L("cmd_secured", "Objective secured.", "Flag secured.", "Well done, all units.") +
    L("losing_point", "We are losing the point.", "They are taking the point.", "Retake the point.") +
    L("cmd_armour", "Enemy armour approaching.", "Enemy has been sighted.", "Enemy is retreating.") +
    L("cmd_comms", "Stand by for orders.", "Say again, over.", "Roger, out.", "Sitrep, over.", "Smoke out.")
)
LEADER = pick(SQUAD_ALL, 2, skip={"idle", "thanks", "patched", "full", "climbing", "dismount", "mount", "low_ammo"}) + (
    L("cmd_attack", "Move up!", "Follow me!", "Advance!", "Stay together!") + L("cmd_hold", "Hold your fire!", "Hold position!") +
    L("cmd_fall", "Fall back to the line!", "Fall back, now!") + L("lead_orders", "Watch your sectors!", "Spread out!", "Keep your heads down!", "Flank left!", "Flank right!")
)
MEDIC = (
    L("medic_coming", "Medic coming!", "Hold on, I am coming!", "On my way!", "Medic here, where are you hit?") +
    L("patched", "Patched up.", "You are good.", "All fixed.", "You are going to be fine.", "Stay with me.", "Hold still.") +
    L("medic_work", "Pressure on the wound!", "Bandaging now.", "I have got you.", "Keep your head down!", "He is stable.", "Stretcher, bring a stretcher!", "Get him out of here!", "I need cover!") +
    L("man_down", "Man down!", "Man down, I am on my way!") + L("medic_call", "Medic!")
)
PILOT = (
    L("air_on_station", "Aircraft on station.", "Gunship on station.", "Standing by for tasking.") +
    L("air_attack", "Rolling in hot!", "Guns, guns, guns!", "Target in sight.", "Visual on the enemy.", "Winchester, out of ammo.", "Break right!", "Flares away!") +
    L("air_hit", "Taking ground fire!", "Aircraft hit, aircraft hit!", "Engine failure, going down!", "Mayday, mayday!", "Bingo fuel, heading home.") +
    L("air_land", "Landing zone is hot!", "On final approach.", "Touchdown, go go go!", "Cleared to land.", "Lifting off.", "Climbing out.", "Dropping supplies.", "Medevac inbound.") +
    L("aircraft", "Aircraft inbound!", "Egress now!")
)
ENEMY = (
    L("e_contact", "There they are!", "Over there!", "Enemy spotted!", "I see them!", hot=True) +
    L("e_fire", "Open fire!", "Get them!", "Hit them!", "We are taking fire!", hot=True) +
    L("e_grenade", "Grenade!", "Frag out!", "Take this!", hot=True) +
    L("e_down", "Man down!", "They killed him!", "Medic!", hot=True) +
    L("e_misc", "Flank them!", "They are on the left!", "They are on the right!", "Push forward!", "Charge!", "Surround them!", "Get down!", "Hold the line!", "Pull back!", "Cover me!", "Reloading!", "Behind you!", "Retreat!")
)

LINESETS = {
    "michael": CREW,
    "lewis":   pick(SQUAD_ALL, 2),
    "echo":    pick(SQUAD_ALL, 2, skip=SQUAD_KEYS_SKIP_FOR_VOICE_B),
    "nicole":  pick(SQUAD_ALL, 2, skip=SQUAD_KEYS_SKIP_FOR_VOICE_B),
    "daniel":  LEADER,
    "fable":   COMMANDER,
    "emma":    COMMANDER[::2],
    "sarah":   MEDIC,
    "fenrir":  PILOT,
    "george":  ENEMY,
    "adam":    ENEMY,
}
STRICT_END = re.compile(r"[ptk]\W*$", re.I)
TWO_TAKE_KEYS = {"contact", "taking_fire", "grenade", "man_down", "medic_call", "pinned", "e_contact", "e_fire", "e_grenade", "retreat"}

def slugify(t): return re.sub(r"[^a-z0-9]+", "", t.lower())

def maxdur(text):
    w = len(text.split()); c = len(re.findall(r"[,.!?]", text))
    return 0.75 + 0.5 * w + 0.12 * c

# ----------------------------------------------------------------------------- generation
SHARE_RADIO = {"michael", "lewis", "echo", "nicole", "daniel", "george", "adam"}   # radio = the same take through the radio chain (these voices shout into the radio)

def letters(text): return len(re.sub(r"[^a-z]", "", text.lower()))

def dur_ok(d, text):
    """Plausible speaking time: at least 0.05 s per letter (faster means swallowed or truncated) and not babble."""
    L = letters(text)
    return max(0.14, 0.05 * L) <= d <= min(maxdur(text), 0.35 + 0.16 * L)

def good(M, x, text):
    return dur_ok(len(x) / M.SR, text)

def one_take(M, text, exag, cfg, seed, strict, label):
    """Generate; retry (new seed) up to 4 times if the measured duration is implausible. If none is plausible,
    keep the attempt whose duration is closest to 0.075 s per letter (typical brisk speech)."""
    best = None
    for i in range(4):
        raw = M.gen(text, exag, cfg, seed + i * 977)
        x = M.prep(raw, strict)
        if good(M, x, text):
            return x
        dev = abs(len(x) / M.SR - 0.075 * letters(text))
        if best is None or dev < best[0]: best = (dev, x)
        print(f"   retry {label} dur={len(x)/M.SR:.2f}", flush=True)
    return best[1]

def prune_implausible(out_root, meta):
    """Drop (files + metadata) every line whose shout take is implausibly short or long, so run() regenerates it."""
    bad = {(m["voice"], m["text"]) for m in meta if m["style"] == "shout" and m["take"] == 1 and not dur_ok(m["duration_s"], m["text"])}
    keep = []
    for m in meta:
        if (m["voice"], m["text"]) in bad:
            try: os.remove(os.path.join(out_root, m["file"]))
            except OSError: pass
        else: keep.append(m)
    print(f"pruned {len(bad)} implausible lines for regeneration", flush=True)
    return keep, sorted({v for v, _ in bad})

def run(M, ids):
    out_root = M.VOICES_OUT
    os.makedirs(out_root, exist_ok=True)
    meta_path = os.path.join(out_root, "lines.json")
    meta = json.load(open(meta_path, encoding="utf8")) if os.path.exists(meta_path) else []
    if os.environ.get("VOX_REDO"):
        meta, affected = prune_implausible(out_root, meta)
        ids = [i for i in (ids or list(VOICES)) if i in affected]
    done = {m["file"] for m in meta}
    ids = ids or list(VOICES)

    def save():
        json.dump(meta, open(meta_path, "w", encoding="utf8"), indent=1, ensure_ascii=False)
        json.dump({k: dict(role=x["role"], desc=x["desc"], reference=x["ref"]) for k, x in VOICES.items()},
                  open(os.path.join(out_root, "voices.json"), "w", encoding="utf8"), indent=1)

    def emit(vid, role, key, text, style, ti, x):
        slug = slugify(text)
        fname = f"{vid}/{vid}__{slug}__{style}_t{ti}.ogg"
        n, pk = M.write_ogg(os.path.join(out_root, fname), x, 60)
        d, sr = sf.read(os.path.join(out_root, fname))
        meta.append(dict(file=fname, text=text, role=role, voice=vid, style=style, take=ti, vlines_key=(key if key in VLINES_KEYS else None), group=key,
                         duration_s=round(len(d) / sr, 2), kb=round(n / 1024, 1), peak_db=round(pk, 1)))
        done.add(fname)
        return n

    for vid in ids:
        v = VOICES[vid]
        os.makedirs(os.path.join(out_root, vid), exist_ok=True)
        M.set_voice(v["ref"])
        seen, lines = set(), []
        for key, text, hot in LINESETS[vid]:
            if slugify(text) in seen: continue
            seen.add(slugify(text)); lines.append((key, text, hot))
        print(f"=== voice {vid} ({v['role']}) {len(lines)} lines", flush=True)
        t0 = time.time(); vbytes = 0
        for li, (key, text, hot) in enumerate(lines):
            slug = slugify(text)
            if f"{vid}/{vid}__{slug}__shout_t1.ogg" in done: continue
            strict = text.lower().startswith(("up", "weapon up"))
            ex = v["sx"] + (0.0 if hot else -0.15); cf = v["sc"] + (0.0 if hot else 0.08)
            seed = 5000 + li * 31
            xs = one_take(M, text, ex, cf, seed, strict, f"{vid}/{slug}/shout")
            xs = M.ms.stretch(xs, 1.12)
            vbytes += emit(vid, v["role"], key, text, "shout", 1, M.shout_chain(xs, 2.2, 0.45, 1.15))
            if vid in SHARE_RADIO:
                xr = xs
            else:
                xr = one_take(M, text, v["rx"], v["rc"], seed + 7, strict, f"{vid}/{slug}/radio")
                xr = M.ms.stretch(xr, 1.06)
            vbytes += emit(vid, v["role"], key, text, "radio", 1, M.radio_chain(xr))
            if key in TWO_TAKE_KEYS:                                   # a second take for the most repeated combat calls
                x2 = M.ms.stretch(one_take(M, text, ex, cf, seed + 4001, strict, f"{vid}/{slug}/t2"), 1.12)
                vbytes += emit(vid, v["role"], key, text, "shout", 2, M.shout_chain(x2, 2.2, 0.45, 1.15))
                vbytes += emit(vid, v["role"], key, text, "radio", 2, M.radio_chain(x2))
            if li % 4 == 3 or li == len(lines) - 1:
                save()
                print(f"  {vid} {li+1}/{len(lines)} {time.time()-t0:.0f}s {vbytes/1024:.0f} KB", flush=True)
        save()
    M.free_gpu()
