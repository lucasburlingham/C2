(() => {
  let mediaRecorder = null;
  let ws = null;
  const startBtn = document.getElementById('start-mic');
  const stopBtn = document.getElementById('stop-mic');
  const statusEl = document.getElementById('mic-status');

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
    } catch (err) {
      console.error('startStreaming error', err);
      statusEl.innerText = 'error';
    }
  }

  function stopStreaming() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    mediaRecorder = null;
  }

  startBtn.addEventListener('click', startStreaming);
  stopBtn.addEventListener('click', stopStreaming);
})();
