import asyncio
import threading
import socket
from typing import Dict, Set, Optional

_servers: Dict[str, Dict] = {}


def _start_server_in_thread(stream_id: str, host: str = '127.0.0.1', port: int = 0) -> Dict:
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    result = {}

    async def handle_client(reader, writer):
        # store writer
        peers = _servers[stream_id].setdefault('writers', set())
        peers.add(writer)
        try:
            while not reader.at_eof():
                await asyncio.sleep(1)
        finally:
            peers.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run_server():
        server = await asyncio.start_server(handle_client, host=host, port=port)
        sockets = server.sockets
        bind_port = sockets[0].getsockname()[1]
        _servers[stream_id] = {'loop': loop, 'server': server, 'writers': set(), 'port': bind_port}
        result['port'] = bind_port
        ready.set()
        await server.serve_forever()

    def thread_target():
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_server())
        except Exception:
            pass

    th = threading.Thread(target=thread_target, daemon=True)
    th.start()
    ready.wait(timeout=2)
    return {'port': result.get('port')}


def start_relay(stream_id: str, host: str = '127.0.0.1', port: int = 0) -> Dict:
    if stream_id in _servers:
        return {'ok': False, 'error': 'relay already running', 'port': _servers[stream_id].get('port')}
    info = _start_server_in_thread(stream_id, host=host, port=port)
    if not info.get('port'):
        return {'ok': False, 'error': 'failed to start relay'}
    return {'ok': True, 'port': info['port']}


def stop_relay(stream_id: str) -> Dict:
    meta = _servers.get(stream_id)
    if not meta:
        return {'ok': False, 'error': 'not running'}
    loop = meta['loop']
    server = meta['server']

    def stop():
        server.close()

    loop.call_soon_threadsafe(stop)
    _servers.pop(stream_id, None)
    return {'ok': True}


def send_bytes(stream_id: str, data: bytes) -> int:
    """Synchronously write bytes to all connected TCP clients for stream_id. Returns number attempted."""
    meta = _servers.get(stream_id)
    if not meta:
        return 0
    writers = list(meta.get('writers', set()))
    count = 0
    for w in writers:
        try:
            w.write(data)
            # schedule drain on that loop
            fut = asyncio.run_coroutine_threadsafe(w.drain(), meta['loop'])
            try:
                fut.result(timeout=1)
            except Exception:
                pass
            count += 1
        except Exception:
            pass
    return count


def get_port(stream_id: str) -> Optional[int]:
    meta = _servers.get(stream_id)
    if not meta:
        return None
    return meta.get('port')
