"""
AURA FastAPI Backend — v4.0 Final
===================================
Run locally:
    uvicorn main:app --reload --port 8002
"""

import os
import httpx
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn

# ── App setup ──────────────────────────────────────────────────
app = FastAPI(title="AURA API", version="4.0")

# ── CORS ───────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Environment variables ───────────────────────────────────────
SUPABASE_URL        = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY        = os.getenv("SUPABASE_KEY", "")
HF_TOKEN            = os.getenv("HF_TOKEN", "")   # ← paste your hf_xxx token
N8N_CHAT_WEBHOOK    = os.getenv("N8N_CHAT_WEBHOOK", "")
N8N_BOOKING_WEBHOOK = os.getenv("N8N_BOOKING_WEBHOOK", "")
N8N_SCAN_WEBHOOK    = os.getenv("N8N_SCAN_WEBHOOK", "")

# ── HuggingFace models (tried in order until one works) ────────
# Primary:  madhur08/skin-disease-classifier  (10 conditions, inference hosted)
# Fallback: nateraw/skin-condition-image-classification
HF_MODELS = [
    "https://api-inference.huggingface.co/models/madhur08/skin-disease-classifier",
    "https://api-inference.huggingface.co/models/Gauravdhamane/skin_diseases",
    "https://api-inference.huggingface.co/models/SharanSMenon/skin-disease-classifier",
]

# ── Data models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None

class AppointmentRequest(BaseModel):
    user_id: str
    user_name: str
    user_email: str
    doctor_name: str
    doctor_specialty: str
    preferred_date: Optional[str] = None
    notes: Optional[str] = None

# ══════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════
KB = {
    "acne": {
        "title"  : "Acne Vulgaris",
        "advice" : "Use Salicylic Acid 2% or Benzoyl Peroxide. Avoid heavy oils. Keep pillowcases clean.",
        "routine": "Gentle Cleanser → BHA Toner → Oil-free Moisturizer → SPF 30+"
    },
    "eczema": {
        "title"  : "Eczema / Dermatitis",
        "advice" : "Focus on barrier repair. Use fragrance-free creams with Ceramides. Avoid long hot showers.",
        "routine": "Creamy Cleanser → Thick Ceramide Moisturizer (on damp skin) → Healing Ointment"
    },
    "pigmentation": {
        "title"  : "Hyperpigmentation",
        "advice" : "Daily sun protection is essential. Look for Vitamin C, Niacinamide, or Kojic Acid.",
        "routine": "Vitamin C Serum → Moisturizer → SPF 50+ (reapply every 2 hours outdoors)"
    },
    "rosacea": {
        "title"  : "Rosacea",
        "advice" : "Use gentle, fragrance-free products. Azelaic Acid can help. Avoid spicy food and alcohol.",
        "routine": "Gentle Cleanser → Azelaic Acid → Mineral SPF"
    },
    "dry": {
        "title"  : "Dry Skin",
        "advice" : "Layer hydration: hyaluronic acid serum followed by a rich moisturizer. Lock in with facial oil.",
        "routine": "Hydrating Cleanser → HA Serum → Rich Moisturizer → Facial Oil (night)"
    },
    "psoriasis": {
        "title"  : "Psoriasis",
        "advice" : "Use coal tar or salicylic acid shampoos. Moisturize heavily. Avoid triggers like stress and smoking.",
        "routine": "Gentle Cleanser → Heavy Emollient → Prescribed Topical → SPF 30+"
    },
    "melanoma": {
        "title"  : "Suspicious Lesion Detected",
        "advice" : "⚠️ Please see a dermatologist immediately. Do not delay — early detection is critical.",
        "routine": "Consult a dermatologist immediately for diagnosis and treatment."
    },
    "healthy": {
        "title"  : "Healthy Skin",
        "advice" : "Your skin looks great! Focus on maintenance, hydration, and consistent SPF use.",
        "routine": "Gentle Cleanser → Hydrating Serum → Moisturizer → SPF 30+"
    },
    "inconclusive": {
        "title"  : "Inconclusive Analysis",
        "advice" : "⚠️ Analysis uncertain. Please ensure you are in a bright room, hold the camera closer, and keep your face still.",
        "routine": "Retry Scan → Use Natural Light → Center Face in Frame"
    }
}

# ══════════════════════════════════════════════════════════════
# PRODUCTS DATABASE (used by /products endpoint & products.html)
# ══════════════════════════════════════════════════════════════
PRODUCTS_DB = {
    "acne": [
        {
            "id": "acne-1", "name": "CeraVe Acne Foaming Cream Cleanser",
            "brand": "CeraVe", "price": "₹899", "rating": 4.5, "reviews": 12400,
            "ingredient": "Benzoyl Peroxide 4%", "use": "Twice daily cleanser",
            "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=300&h=300&fit=crop",
            "badge": "Best Seller", "badge_color": "#00CC7E",
            "description": "Gentle foaming cleanser that treats and prevents acne without over-drying.",
            "where_to_buy": "https://www.amazon.in/s?k=cerave+acne+cleanser"
        },
        {
            "id": "acne-2", "name": "Paula's Choice BHA Liquid Exfoliant",
            "brand": "Paula's Choice", "price": "₹2,800", "rating": 4.8, "reviews": 34000,
            "ingredient": "Salicylic Acid 2%", "use": "Once daily after cleansing",
            "image": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=300&h=300&fit=crop",
            "badge": "Editor's Pick", "badge_color": "#0078FF",
            "description": "Cult-favorite BHA exfoliant that unclogs pores and smooths skin texture.",
            "where_to_buy": "https://www.amazon.in/s?k=paulas+choice+bha"
        },
        {
            "id": "acne-3", "name": "The Ordinary Niacinamide 10% + Zinc 1%",
            "brand": "The Ordinary", "price": "₹590", "rating": 4.4, "reviews": 89000,
            "ingredient": "Niacinamide 10%", "use": "Morning and evening serum",
            "image": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=300&h=300&fit=crop",
            "badge": "Best Value", "badge_color": "#FF9A00",
            "description": "Reduces blemishes, pore appearance, and controls excess oil production.",
            "where_to_buy": "https://www.amazon.in/s?k=ordinary+niacinamide"
        },
        {
            "id": "acne-4", "name": "La Roche-Posay Effaclar Duo+",
            "brand": "La Roche-Posay", "price": "₹1,650", "rating": 4.6, "reviews": 21000,
            "ingredient": "Benzoyl Peroxide 5.5%", "use": "Spot treatment",
            "image": "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=300&h=300&fit=crop",
            "badge": "Dermatologist Recommended", "badge_color": "#7B4FFF",
            "description": "Targets acne spots while preventing new breakouts from forming.",
            "where_to_buy": "https://www.amazon.in/s?k=la+roche+posay+effaclar"
        },
    ],
    "eczema": [
        {
            "id": "eczema-1", "name": "CeraVe Moisturizing Cream",
            "brand": "CeraVe", "price": "₹1,299", "rating": 4.8, "reviews": 67000,
            "ingredient": "Ceramides + Hyaluronic Acid", "use": "Twice daily on damp skin",
            "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=300&h=300&fit=crop",
            "badge": "Best Seller", "badge_color": "#00CC7E",
            "description": "Rich, non-greasy cream that restores the skin barrier with essential ceramides.",
            "where_to_buy": "https://www.amazon.in/s?k=cerave+moisturizing+cream"
        },
        {
            "id": "eczema-2", "name": "Vanicream Gentle Facial Cleanser",
            "brand": "Vanicream", "price": "₹950", "rating": 4.7, "reviews": 18000,
            "ingredient": "Fragrance-Free Formula", "use": "Daily gentle cleansing",
            "image": "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=300&h=300&fit=crop",
            "badge": "Sensitive Skin Safe", "badge_color": "#00C6FF",
            "description": "Free of dyes, fragrance, masking fragrance, lanolin, parabens, and formaldehyde.",
            "where_to_buy": "https://www.amazon.in/s?k=vanicream+cleanser"
        },
        {
            "id": "eczema-3", "name": "Aquaphor Healing Ointment",
            "brand": "Aquaphor", "price": "₹750", "rating": 4.9, "reviews": 45000,
            "ingredient": "Petrolatum 41%", "use": "Night — seals in moisture",
            "image": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=300&h=300&fit=crop",
            "badge": "Dermatologist Recommended", "badge_color": "#7B4FFF",
            "description": "Protects and heals dry, cracked, and irritated skin overnight.",
            "where_to_buy": "https://www.amazon.in/s?k=aquaphor+healing+ointment"
        },
        {
            "id": "eczema-4", "name": "Aveeno Eczema Therapy Daily Moisturizing Cream",
            "brand": "Aveeno", "price": "₹1,100", "rating": 4.5, "reviews": 29000,
            "ingredient": "Colloidal Oatmeal 1%", "use": "Daily moisturizer for eczema",
            "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=300&h=300&fit=crop",
            "badge": "Clinically Tested", "badge_color": "#0078FF",
            "description": "Steroid-free formula clinically shown to relieve itchy, irritated eczema-prone skin.",
            "where_to_buy": "https://www.amazon.in/s?k=aveeno+eczema+therapy"
        },
    ],
    "pigmentation": [
        {
            "id": "pig-1", "name": "TruSkin Vitamin C Serum",
            "brand": "TruSkin", "price": "₹1,450", "rating": 4.4, "reviews": 56000,
            "ingredient": "Vitamin C 20% + Hyaluronic Acid", "use": "Every morning before SPF",
            "image": "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=300&h=300&fit=crop",
            "badge": "Best Seller", "badge_color": "#00CC7E",
            "description": "Brightens dark spots, evens skin tone, and boosts collagen production.",
            "where_to_buy": "https://www.amazon.in/s?k=truskin+vitamin+c+serum"
        },
        {
            "id": "pig-2", "name": "The Ordinary Alpha Arbutin 2% + HA",
            "brand": "The Ordinary", "price": "₹750", "rating": 4.5, "reviews": 41000,
            "ingredient": "Alpha Arbutin 2%", "use": "Morning and night serum",
            "image": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=300&h=300&fit=crop",
            "badge": "Best Value", "badge_color": "#FF9A00",
            "description": "Reduces the appearance of dark spots and hyperpigmentation over time.",
            "where_to_buy": "https://www.amazon.in/s?k=ordinary+alpha+arbutin"
        },
        {
            "id": "pig-3", "name": "EltaMD UV Clear Broad-Spectrum SPF 46",
            "brand": "EltaMD", "price": "₹3,200", "rating": 4.8, "reviews": 38000,
            "ingredient": "Zinc Oxide + Niacinamide", "use": "Every morning — last step",
            "image": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=300&h=300&fit=crop",
            "badge": "Dermatologist #1 Pick", "badge_color": "#7B4FFF",
            "description": "Lightweight SPF that protects against UV-induced pigmentation and dark spots.",
            "where_to_buy": "https://www.amazon.in/s?k=eltamd+uv+clear+spf"
        },
        {
            "id": "pig-4", "name": "Murad Rapid Age Spot Correcting Serum",
            "brand": "Murad", "price": "₹4,500", "rating": 4.6, "reviews": 11000,
            "ingredient": "Hydroquinone 2% + Glycolic Acid", "use": "Night serum on dark spots",
            "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=300&h=300&fit=crop",
            "badge": "Fast Acting", "badge_color": "#FF9A00",
            "description": "Visibly reduces dark spots and sun damage in as little as 1 week.",
            "where_to_buy": "https://www.amazon.in/s?k=murad+dark+spot+serum"
        },
    ],
    "rosacea": [
        {
            "id": "ros-1", "name": "La Roche-Posay Toleriane Hydrating Gentle Cleanser",
            "brand": "La Roche-Posay", "price": "₹1,100", "rating": 4.7, "reviews": 24000,
            "ingredient": "Ceramides + Niacinamide", "use": "Daily gentle cleanser",
            "image": "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=300&h=300&fit=crop",
            "badge": "Rosacea Safe", "badge_color": "#00CC7E",
            "description": "Ultra-gentle cleanser that soothes redness without stripping the skin barrier.",
            "where_to_buy": "https://www.amazon.in/s?k=la+roche+posay+toleriane"
        },
        {
            "id": "ros-2", "name": "The Ordinary Azelaic Acid Suspension 10%",
            "brand": "The Ordinary", "price": "₹650", "rating": 4.3, "reviews": 19000,
            "ingredient": "Azelaic Acid 10%", "use": "Twice daily after cleanser",
            "image": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=300&h=300&fit=crop",
            "badge": "Best Value", "badge_color": "#FF9A00",
            "description": "Reduces redness, flushing, and bumps associated with rosacea.",
            "where_to_buy": "https://www.amazon.in/s?k=ordinary+azelaic+acid"
        },
        {
            "id": "ros-3", "name": "EltaMD UV Physical Broad-Spectrum SPF 41",
            "brand": "EltaMD", "price": "₹2,800", "rating": 4.7, "reviews": 16000,
            "ingredient": "Zinc Oxide + Titanium Dioxide", "use": "Daily mineral sunscreen",
            "image": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=300&h=300&fit=crop",
            "badge": "Rosacea Friendly", "badge_color": "#7B4FFF",
            "description": "100% mineral SPF that doesn't trigger rosacea flare-ups.",
            "where_to_buy": "https://www.amazon.in/s?k=eltamd+uv+physical"
        },
        {
            "id": "ros-4", "name": "Avene Antirougeurs Fort Relief Concentrate",
            "brand": "Avene", "price": "₹2,200", "rating": 4.5, "reviews": 8000,
            "ingredient": "Ruscus Extract + Vitamin PP", "use": "Morning serum for redness",
            "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=300&h=300&fit=crop",
            "badge": "Clinically Proven", "badge_color": "#0078FF",
            "description": "Visibly reduces persistent redness and diffuse rosacea over time.",
            "where_to_buy": "https://www.amazon.in/s?k=avene+antirougeurs"
        },
    ],
    "dry": [
        {
            "id": "dry-1", "name": "Neutrogena Hydro Boost Water Gel",
            "brand": "Neutrogena", "price": "₹799", "rating": 4.5, "reviews": 43000,
            "ingredient": "Hyaluronic Acid", "use": "Daily lightweight moisturizer",
            "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=300&h=300&fit=crop",
            "badge": "Best Seller", "badge_color": "#00CC7E",
            "description": "Oil-free water gel that quenches dry skin and keeps it hydrated all day.",
            "where_to_buy": "https://www.amazon.in/s?k=neutrogena+hydro+boost"
        },
        {
            "id": "dry-2", "name": "The Inkey List Hyaluronic Acid Serum",
            "brand": "The Inkey List", "price": "₹950", "rating": 4.4, "reviews": 22000,
            "ingredient": "Hyaluronic Acid 2%", "use": "On damp skin before moisturizer",
            "image": "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=300&h=300&fit=crop",
            "badge": "Best Value", "badge_color": "#FF9A00",
            "description": "Draws moisture into the skin for lasting plumpness and hydration.",
            "where_to_buy": "https://www.amazon.in/s?k=inkey+list+hyaluronic+acid"
        },
        {
            "id": "dry-3", "name": "Tatcha The Dewy Skin Cream",
            "brand": "Tatcha", "price": "₹6,500", "rating": 4.7, "reviews": 17000,
            "ingredient": "Squalane + Japanese Purple Rice", "use": "Night — rich moisturizer",
            "image": "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=300&h=300&fit=crop",
            "badge": "Luxury Pick", "badge_color": "#7B4FFF",
            "description": "Ultra-rich plumping cream that deeply nourishes very dry skin overnight.",
            "where_to_buy": "https://www.amazon.in/s?k=tatcha+dewy+skin+cream"
        },
        {
            "id": "dry-4", "name": "The Ordinary 100% Plant-Derived Squalane",
            "brand": "The Ordinary", "price": "₹720", "rating": 4.6, "reviews": 31000,
            "ingredient": "Squalane 100%", "use": "Night — final sealing step",
            "image": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=300&h=300&fit=crop",
            "badge": "Best Value", "badge_color": "#FF9A00",
            "description": "Lightweight facial oil that seals in all moisture without clogging pores.",
            "where_to_buy": "https://www.amazon.in/s?k=ordinary+squalane"
        },
    ],
    "psoriasis": [
        {
            "id": "pso-1", "name": "Neutrogena T/Gel Therapeutic Shampoo",
            "brand": "Neutrogena", "price": "₹650", "rating": 4.4, "reviews": 28000,
            "ingredient": "Coal Tar 0.5%", "use": "2-3 times per week",
            "image": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=300&h=300&fit=crop",
            "badge": "Clinically Proven", "badge_color": "#0078FF",
            "description": "Controls scalp psoriasis, seborrheic dermatitis, and dandruff.",
            "where_to_buy": "https://www.amazon.in/s?k=neutrogena+tgel"
        },
        {
            "id": "pso-2", "name": "MG217 Psoriasis Medicated Moisturizer",
            "brand": "MG217", "price": "₹1,800", "rating": 4.3, "reviews": 9000,
            "ingredient": "Salicylic Acid 3%", "use": "Daily on affected areas",
            "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=300&h=300&fit=crop",
            "badge": "Psoriasis Safe", "badge_color": "#00CC7E",
            "description": "Softens and removes psoriasis scales while moisturizing dry patches.",
            "where_to_buy": "https://www.amazon.in/s?k=mg217+psoriasis"
        },
        {
            "id": "pso-3", "name": "CeraVe Psoriasis Moisturizing Cream",
            "brand": "CeraVe", "price": "₹1,400", "rating": 4.5, "reviews": 14000,
            "ingredient": "Salicylic Acid + Ceramides", "use": "Twice daily moisturizer",
            "image": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=300&h=300&fit=crop",
            "badge": "Dermatologist Recommended", "badge_color": "#7B4FFF",
            "description": "Gently removes scales and helps restore the skin barrier in psoriasis.",
            "where_to_buy": "https://www.amazon.in/s?k=cerave+psoriasis+cream"
        },
    ],
    "healthy": [
        {
            "id": "hlt-1", "name": "CeraVe Hydrating Facial Cleanser",
            "brand": "CeraVe", "price": "₹799", "rating": 4.7, "reviews": 78000,
            "ingredient": "Ceramides + Hyaluronic Acid", "use": "Twice daily cleanser",
            "image": "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=300&h=300&fit=crop",
            "badge": "Best Seller", "badge_color": "#00CC7E",
            "description": "Gentle daily cleanser that hydrates while removing makeup and impurities.",
            "where_to_buy": "https://www.amazon.in/s?k=cerave+hydrating+cleanser"
        },
        {
            "id": "hlt-2", "name": "Supergoop Unseen Sunscreen SPF 40",
            "brand": "Supergoop", "price": "₹2,900", "rating": 4.6, "reviews": 29000,
            "ingredient": "Zinc Oxide + Red Algae", "use": "Every morning — final step",
            "image": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=300&h=300&fit=crop",
            "badge": "Editor's Pick", "badge_color": "#0078FF",
            "description": "Invisible, oil-free SPF that wears perfectly under makeup.",
            "where_to_buy": "https://www.amazon.in/s?k=supergoop+unseen+sunscreen"
        },
        {
            "id": "hlt-3", "name": "The Ordinary Hyaluronic Acid 2% + B5",
            "brand": "The Ordinary", "price": "₹590", "rating": 4.4, "reviews": 62000,
            "ingredient": "Hyaluronic Acid + Vitamin B5", "use": "Daily hydrating serum",
            "image": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=300&h=300&fit=crop",
            "badge": "Best Value", "badge_color": "#FF9A00",
            "description": "Multi-depth hydration serum that plumps and smooths healthy skin.",
            "where_to_buy": "https://www.amazon.in/s?k=ordinary+hyaluronic+acid+b5"
        },
    ],
    "inconclusive": [
        {
            "id": "inc-1", "name": "Lighting & Angle Guide",
            "brand": "AURA Tips", "price": "Free", "rating": 5.0, "reviews": 100,
            "ingredient": "Better Photos", "use": "Scan optimization",
            "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=300&h=300&fit=crop",
            "badge": "Required", "badge_color": "#FF4D6A",
            "description": "Ensure sunlight is hitting your face directly. Avoid overhead shadows.",
            "where_to_buy": "#"
        }
    ],
}

# ══════════════════════════════════════════════════════════════
# HF LABEL MAPPING (covers all common model output formats)
# ══════════════════════════════════════════════════════════════
HF_LABEL_MAP = {
    # Acne
    "acne"                        : "acne",
    "acne and rosacea"            : "acne",
    "acne vulgaris"               : "acne",
    "pimple"                      : "acne",
    "pimples"                     : "acne",
    "pustule"                     : "acne",
    "pustules"                    : "acne",
    "breakout"                    : "acne",
    "breakouts"                   : "acne",
    "comedones"                   : "acne",
    "comedonal acne"              : "acne",
    "inflammatory acne"           : "acne",
    "cystic acne"                 : "acne",
    "nodular acne"                : "acne",
    "blemish"                     : "acne",
    "blemishes"                   : "acne",
    "spotty skin"                 : "acne",
    "blackhead"                   : "acne",
    "level 1"                     : "acne",
    "level 2"                     : "acne",
    "level 3"                     : "acne",
    "mild acne"                   : "acne",
    "moderate acne"               : "acne",
    "severe acne"                 : "acne",
    # Eczema
    "eczema"                      : "eczema",
    "atopic dermatitis"           : "eczema",
    "dermatitis"                  : "eczema",
    "contact dermatitis"          : "eczema",
    "seborrheic dermatitis"       : "eczema",
    # Pigmentation
    "hyperpigmentation"           : "pigmentation",
    "melasma"                     : "pigmentation",
    "dark spots"                  : "pigmentation",
    "pigmented benign keratosis"  : "pigmentation",
    "lentigo"                     : "pigmentation",
    # Rosacea
    "rosacea"                     : "rosacea",
    "redness"                     : "rosacea",
    # Dry / Psoriasis
    "dry skin"                    : "dry",
    "xerosis"                     : "dry",
    "psoriasis"                   : "psoriasis",
    "flaky skin"                  : "dry",
    # Cancer / serious
    "melanoma"                    : "melanoma",
    "basal cell carcinoma"        : "melanoma",
    "squamous cell carcinoma"     : "melanoma",
    "actinic keratosis"           : "melanoma",
    # Healthy
    "normal"                      : "healthy",
    "normal skin"                 : "healthy",
    "healthy skin"                : "healthy",
    "clear skin"                  : "healthy",
    "clear"                       : "healthy",
    "no disease"                  : "healthy",
    "level 0"                     : "healthy",
}

def map_hf_label(label: str) -> str:
    label_lower = label.lower().strip()
    if label_lower in HF_LABEL_MAP:
        return HF_LABEL_MAP[label_lower]
    for key, kb_key in HF_LABEL_MAP.items():
        if key in label_lower or label_lower in key:
            return kb_key
    return "healthy"

def confidence_to_severity(confidence: float) -> str:
    if confidence >= 0.80: return "High"
    if confidence >= 0.50: return "Medium"
    return "Low"

def build_remedies(kb_key: str) -> list:
    advice = KB.get(kb_key, KB["healthy"])
    return [
        {"title": "Daily Routine", "desc": advice["routine"]},
        {"title": "Key Advice",    "desc": advice["advice"]},
    ]

def build_products(kb_key: str) -> list:
    """Return top 2 products for scan results panel."""
    prods = PRODUCTS_DB.get(kb_key, PRODUCTS_DB["healthy"])
    return [
        {"name": p["name"], "use": p["use"], "ingredient": p["ingredient"]}
        for p in prods[:2]
    ]

# ══════════════════════════════════════════════════════════════
# CHATBOT
# ══════════════════════════════════════════════════════════════
KB_CHAT = {
    ("acne", "pimple", "breakout", "spot"):
        lambda: f"💊 {KB['acne']['advice']}\n\nRoutine: {KB['acne']['routine']}",
    ("eczema", "dermatitis", "itchy", "rash"):
        lambda: f"🌿 {KB['eczema']['advice']}\n\nRoutine: {KB['eczema']['routine']}",
    ("pigmentation", "dark spot", "uneven", "hyperpigmentation"):
        lambda: f"✨ {KB['pigmentation']['advice']}\n\nRoutine: {KB['pigmentation']['routine']}",
    ("rosacea", "redness", "flushing"):
        lambda: f"🌸 {KB['rosacea']['advice']}\n\nRoutine: {KB['rosacea']['routine']}",
    ("dry", "flaky", "tight", "dehydrated"):
        lambda: f"💧 {KB['dry']['advice']}\n\nRoutine: {KB['dry']['routine']}",
    ("psoriasis", "scaly", "plaques"):
        lambda: f"🩺 {KB['psoriasis']['advice']}\n\nRoutine: {KB['psoriasis']['routine']}",
    ("moistur", "hydrat"):
        lambda: "💧 Moisturize twice daily — morning and night. Apply while skin is still slightly damp. Look for Hyaluronic Acid, Glycerin, or Ceramides.",
    ("spf", "sunscreen", "sun protect"):
        lambda: "☀️ SPF is the single most effective anti-aging product. Use SPF 30+ every morning even on cloudy days. Reapply every 2 hours outdoors.",
    ("ingredient", "avoid", "bad ingredient", "paraben"):
        lambda: "⚠️ Avoid: Parabens, SLS/SLES sulfates, synthetic fragrances, denatured alcohol, and formaldehyde-releasing preservatives.",
    ("doctor", "dermatologist", "see a doctor", "when"):
        lambda: "🩺 See a dermatologist if symptoms persist more than 2 weeks, worsen suddenly, are painful, or accompany a fever. Book right here in AURA!",
    ("routine", "regimen"):
        lambda: "📋 Basic routine: Cleanser → Serum → Moisturizer → SPF (AM). At night: Cleanser → Treatment → Rich Moisturizer.",
    ("skin type", "what type", "oily", "combination", "sensitive"):
        lambda: "🔍 Skin types: Normal, Oily (shiny/large pores), Dry (tight/flaky), Combination (oily T-zone), Sensitive (reacts easily). AURA's AI scan can identify yours!",
    ("hello", "hi", "hey", "help"):
        lambda: "👋 Hi! I'm AURA's AI skincare assistant. Ask me about skin conditions, routines, ingredients, or when to see a doctor! 🌿",
    ("product", "recommend", "buy", "suggest"):
        lambda: "🛍️ Check out the Products page in your dashboard for condition-specific product recommendations with prices and where to buy!",
    ("scan", "result", "confidence", "severity"):
        lambda: "🔬 Your scan shows Detected Condition, Severity (Low/Medium/High), and Confidence Score. Low = minor concern. High = see a dermatologist soon.",
}

DEFAULT_RESPONSE = "🌿 I can help with skin conditions (acne, eczema, pigmentation, rosacea, dry skin, psoriasis), routines, ingredients, and product recommendations. What would you like to know?"

def keyword_response(message: str) -> str:
    msg = message.lower()
    for keywords, fn in KB_CHAT.items():
        if any(w in msg for w in keywords):
            return fn()
    return DEFAULT_RESPONSE

# ── Try local ML classifier (optional) ────────────────────────
classifier = None
try:
    from skincare_classifier import SkincareClassifier
    classifier = SkincareClassifier()
    print("✅ SkincareClassifier loaded.")
except Exception as e:
    print(f"⚠️  ML model not loaded ({e}). Using HuggingFace API.")


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status"      : "ok",
        "version"     : "4.0",
        "ml_model"    : classifier is not None,
        "hf_token"    : bool(HF_TOKEN),
        "supabase"    : bool(SUPABASE_URL),
        "n8n_chat"    : bool(N8N_CHAT_WEBHOOK),
        "n8n_booking" : bool(N8N_BOOKING_WEBHOOK),
    }

# ── PRODUCTS endpoint ──────────────────────────────────────────
@app.get("/products")
async def get_all_products():
    """Return all products for the products page."""
    return {"products": PRODUCTS_DB, "categories": list(PRODUCTS_DB.keys())}

@app.get("/products/{condition}")
async def get_products_by_condition(condition: str):
    """Return products for a specific skin condition."""
    prods = PRODUCTS_DB.get(condition.lower(), PRODUCTS_DB["healthy"])
    return {"condition": condition, "products": prods, "count": len(prods)}

# ── CHAT ───────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    if N8N_CHAT_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(N8N_CHAT_WEBHOOK, json={
                    "message": req.message, "user_id": req.user_id, "source": "aura-chat"
                })
                if resp.status_code == 200:
                    data = resp.json()
                    return {"response": data.get("response", keyword_response(req.message)), "source": "n8n"}
        except Exception as e:
            print(f"⚠️  n8n chat webhook failed: {e}")
    return {"response": keyword_response(req.message), "source": "kb"}

# ── PREDICT ────────────────────────────────────────────────────
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    result = None

    # Priority 1: Local ML classifier
    if classifier is not None:
        tmp_path = "/tmp/aura_scan.jpg"
        with open(tmp_path, "wb") as f:
            f.write(contents)
        try:
            raw      = classifier.classify(tmp_path)
            pred_key = raw.get("prediction") or raw.get("condition", "healthy")
            advice   = KB.get(pred_key, KB["healthy"])
            result   = {
                "condition" : advice["title"],
                "severity"  : raw.get("severity", "Medium"),
                "confidence": raw.get("confidence", 0.75),
                "advice"    : advice,
                "remedies"  : build_remedies(pred_key),
                "products"  : build_products(pred_key),
                "source"    : "local-ml",
            }
        except Exception as e:
            print(f"⚠️  Local classifier error: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # Priority 2: HuggingFace API — try each model until one works
    if result is None and HF_TOKEN:
        for model_url in HF_MODELS:
            try:
                print(f"🔍 Trying model: {model_url}")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        model_url,
                        headers={"Authorization": f"Bearer {HF_TOKEN}"},
                        content=contents,
                    )

                print(f"📊 Status: {resp.status_code} | Response: {resp.text[:300]}")

                if resp.status_code == 200:
                    hf_results = resp.json()
                    if isinstance(hf_results, list) and len(hf_results) > 0:
                        # --- Clinical Sensitivity Logic ---
                        # Goal: Prioritize potential conditions even if "Healthy" is slightly higher.
                        best_candidate = None # (score, label, kb_key)
                        
                        for entry in hf_results[:5]: # look at top 5 candidates
                            l   = entry.get("label", "healthy")
                            s   = float(entry.get("score", 0.0))
                            k   = map_hf_label(l)
                            
                            # If it's a known condition (not healthy/inconclusive) and has > 10% score
                            if k not in ["healthy", "inconclusive"] and s > 0.10:
                                # Prioritize the first significant condition found
                                # (usually the most specific one if the model is well-ordered)
                                if best_candidate is None or s > best_candidate[0]:
                                    best_candidate = (s, l, k)
                        
                        # Fallback to top result if no significant conditions found
                        if best_candidate is None:
                            top        = hf_results[0]
                            label      = top.get("label", "healthy")
                            confidence = float(top.get("score", 0.75))
                            kb_key     = map_hf_label(label)
                        else:
                            confidence, label, kb_key = best_candidate

                        # Guard against low confidence "healthy" results
                        if kb_key == "healthy" and confidence < 0.20:
                            print(f"⚠️ Low confidence ({confidence:.2f}) for 'healthy'. Marking as inconclusive.")
                            kb_key = "inconclusive"

                        advice     = KB.get(kb_key, KB["healthy"])
                        result     = {
                            "condition" : advice["title"],
                            "severity"  : "Inconclusive" if kb_key == "inconclusive" else confidence_to_severity(confidence),
                            "confidence": round(confidence, 3),
                            "advice"    : advice,
                            "remedies"  : build_remedies(kb_key),
                            "products"  : build_products(kb_key),
                            "source"    : "huggingface",
                            "raw_label" : label,
                            "all_labels": hf_results[:3],
                        }
                        print(f"✅ Resolved: {label} ({confidence:.0%}) → {kb_key} [{'Condition' if best_candidate else 'Normal'}]")
                        break

                elif resp.status_code == 503:
                    print(f"⏳ Model loading (503) — trying next model")
                    continue

            except Exception as e:
                print(f"⚠️  Model error ({model_url}): {e}")
                continue

    # Priority 3: Mock fallback
    if result is None:
        print("⚠️  All models failed. Using mock data. Check HF_TOKEN and model availability.")
        result = {
            "condition" : KB["healthy"]["title"],
            "severity"  : "Low",
            "confidence": 0.88,
            "advice"    : KB["healthy"],
            "remedies"  : build_remedies("healthy"),
            "products"  : build_products("healthy"),
            "source"    : "mock",
        }

    # n8n scan webhook (fire-and-forget)
    if N8N_SCAN_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(N8N_SCAN_WEBHOOK, json={
                    "condition" : result["condition"],
                    "severity"  : result["severity"],
                    "confidence": result["confidence"],
                    "source"    : "aura-scan",
                })
        except Exception:
            pass

    return result

# ── BOOK APPOINTMENT ───────────────────────────────────────────
@app.post("/book-appointment")
async def book_appointment(req: AppointmentRequest):
    # Supabase — uncomment when ready
    # from supabase import create_client
    # sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    # sb.table("appointments").insert({...}).execute()

    if N8N_BOOKING_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(N8N_BOOKING_WEBHOOK, json={
                    "user_name": req.user_name, "user_email": req.user_email,
                    "doctor_name": req.doctor_name, "doctor_specialty": req.doctor_specialty,
                    "preferred_date": req.preferred_date or "To be confirmed",
                    "notes": req.notes or "", "source": "aura-booking",
                })
        except Exception as e:
            print(f"⚠️  n8n booking webhook failed: {e}")

    return {
        "status"     : "success",
        "message"    : f"Appointment request for {req.doctor_name} has been submitted.",
        "appointment": {
            "doctor": req.doctor_name, "specialty": req.doctor_specialty,
            "user": req.user_name, "date": req.preferred_date or "To be confirmed",
            "notes": req.notes or "",
        }
    }

# ── GET APPOINTMENTS ───────────────────────────────────────────
@app.get("/appointments/{user_id}")
async def get_appointments(user_id: str):
    # from supabase import create_client
    # sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    # data = sb.table("appointments").select("*").eq("user_id", user_id).execute()
    # return {"appointments": data.data}
    return {"appointments": [], "message": "Connect Supabase to load real appointments."}

# ── HTML PAGES ─────────────────────────────────────────────────
@app.get("/dashboard")
@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/products.html")
@app.get("/products-page")
async def serve_products():
    return FileResponse("products.html")

@app.get("/admin")
@app.get("/admin.html")
async def serve_admin():
    return FileResponse("admin.html")

# Static mount — MUST be last
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
