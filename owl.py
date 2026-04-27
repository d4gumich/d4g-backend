from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Default fallback (or pull from environment)
SIMILARITY_API_URL = os.environ.get("SIMILARITY_API", "https://similarity-api-559650505418.us-central1.run.app/similarity")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyAUxxF0Itb29ya3ZD7EIZICyrElQNOGBAc")
genai.configure(api_key=GOOGLE_API_KEY)

# System prompt
SYSTEM_PROMPT = (
    "You are a Q&A assistant dedicated to providing accurate, up-to-date information "
    "from ReliefWeb, a humanitarian platform managed by OCHA. Use the provided context documents "
    "to answer the user’s question. If you cannot find the answer or are not sure, say that you do not know. "
    "Keep your answer to ten sentences maximum, be clear and concise. Always end by inviting the user to ask more!"
)

@app.route("/api/owl", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        query = data.get("query", "").strip()
        k = int(data.get("k", 5))
        temperature = float(data.get("temperature", 0.5))
        model_name = data.get("model", "gemini-1.5-flash")

        if not query:
            return jsonify({"error": "Missing query"}), 400

        # Step 1: Call similarity API
        payload = {"text": query, "k": k}
        try:
            sim_response = requests.post(SIMILARITY_API_URL, json=payload)
            sim_response.raise_for_status()
            similar_docs = sim_response.json().get("results", [])
        except Exception as e:
            return jsonify({"error": f"Similarity API error: {str(e)}"}), 500

        if not similar_docs:
            return jsonify({
                "answer": "I couldn't find any relevant documents to answer your question.",
                "documents": []
            })

        # Step 2: Create context string
        context_details = "\n\n".join([doc.get("combined_details", "No details") for doc in similar_docs])

        # Step 3: Generate answer from Gemini
        full_prompt = f"{SYSTEM_PROMPT}\n\n### Context:\n{context_details}\n\n### User Question:\n{query}"
        model = genai.GenerativeModel(model_name)

        response = model.generate_content(full_prompt, generation_config={"temperature": temperature})
        answer = response.text.strip()

        return jsonify({
            "answer": answer,
            "documents": similar_docs
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
