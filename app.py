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
WHATSAPP_PHONE = "261382817100"

def calculate_days_left(date_fin_str):
    if not date_fin_str:
        return "Non défini"
    try:
        fin = datetime.strptime(date_fin_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        diff = (fin - today).days
        if diff > 0:
            return f"🟢 Reste {diff} j"
        elif diff == 0:
            return "🟡 Expire ce soir"
        else:
            return f"🔴 Expiré ({abs(diff)} j)"
    except:
        return date_fin_str

# --- DASHBOARD ADMIN PRO AVEC POPUPS 100% FONCTIONNELLES ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <title>ISP Manager Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: #0b0f19; color: #f1f5f9; font-family: system-ui, -apple-system, sans-serif; padding: 20px; }
        .card-stat { background: #131c31; border: 1px solid #1e293b; border-radius: 14px; padding: 18px; }
        .stat-val { font-size: 2rem; font-weight: 800; color: #38bdf8; }
        .table-dark { background: #131c31; border: 1px solid #1e293b; border-radius: 12px; }
        .search-box { background: #131c31; color: white; border: 1px solid #38bdf8; padding: 12px 18px; border-radius: 10px; width: 100%; font-size: 15px; }
        .search-box:focus { outline: none; border-color: #00ff88; }
        .badge-hotspot { background: #0284c7; color: white; }
        .badge-pppoe { background: #7c3aed; color: white; }
        .modal-content { background: #131c31; color: white; border: 1px solid #334155; border-radius: 16px; }
        .form-control, .form-select { background: #0b0f19; color: white; border: 1px solid #334155; }
        .form-control:focus { background: #0b0f19; color: white; }
        .btn-filter { background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 8px; }
        .btn-filter.active { background: #38bdf8; color: black; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Header -->
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
            <div>
                <h2 class="text-info fw-bold m-0"><i class="fa-solid fa-tower-broadcast"></i> ISP Hotspot & PPPoE Manager</h2>
                <small class="text-secondary">MikroTik hAP ax2 Control Center</small>
            </div>
            <div>
                <a href="/admin/export-csv?pwd={{ pwd }}" class="btn btn-success"><i class="fa-solid fa-file-excel"></i> Export Excel</a>
                <a href="/set-webhook?pwd={{ pwd }}" class="btn btn-outline-info ms-1"><i class="fa-brands fa-telegram"></i> Synchro Bot</a>
            </div>
        </div>

        <!-- 4 Stats Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card-stat">
                    <span class="text-secondary"><i class="fa-solid fa-bolt text-warning"></i> Conso Réseau Aujourd'hui</span>
                    <div class="stat-val text-warning">{{ "%.2f"|format(total_bandwidth_today) }} <small style="font-size:16px;">Go</small></div>
                    <small class="text-secondary">Total Hotspot + PPPoE du jour</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card-stat">
                    <span class="text-secondary"><i class="fa-solid fa-chart-pie text-success"></i> Conso Réseau ce Mois</span>
                    <div class="stat-val text-success">{{ "%.2f"|format(total_bandwidth_month) }} <small style="font-size:16px;">Go</small></div>
                    <small class="text-secondary">Cumul total mensuel</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card-stat">
                    <span class="text-secondary"><i class="fa-solid fa-users text-primary"></i> Total Clients</span>
                    <div class="stat-val text-info">{{ clients|length }}</div>
                    <small class="text-secondary">📶 {{ count_hotspot }} Hotspot | 🌐 {{ count_pppoe }} PPPoE</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card-stat">
                    <span class="text-secondary"><i class="fa-brands fa-whatsapp text-success"></i> WhatsApp Admin</span>
                    <div class="h5 mt-2 text-white font-monospace">+261 38 28 171 00</div>
                    <small class="text-success"><i class="fa-brands fa-telegram"></i> @{{ bot_name }}</small>
                </div>
            </div>
        </div>

        <!-- Recherche & Filtres -->
        <div class="row g-2 mb-3">
            <div class="col-md-8">
                <input type="text" id="searchInput" class="search-box" placeholder="🔎 Chercher un client par son nom ou son type..." onkeyup="filterTable()">
            </div>
            <div class="col-md-4 d-flex gap-1">
                <button class="btn btn-filter active flex-fill" onclick="setFilter('all')">Tous ({{ clients|length }})</button>
                <button class="btn btn-filter flex-fill" onclick="setFilter('Hotspot')">📶 Hotspot</button>
                <button class="btn btn-filter flex-fill" onclick="setFilter('PPPoE')">🌐 PPPoE</button>
            </div>
        </div>

        <!-- Tableau -->
        <div class="table-responsive">
            <table class="table table-dark table-hover align-middle mb-0" id="clientsTable">
                <thead>
                    <tr class="table-secondary text-dark">
                        <th>Type</th>
                        <th>Identifiant</th>
                        <th>Aujourd'hui</th>
                        <th>Total Mois</th>
                        <th>Date Début</th>
                        <th>Date Fin</th>
                        <th>Validité</th>
                        <th>Statut</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in clients %}
                    <tr class="client-row" data-type="{{ c.client_type }}">
                        <td>
                            {% if c.client_type == 'PPPoE' %}
                                <span class="badge badge-pppoe"><i class="fa-solid fa-network-wired"></i> PPPoE</span>
                            {% else %}
                                <span class="badge badge-hotspot"><i class="fa-solid fa-wifi"></i> Hotspot</span>
                            {% endif %}
                        </td>
                        <td class="client-name fw-bold text-info">{{ c.username }}</td>
                        <td>{{ "%.2f"|format(c.daily_bytes / 1073741824) }} Go / {{ c.limit_daily_gb }} Go</td>
                        <td class="text-success fw-bold font-monospace">{{ "%.2f"|format(c.monthly_bytes / 1073741824) }} Go</td>
                        <td>{{ c.date_debut or '---' }}</td>
                        <td>{{ c.date_fin or '---' }}</td>
                        <td><span class="badge bg-dark border p-2">{{ calc_days(c.date_fin) }}</span></td>
                        <td>
                            {% if c.status == 'active' %}
                                <span class="badge bg-success">Actif</span>
                            {% else %}
                                <span class="badge bg-danger">Suspendu</span>
                            {% endif %}
                        </td>
                        <td class="text-end">
                            <a href="/admin/quick-renew?username={{ c.username }}&pwd={{ pwd }}" class="btn btn-sm btn-outline-success me-1" title="+30 Jours">
                                ➕ +30j
                            </a>
                            <button type="button" class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#editModal{{ loop.index }}">
                                ✏️ Modifier
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- MODALS HORS DU TABLEAU POUR FONCTIONNER A 100% -->
    {% for c in clients %}
    <div class="modal fade" id="editModal{{ loop.index }}" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <form action="/admin/edit-client" method="POST">
                    <input type="hidden" name="pwd" value="{{ pwd }}">
                    <input type="hidden" name="username" value="{{ c.username }}">
                    <div class="modal-header">
                        <h5 class="modal-title">Gérer le compte : <span class="text-info">{{ c.username }}</span></h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Type de Connexion :</label>
                            <select name="client_type" class="form-select">
                                <option value="Hotspot" {% if c.client_type == 'Hotspot' %}selected{% endif %}>📶 Hotspot (WiFi Zone)</option>
                                <option value="PPPoE" {% if c.client_type == 'PPPoE' %}selected{% endif %}>🌐 PPPoE (Routeur / Foyer)</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Date Début d'Abonnement :</label>
                            <input type="date" name="date_debut" class="form-control" value="{{ c.date_debut }}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Date Fin d'Abonnement :</label>
                            <input type="date" name="date_fin" class="form-control" value="{{ c.date_fin }}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Quota Quotidien (Go) :</label>
                            <input type="number" name="limit_daily_gb" class="form-control" value="{{ c.limit_daily_gb }}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Statut :</label>
                            <select name="status" class="form-select">
                                <option value="active" {% if c.status == 'active' %}selected{% endif %}>🟢 Actif</option>
                                <option value="blocked" {% if c.status == 'blocked' %}selected{% endif %}>🔴 Suspendu</option>
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="submit" class="btn btn-success">Enregistrer les Modifications</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    {% endfor %}

    <!-- Scripts Filtre & Recherche -->
    <script>
        let currentTypeFilter = 'all';

        function setFilter(type) {
            currentTypeFilter = type;
            document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            filterTable();
        }

        function filterTable() {
            var search = document.getElementById("searchInput").value.toLowerCase();
            var rows = document.querySelectorAll(".client-row");

            rows.forEach(function(row) {
                var name = row.querySelector(".client-name").innerText.toLowerCase();
                var type = row.getAttribute("data-type");

                var matchesSearch = name.indexOf(search) > -1 || type.toLowerCase().indexOf(search) > -1;
                var matchesType = (currentTypeFilter === 'all' || type === currentTypeFilter);

                if (matchesSearch && matchesType) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/admin")
def admin():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "<h2>🔒 Mot de passe incorrect</h2>", 403
    clients = get_all_clients()
    today = datetime.now().strftime("%Y-%m-%d")
    
    count_hotspot = sum(1 for c in clients if c.get("client_type") == "Hotspot")
    count_pppoe = sum(1 for c in clients if c.get("client_type") == "PPPoE")
    total_today = sum(c['daily_bytes'] for c in clients) / 1073741824
    total_month = sum(c['monthly_bytes'] for c in clients) / 1073741824
    
    return render_template_string(DASHBOARD_HTML, clients=clients, pwd=pwd, today_date=today, 
                                  count_hotspot=count_hotspot, count_pppoe=count_pppoe,
                                  total_bandwidth_today=total_today, total_bandwidth_month=total_month,
                                  calc_days=calculate_days_left, bot_name=BOT_USERNAME)

@app.route("/admin/quick-renew")
def quick_renew():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Accès refusé", 403
    uname = request.args.get("username")
    add_days_to_client(uname, 30)
    return redirect(f"/admin?pwd={pwd}")

@app.route("/admin/edit-client", methods=["POST"])
def edit_client():
    pwd = request.form.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Accès refusé", 403
    uname = request.form.get("username")
    d_deb = request.form.get("date_debut")
    d_fin = request.form.get("date_fin")
    lim = int(request.form.get("limit_daily_gb") or 30)
    ctype = request.form.get("client_type") or "Hotspot"
    st = request.form.get("status") or "active"
    edit_client_dates(uname, d_deb, d_fin, lim, ctype, st)
    return redirect(f"/admin?pwd={pwd}")

@app.route("/admin/export-csv")
def export_csv():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Accès refusé", 403
    clients = get_all_clients()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Type", "Client", "Conso Jour (Go)", "Conso Mois (Go)", "Date Debut", "Date Fin", "Validite", "Statut", "Derniere Synchro"])
    
    for c in clients:
        d_go = round(c['daily_bytes'] / 1073741824, 2)
        m_go = round(c['monthly_bytes'] / 1073741824, 2)
        val = calculate_days_left(c['date_fin'])
        writer.writerow([c['client_type'], c['username'], d_go, m_go, c['date_debut'], c['date_fin'], val, c['status'], c['last_update']])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=rapport_isp_{datetime.now().strftime('%Y_%m_%d')}.csv"}
    )

# --- PAGE CLIENT STATUT ---
CLIENT_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <title>Espace Client WiFi & Fibre</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #070b14; color: white; text-align: center; padding: 25px 15px; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .box { background: #0f172a; width: 100%; max-width: 420px; padding: 30px 20px; border-radius: 20px; border: 1px solid #1e293b; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
        .val { font-size: 32px; font-weight: 800; color: #38bdf8; margin: 6px 0; }
        .val-month { font-size: 32px; font-weight: 800; color: #4ade80; margin: 6px 0; }
        .bar-bg { background: #1e293b; height: 16px; border-radius: 8px; overflow: hidden; margin: 12px 0; }
        .bar-fill { background: linear-gradient(90deg, #38bdf8, #00ff88); height: 100%; }
        .badge-type { background: #1e293b; padding: 6px 14px; border-radius: 20px; border: 1px solid #38bdf8; font-size: 14px; display: inline-block; margin-bottom: 10px; }
        .info-card { background: #131d33; padding: 14px; border-radius: 12px; border: 1px solid #334155; margin: 15px 0; }
        .btn-tg { display: flex; align-items: center; justify-content: center; gap: 8px; background: #0088cc; color: white; padding: 12px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 12px; font-size: 15px; }
        .btn-wa { display: flex; align-items: center; justify-content: center; gap: 8px; background: #25D366; color: white; padding: 12px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 10px; font-size: 15px; }
    </style>
</head>
<body>
    <div class="box">
        <div class="badge-type">
            <i class="fa-solid fa-signal text-info"></i> Compte {{ client.client_type }}
        </div>
        <h2 style="color:#facc15; margin: 0 0 15px 0;">👤 {{ client.username }}</h2>
        
        <p style="margin: 0; color: #94a3b8; font-size: 14px;">Consommation Aujourd'hui :</p>
        <div class="val">{{ "%.2f"|format(daily_go) }} <small style="font-size:16px; color:#94a3b8;">/ {{ client.limit_daily_gb }} Go</small></div>
        <div class="bar-bg"><div class="bar-fill" style="width: {{ daily_pct }}%;"></div></div>
        
        <p style="margin: 15px 0 0 0; color: #94a3b8; font-size: 14px;">Total Consommé ce Mois :</p>
        <div class="val-month">{{ "%.2f"|format(monthly_go) }} <small style="font-size:16px;">Go</small></div>
        
        <div class="info-card">
            📅 Validité de l'Abonnement : <br>
            <b style="font-size: 17px; color: #f8fafc;">{{ days_left }}</b><br>
            <small style="color:#94a3b8;">Expire le : {{ client.date_fin or 'Non défini' }}</small>
        </div>
        
        <a class="btn-tg" href="https://t.me/{{ bot_name }}?start={{ client.username }}">
            <i class="fa-brands fa-telegram"></i> Suivre sur Telegram
        </a>

        <a class="btn-wa" href="https://wa.me/{{ wa_phone }}?text={{ wa_msg }}" target="_blank">
            <i class="fa-brands fa-whatsapp"></i> Recharger via WhatsApp
        </a>
    </div>
</body>
</html>
"""

@app.route("/status/<username>")
def status(username):
    client = get_client(username)
    if not client:
        return "<h3>❌ Utilisateur non trouvé.</h3>"
    daily_go = client["daily_bytes"] / 1073741824
    monthly_go = client["monthly_bytes"] / 1073741824
    lim = client["limit_daily_gb"] or 30
    daily_pct = min(100, (daily_go / lim) * 100)
    days_left = calculate_days_left(client["date_fin"])
    
    wa_msg = urllib.parse.quote(f"Bonjour, je souhaite recharger l'abonnement de mon compte : {username}")
    
    return render_template_string(CLIENT_HTML, client=client, daily_go=daily_go, monthly_go=monthly_go, 
                                  daily_pct=daily_pct, days_left=days_left, bot_name=BOT_USERNAME, 
                                  wa_phone=WHATSAPP_PHONE, wa_msg=wa_msg)

# --- BOT TELEGRAM ---
def send_telegram_msg(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)

@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    update = request.get_json() or {}
    
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        
        if data == "tuto":
            tuto_text = "📖 <b>GUIDE CLIENT :</b>\n\n👉 Tapez simplement votre identifiant WiFi ou PPPoE dans ce chat pour obtenir votre solde !"
            send_telegram_msg(chat_id, tuto_text)
        elif data == "contact":
            contact_text = f"📞 <b>SUPPORT :</b>\n\nWhatsApp Admin : +261 38 28 171 00"
            send_telegram_msg(chat_id, contact_text)
        return jsonify({"status": "ok"})

    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()

        if text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1:
                uname = parts[1]
                reply_client_stats(chat_id, uname)
            else:
                welcome_text = "👋 <b>Bienvenue sur votre Espace Télécom !</b>\n\n👉 Envoyez votre <b>identifiant client</b> pour voir votre solde en direct."
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📖 Guide & Aide", "callback_data": "tuto"}],
                        [{"text": "📞 Support WhatsApp", "callback_data": "contact"}]
                    ]
                }
                send_telegram_msg(chat_id, welcome_text, keyboard)
        else:
            reply_client_stats(chat_id, text)

    return jsonify({"status": "ok"})

def reply_client_stats(chat_id, username):
    c = get_client(username)
    if c:
        d_go = round(c['daily_bytes'] / 1073741824, 2)
        m_go = round(c['monthly_bytes'] / 1073741824, 2)
        val = calculate_days_left(c['date_fin'])
        icon = "🌐 PPPoE" if c.get('client_type') == 'PPPoE' else "📶 Hotspot"
        msg = (
            f"📊 <b>SOLDE : {c['username']}</b> ({icon})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Aujourd'hui :</b> {d_go} Go / {c['limit_daily_gb']} Go\n"
            f"📆 <b>Total ce mois :</b> {m_go} Go\n"
            f"⏳ <b>Abonnement :</b> {val}\n"
            f"🏁 <b>Date Expiration :</b> {c['date_fin'] or 'Non défini'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Statut : 🟢 En ligne"
        )
    else:
        msg = f"❌ Compte '{username}' introuvable."
    send_telegram_msg(chat_id, msg)

@app.route("/set-webhook")
def set_webhook():
    wh_url = f"https://mikrotik-ax2.onrender.com/webhook/telegram"
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={wh_url}").json()
    return f"<h3>Résultat Webhook :</h3><pre>{res}</pre><br><a href='/admin?pwd={request.args.get('pwd')}'>Retour au Dashboard</a>"

# --- API MIKROTIK ---
@app.route("/api/update", methods=["POST"])
def api_update():
    data = request.json or {}
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "unauthorized"}), 403
    for u in data.get("users", []):
        update_client_usage(u["username"], u["bytes"], u.get("type", "Hotspot"))
    return jsonify({"status": "ok"})

@app.route("/api/reset-daily", methods=["POST"])
def api_reset():
    data = request.json or {}
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "unauthorized"}), 403
    reset_daily()
    return jsonify({"status": "reset done"})

@app.route("/")
def index():
    return "🔥 ISP Hotspot & PPPoE Control Center Actif"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
