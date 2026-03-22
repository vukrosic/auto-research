"""WebSocket SSH terminal — real PTY sessions to GPUs via paramiko.

Admin-only. Supports multiple concurrent terminal sessions.
"""
import asyncio
import logging
import paramiko
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from api.database import SessionLocal
from api.models import GPU, User

router = APIRouter()
logger = logging.getLogger(__name__)


def get_user_by_session(token: str | None) -> User | None:
    """Look up user by api_key (used as session token)."""
    if not token:
        return None
    db = SessionLocal()
    try:
        return db.query(User).filter(User.api_key == token, User.is_active == True).first()
    finally:
        db.close()


def get_user_from_request(websocket: WebSocket, token: str | None) -> User | None:
    """Try token query param first, then session cookie."""
    # Query param: ?token=ar_xxxx
    if token:
        return get_user_by_session(token)
    # Cookie fallback
    cookie_header = websocket.headers.get("cookie", "")
    for item in cookie_header.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            if k.strip() == "session":
                return get_user_by_session(v.strip())
    return None


@router.websocket("/ws/{gpu_id}")
async def terminal_ws(websocket: WebSocket, gpu_id: int, token: str | None = Query(default=None)):
    """WebSocket SSH terminal session.

    Auth: pass ?token=<api_key> or use the session cookie.
    Client sends JSON: {type: 'input', data: '...'} or {type: 'resize', cols, rows}
    Server sends JSON: {type: 'output', data: '...'} or {type: 'error', data: '...'}
    """
    user = get_user_from_request(websocket, token)

    if not user or user.tier != "admin":
        await websocket.accept()
        await websocket.send_json({"type": "error", "data": "Admin access required"})
        await websocket.close(code=4003)
        return

    # Get GPU
    db = SessionLocal()
    try:
        gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
        if not gpu:
            await websocket.accept()
            await websocket.send_json({"type": "error", "data": f"GPU {gpu_id} not found"})
            await websocket.close(code=4004)
            return
        host = gpu.host
        port = gpu.port
        ssh_user = gpu.user
        password = gpu.password
        gpu_name = gpu.name
    finally:
        db.close()

    await websocket.accept()
    await websocket.send_json({"type": "output", "data": f"Connecting to {gpu_name} ({host}:{port})...\r\n"})

    # Connect SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname=host,
            port=port,
            username=ssh_user,
            password=password,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as e:
        await websocket.send_json({"type": "error", "data": f"SSH connection failed: {e}"})
        await websocket.close()
        return

    # Open PTY channel
    chan = ssh.invoke_shell(term="xterm-256color", width=220, height=50)
    chan.setblocking(False)

    async def read_ssh():
        """Read from SSH channel and forward to WebSocket."""
        try:
            while True:
                await asyncio.sleep(0.02)
                if chan.recv_ready():
                    data = chan.recv(4096)
                    if not data:
                        break
                    await websocket.send_json({"type": "output", "data": data.decode("utf-8", errors="replace")})
                if chan.closed:
                    break
        except Exception:
            pass

    reader_task = asyncio.create_task(read_ssh())

    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "input":
                chan.send(msg["data"])
            elif msg.get("type") == "resize":
                w = msg.get("cols", 220)
                h = msg.get("rows", 50)
                chan.resize_pty(width=w, height=h)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Terminal error on {gpu_name}: {e}")
    finally:
        reader_task.cancel()
        chan.close()
        ssh.close()
        logger.info(f"Terminal session to {gpu_name} closed")
