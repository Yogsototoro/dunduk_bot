import asyncio
import subprocess
import aiohttp
import socket
import psutil
from datetime import datetime, timedelta, timezone
from logger import log
from database_sqlite import db
from config import PRIMARY_ADMIN_USERNAME

MY_FINGERPRINT = "xV4C9jwt4YQm2/duSNidpA4wZYHK6d9GrqYpSd6swrQ"

async def get_system_info():
    """Gather current system snapshot."""
    try:
        # Interfaces
        addrs = psutil.net_if_addrs()
        iface = "ens3" if "ens3" in addrs else (list(addrs.keys())[0] if addrs else "unknown")
        ip = "unknown"
        if iface in addrs:
            for addr in addrs[iface]:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    break
        
        # Ports (listening)
        ports = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port not in [22, 8080]:
                ports.append(str(conn.laddr.port))
        
        return {
            "iface": f"{iface} ({ip})",
            "ports": ", ".join(ports[:5]) if ports else "None"
        }
    except:
        return {"iface": "unknown", "ports": "unknown"}

async def get_host_intel_v2(ip):
    intel = {
        "loc": "📍 Unknown", 
        "isp": "🏢 Unknown", 
        "rdns": "🌐 No PTR", 
        "org": "🏢 Unknown",
        "risk_score": "🟡 MED"
    }
    
    if ip in ["127.0.0.1", "64.188.72.234"]:
        return {"loc": "📍 VDS Local", "isp": "🏢 Internal", "rdns": "🌐 localhost", "org": "Internal", "risk_score": "🟢 LOW"}

    try:
        loop = asyncio.get_event_loop()
        rdns = await loop.run_in_executor(None, lambda: socket.gethostbyaddr(ip)[0])
        intel["rdns"] = f"🌐 {rdns}"
    except: pass

    try:
        async with aiohttp.ClientSession() as s:
            # Query ip-api for rich data
            async with s.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org,as,mobile,proxy,hosting") as r:
                d = await r.json()
                if d.get('status') == 'success':
                    intel["loc"] = f"📍 {d['country']}, {d['city']}"
                    intel["isp"] = f"🏢 {d['isp']} ({d['as']})"
                    intel["org"] = d.get('org', 'Unknown')
                    
                    # Basic risk heuristic
                    if d.get('proxy') or d.get('hosting'):
                        intel["risk_score"] = "🔴 HIGH (Proxy/Hosting)"
    except: pass
    
    return intel

async def monitor_auth_log(bot):
    log("🛡 SSH Security Monitor Active (Enhanced)")
    moscow_tz = timezone(timedelta(hours=3))
    
    # Cache admin chat id
    admin_data = db.get_user(PRIMARY_ADMIN_USERNAME)
    admin_chat_id = admin_data['user_id'] if admin_data else None
    
    try:
        # Re-verify admin chat ID on start
        if not admin_chat_id:
            from config import ADMIN_USERNAMES
            for admin_nick in ADMIN_USERNAMES:
                u = db.get_user(admin_nick)
                if u and u['user_id']:
                    admin_chat_id = u['user_id']
                    break

        proc = await asyncio.create_subprocess_exec(
            "journalctl", "-u", "ssh", "-n", "0", "-f", 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes: break
            line = line_bytes.decode('utf-8').strip()
            now = datetime.now(moscow_tz).strftime('%H:%M:%S')
            
            if "Accepted" in line:
                ip = line.split("from ")[1].split()[0]
                intel = await get_host_intel_v2(ip)
                is_me = MY_FINGERPRINT in line
                msg = (f"<b>🟢 SSH_AUTH_SUCCESS</b>\n"
                       f"<code>────────────────────</code>\n"
                       f"🕒 <b>Time:</b> <code>{now}</code>\n"
                       f"🌐 <b>IP:</b> <code>{ip}</code>\n"
                       f"{intel['rdns']}\n"
                       f"{intel['loc']}\n"
                       f"🛠 <b>Client:</b> <code>{'Termux' if is_me else 'Unknown'}</code>")
                if admin_chat_id: await bot.send_message(admin_chat_id, msg)

            elif "Failed password" in line:
                try:
                    is_inv = "invalid user" in line
                    user = line.split("user ")[1].split()[0] if is_inv else line.split("for ")[1].split()[0]
                    ip = line.split("from ")[1].split()[0]
                    port = line.split("port ")[1].split()[0]
                except: user, ip, port = "unknown", "unknown", "0"
                
                total = db.log_ssh_attack(ip)
                intel = await get_host_intel_v2(ip)
                sys_info = await get_system_info()
                
                # Heuristic risk calculation
                risk = intel['risk_score']
                if user == 'root': risk = "🔴 CRITICAL (Root Attempt)"
                elif total > 50: risk = "🔴 HIGH (Aggressive Brute)"
                
                alert = f"""<b>AUTH_FAILURE: {'INVALID' if is_inv else 'BRUTE'}</b>
<code>────────────────────</code>
🕒 <b>Time:</b> <code>{now} MSK</code>
👤 <b>Target:</b> <code>{user}</code>
🌐 <b>IP:</b> <a href='https://www.abuseipdb.com/check/{ip}'>{ip}</a>
{intel['rdns']}
{intel['loc']}
{intel['isp']}
<code>────────────────────</code>
💻 <b>System Info (Target):</b>
├ <b>Iface:</b> <code>{sys_info['iface']}</code>
└ <b>Other Ports:</b> <code>{sys_info['ports']}</code>
<code>────────────────────</code>
📊 <b>Intelligence:</b>
├ <b>History:</b> <code>{total} hits</code>
└ <b>Risk:</b> <code>{risk}</code>
ℹ️ <a href='https://scamalytics.com/ip/{ip}'>Scamalytics Report</a> | <a href='https://ipinfo.io/{ip}'>IPInfo</a>"""
                
                if admin_chat_id: 
                    try:
                        await bot.send_message(admin_chat_id, alert, disable_web_page_preview=True)
                    except Exception as e:
                        log(f"Error sending alert: {e}")
                        
    except Exception as e: 
        log(f"Monitor error: {e}")
