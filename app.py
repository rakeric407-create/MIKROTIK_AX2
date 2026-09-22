import os
import io
import csv
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

# --- DASHBOARD ADMIN PRO ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Hotspot Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0f172a; color: #f8fafc; padding: 20px; font-family: system-ui, sans-serif; }
        .card-stat { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 18px; }
        .table-dark { background: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; }
        .search-box { background: #1e293b; color: white; border: 2px solid #38bdf8; padding: 12px 20px; border-radius: 10px; font-size: 16px; width: 100%; }
        .search-box:focus { outline: none; background: #0f172a; color: white; border-color: #00ff88; }
        .modal-content { background: #1e293b; color: white; border: 1px solid #334155; }
        .form-control, .form-select { background: #0f172a; color: white; border: 1px solid #334155; }
        .form-control:focus { background: #0f172a; color: white; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Header -->
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
            <h2 class="text-info fw-bold m-0">📶 Hotspot Manager Pro</h2>
            <div>
                <a href="/admin/export-csv?pwd={{ pwd }}" class="btn btn-success me-2">📥 Export Excel / CSV</a>
                <a href="/set-webhook?pwd={{ pwd }}" class="btn btn-outline-info">🤖 Synchro Bot</a>
            </div>
        </div>

        <!-- Stats -->
        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card-stat">
                    <span class="text-secondary">Clients Enregistrés</span>
                    <h2 class="text-primary mt-1" id="totalClients">{{ clients|length }}</h2>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card-stat">
                    <span class="text-secondary">Date du Serveur</span>
                    <h2 class="text-warning mt-1">{{ today_date }}</h2>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card-stat">
                    <span class="text-secondary">Bot Telegram</span>
                    <h2 class="text-success mt-1">@{{ bot_name }}</h2>
                </div>
            </div>
        </div>

        <!-- Barre de recherche en direct -->
        <div class="mb-3">
            <input type="text" id="searchInput" class="search-box" placeholder="🔎 Tapez un nom de client pour chercher en direct..." onkeyup="filterTable()">
        </div>

        <!-- Tableau -->
        <div class="table-responsive">
            <table class="table table-dark table-hover align-middle" id="clientsTable">
                <thead>
                    <tr class="table-secondary text-dark">
                        <th>Client</th>
                        <th>Aujourd'hui</th>
                        <th>Cumul Mois</th>
                        <th>Début</th>
                        <th>Fin</th>
                        <th>Validité</th>
                        <th>Statut</th>
                        <th>Actions Rapides</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in clients %}
                    <tr>
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
                        <td>
                            <!-- Bouton +30 Jours -->
                            <a href="/admin/quick-renew?username={{ c.username }}&pwd={{ pwd }}" 
                               class="btn btn-sm btn-outline-success me-1" 
                               title="Ajouter 30 jours immédiatement">
                               ➕ +30 Jours
                            </a>

                            <!-- Bouton Modifier -->
                            <button class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#editModal{{ loop.index }}">
                                ✏️ Modifier
                            </button>

                            <!-- Modal Édition -->
                            <div class="modal fade" id="editModal{{ loop.index }}" tabindex="-1">
                                <div class="modal-dialog">
                                    <div class="modal-content">
                                        <form action="/admin/edit-client" method="POST">
                                            <input type="hidden" name="pwd" value="{{ pwd }}">
                                            <input type="hidden" name="username" value="{{ c.username }}">
                                            <div class="modal-header">
                                                <h5 class="modal-title">Client : {{ c.username }}</h5>
                                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                            </div>
                                            <div class="modal-body">
                                                <div class="mb-3">
                                                    <label>Date Début :</label>
                                                    <input type="date" name="date_debut" class="form-control" value="{{ c.date_debut }}">
                                                </div>
                                                <div class="mb-3">
                                                    <label>Date Fin :</label>
                                                    <input type="date" name="date_fin" class="form-control" value="{{ c.date_fin }}">
                                                </div>
                                                <div class="mb-3">
                                                    <label>Limite Quotidienne (Go) :</label>
                                                    <input type="number" name="limit_daily_gb" class="form-control" value="{{ c.limit_daily_gb }}">
                                                </div>
                                                <div class="mb-3">
                                                    <label>Statut :</label>
                                                    <select name="status" class="form-select">
                                                        <option value="active" {% if c.status == 'active' %}selected{% endif %}>Actif</option>
                                                        <option value="blocked" {% if c.status == 'blocked' %}selected{% endif %}>Suspendu</option>
                                                    </select>
                                                </div>
                                            </div>
                                            <div class="modal-footer">
                                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                                                <button type="submit" class="btn btn-success">Sauvegarder</button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Script de recherche en direct -->
    <script>
        function filterTable() {
            var input = document.getElementById("searchInput");
            var filter = input.value.toLowerCase();
            var table = document.getElementById("clientsTable");
            var tr = table.getElementsByTagName("tr");

            for (var i = 1; i < tr.length; i++) {
                var td = tr[i].getElementsByClassName("client-name")[0];
                if (td) {
                    var txtValue = td.textContent || td.innerText;
                    if (txtValue.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
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
    return render_template_string(DASHBOARD_HTML, clients=clients, pwd=pwd, today_date=today, calc_days=calculate_days_left, bot_name=BOT_USERNAME)

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
    st = request.form.get("status") or "active"
    edit_client_dates(uname, d_deb, d_fin, lim, st)
    return redirect(f"/admin?pwd={pwd}")

@app.route("/admin/export-csv")
def export_csv():
    pwd = request.args.get("pwd")
    if pwd != ADMIN_PASSWORD and pwd != "mon_mot_de_passe_secret":
        return "Accès refusé", 403
    clients = get_all_clients()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Client", "Conso Jour (Go)", "Conso Mois (Go)", "Date Debut", "Date Fin", "Validite", "Statut", "Derniere Synchro"])
    
    for c in clients:
        d_go = round(c['daily_bytes'] / 1073741824, 2)
        m_go = round(c['monthly_bytes'] / 1073741824, 2)
        val = calculate_days_left(c['date_fin'])
        writer.writerow([c['username'], d_go, m_go, c['date_debut'], c['date_fin'], val, c['status'], c['last_update']])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=rapport_hotspot_{datetime.now().strftime('%Y_%m_%d')}.csv"}
    )

# --- PAGE CLIENT STATUT ---
CLIENT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mon Solde WiFi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: system-ui, sans-serif; background: #0f172a; color: white; text-align: center; padding: 20px; }
        .box { background: #1e293b; max-width: 420px; margin: auto; padding: 25px; border-radius: 16px; border: 1px solid #334155; }
        .val { font-size: 28px; font-weight: bold; color: #38bdf8; margin: 8px 0; }
        .val-month { font-size: 28px; font-weight: bold; color: #4ade80; margin: 8px 0; }
        .bar-bg { background: #334155; height: 16px; border-radius: 8px; overflow: hidden; margin: 12px 0; }
        .bar-fill { background: #38bdf8; height: 100%; }
        .badge { background: #0f172a; padding: 10px; border-radius: 10px; border: 1px solid #38bdf8; display: block; margin: 15px 0; }
        .btn { display: block; background: #0088cc; color: white; padding: 12px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 10px; font-size: 16px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>📶 Solde Utilisateur</h2>
        <h3 style="color:#facc15;">👤 {{ client.username }}</h3>
        <hr style="border: 0.5px solid #334155;">
        
        <p style="margin: 0; color: #94a3b8;">Consommation Aujourd'hui :</p>
        <div class="val">{{ "%.2f"|format(daily_go) }} Go <small style="font-size:15px; color:#94a3b8;">/ {{ client.limit_daily_gb }} Go</small></div>
        <div class="bar-bg"><div class="bar-fill" style="width: {{ daily_pct }}%;"></div></div>
        
        <p style="margin: 0; color: #94a3b8;">Total Consommé ce Mois :</p>
        <div class="val-month">{{ "%.2f"|format(monthly_go) }} Go</div>
        
        <div class="badge">
            📅 Validité Abonnement : <b>{{ days_left }}</b><br>
            <small style="color:#94a3b8;">Date d'expiration : {{ client.date_fin or 'Non défini' }}</small>
        </div>
        
        <a class="btn" href="https://t.me/{{ bot_name }}?start={{ client.username }}">💬 Consulter sur Telegram</a>
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
    return render_template_string(CLIENT_HTML, client=client, daily_go=daily_go, monthly_go=monthly_go, daily_pct=daily_pct, days_left=days_left, bot_name=BOT_USERNAME)

# --- BOT TELEGRAM PRO AVEC ACCUEIL & TUTORIEL ---
def send_telegram_msg(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)

@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    update = request.get_json() or {}
    
    # 1. Gestion des clics sur boutons interactifs (Callback Query)
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        
        if data == "tuto":
            tuto_text = (
                "📖 <b>GUIDE & TUTORIEL D'UTILISATION :</b>\n\n"
                "1️⃣ <b>Comment connaître mon solde ?</b>\n"
                "👉 Envoyez simplement votre <b>Code / Identifiant WiFi</b> directement dans ce chat !\n\n"
                "2️⃣ <b>Où trouver mon code ?</b>\n"
                "👉 Il est inscrit sur votre ticket WiFi ou votre reçu d'abonnement.\n\n"
                "3️⃣ <b>Règles de connexion :</b>\n"
                "• Quota journalier : 30 Go / jour.\n"
                "• Le compteur journalier se remet à 0 à minuit.\n"
                "• Le compteur mensuel cumule tout votre mois."
            )
            send_telegram_msg(chat_id, tuto_text)
        elif data == "contact":
            contact_text = (
                "📞 <b>SUPPORT & ASSISTANCE ADMIN :</b>\n\n"
                "Pour recharger ou signaler un problème :\n"
                "🔹 Rendez-vous au guichet du Hotspot\n"
                "🔹 Ou contactez l'administrateur de la zone."
            )
            send_telegram_msg(chat_id, contact_text)
        return jsonify({"status": "ok"})

    # 2. Gestion des messages texte
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()

        # Si le message commence par /start avec un nom de client (ex: /start client1)
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1:
                uname = parts[1]
                reply_client_stats(chat_id, uname)
            else:
                # Menu Accueil & Tutoriel
                welcome_text = (
                    "👋 <b>Bienvenue sur le Bot WiFi Zone !</b>\n\n"
                    "Ce bot vous permet de suivre votre consommation internet en direct.\n\n"
                    "👉 <b>Envoyez simplement votre code / identifiant WiFi</b> dans cette discussion pour voir votre solde.\n\n"
                    "<i>Ou utilisez les boutons ci-dessous :</i>"
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📖 Voir le Tutoriel", "callback_data": "tuto"}],
                        [{"text": "📞 Contacter le Support", "callback_data": "contact"}]
                    ]
                }
                send_telegram_msg(chat_id, welcome_text, keyboard)
        
        elif text.startswith("/tuto") or text.startswith("/help"):
            tuto_text = (
                "📖 <b>TUTORIEL RAPIDE :</b>\n\n"
                "Tapez directement votre identifiant client dans ce chat pour obtenir votre solde !"
            )
            send_telegram_msg(chat_id, tuto_text)
        
        else:
            # Le client a tapé directement son nom/code (ex: "client01")
            reply_client_stats(chat_id, text)

    return jsonify({"status": "ok"})

def reply_client_stats(chat_id, username):
    c = get_client(username)
    if c:
        d_go = round(c['daily_bytes'] / 1073741824, 2)
        m_go = round(c['monthly_bytes'] / 1073741824, 2)
        val = calculate_days_left(c['date_fin'])
        msg = (
            f"📊 <b>SOLDE DU COMPTE : {c['username']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Aujourd'hui :</b> {d_go} Go / {c['limit_daily_gb']} Go\n"
            f"📆 <b>Total ce mois :</b> {m_go} Go\n"
            f"⏳ <b>Validité :</b> {val}\n"
            f"🏁 <b>Expiration :</b> {c['date_fin'] or 'Non défini'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Statut : 🟢 En Ligne"
        )
    else:
        msg = (
            f"❌ <b>Compte '{username}' introuvable.</b>\n\n"
            f"Veuillez vérifier l'orthographe de votre identifiant ou cliquer depuis le portail WiFi."
        )
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
        update_client_usage(u["username"], u["bytes"])
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
    return "🔥 Hotspot Manager Pro Actif"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
