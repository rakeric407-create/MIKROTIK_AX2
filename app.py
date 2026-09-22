from flask import Flask, request, jsonify, render_template_string
from database import init_db, update_client, get_client, get_all_clients, reset_daily
import os

app = Flask(__name__)
init_db()

# ===== SÉCURITÉ : Changez ce mot de passe ! =====
ADMIN_PASSWORD = "mon_mot_de_passe_secret"
API_SECRET = "cle_secrete_12345"

# ===== DASHBOARD ADMIN =====
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>📊 Dashboard Hotspot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; background: #1a1a2e; color: white; padding: 20px; }
        h1 { color: #00d4ff; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #16213e; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #333; }
        .active { color: #00ff88; }
        .blocked { color: #ff4444; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>📊 Dashboard Hotspot WiFi</h1>
    <div class="card">
        <h3>👥 Total clients : {{ total }}</h3>
        <h3>🟢 Actifs : {{ actifs }}</h3>
    </div>
    <table>
        <tr><th>Client</th><th>Aujourd'hui</th><th>Ce mois</th><th>Statut</th><th>Dernière MAJ</th></tr>
        {% for c in clients %}
        <tr>
            <td><b>{{ c.username }}</b></td>
            <td>{{ "%.2f"|format(c.daily_bytes / 1073741824) }} Go / 30 Go</td>
            <td>{{ "%.2f"|format(c.monthly_bytes / 1073741824) }} Go</td>
            <td class="{{ 'active' if c.status == 'active' else 'blocked' }}">
                {{ '🟢 Actif' if c.status == 'active' else '🔴 Bloqué' }}
            </td>
            <td>{{ c.last_update }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/admin")
def admin():
    pwd = request.args.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return "<h2>🔒 Mot de passe incorrect. Ajoutez ?pwd=VOTRE_MOT_DE_PASSE à l'URL</h2>"
    clients = get_all_clients()
    actifs = sum(1 for c in clients if c["status"] == "active")
    return render_template_string(DASHBOARD_HTML, clients=clients, total=len(clients), actifs=actifs)

# ===== PAGE CLIENT =====
CLIENT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mon Compte WiFi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; background: #0f0f23; color: white; text-align: center; padding: 20px; }
        .card { background: #1a1a3e; padding: 30px; border-radius: 15px; max-width: 400px; margin: auto; }
        .bar { background: #333; height: 25px; border-radius: 12px; overflow: hidden; margin: 10px 0; }
        .fill { background: linear-gradient(90deg, #00ff88, #00d4ff); height: 100%; border-radius: 12px; }
        .fill.warning { background: linear-gradient(90deg, #ff8800, #ff4444); }
        h1 { color: #00d4ff; }
        .big { font-size: 2em; color: #00ff88; }
        .tg-btn { background: #0088cc; color: white; padding: 15px 25px; border-radius: 10px;
                  text-decoration: none; display: inline-block; margin-top: 20px; font-size: 1.1em; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📶 Mon Compte WiFi</h1>
        <h2>👤 {{ client.username }}</h2>
        
        <h3>📅 Aujourd'hui</h3>
        <p class="big">{{ "%.2f"|format(daily_go) }} Go <small>/ 30 Go</small></p>
        <div class="bar"><div class="fill {{ 'warning' if daily_pct > 80 else '' }}" style="width: {{ daily_pct }}%"></div></div>
        
        <h3>📆 Ce mois-ci</h3>
        <p class="big">{{ "%.2f"|format(monthly_go) }} Go</p>
        
        <p>Statut : {{ '🟢 Connecté' if client.status == 'active' else '🔴 Coupé' }}</p>
        <p><small>Dernière mise à jour : {{ client.last_update }}</small></p>
        
        <a href="https://t.me/{{ bot_name }}?start={{ client.username }}" class="tg-btn">
            💬 Suivre sur Telegram
        </a>
    </div>
</body>
</html>
"""

@app.route("/status/<username>")
def client_status(username):
    client = get_client(username)
    if not client:
        return "<h2>❌ Client introuvable</h2>"
    daily_go = client["daily_bytes"] / 1073741824
    monthly_go = client["monthly_bytes"] / 1073741824
    daily_pct = min(100, (daily_go / 30) * 100)
    bot_name = os.environ.get("BOT_USERNAME", "votre_bot")
    return render_template_string(CLIENT_HTML, client=client, daily_go=daily_go,
                                  monthly_go=monthly_go, daily_pct=daily_pct, bot_name=bot_name)

# ===== API : Le MikroTik envoie les stats ici =====
@app.route("/api/update", methods=["POST"])
def api_update():
    data = request.json
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "Non autorisé"}), 403
    for user in data.get("users", []):
        update_client(user["username"], user["bytes"])
    return jsonify({"status": "ok"})

@app.route("/api/reset-daily", methods=["POST"])
def api_reset():
    data = request.json
    if data.get("secret") != API_SECRET:
        return jsonify({"error": "Non autorisé"}), 403
    reset_daily()
    return jsonify({"status": "reset ok"})

@app.route("/")
def home():
    return "<h1>🔥 Hotspot Manager Actif</h1><p>Dashboard : /admin?pwd=XXX</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
