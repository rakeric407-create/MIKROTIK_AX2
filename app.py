import os
import io
import csv
import urllib.parse
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, Response
from database import init_db, update_client_usage, edit_client_dates, add_days_to_client, get_client, get_all_clients, reset_daily

app = Flask(__name__)
init_db()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "382817100")
API_SECRET = os.environ.get("API_SECRET", "cle_secrete_12345")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8688609760:AAGu72P6OKNAxkXxUORGZHyfUj3PpHe-Mec")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MICTOTECK_301BOT")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WHATSAPP_PHONE = "261382817100"

def calc_days(date_fin_str):
    if not date_fin_str:
        return "Non defini"
    try:
        fin = datetime.strptime(date_fin_str, "%Y-%m-%d").date()
        diff = (fin - datetime.now().date()).days
        if diff > 0:
            return f"Reste {diff} j"
        elif diff == 0:
            return "Expire ce soir"
        else:
            return f"Expir ({abs(diff)} j)"
    except:
        return date_fin_str

def send_tg(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)

def send_admin_alert(username, bytes_used, limit_gb, client_type):
    if not ADMIN_CHAT_ID:
        return
    conso = round(bytes_used / 1073741824, 2)
    icon = "PPPoE" if client_type == "PPPoE" else "Hotspot"
    msg = (f"🚨 <b>ALERTE QUOTA DEPASSE !</b>\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"👤 <b>Client :</b> <code>{username}</code>\n"
           f"📡 <b>Type :</b> {icon}\n"
           f"📊 <b>Consomme :</b> <b>{conso} Go</b> / {limit_gb} Go\n"
           f"⏰ <b>Heure :</b> {datetime.now().strftime('%H:%M')}\n"
           f"━━━━━━━━━━━━━━━━━━━━\n"
           f"⚠️ <i>Limite journaliere atteinte.</i>")
    send_tg(ADMIN_CHAT_ID, msg)

# ============================================================
# DASHBOARD ADMIN
# ============================================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIKROTECK 301 - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
body{background:#0b0f19;color:#f1f5f9;font-family:system-ui,sans-serif;padding:20px}
.cs{background:#131c31;border:1px solid #1e293b;border-radius:14px;padding:18px}
.sv{font-size:2rem;font-weight:800}
.td{background:#131c31;border:1px solid #1e293b;border-radius:12px}
.sb{background:#131c31;color:white;border:1px solid #38bdf8;padding:12px 18px;border-radius:10px;width:100%;font-size:15px}
.sb:focus{outline:none;border-color:#00ff88;box-shadow:0 0 10px rgba(0,255,136,0.3)}
.bh{background:#0284c7;color:white;padding:5px 10px;border-radius:6px}
.bp{background:#7c3aed;color:white;padding:5px 10px;border-radius:6px}
.bf{background:#1e293b;color:#94a3b8;border:1px solid #334155;border-radius:8px}
.bf.active{background:#38bdf8;color:black;font-weight:bold}
.ar{background:rgba(239,68,68,0.15)!important;border-left:4px solid #ef4444}
.ab{background:linear-gradient(90deg,#b91c1c,#dc2626);color:white;padding:14px 20px;border-radius:12px;margin-bottom:20px;font-weight:bold;box-shadow:0 4px 15px rgba(220,38,38,0.4)}
</style>
</head>
<body>
<div class="container-fluid">
<div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
<div>
<h2 class="text-info fw-bold m-0"><i class="fa-solid fa-tower-broadcast"></i> MIKROTECK 301 Admin</h2>
<small class="text-secondary">Hotspot & PPPoE | 40 000 Ar / 30j | 05h-00h</small>
</div>
<div>
<a href="/admin/export-csv?pwd={{pwd}}" class="btn btn-success"><i class="fa-solid fa-file-excel"></i> Export</a>
<a href="/set-webhook?pwd={{pwd}}" class="btn btn-outline-info ms-1"><i class="fa-brands fa-telegram"></i> Bot</a>
</div>
</div>

{% if exceeded_count > 0 %}
<div class="ab d-flex align-items-center justify-content-between">
<span><i class="fa-solid fa-triangle-exclamation fa-lg me-2"></i> {{exceeded_count}} client(s) ont depasse 30 Go aujourd'hui !</span>
<button class="btn btn-sm btn-dark" onclick="setFilter('exceeded')">Voir</button>
</div>
{% endif %}

<div class="row g-3 mb-4">
<div class="col-md-3"><div class="cs"><span class="text-secondary"><i class="fa-solid fa-bolt text-warning"></i> Conso Aujourd'hui</span><div class="sv text-warning">{{"%.2f"|format(t_today)}} <small style="font-size:16px">Go</small></div></div></div>
<div class="col-md-3"><div class="cs"><span class="text-secondary"><i class="fa-solid fa-chart-pie text-success"></i> Conso ce Mois</span><div class="sv text-success">{{"%.2f"|format(t_month)}} <small style="font-size:16px">Go</small></div></div></div>
<div class="col-md-3"><div class="cs"><span class="text-secondary"><i class="fa-solid fa-users text-primary"></i> Clients</span><div class="sv text-info">{{clients|length}}</div><small class="text-secondary">Hotspot {{c_hs}} | PPPoE {{c_pp}}</small></div></div>
<div class="col-md-3"><div class="cs"><span class="text-secondary"><i class="fa-brands fa-whatsapp text-success"></i> Admin</span><div class="h5 mt-2 text-white font-monospace">+261 38 28 171 00</div><small class="text-success"><i class="fa-brands fa-telegram"></i> @{{bot}}</small></div></div>
</div>

<div class="row g-2 mb-3">
<div class="col-md-7"><input type="text" id="si" class="sb" placeholder="🔎 Chercher un client..." onkeyup="ft()"></div>
<div class="col-md-5 d-flex gap-1">
<button class="bf active flex-fill" id="ba" onclick="sf('all')">Tous ({{clients|length}})</button>
<button class="bf flex-fill" id="bhs" onclick="sf('Hotspot')">📶 HS</button>
<button class="bf flex-fill" id="bpp" onclick="sf('PPPoE')">🌐 PPP</button>
<button class="bf flex-fill text-danger fw-bold" id="bex" onclick="sf('exceeded')">⚠️ ({{exceeded_count}})</button>
</div>
</div>

<div class="table-responsive">
<table class="table table-dark table-hover align-middle mb-0 td" id="ct">
<thead><tr class="table-secondary text-dark">
<th>Type</th><th>Client</th><th>Aujourd'hui</th><th>Mois</th><th>Debut</th><th>Fin</th><th>Validite</th><th>Statut</th><th class="text-end">Actions</th>
</tr></thead>
<tbody>
{% for c in clients %}
{% set dg = c.daily_bytes / 1073741824 %}
{% set ex = dg >= c.limit_daily_gb %}
<tr class="client-row {{'ar' if ex else ''}}" data-type="{{c.client_type}}" data-ex="{{'y' if ex else 'n'}}">
<td>{% if c.client_type=='PPPoE' %}<span class="bp"><i class="fa-solid fa-network-wired"></i> PPPoE</span>{% else %}<span class="bh"><i class="fa-solid fa-wifi"></i> HS</span>{% endif %}</td>
<td class="cn fw-bold text-info">{{c.username}} {% if ex %}<span class="badge bg-danger ms-1">FUP</span>{% endif %}</td>
<td>{% if ex %}<span class="text-danger fw-bold"><i class="fa-solid fa-triangle-exclamation"></i> {{"%.2f"|format(dg)}} / {{c.limit_daily_gb}} Go</span>{% else %}{{"%.2f"|format(dg)}} / {{c.limit_daily_gb}} Go{% endif %}</td>
<td class="text-success fw-bold font-monospace">{{"%.2f"|format(c.monthly_bytes/1073741824)}} Go</td>
<td>{{c.date_debut or '---'}}</td>
<td>{{c.date_fin or '---'}}</td>
<td><span class="badge bg-dark border p-2">{{cd(c.date_fin)}}</span></td>
<td>{% if c.status=='active' %}<span class="badge bg-success">Actif</span>{% else %}<span class="badge bg-danger">Suspendu</span>{% endif %}</td>
<td class="text-end">
<a href="/admin/quick-renew?username={{c.username}}&pwd={{pwd}}" class="btn btn-sm btn-outline-success me-1">+30j</a>
<a href="/admin/edit?username={{c.username}}&pwd={{pwd}}" class="btn btn-sm btn-primary">✏️</a>
</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>
<script>
let cf='all';
function sf(f){cf=f;document.querySelectorAll('.bf').forEach(b=>b.classList.remove('active'));
if(f==='all')document.getElementById('ba').classList.add('active');
if(f==='Hotspot')document.getElementById('bhs').classList.add('active');
if(f==='PPPoE')document.getElementById('bpp').classList.add('active');
if(f==='exceeded')document.getElementById('bex').classList.add('active');ft();}
function ft(){var s=document.getElementById('si').value.toLowerCase();
document.querySelectorAll('.client-row').forEach(r=>{
var n=r.querySelector('.cn').innerText.toLowerCase(),t=r.getAttribute('data-type'),e=r.getAttribute('data-ex');
var ms=n.indexOf(s)>-1||t.toLowerCase().indexOf(s)>-1;
var mf=cf==='all'||(cf==='Hotspot'&&t==='Hotspot')||(cf==='PPPoE'&&t==='PPPoE')||(cf==='exceeded'&&e==='y');
r.style.display=ms&&mf?'':'none';});}
</script>
</body>
</html>
"""

# ============================================================
# PAGE EDITION CLIENT
# ============================================================
EDIT_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Modifier {{c.username}}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0b0f19;color:#f1f5f9;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
.ec{background:#131c31;border:1px solid #1e293b;border-radius:16px;padding:30px;width:100%;max-width:500px;box-shadow:0 10px 30px rgba(0,0,0,0.5)}
.fc,.fs{background:#0b0f19;color:white;border:1px solid #334155;padding:10px;border-radius:8px}
.fc:focus,.fs:focus{background:#0b0f19;color:white;border-color:#38bdf8}
.bq{background:#1e293b;color:#38bdf8;border:1px solid #334155;font-size:13px;padding:4px 10px;border-radius:6px;cursor:pointer;margin-top:5px}
</style>
</head>
<body>
<div class="ec">
<h3 class="text-info fw-bold mb-1">✏️ Modifier Client</h3>
<p class="text-secondary mb-4">Compte : <b class="text-warning font-monospace" style="font-size:18px">{{c.username}}</b></p>
<form action="/admin/edit-client" method="POST">
<input type="hidden" name="pwd" value="{{pwd}}">
<input type="hidden" name="username" value="{{c.username}}">
<div class="mb-3"><label class="form-label text-secondary">Type :</label>
<select name="client_type" class="fs"><option value="Hotspot" {%if c.client_type=='Hotspot'%}selected{%endif%}>📶 Hotspot</option><option value="PPPoE" {%if c.client_type=='PPPoE'%}selected{%endif%}>🌐 PPPoE</option></select></div>
<div class="mb-3"><label class="form-label text-secondary">Date Debut :</label><input type="date" name="date_debut" class="fc" value="{{c.date_debut}}"></div>
<div class="mb-3"><label class="form-label text-secondary">Date Fin :</label><input type="date" id="df" name="date_fin" class="fc" value="{{c.date_fin}}">
<div><button type="button" class="bq" onclick="qd(30)">+30j</button> <button type="button" class="bq" onclick="qd(60)">+60j</button> <button type="button" class="bq" onclick="qd(90)">+90j</button></div></div>
<div class="mb-3"><label class="form-label text-secondary">Quota Jour (Go) :</label><input type="number" name="limit_daily_gb" class="fc" value="{{c.limit_daily_gb}}"></div>
<div class="mb-4"><label class="form-label text-secondary">Statut :</label>
<select name="status" class="fs"><option value="active" {%if c.status=='active'%}selected{%endif%}>🟢 Actif</option><option value="blocked" {%if c.status=='blocked'%}selected{%endif%}>🔴 Suspendu</option></select></div>
<div class="d-flex gap-2">
<a href="/admin?pwd={{pwd}}" class="btn btn-secondary flex-fill">Annuler</a>
<button type="submit" class="btn btn-success flex-fill fw-bold">💾 Enregistrer</button>
</div>
</form>
</div>
<script>function qd(d){let x=new Date();x.setDate(x.getDate()+d);document.getElementById('df').value=x.toISOString().split('T')[0];}</script>
</body>
</html>
"""

# ============================================================
# PAGE CLIENT STATUT
# ============================================================
CLIENT_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIKROTECK 301 - Solde</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
body{font-family:system-ui,sans-serif;background:#070b14;color:white;text-align:center;padding:25px 15px;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:#0f172a;width:100%;max-width:420px;padding:30px 20px;border-radius:20px;border:1px solid #1e293b;box-shadow:0 10px 30px rgba(0,0,0,0.6)}
.val{font-size:32px;font-weight:800;color:#38bdf8;margin:6px 0}
.val.danger{color:#ef4444}
.vm{font-size:32px;font-weight:800;color:#4ade80;margin:6px 0}
.bb{background:#1e293b;height:16px;border-radius:8px;overflow:hidden;margin:12px 0}
.bf{background:linear-gradient(90deg,#38bdf8,#00ff88);height:100%}
.bf.danger{background:linear-gradient(90deg,#f87171,#ef4444)}
.bt{background:#1e293b;padding:6px 14px;border-radius:20px;border:1px solid #38bdf8;font-size:14px;display:inline-block;margin-bottom:10px}
.ic{background:#131d33;padding:14px;border-radius:12px;border:1px solid #334155;margin:15px 0}
.ab{background:rgba(239,68,68,0.15);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:12px;margin-bottom:15px;font-size:14px}
.btn{display:flex;align-items:center;justify-content:center;gap:8px;padding:12px;border-radius:10px;text-decoration:none;font-weight:bold;margin-top:10px;font-size:15px;color:white}
.btg{background:#0088cc}.bwa{background:#25D366}
</style>
</head>
<body>
<div class="box">
<div class="bt"><i class="fa-solid fa-signal text-info"></i> {{client.client_type}}</div>
<h2 style="color:#facc15;margin:0 0 15px">👤 {{client.username}}</h2>
{% if is_ex %}<div class="ab"><i class="fa-solid fa-triangle-exclamation"></i> <b>Quota Journalier Atteint !</b><br>Debit reduit (FUP). Renouvellement a 00h00.</div>{% endif %}
<p style="margin:0;color:#94a3b8;font-size:14px">Aujourd'hui :</p>
<div class="val {{'danger' if is_ex else ''}}">{{"%.2f"|format(dg)}} <small style="font-size:16px;color:#94a3b8">/ {{client.limit_daily_gb}} Go</small></div>
<div class="bb"><div class="bf {{'danger' if is_ex else ''}}" style="width:{{dp}}%"></div></div>
<p style="margin:15px 0 0;color:#94a3b8;font-size:14px">Total ce Mois :</p>
<div class="vm">{{"%.2f"|format(mg)}} <small style="font-size:16px">Go</small></div>
<div class="ic">📅 Abonnement : <b>{{dl}}</b><br><small style="color:#94a3b8">Expire : {{client.date_fin or 'Non defini'}}</small></div>
<a class="btn btg" href="https://t.me/{{bot}}?start={{client.username}}"><i class="fa-brands fa-telegram"></i> Telegram</a>
<a class="btn bwa" href="https://wa.me/{{wa}}?text={{wm}}" target="_blank"><i class="fa-brands fa-whatsapp"></i> WhatsApp Admin</a>
</div>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================
@app.route("/admin")
def admin():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "<h2>🔒 Mot de passe incorrect</h2>", 403
    clients = get_all_clients()
    chs = sum(1 for c in clients if c.get("client_type") == "Hotspot")
    cpp = sum(1 for c in clients if c.get("client_type") == "PPPoE")
    tt = sum(c['daily_bytes'] for c in clients) / 1073741824
    tm = sum(c['monthly_bytes'] for c in clients) / 1073741824
    ec = sum(1 for c in clients if (c['daily_bytes']/1073741824) >= (c['limit_daily_gb'] or 30))
    return render_template_string(DASHBOARD_HTML, clients=clients, pwd=pwd, c_hs=chs, c_pp=cpp,
                                  t_today=tt, t_month=tm, exceeded_count=ec, cd=calc_days, bot=BOT_USERNAME)

@app.route("/admin/edit")
def edit_page():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Acces refuse", 403
    c = get_client(request.args.get("username"))
    if not c:
        return "Client introuvable", 404
    return render_template_string(EDIT_HTML, c=c, pwd=pwd)

@app.route("/admin/edit-client", methods=["POST"])
def edit_client():
    pwd = request.form.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Acces refuse", 403
    edit_client_dates(request.form.get("username"), request.form.get("date_debut"),
                      request.form.get("date_fin"), int(request.form.get("limit_daily_gb") or 30),
                      request.form.get("client_type") or "Hotspot", request.form.get("status") or "active")
    return redirect(f"/admin?pwd={pwd}")

@app.route("/admin/quick-renew")
def quick_renew():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Acces refuse", 403
    add_days_to_client(request.args.get("username"), 30)
    return redirect(f"/admin?pwd={pwd}")

@app.route("/admin/export-csv")
def export_csv():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Acces refuse", 403
    clients = get_all_clients()
    o = io.StringIO()
    w = csv.writer(o, delimiter=';')
    w.writerow(["Type","Client","Jour Go","Mois Go","Debut","Fin","Validite","Statut","Synchro"])
    for c in clients:
        w.writerow([c['client_type'], c['username'], round(c['daily_bytes']/1073741824,2),
                    round(c['monthly_bytes']/1073741824,2), c['date_debut'], c['date_fin'],
                    calc_days(c['date_fin']), c['status'], c['last_update']])
    o.seek(0)
    return Response(o.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename=rapport_{datetime.now().strftime('%Y_%m_%d')}.csv"})

@app.route("/status/<username>")
def status(username):
    c = get_client(username)
    if not c:
        return "<h3>Client introuvable</h3>"
    dg = c["daily_bytes"]/1073741824
    mg = c["monthly_bytes"]/1073741824
    lim = c["limit_daily_gb"] or 30
    dp = min(100, (dg/lim)*100)
    ie = dg >= lim
    wm = urllib.parse.quote(f"Bonjour, je souhaite recharger le compte : {username}")
    return render_template_string(CLIENT_HTML, client=c, dg=dg, mg=mg, dp=dp, is_ex=ie,
                                  dl=calc_days(c["date_fin"]), bot=BOT_USERNAME, wa=WHATSAPP_PHONE, wm=wm)

# ============================================================
# BOT TELEGRAM WEBHOOK
# ============================================================
@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    update = request.get_json() or {}
    if "callback_query" in update:
        cb = update["callback_query"]
        cid = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        if data == "tuto":
            send_tg(cid, "📖 <b>TUTORIEL :</b>\n\n👉 Tapez votre identifiant WiFi ou PPPoE dans ce chat pour voir votre solde !\n\n💰 Tarif : 40 000 Ar / 30 jours\n📊 Quota : 30 Go / jour\n⏰ Horaires : 05h00 - 00h00")
        elif data == "contact":
            send_tg(cid, f"📞 <b>SUPPORT :</b>\n\nWhatsApp : +261 38 28 171 00\nMvola : 038 28 171 00\nAdmin : Jean Eric")
        return jsonify({"status": "ok"})

    if "message" in update:
        msg = update["message"]
        cid = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1:
                reply_stats(cid, parts[1])
            else:
                kb = {"inline_keyboard": [[{"text": "📖 Tutoriel", "callback_data": "tuto"}], [{"text": "📞 Contact Admin", "callback_data": "contact"}]]}
                send_tg(cid, "👋 <b>Bienvenue sur MIKROTECK 301 !</b>\n\n👉 Envoyez votre identifiant pour voir votre solde.", kb)
        elif text.startswith("/myid"):
            send_tg(cid, f"🆔 Votre Chat ID : <code>{cid}</code>")
        else:
            reply_stats(cid, text)
    return jsonify({"status": "ok"})

def reply_stats(cid, username):
    c = get_client(username)
    if c:
        dg = round(c['daily_bytes']/1073741824, 2)
        mg = round(c['monthly_bytes']/1073741824, 2)
        icon = "PPPoE" if c.get('client_type') == 'PPPoE' else "Hotspot"
        st = "🔴 FUP (Debit reduit)" if dg >= c['limit_daily_gb'] else "🟢 En ligne"
        send_tg(cid, f"📊 <b>SOLDE : {c['username']}</b> ({icon})\n━━━━━━━━━━━━━━━━━━━━\n📅 Aujourd'hui : {dg} / {c['limit_daily_gb']} Go\n📆 Mois : {mg} Go\n⏳ Abonnement : {calc_days(c['date_fin'])}\n🏁 Expire : {c['date_fin'] or 'Non defini'}\n━━━━━━━━━━━━━━━━━━━━\nStatut : {st}")
    else:
        send_tg(cid, f"❌ Compte '{username}' introuvable.")

@app.route("/set-webhook")
def set_webhook():
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://mikrotik-ax2.onrender.com/webhook/telegram").json()
    return f"<h3>Webhook :</h3><pre>{res}</pre><br><a href='/admin?pwd={request.args.get('pwd')}'>Retour</a>"

# ============================================================
# API MIKROTIK
# ============================================================
@app.route("/api/update", methods=["POST"])
def api_update():
    data = request.json or {}
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "unauthorized"}), 403
    for u in data.get("users", []):
        sa, tb, lg, ct = update_client_usage(u["username"], u["bytes"], u.get("type", "Hotspot"))
        if sa:
            send_admin_alert(u["username"], tb, lg, ct)
    return jsonify({"status": "ok"})

@app.route("/api/reset-daily", methods=["POST"])
def api_reset():
    data = request.json or {}
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "unauthorized"}), 403
    reset_daily()
    return jsonify({"status": "reset done"})

# ============================================================
# API CHAT CLIENT / ACHETEUR (depuis le portail MikroTik)
# ============================================================
@app.route("/api/chat", methods=["POST"])
def client_chat():
    data = request.json or {}
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "unauthorized"}), 403
    username = data.get("username", "Inconnu")
    message = data.get("message", "")
    source = data.get("source", "status")
    if not message:
        return jsonify({"status": "empty"}), 400
    now = datetime.now().strftime("%H:%M")
    if source == "login":
        icon = "🛒"
        label = "ACHETEUR (Page Login)"
    else:
        icon = "💬"
        label = "CLIENT CONNECTE"
    alert = (f"{icon} <b>{label}</b>\n"
             f"━━━━━━━━━━━━━━━━━━━━\n"
             f"👤 <b>Nom :</b> <code>{username}</code>\n"
             f"⏰ <b>Heure :</b> {now}\n"
             f"━━━━━━━━━━━━━━━━━━━━\n"
             f"📩 <b>Message :</b>\n{message}\n"
             f"━━━━━━━━━━━━━━━━━━━━\n"
             f"💡 <i>Repondez via Telegram ou WhatsApp 038 28 171 00</i>")
    if ADMIN_CHAT_ID:
        send_tg(ADMIN_CHAT_ID, alert)
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    return "🔥 MIKROTECK 301 - ISP Manager Actif"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
