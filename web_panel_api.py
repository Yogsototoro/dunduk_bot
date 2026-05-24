import os
import hmac
import hashlib
from urllib.parse import parse_qs, unquote
from fastapi import FastAPI, Header, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, FileResponse
import psutil
from datetime import datetime
import sys
import json
import logging
import tarfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('web_panel')

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from database_sqlite import db
    from config import BOT_TOKEN, PRIMARY_ADMIN_USERNAME, PANEL_TOKEN
except ImportError as e:
    logger.error(f'Import error: {e}')
    sys.exit(1)

app = FastAPI()

def verify_access(init_data: str, token: str) -> bool:
    if token and token == PANEL_TOKEN: return True
    if init_data:
        try:
            params = dict(item.split('=', 1) for item in init_data.split('&'))
            received_hash = params.pop('hash', None)
            if received_hash:
                data_check_string = '\n'.join([f'{k}={unquote(params[k])}' for k in sorted(params.keys())])
                secret_key = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
                calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
                if calc_hash == received_hash: return True
        except: pass
    return False

@app.get('/', response_class=HTMLResponse)
async def get_index():
    path = os.path.join(current_dir, 'web', 'index.html')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read()
    return 'Index not found'

@app.get('/api/data')
async def get_data(initData: str = Query(None), token: str = Query(None)):
    if not verify_access(initData, token): raise HTTPException(status_code=403)
    
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/')
    uptime = str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0]
    
    listening_procs = {}
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.status == 'LISTEN':
                    listening_procs[conn.laddr.port] = proc.info['name']
        except: pass

    active_ports = {}
    for conn in psutil.net_connections(kind='inet'):
        if conn.status == 'ESTABLISHED' and conn.laddr.port:
            port = conn.laddr.port
            if port in listening_procs or port in [22, 2040, 8080, 8000]:
                if port not in active_ports:
                    active_ports[port] = {'port': port, 'conns': 0, 'ips': set(), 'name': listening_procs.get(port, 'unknown')}
                active_ports[port]['conns'] += 1
                if conn.raddr: active_ports[port]['ips'].add(conn.raddr.ip)

    port_list = []
    for p in active_ports.values():
        p['ips'] = len(p['ips'])
        port_list.append(p)
    
    participants = []
    for username in db.get_participants():
        u_row = db.get_user(username)
        participants.append({'username': username, 'is_dunduk': bool(dict(u_row).get('is_dunduk', False)) if u_row else False})
    
    attacks = []
    attacks_cursor = db._execute('SELECT ip, count, last_attack FROM ssh_attacks ORDER BY count DESC LIMIT 15')
    if attacks_cursor: attacks = [dict(row) for row in attacks_cursor.fetchall()]

    return {
        'stats': {'cpu': cpu, 'ram': ram, 'disk_free': round(disk.free / (1024**3), 1), 'uptime': uptime},
        'config': {'location': db.get_location(), 'schedule': db.get_schedule(), 'limit': db.get_max_participants(), 'is_cancelled': bool(db.is_mece_cancelled())},
        'participants': participants,
        'attacks': attacks,
        'ports': sorted(port_list, key=lambda x: x['conns'], reverse=True)
    }

@app.post('/api/action')
async def bot_action(initData: str = Query(None), token: str = Query(None), data: dict = Body(...)):
    if not verify_access(initData, token): raise HTTPException(status_code=403)
    action = data.get('action')
    val = data.get('value')
    if action == 'set_location': db.set_location(val)
    elif action == 'set_schedule': db.set_schedule(val)
    elif action == 'toggle_cancel':
        if db.is_mece_cancelled(): db.uncancel_mece()
        else: db.cancel_mece()
    elif action == 'toggle_dunduk':
        u = db.get_user(val)
        db.set_dunduk(val, not dict(u).get('is_dunduk', False) if u else True)
    elif action == 'restart_bot': os.system('pkill -9 -f bot.py')
    elif action == 'get_logs':
        log_path = os.path.join(current_dir, 'logs', 'bot.log')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                return {'status': 'ok', 'logs': ''.join(f.readlines()[-50:])}
    return {'status': 'ok'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8080)
