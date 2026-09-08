(() => {
  let mediaRecorder = null;
  let ws = null;
  const startBtn = document.getElementById('start-mic');
  const stopBtn = document.getElementById('stop-mic');
  const statusEl = document.getElementById('mic-status');
  const usernameInput = document.getElementById('mic-username');

  function wsUrl() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${protocol}://${location.host}/ws/audio/teststream`;
  }

  async function startStreaming() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      statusEl.innerText = 'getUserMedia not supported';
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

      ws = new WebSocket(wsUrl());
      ws.binaryType = 'arraybuffer';

      // send join message with username when open
      ws.addEventListener('open', () => {
        const uname = usernameInput ? usernameInput.value.trim() : '';
        if (uname) {
          try {
            ws.send(JSON.stringify({ type: 'join', username: uname }));
          } catch (e) {
            console.error('join send', e);
          }
        }
      });

      ws.addEventListener('open', () => {
        statusEl.innerText = 'ws open';
      });
      ws.addEventListener('close', () => {
        statusEl.innerText = 'ws closed';
      });
      ws.addEventListener('error', (e) => {
        console.error('ws error', e);
        statusEl.innerText = 'ws error';
      });

      mediaRecorder.addEventListener('dataavailable', async (ev) => {
        if (!ev.data || ev.data.size === 0) return;
        try {
          const buf = await ev.data.arrayBuffer();
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(buf);
          }
        } catch (err) {
          console.error('send error', err);
        }
      });

      mediaRecorder.addEventListener('start', () => {
        statusEl.innerText = 'streaming';
        startBtn.disabled = true;
        stopBtn.disabled = false;
      });
      mediaRecorder.addEventListener('stop', () => {
        statusEl.innerText = 'stopped';
        startBtn.disabled = false;
        stopBtn.disabled = true;
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        ws = null;
      });

      // small timeslice to produce regular chunks
      mediaRecorder.start(250);
      // PTT handling: both keyboard (Space) and button/touch
      let isPtt = false;
      const pttBtn = document.getElementById('ptt-btn');
      function sendPtt(state) {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        try { ws.send(JSON.stringify({ type: 'ptt', state: state })); } catch (err) {}
        // also inform server radio PTT endpoint so hardware keying occurs
        try {
          fetch(`/radio/ptt?keying=${state ? 'true' : 'false'}`, { method: 'POST' }).catch(() => {});
        } catch (err) {}
      }

      function handleKeyDown(e) {
        if (e.code === 'Space' && !isPtt && document.activeElement.tagName !== 'INPUT') {
          isPtt = true;
          sendPtt(true);
          if (pttBtn) pttBtn.classList.add('active');
        }
      }

      function handleKeyUp(e) {
        if (e.code === 'Space' && isPtt) {
          isPtt = false;
          sendPtt(false);
          if (pttBtn) pttBtn.classList.remove('active');
        }
      }

      function handlePttDown(e) {
        if (!isPtt) {
          isPtt = true;
          sendPtt(true);
          if (pttBtn) pttBtn.classList.add('active');
        }
      }

      function handlePttUp(e) {
        if (isPtt) {
          isPtt = false;
          sendPtt(false);
          if (pttBtn) pttBtn.classList.remove('active');
        }
      }

      window.addEventListener('keydown', handleKeyDown);
      window.addEventListener('keyup', handleKeyUp);
      if (pttBtn) {
        pttBtn.addEventListener('mousedown', handlePttDown);
        document.addEventListener('mouseup', handlePttUp);
        pttBtn.addEventListener('touchstart', handlePttDown);
        pttBtn.addEventListener('touchend', handlePttUp);
      }

      // cleanup on stop
      mediaRecorder._pttCleanup = () => {
        window.removeEventListener('keydown', handleKeyDown);
        window.removeEventListener('keyup', handleKeyUp);
        if (pttBtn) {
          pttBtn.removeEventListener('mousedown', handlePttDown);
          document.removeEventListener('mouseup', handlePttUp);
          pttBtn.removeEventListener('touchstart', handlePttDown);
          pttBtn.removeEventListener('touchend', handlePttUp);
        }
      };
    } catch (err) {
      console.error('startStreaming error', err);
      statusEl.innerText = 'error';
    }
  }

  function stopStreaming() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    if (mediaRecorder && mediaRecorder._pttCleanup) mediaRecorder._pttCleanup();
    mediaRecorder = null;
  }

  startBtn.addEventListener('click', startStreaming);
  stopBtn.addEventListener('click', stopStreaming);
})();
