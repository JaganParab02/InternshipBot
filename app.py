from flask import Flask, request, jsonify
from flask_cors import CORS
from internshipHunterBot import scrape_jobs, rank_jobs_by_resume_similarity_from_pdf  # your code here

app = Flask(__name__)
CORS(app)  # allow React frontend to access backend

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    keywords = data.get("keywords")
    location = data.get("location")
    resume_path = data.get("resume_path")

    print("Received data:", data)
    if not email or not password or not keywords or not location or not resume_path:
        return jsonify({"error": "Missing required fields"}), 400

    job_list = scrape_jobs(email, password, keywords, location)
    ranked = rank_jobs_by_resume_similarity_from_pdf(resume_path, job_list)
    return jsonify(ranked)

if __name__ == "__main__":
    app.run(debug=True)
