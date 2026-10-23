import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from .db import init_db, upsert_job, get_all_jobs, get_job

# Flask app
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialise database on import
init_db()

# ----- Portal A -----
@app.route("/portal_a", methods=["GET", "POST"])
def portal_a():
    if request.method == "POST":
        # Extract form fields
        job_id = request.form.get("job_id", "").strip()
        customer = request.form.get("customer", "").strip()
        address = request.form.get("address", "").strip()
        work_description = request.form.get("work_description", "").strip()
        priority = request.form.get("priority", "").strip()
        due_date = request.form.get("due_date", "").strip()

        # Basic validation
        if not job_id or not customer or not address:
            return "Missing required fields", 400

        upsert_job(job_id, customer, address, work_description, priority, due_date, portal="A")
        return redirect(url_for("dashboard"))
    return render_template("portal_a.html")

# ----- Portal B -----
@app.route("/portal_b", methods=["GET", "POST"])
def portal_b():
    if request.method == "POST":
        job_id = request.form.get("job_id", "").strip()
        company = request.form.get("company", "").strip()
        contact = request.form.get("contact", "").strip()
        phone = request.form.get("phone", "").strip()

        # File upload
        uploaded_file = request.files.get("document")
        file_path = None
        if uploaded_file and uploaded_file.filename:
            # Save file with secure name (here we just keep original, risky but demo)
            filename = uploaded_file.filename
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            uploaded_file.save(save_path)
            file_path = filename

        # Persist job record – map company to customer field; other fields left empty for now
        if job_id:
            upsert_job(job_id, company, "", "", "", "", "B")
        # For portal B we also store file path; we could add a column but keeping simple
        return redirect(url_for("dashboard"))
    return render_template("portal_b.html")

# ----- Dashboard -----
@app.route("/dashboard")
def dashboard():
    jobs = get_all_jobs()
    return render_template("dashboard.html", jobs=jobs)

# ----- Serve uploaded files -----
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ----- Health check -----
@app.route("/")
def index():
    return "OpsBridge – Field Service Automation Demo (Milestone 2)"

if __name__ == "__main__":
    app.run(debug=True, port=5000)