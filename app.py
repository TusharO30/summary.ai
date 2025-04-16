from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import fitz  
import pytesseract
from PIL import Image
import base64
import io
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# Language mapping for prompts
LANGUAGE_PROMPTS = {
    'en': {
        'short': "Summarize this research paper in English in 3-4 bullet points focusing on key contributions, methodology, and results. Use academic language.",
        'medium': "Summarize this research paper in English in 5-7 bullet points focusing on key contributions, methodology, and results. Use academic language.",
        'long': "Provide a comprehensive summary in English (10+ bullet points) of this research paper, covering all key aspects including contributions, methodology, results, and implications."
    },
    'hi': {
        'short': "इस शोध पत्र का हिंदी में संक्षिप्त सारांश दें (3-4 बुलेट पॉइंट्स में), मुख्य योगदान, पद्धति और परिणामों पर ध्यान केंद्रित करें। शैक्षणिक भाषा का प्रयोग करें।",
        'medium': "इस शोध पत्र का हिंदी में मध्यम लंबाई का सारांश दें (5-7 बुलेट पॉइंट्स में), मुख्य योगदान, पद्धति और परिणामों पर ध्यान केंद्रित करें। शैक्षणिक भाषा का प्रयोग करें।",
        'long': "इस शोध पत्र का हिंदी में विस्तृत सारांश दें (10+ बुलेट पॉइंट्स में), सभी प्रमुख पहलुओं को शामिल करें जिसमें योगदान, पद्धति, परिणाम और निहितार्थ शामिल हैं।"
    },
    'mr': {
        'short': "या संशोधन पत्राचा मराठीत संक्षिप्त सारांश द्या (3-4 बुलेट पॉइंट्समध्ये), मुख्य योगदान, पद्धत आणि निकालांवर लक्ष केंद्रित करा. शैक्षणिक भाषा वापरा.",
        'medium': "या संशोधन पत्राचा मराठीत मध्यम लांबीचा सारांश द्या (5-7 बुलेट पॉइंट्समध्ये), मुख्य योगदान, पद्धत आणि निकालांवर लक्ष केंद्रित करा. शैक्षणिक भाषा वापरा.",
        'long': "या संशोधन पत्राचा मराठीत तपशीलवार सारांश द्या (10+ बुलेट पॉइंट्समध्ये), सर्व प्रमुख पैलूंना समाविष्ट करा ज्यामध्ये योगदान, पद्धत, निकाल आणि परिणाम समाविष्ट आहेत."
    },
    'es': {
        'short': "Resume este artículo de investigación en español en 3-4 puntos clave, centrándose en las contribuciones principales, metodología y resultados. Utilice lenguaje académico.",
        'medium': "Resume este artículo de investigación en español en 5-7 puntos clave, centrándose en las contribuciones principales, metodología y resultados. Utilice lenguaje académico.",
        'long': "Proporcione un resumen exhaustivo en español (10+ puntos clave) de este artículo de investigación, cubriendo todos los aspectos clave incluyendo contribuciones, metodología, resultados e implicaciones."
    },
    'fr': {
        'short': "Résumez cet article de recherche en français en 3-4 points clés, en mettant l'accent sur les contributions principales, la méthodologie et les résultats. Utilisez un langage académique.",
        'medium': "Résumez cet article de recherche en français en 5-7 points clés, en mettant l'accent sur les contributions principales, la méthodologie et les résultats. Utilisez un langage académique.",
        'long': "Fournissez un résumé détaillé en français (10+ points clés) de cet article de recherche, couvrant tous les aspects clés y compris les contributions, la méthodologie, les résultats et les implications."
    },
    'de': {
        'short': "Fassen Sie diese Forschungsarbeit auf Deutsch in 3-4 Stichpunkten zusammen, wobei Sie sich auf die wichtigsten Beiträge, Methoden und Ergebnisse konzentrieren. Verwenden Sie akademische Sprache.",
        'medium': "Fassen Sie diese Forschungsarbeit auf Deutsch in 5-7 Stichpunkten zusammen, wobei Sie sich auf die wichtigsten Beiträge, Methoden und Ergebnisse konzentrieren. Verwenden Sie akademische Sprache.",
        'long': "Erstellen Sie eine umfassende Zusammenfassung auf Deutsch (10+ Stichpunkte) dieser Forschungsarbeit, die alle wichtigen Aspekte abdeckt, einschließlich Beiträge, Methodik, Ergebnisse und Implikationen."
    },
    'zh': {
        'short': "用中文简要总结这篇研究论文（3-4个要点），重点关注主要贡献、方法和结果。使用学术语言。",
        'medium': "用中文中等长度总结这篇研究论文（5-7个要点），重点关注主要贡献、方法和结果。使用学术语言。",
        'long': "用中文详细总结这篇研究论文（10+个要点），涵盖所有关键方面，包括贡献、方法、结果和影响。"
    },
    'ja': {
        'short': "この研究論文を日本語で簡潔に要約してください（3-4つのポイント）。主な貢献、方法論、結果に焦点を当て、学術的な言葉を使用してください。",
        'medium': "この研究論文を日本語で中程度の長さで要約してください（5-7つのポイント）。主な貢献、方法論、結果に焦点を当て、学術的な言葉を使用してください。",
        'long': "この研究論文を日本語で詳細に要約してください（10+のポイント）。貢献、方法論、結果、含意を含むすべての主要な側面をカバーしてください。"
    },
    'ar': {
        'short': "لخص ورقة البحث هذه باللغة العربية في 3-4 نقاط رئيسية، مع التركيز على المساهمات الرئيسية والمنهجية والنتائج. استخدم لغة أكاديمية.",
        'medium': "لخص ورقة البحث هذه باللغة العربية في 5-7 نقاط رئيسية، مع التركيز على المساهمات الرئيسية والمنهجية والنتائج. استخدم لغة أكاديمية.",
        'long': "قدم ملخصًا شاملًا باللغة العربية (10+ نقاط رئيسية) لورقة البحث هذه، مع تغطية جميع الجوانب الرئيسية بما في ذلك المساهمات والمنهجية والنتائج والآثار المترتبة عليها."
    }
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/check-auth")
def check_auth():
    try:
        genai.list_models()
        return jsonify({"status": "OK", "message": "Authentication successful"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/extract-text", methods=["POST"])
def extract_text():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400

    try:
        pdf_file = request.files['pdf']
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()

        if not text.strip():
            return jsonify({"error": "No text extracted from PDF"}), 400

        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/extract-images", methods=["POST"])
def extract_images():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400

    try:
        pdf_file = request.files['pdf']
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        images = []
        ocr_texts = []

        for page_index in range(len(doc)):
            page = doc[page_index]
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                images.append({
                    "page": page_index + 1,
                    "image_index": img_index + 1,
                    "ext": image_ext,
                    "base64": encoded_image
                })

                image = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(image)
                if ocr_text.strip():
                    ocr_texts.append(ocr_text.strip())

        return jsonify({"images": images, "ocr_text": "\n".join(ocr_texts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    text = data.get("text", "").strip()
    ocr_text = data.get("ocr_text", "").strip()
    length = data.get("length", "medium")
    language = data.get("language", "en")  # Default to English if not specified

    combined_text = f"{text}\n\n[Text extracted from graphs/images:]\n{ocr_text}".strip()

    if len(combined_text) < 100:
        return jsonify({"error": "Combined text must be ≥100 characters"}), 400

    # Get the appropriate prompt based on language and length
    try:
        prompt_template = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS['en']).get(length, LANGUAGE_PROMPTS['en']['medium'])
    except KeyError:
        prompt_template = LANGUAGE_PROMPTS['en']['medium']

    prompt = f"{prompt_template}\n\nHere's the text:\n\n{combined_text}"

    try:
        response = model.generate_content(prompt)
        return jsonify({"summary": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)