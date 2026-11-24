// Studio GBRO fork: widgets of the professional version.
import { bridge, h, haptic, icon, labelled } from '../main.js';
import { W } from '../registry.js';
import { every } from './helpers.js';

// This fork's own texts: French for the team, English otherwise (they are kept out of the upstream PANEL tables).
const TXT = {
  en: { title: 'Phone music', grant: 'Allow access', ask: 'Allow notification access once to see the music of this phone',
    none: 'Nothing playing', only: 'Only on the phone', prev: 'Previous', play: 'Play', pause: 'Pause', next: 'Next' },
  fr: { title: 'Musique du téléphone', grant: "Autoriser l'accès", ask: "Autorisez une fois l'accès aux notifications pour voir la musique de ce téléphone",
    none: 'Aucune lecture en cours', only: 'Seulement sur le téléphone', prev: 'Précédent', play: 'Lecture', pause: 'Pause', next: 'Suivant' },
};
const L = () => TXT[(window.PhoneBoxI18n?.getLang?.() || 'en').slice(0, 2)] || TXT.en;

// The music playing on the phone itself (Deezer, Spotify…), next to the PC's "Now playing": one screen for both.
// Android needs "notification access" once to show other apps' media; nothing of it goes to the PC.
W['phone-media'] = {
  needs: ['tick'],
  create(box) {
    const art = h('img', 'gpm-art');
    art.alt = '';
    const title = h('div', 'gpm-title'), artist = h('div', 'gpm-artist'), app = h('div', 'gpm-app');
    const prev = labelled(h('button', 'pb', icon('skip-back')), L().prev);
    const play = labelled(h('button', 'pb', icon('play')), L().play);
    const next = labelled(h('button', 'pb', icon('skip-forward')), L().next);
    const grant = h('button', 'btn gpm-grant');
    grant.textContent = L().grant;
    const info = h('div', 'gpm-info', app, title, artist);
    const btns = h('div', 'pomo-btns', prev, play, next);
    box.style.cssText += ';display:flex;flex-direction:column;gap:8px;justify-content:center;overflow:hidden';
    art.style.cssText = 'width:64px;height:64px;border-radius:10px;object-fit:cover;flex:none;display:none';
    title.style.cssText = 'font-weight:600;font-size:1.05em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
    artist.style.cssText = 'opacity:.75;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
    app.style.cssText = 'font-size:.75em;letter-spacing:.08em;text-transform:uppercase;opacity:.55';
    info.style.cssText = 'min-width:0;flex:1';
    const row = h('div', 'gpm-row', art, info);
    row.style.cssText = 'display:flex;gap:12px;align-items:center;min-width:0';
    box.append(row, btns, grant);
    let playing = false;
    const send = (cmd) => { haptic(); try { bridge.phoneMediaCommand(cmd); } catch (_) {} setTimeout(load, 400); };
    prev.addEventListener('click', () => send('previous'));
    next.addEventListener('click', () => send('next'));
    play.addEventListener('click', () => send(playing ? 'pause' : 'play'));
    grant.addEventListener('click', () => { try { bridge.phoneMediaAccess(); } catch (_) {} });
    const show = (s) => {
      const has = !!(s && s.access);
      grant.style.display = has ? 'none' : '';
      btns.style.display = has && s.title ? '' : 'none';
      const l = L();
      if (!bridge?.phoneMedia) { grant.style.display = 'none'; app.textContent = ''; title.textContent = l.only; artist.textContent = ''; return; }
      if (!has) { app.textContent = l.title; title.textContent = l.ask; artist.textContent = ''; art.style.display = 'none'; return; }
      if (!s.title) { app.textContent = l.title; title.textContent = l.none; artist.textContent = ''; art.style.display = 'none'; return; }
      playing = !!s.playing;
      play.replaceChildren(icon(playing ? 'pause' : 'play'));
      play.setAttribute('aria-label', playing ? l.pause : l.play);
      app.textContent = s.app || '';
      title.textContent = s.title;
      artist.textContent = s.artist || '';
      if (s.art) { if (art.src !== s.art) art.src = s.art; art.style.display = ''; } else art.style.display = 'none';
    };
    const load = () => { try { show(bridge?.phoneMedia ? JSON.parse(bridge.phoneMedia()) : null); } catch (_) { show(null); } };
    const tickLoad = every(2000, load);
    load();
    return { update: tickLoad };
  },
};
