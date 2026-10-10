import os
import csv
import logging
import threading
import time
from pathlib import Path
from flask import Flask, render_template_string, jsonify, send_from_directory, request
from app.config import Config
from app.pipeline import Pipeline
from app.db import DatabaseManager

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global background worker state
pipeline_state = {
    "status": "idle",  # "idle", "running", "completed", "failed"
    "progress": "",
    "summary": None,
    "error": None,
    "start_time": None
}
pipeline_lock = threading.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automated Micro-Influencer Outreach System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --accent-purple: #8b5cf6;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-pink: #ec4899;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-gradient); color: var(--text-main); min-height: 100vh; padding: 2rem 1rem; }
        .container { max-width: 1200px; margin: 0 auto; }

        header { text-align: center; margin-bottom: 2.5rem; }
        header h1 { font-size: 2.25rem; font-weight: 700; background: linear-gradient(to right, #a78bfa, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }
        header p { color: var(--text-sub); font-size: 1rem; }

        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }
        .stat-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.5rem; backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); }
        .stat-card .label { color: var(--text-sub); font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; margin-bottom: 0.5rem; }
        .stat-card .value { font-size: 2rem; font-weight: 700; color: var(--text-main); }

        .action-bar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 1rem; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 2rem; backdrop-filter: blur(12px); }
        .btn { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s ease; text-decoration: none; font-size: 0.95rem; }
        .btn-primary { background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); color: #fff; box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4); }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6); }
        .btn-secondary { background: rgba(255, 255, 255, 0.08); color: var(--text-main); border: 1px solid var(--card-border); }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.15); }
        .btn-disabled { opacity: 0.6; cursor: not-allowed; transform: none !important; }

        .table-container { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; overflow-x: auto; backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
        th { background: rgba(15, 23, 42, 0.8); color: var(--text-sub); font-weight: 600; padding: 1rem 1.25rem; border-bottom: 1px solid var(--card-border); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
        td { padding: 1rem 1.25rem; border-bottom: 1px solid var(--card-border); color: var(--text-main); vertical-align: top; }
        tr:hover { background: rgba(255, 255, 255, 0.03); }

        .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
        .badge-simulated { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .badge-skipped { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-dup { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }

        .status-box { margin-top: 1rem; padding: 1rem; border-radius: 8px; font-size: 0.9rem; display: none; }
        .status-box.active { display: block; }
        .status-info { background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; color: #93c5fd; }
        .status-success { background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #6ee7b7; }
        .status-error { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #fca5a5; }

        .spinner { border: 3px solid rgba(255,255,255,0.3); border-top: 3px solid #fff; border-radius: 50%; width: 18px; height: 18px; animation: spin 1s linear infinite; display: inline-block; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Automated Micro-Influencer Outreach System</h1>
            <p>Production Pipeline & Real-Time Outreach Dashboard</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Candidates Discovered</div>
                <div class="value">{{ stats.discovered }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Qualified Micro-Influencers</div>
                <div class="value" style="color: #60a5fa;">{{ stats.qualified }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Simulated Outreach Sent</div>
                <div class="value" style="color: #34d399;">{{ stats.simulated }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Database Logged</div>
                <div class="value" style="color: #a78bfa;">{{ stats.db_count }}</div>
            </div>
        </div>

        <div class="action-bar">
            <div>
                <button id="runBtn" class="btn btn-primary" onclick="runPipeline()">
                    <span id="btnText">▶ Run Outreach Pipeline</span>
                </button>
            </div>
            <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                <a href="/download/outreach_tracker.csv" class="btn btn-secondary">📥 Tracker CSV</a>
                <a href="/download/qualified_influencers.csv" class="btn btn-secondary">📥 Qualified CSV</a>
                <a href="/download/classified_influencers.csv" class="btn btn-secondary">📥 Classified CSV</a>
            </div>
        </div>

        <div id="statusBox" class="status-box"></div>

        <div class="table-container" style="margin-top: 1.5rem;">
            <table>
                <thead>
                    <tr>
                        <th>Influencer</th>
                        <th>Followers</th>
                        <th>Engagement Rate</th>
                        <th>Email</th>
                        <th>Email Pitch</th>
                        <th>Instagram DM</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% if records %}
                        {% for r in records %}
                        <tr>
                            <td>
                                <strong>{{ r.Influencer or r.influencer_name }}</strong><br>
                                <a href="{{ r['Profile URL'] }}" target="_blank" style="color: #60a5fa; font-size: 0.8rem;">View Channel</a>
                            </td>
                            <td>{{ "{:,}".format(r['Follower Count']|int if r['Follower Count'] else 0) }}</td>
                            <td>{{ r['Engagement Rate'] }}</td>
                            <td><span style="font-family: monospace;">{{ r['Contact Email'] or r['email'] }}</span></td>
                            <td style="max-width: 320px; line-height: 1.4;">{{ r['Email Pitch'] or r['message_generated'] }}</td>
                            <td style="max-width: 220px; line-height: 1.4;">{{ r['Instagram DM'] }}</td>
                            <td>
                                {% set st = r['Status'] or r['status'] %}
                                {% if st == 'SIMULATED' %}
                                    <span class="badge badge-simulated">SIMULATED</span>
                                {% elif 'DUPLICATE' in st %}
                                    <span class="badge badge-dup">DUPLICATE</span>
                                {% else %}
                                    <span class="badge badge-skipped">{{ st }}</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="7" style="text-align: center; color: var(--text-sub); padding: 3rem;">
                                No outreach records found. Click <strong>"Run Outreach Pipeline"</strong> to discover influencers.
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let pollInterval = null;

        function updateStatusUI(data) {
            const btn = document.getElementById('runBtn');
            const btnText = document.getElementById('btnText');
            const statusBox = document.getElementById('statusBox');

            if (data.status === 'running') {
                btn.classList.add('btn-disabled');
                btn.disabled = true;
                btnText.innerHTML = '<span class="spinner"></span> Running Pipeline...';
                statusBox.className = 'status-box active status-info';
                statusBox.innerHTML = '⏳ <strong>Pipeline Running:</strong> ' + (data.progress || 'Executing discovery, enrichment, filtering, AI personalization, and outreach simulation...');
            } else if (data.status === 'completed') {
                if (pollInterval) clearInterval(pollInterval);
                statusBox.className = 'status-box active status-success';
                const s = data.summary || {};
                statusBox.innerHTML = '✅ <strong>Pipeline Complete!</strong> Discovered: ' + (s.discovered_count || 0) + ' | Qualified: ' + (s.qualified_count || 0) + ' | Simulated Sends: ' + (s.simulated_send_count || 0) + '. Reloading page...';
                btn.classList.remove('btn-disabled');
                btn.disabled = false;
                btnText.innerHTML = '▶ Run Outreach Pipeline';
                setTimeout(() => window.location.reload(), 2500);
            } else if (data.status === 'failed') {
                if (pollInterval) clearInterval(pollInterval);
                statusBox.className = 'status-box active status-error';
                statusBox.innerHTML = '❌ <strong>Pipeline Error:</strong> ' + (data.error || 'Execution failed.');
                btn.classList.remove('btn-disabled');
                btn.disabled = false;
                btnText.innerHTML = '▶ Run Outreach Pipeline';
            }
        }

        function pollStatus() {
            fetch('/pipeline-status')
                .then(async res => {
                    const text = await res.text();
                    try {
                        return JSON.parse(text);
                    } catch(e) {
                        throw new Error("Server response error (" + res.status + "): " + text.substring(0, 100));
                    }
                })
                .then(data => {
                    updateStatusUI(data);
                })
                .catch(err => {
                    console.error("Polling status error:", err);
                });
        }

        function runPipeline() {
            const btn = document.getElementById('runBtn');
            const btnText = document.getElementById('btnText');
            const statusBox = document.getElementById('statusBox');

            btn.classList.add('btn-disabled');
            btn.disabled = true;
            btnText.innerHTML = '<span class="spinner"></span> Starting Pipeline...';
            
            statusBox.className = 'status-box active status-info';
            statusBox.innerHTML = '⏳ Initializing 7-stage outreach pipeline...';

            fetch('/run-pipeline', { method: 'POST' })
                .then(async res => {
                    const text = await res.text();
                    let data = {};
                    try {
                        data = JSON.parse(text);
                    } catch(e) {
                        throw new Error("Server returned non-JSON response (Status " + res.status + "): " + text.substring(0, 150));
                    }

                    if (res.ok && data.success) {
                        if (!pollInterval) {
                            pollInterval = setInterval(pollStatus, 2500);
                        }
                        pollStatus();
                    } else {
                        statusBox.className = 'status-box active status-error';
                        statusBox.innerHTML = '❌ <strong>Error:</strong> ' + (data.error || 'Failed to start pipeline');
                        btn.classList.remove('btn-disabled');
                        btn.disabled = false;
                        btnText.innerHTML = '▶ Run Outreach Pipeline';
                    }
                })
                .catch(err => {
                    statusBox.className = 'status-box active status-error';
                    statusBox.innerHTML = '❌ <strong>Execution Error:</strong> ' + err.message;
                    btn.classList.remove('btn-disabled');
                    btn.disabled = false;
                    btnText.innerHTML = '▶ Run Outreach Pipeline';
                });
        }

        window.addEventListener('DOMContentLoaded', () => {
            pollStatus();
        });
    </script>
</body>
</html>
"""

def get_stats():
    tracker_path = Config.DATA_DIR / "outreach_tracker.csv"
    classified_path = Config.DATA_DIR / "classified_influencers.csv"
    
    discovered = 0
    qualified = 0
    simulated = 0
    db_count = 0

    if classified_path.exists():
        try:
            with open(classified_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                discovered = len(rows)
                qualified = sum(1 for r in rows if r.get("filter_status") == "QUALIFIED")
        except Exception:
            pass

    records = []
    if tracker_path.exists():
        try:
            with open(tracker_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = list(reader)
                simulated = sum(1 for r in records if r.get("Status") == "SIMULATED" or r.get("Sent") == "True")
        except Exception:
            pass

    try:
        db = DatabaseManager()
        db_count = len(db.get_all_logs())
    except Exception:
        db_count = 0

    return {
        "discovered": discovered,
        "qualified": qualified,
        "simulated": simulated,
        "db_count": db_count
    }, records

@app.route("/")
def index():
    stats, records = get_stats()
    return render_template_string(HTML_TEMPLATE, stats=stats, records=records)

def _execute_pipeline():
    global pipeline_state
    try:
        if not Config.validate_youtube_key():
            raise ValueError("YOUTUBE_API_KEY environment variable is missing on Render. Please configure YOUTUBE_API_KEY in Render Environment variables.")

        pipeline = Pipeline()
        summary = pipeline.run(target_discovery_count=Config.TARGET_DISCOVERY_COUNT)
        
        with pipeline_lock:
            pipeline_state["status"] = "completed"
            pipeline_state["summary"] = summary
            pipeline_state["progress"] = "Completed successfully"
    except Exception as e:
        logger.error(f"Error running pipeline in background: {e}", exc_info=True)
        with pipeline_lock:
            pipeline_state["status"] = "failed"
            pipeline_state["error"] = str(e)

@app.route("/run-pipeline", methods=["POST"])
def run_pipeline():
    global pipeline_state
    with pipeline_lock:
        if pipeline_state["status"] == "running":
            return jsonify({"success": True, "message": "Pipeline is already running."})

        if not Config.validate_youtube_key():
            return jsonify({"success": False, "error": "YOUTUBE_API_KEY is missing. Please set your YOUTUBE_API_KEY in the Render Environment Variables tab."}), 400

        pipeline_state["status"] = "running"
        pipeline_state["error"] = None
        pipeline_state["summary"] = None
        pipeline_state["progress"] = "Executing discovery, enrichment, filtering, AI personalization, and outreach simulation..."
        pipeline_state["start_time"] = time.time()

    thread = threading.Thread(target=_execute_pipeline, daemon=True)
    thread.start()
    return jsonify({"success": True, "message": "Pipeline started."})

@app.route("/pipeline-status", methods=["GET"])
def pipeline_status():
    with pipeline_lock:
        return jsonify(pipeline_state)

@app.route("/download/<filename>")
def download_file(filename):
    allowed_files = [
        "outreach_tracker.csv",
        "qualified_influencers.csv",
        "classified_influencers.csv",
        "personalized_outreach.csv",
        "influencers.csv",
    ]
    if filename in allowed_files:
        return send_from_directory(Config.DATA_DIR, filename, as_attachment=True)
    return "File not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
