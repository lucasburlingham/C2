(() => {
  const KEY = 'c2_audio_settings_v1';

  function defaultSettings() {
    return {
      localPlayback: false,
      outputDeviceId: null,
      outputGain: 1.0,
    };
  }

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultSettings();
      return JSON.parse(raw);
    } catch (e) {
      return defaultSettings();
    }
  }

  function save(s) {
    try {
      localStorage.setItem(KEY, JSON.stringify(s));
      window.dispatchEvent(new CustomEvent('audioSettingsChanged', { detail: s }));
    } catch (e) {}
  }

  async function enumerateOutputs(selectEl, currentId) {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const outs = devices.filter(d => d.kind === 'audiooutput');
      selectEl.innerHTML = '';
      const none = document.createElement('option');
      none.value = '';
      none.text = 'Default';
      selectEl.appendChild(none);
      outs.forEach(d => {
        const o = document.createElement('option');
        o.value = d.deviceId;
        o.text = d.label || `Output ${d.deviceId}`;
        selectEl.appendChild(o);
      });
      if (currentId) selectEl.value = currentId;
    } catch (e) {
      // ignore
    }
  }

  async function init() {
    const chk = document.getElementById('audio-local-playback');
    const select = document.getElementById('audio-output-select');
    const gain = document.getElementById('audio-output-gain');
    const gainVal = document.getElementById('audio-output-gain-val');
    if (!chk || !select || !gain) return;

    const settings = load();
    chk.checked = !!settings.localPlayback;
    gain.value = settings.outputGain ?? 1.0;
    gainVal.innerText = parseFloat(gain.value).toFixed(2);

    try { await enumerateOutputs(select, settings.outputDeviceId); } catch (e) {}

    chk.addEventListener('change', () => {
      const s = load();
      s.localPlayback = chk.checked;
      save(s);
    });

    select.addEventListener('change', () => {
      const s = load();
      s.outputDeviceId = select.value || null;
      save(s);
    });

    gain.addEventListener('input', () => {
      gainVal.innerText = parseFloat(gain.value).toFixed(2);
      const s = load();
      s.outputGain = parseFloat(gain.value);
      save(s);
    });

    // refresh device list if permission granted later
    navigator.mediaDevices.addEventListener && navigator.mediaDevices.addEventListener('devicechange', async () => {
      try { await enumerateOutputs(select, load().outputDeviceId); } catch (e) {}
    });

    // expose current settings getter
    window.getC2AudioSettings = () => load();
  }

  // init on DOM ready
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

})();
