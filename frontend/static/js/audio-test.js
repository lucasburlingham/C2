(() => {
  async function playTestTone(duration = 800, freq = 1000) {
    const settings = window.getC2AudioSettings ? window.getC2AudioSettings() : null;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();
    gainNode.gain.value = settings?.outputGain ?? 1.0;
    osc.type = 'sine';
    osc.frequency.value = freq;

    const dest = ctx.createMediaStreamDestination();
    osc.connect(gainNode);
    gainNode.connect(dest);

    const audioEl = document.createElement('audio');
    audioEl.autoplay = true;
    audioEl.srcObject = dest.stream;
    audioEl.style.display = 'none';
    document.body.appendChild(audioEl);

    if (settings?.outputDeviceId && typeof audioEl.setSinkId === 'function') {
      try { await audioEl.setSinkId(settings.outputDeviceId); } catch (e) { console.warn('setSinkId failed', e); }
    }

    osc.start();
    setTimeout(async () => {
      try { osc.stop(); } catch (e) {}
      try { audioEl.pause(); audioEl.srcObject = null; if (audioEl.parentNode) audioEl.parentNode.removeChild(audioEl); } catch (e) {}
      try { await ctx.close(); } catch (e) {}
    }, duration);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('audio-test-tone');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      const old = btn.innerText;
      btn.innerText = 'Playing...';
      try { await playTestTone(800, 1000); } catch (e) { console.error(e); }
      setTimeout(() => { btn.disabled = false; btn.innerText = old; }, 900);
    });
  });
})();
