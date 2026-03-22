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


def get_user_by_cookie(cookie_header: str | None) -> User | None:
    """Extract user from session cookie (matches auth.py pattern)."""
    if not cookie_header:
        return None
    cookies = {}
    for item in cookie_header.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    api_key = cookies.get("session")
    if not api_key:
        return None
    db = SessionLocal()
    try:
        return db.query(User).filter(User.api_key == api_key, User.is_active == True).first()
    finally:
        db.close()


@router.websocket("/ws/{gpu_id}")
async def terminal_ws(websocket: WebSocket, gpu_id: int):
    """WebSocket SSH terminal session.

    Client sends text (keystrokes). Server sends back terminal output.
    Provides a real interactive PTY over SSH.
    """
    # Auth check — admin only
    cookie_header = websocket.headers.get("cookie")
    user = get_user_by_cookie(cookie_header)
    if not user or user.tier != "admin":
        await websocket.close(code=4003, reason="Admin only")
        return

    # Get GPU
    db = SessionLocal()
    try:
        gpu = db.query(GPU).filter(GPU.id == gpu_id).first()
        if not gpu:
            await websocket.close(code=4004, reason="GPU not found")
            return
        host = gpu.host
        port = gpu.port
        ssh_user = gpu.user
        password = gpu.password
    finally:
        db.close()

    await websocket.accept()

    # Connect SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname=host,
            port=port,
            username=ssh_user,
            password=password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as e:
        await websocket.send_json({"type": "error", "data": f"SSH connection failed: {e}"})
        await websocket.close()
        return

    # Open PTY channel
    chan = ssh.invoke_shell(term="xterm-256color", width=120, height=40)
    chan.setblocking(False)

    async def read_ssh():
        """Read from SSH channel and send to WebSocket."""
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
        except (WebSocketDisconnect, Exception):
            pass

    reader_task = asyncio.create_task(read_ssh())

    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "input":
                chan.send(msg["data"])
            elif msg.get("type") == "resize":
                w = msg.get("cols", 120)
                h = msg.get("rows", 40)
                chan.resize_pty(width=w, height=h)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Terminal error: {e}")
    finally:
        reader_task.cancel()
        chan.close()
        ssh.close()
