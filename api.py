from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import httpx  # For HuggingFace API calls

app = FastAPI(title="AURA API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Environment Configuration ────────────────────────────────
HF_TOKEN = os.getenv("HF_TOKEN", "") # Add your token to .env or system env
N8N_SCAN_WEBHOOK = os.getenv("N8N_SCAN_WEBHOOK", "")

# ── HuggingFace Mapping ──────────────────────────────────────
HF_LABEL_MAP = {
    "acne": "acne", "acne and rosacea": "acne", "acne vulgaris": "acne", "pimple": "acne",
    "eczema": "eczema", "atopic dermatitis": "eczema", "dermatitis": "eczema",
    "hyperpigmentation": "pigmentation", "melasma": "pigmentation", "dark spots": "pigmentation",
    "rosacea": "rosacea", "redness": "rosacea",
    "dry skin": "dry", "xerosis": "dry", "psoriasis": "dry",
    "normal skin": "healthy", "healthy skin": "healthy", "clear skin": "healthy"
}

def map_hf_label(label: str) -> str:
    label_lower = label.lower().strip()
    if label_lower in HF_LABEL_MAP: return HF_LABEL_MAP[label_lower]
    for key, kb_key in HF_LABEL_MAP.items():
        if key in label_lower or label_lower in key: return kb_key
    return "healthy"

def confidence_to_severity(confidence: float) -> str:
    if confidence >= 0.80: return "High"
    elif confidence >= 0.50: return "Medium"
    return "Low"

def build_remedies(kb_key: str) -> list:
    advice = KB.get(kb_key, KB["healthy"])
    return [
        {"title": "Daily Routine", "desc": advice["routine"]},
        {"title": "Key Advice",    "desc": advice["advice"]},
    ]

def build_products(kb_key: str) -> list:
    products = {
        "acne": [{"name": "Salicylic Acid Cleanser", "use": "Twice daily", "ingredient": "Salicylic Acid 2%"}],
        "eczema": [{"name": "CeraVe Moisturizing Cream", "use": "Twice daily", "ingredient": "Ceramides"}],
        "pigmentation": [{"name": "Vitamin C Serum", "use": "Morning", "ingredient": "L-Ascorbic Acid"}],
        "rosacea": [{"name": "Azelaic Acid Cream", "use": "Twice daily", "ingredient": "Azelaic Acid 10%"}],
        "dry": [{"name": "Rich Ceramide Cream", "use": "Morning and night", "ingredient": "Ceramides"}],
        "healthy": [{"name": "Gentle Cleanser", "use": "Twice daily", "ingredient": "Amino Acids"}]
    }
    return products.get(kb_key, products["healthy"])

# ── Data models ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

# ── Knowledge base ───────────────────────────────────────────
KB = {
    "acne": {
        "title": "Acne Vulgaris",
        "advice": "Use Salicylic Acid 2% or Benzoyl Peroxide. Avoid heavy oils. Keep pillowcases clean.",
        "routine": "Gentle Cleanser → BHA Toner → Oil-free Moisturizer → SPF 30+"
    },
    "eczema": {
        "title": "Eczema / Dermatitis",
        "advice": "Focus on barrier repair. Use fragrance-free creams with Ceramides. Avoid long hot showers.",
        "routine": "Creamy Cleanser → Thick Ceramide Moisturizer (on damp skin) → Healing Ointment"
    },
    "pigmentation": {
        "title": "Hyperpigmentation",
        "advice": "Daily sun protection is essential. Look for Vitamin C, Niacinamide, or Kojic Acid.",
        "routine": "Vitamin C Serum → Moisturizer → SPF 50+ (reapply every 2 hours outdoors)"
    },
    "rosacea": {
        "title": "Rosacea",
        "advice": "Use gentle, fragrance-free products. Azelaic Acid can help. Avoid triggers like spicy food and alcohol.",
        "routine": "Gentle Cleanser → Azelaic Acid → Mineral SPF"
    },
    "dry": {
        "title": "Dry Skin",
        "advice": "Layer hydration: hyaluronic acid serum followed by a rich moisturizer. Lock in moisture with facial oil.",
        "routine": "Hydrating Cleanser → HA Serum → Rich Moisturizer → Facial Oil (night)"
    },
    "healthy": {
        "title": "Healthy Skin",
        "advice": "Your skin looks great! Focus on maintenance, hydration, and consistent SPF use.",
        "routine": "Gentle Cleanser → Hydrating Serum → Moisturizer → SPF 30+"
    }
}

# ── Try to load ML classifier ────────────────────────────────
classifier = None
try:
    from skincare_classifier import SkincareClassifier
    classifier = SkincareClassifier()
    print("✅ SkincareClassifier loaded.")
except Exception as e:
    print(f"⚠️  ML model not loaded ({e}). Falling back to mock data.")

# ── HEALTH ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "ml_model": classifier is not None}

# ── HTML PAGES ───────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/dashboard")
async def dashboard():
    return FileResponse("dashboard.html")

@app.get("/dashboard.html")
async def dashboard_html():
    return FileResponse("dashboard.html")

@app.get("/admin")
async def admin():
    return FileResponse("admin.html")

@app.get("/admin.html")
async def admin_html():
    return FileResponse("admin.html")

# ── PREDICT ──────────────────────────────────────────────────
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Skin condition prediction using HuggingFace image classification."""
    contents = await file.read()

    if HF_TOKEN:
        try:
            HF_MODEL_URL = "https://api-inference.huggingface.co/models/Anwarkh1/Skin_Disease-Image_Classification"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    HF_MODEL_URL,
                    headers={"Authorization": f"Bearer {HF_TOKEN}"},
                    content=contents,
                )

            if resp.status_code == 200:
                hf_results = resp.json()
                if isinstance(hf_results, list) and len(hf_results) > 0:
                    top = hf_results[0]
                    label = top.get("label", "healthy")
                    confidence = float(top.get("score", 0.75))
                    kb_key = map_hf_label(label)
                    advice = KB.get(kb_key, KB["healthy"])

                    result = {
                        "condition" : advice["title"],
                        "severity"  : confidence_to_severity(confidence),
                        "confidence": round(confidence, 3),
                        "advice"    : advice,
                        "remedies"  : build_remedies(kb_key),
                        "products"  : build_products(kb_key),
                        "source"    : "huggingface",
                    }

                    if N8N_SCAN_WEBHOOK:
                        try:
                            async with httpx.AsyncClient(timeout=5.0) as client:
                                await client.post(N8N_SCAN_WEBHOOK, json=result)
                        except Exception: pass

                    return result
            elif resp.status_code == 503:
                return {"condition": "Model Loading", "source": "loading"}
        except Exception as e:
            print(f"⚠️ HuggingFace error: {e}")

    # Fallback to local/mock if HF fails or no token
    return {
        "condition" : KB["healthy"]["title"],
        "severity"  : "Low",
        "confidence": 0.88,
        "advice"    : KB["healthy"],
        "remedies"  : build_remedies("healthy"),
        "products"  : build_products("healthy"),
        "source"    : "mock",
    }

# ── CHAT ─────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    """Keyword-based skincare chatbot."""
    msg = req.message.lower()

    if any(w in msg for w in ["acne", "pimple", "breakout", "spot"]):
        return {"response": f"💊 {KB['acne']['advice']}\n\nRoutine: {KB['acne']['routine']}"}
    elif any(w in msg for w in ["eczema", "dermatitis", "itchy", "rash"]):
        return {"response": f"🌿 {KB['eczema']['advice']}\n\nRoutine: {KB['eczema']['routine']}"}
    elif any(w in msg for w in ["pigmentation", "dark spot", "uneven", "hyperpigmentation"]):
        return {"response": f"✨ {KB['pigmentation']['advice']}\n\nRoutine: {KB['pigmentation']['routine']}"}
    elif any(w in msg for w in ["rosacea", "redness", "flushing"]):
        return {"response": f"🌸 {KB['rosacea']['advice']}\n\nRoutine: {KB['rosacea']['routine']}"}
    elif any(w in msg for w in ["dry", "flaky", "tight", "dehydrated"]):
        return {"response": f"💧 {KB['dry']['advice']}\n\nRoutine: {KB['dry']['routine']}"}
    elif any(w in msg for w in ["moistur", "hydrat"]):
        return {"response": "💧 Moisturize twice daily — morning and night. For best results, apply while skin is still slightly damp to lock in hydration. Look for Hyaluronic Acid, Glycerin, or Ceramides."}
    elif any(w in msg for w in ["spf", "sunscreen", "sun protect"]):
        return {"response": "☀️ SPF is the single most effective anti-aging product. Use SPF 30+ every morning even on cloudy days or when indoors near windows. Reapply every 2 hours outdoors."}
    elif any(w in msg for w in ["ingredient", "avoid"]):
        return {"response": "⚠️ For sensitive or acne-prone skin, avoid: artificial fragrances, denatured alcohol, comedogenic oils (coconut oil for acne-prone), and high-percentage acids without buffer. Always patch test new products!"}
    elif any(w in msg for w in ["doctor", "dermatologist", "see a doctor", "when"]):
        return {"response": "🩺 See a dermatologist if symptoms persist more than 2 weeks, worsen suddenly, cover a large area, are painful, or accompany a fever. You can book a consultation right here in AURA!"}
    elif any(w in msg for w in ["routine", "regimen"]):
        return {"response": "📋 A solid basic routine: Cleanser → Serum (targeted treatment) → Moisturizer → SPF (AM). At night: Cleanser → Treatment → Rich Moisturizer. Run an AI scan for a personalized routine!"}
    elif any(w in msg for w in ["skin type", "what type"]):
        return {"response": "🔍 Skin types: Normal (balanced), Oily (shiny, enlarged pores), Dry (tight, flaky), Combination (oily T-zone, dry cheeks), Sensitive (reacts easily). AURA's AI scan can help identify yours!"}
    elif any(w in msg for w in ["hello", "hi", "hey", "help"]):
        return {"response": "👋 Hi! I'm AURA's AI skincare assistant. I can help with skin conditions, routines, ingredients, and when to see a doctor. What's on your mind? 🌿"}
    else:
        return {"response": "🌿 I can help with skin conditions (acne, eczema, pigmentation, rosacea, dry skin), daily routines, ingredients to avoid, and when to see a dermatologist. Try asking about any of these topics!"}

# ── STATIC FILES (must be LAST) ──────────────────────────────
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=False)