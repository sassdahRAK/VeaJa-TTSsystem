"""
gui/pages/api_keys_mixin.py — My API Key Page
==============================================
Password-protected page for storing third-party AI API keys.
"""

import hashlib

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QStackedWidget
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont

_LOCK_TIMEOUT_MS = 300_000   # 5 minutes — enough time to fill in keys without rushing

# ── Provider definitions ──────────────────────────────────────────────────────
# Tuple: (name, subtitle, profile_key, placeholder, docs_url,
#         description, logo_svg_body, logo_color, badge)
# badge: None | "Recommended" | "Highly Recommended"

_PROVIDERS = [
    # ── Voice / TTS ───────────────────────────────────────────────────────────
    (
        "ElevenLabs",
        "Natural TTS · Voice Cloning · Multilingual",
        "api_key_elevenlabs", "…",
        "https://elevenlabs.io/app/settings/api-keys",
        "HIGHLY RECOMMENDED for voice. ElevenLabs produces the most human-like, "
        "natural-sounding speech available — far superior to system TTS. "
        "Connect to replace Veaja's built-in voice engine with studio-quality narration. "
        "Also powers Video script narration and voice cloning.",
        '<ellipse cx="12" cy="12" rx="9" ry="9" stroke="#f97316" stroke-width="1.8" fill="none"/>'
        '<path d="M9 9 V15 M12 7 V17 M15 9 V15" stroke="#f97316" stroke-width="1.8" '
        'stroke-linecap="round"/>',
        "#f97316",
        "Highly Recommended",
    ),
    (
        "OpenAI TTS",
        "TTS-1 · TTS-1-HD · Whisper STT",
        "api_key_openai", "sk-…",
        "https://platform.openai.com/api-keys",
        "RECOMMENDED for voice. OpenAI's TTS-1-HD model produces very natural speech "
        "with 6 built-in voices. Same API key as GPT — no extra setup needed. "
        "Also enables Whisper speech-to-text for future dictation features.",
        '<circle cx="12" cy="12" r="8" stroke="#10a37f" stroke-width="2" fill="none"/>'
        '<circle cx="12" cy="12" r="3" fill="#10a37f"/>',
        "#10a37f",
        "Recommended",
    ),
    # ── Code / Development ────────────────────────────────────────────────────
    (
        "Anthropic Claude",
        "Claude 3.5 Sonnet · Haiku · Opus",
        "api_key_claude", "sk-ant-…",
        "https://console.anthropic.com/settings/keys",
        "HIGHLY RECOMMENDED for Code tab. Claude 3.5 Sonnet is widely regarded as the "
        "best model for code explanation, debugging, and structured analysis. "
        "Excels at following complex instructions and producing detailed, accurate output. "
        "Also best for Instruction and long-document Summary.",
        '<path d="M12 3 L21 20 H3 Z" stroke="#d97706" stroke-width="1.8" fill="none" '
        'stroke-linejoin="round"/>'
        '<line x1="7.5" y1="15" x2="16.5" y2="15" stroke="#d97706" stroke-width="1.8"/>',
        "#d97706",
        "Highly Recommended",
    ),
    (
        "GitHub Copilot",
        "Code completion · Chat · GPT-4o powered",
        "api_key_copilot", "ghp_…",
        "https://github.com/settings/tokens",
        "RECOMMENDED for code features. Copilot is purpose-built for code — "
        "it understands context across files and produces accurate completions. "
        "Use a GitHub Personal Access Token with Copilot scope. "
        "Powers the Code tab's explain and analyse features.",
        '<path d="M12 2 C6.48 2 2 6.48 2 12 C2 16.42 4.87 20.17 8.84 21.5 '
        'C9.34 21.58 9.5 21.27 9.5 21 V19.28 C6.73 19.91 6.14 17.97 6.14 17.97 '
        'C5.68 16.81 5.03 16.5 5.03 16.5 C4.12 15.88 5.1 15.9 5.1 15.9 '
        'C6.1 15.97 6.63 16.93 6.63 16.93 C7.5 18.45 8.97 18 9.54 17.76 '
        'C9.63 17.11 9.89 16.67 10.17 16.42 C7.95 16.17 5.62 15.31 5.62 11.5 '
        'C5.62 10.39 6.01 9.48 6.65 8.77 C6.55 8.52 6.2 7.5 6.75 6.15 '
        'C6.75 6.15 7.59 5.88 9.5 7.17 C10.29 6.95 11.15 6.84 12 6.84 '
        'C12.85 6.84 13.71 6.95 14.5 7.17 C16.41 5.88 17.25 6.15 17.25 6.15 '
        'C17.8 7.5 17.45 8.52 17.35 8.77 C17.99 9.48 18.38 10.39 18.38 11.5 '
        'C18.38 15.32 16.04 16.16 13.81 16.41 C14.17 16.72 14.5 17.33 14.5 18.26 '
        'V21 C14.5 21.27 14.66 21.59 15.17 21.5 C19.14 20.16 22 16.42 22 12 '
        'C22 6.48 17.52 2 12 2 Z" fill="#1f2328"/>',
        "#1f2328",
        "Recommended",
    ),
    (
        "Amazon CodeWhisperer",
        "Code generation · Security scanning",
        "api_key_codewhisperer", "…",
        "https://aws.amazon.com/codewhisperer/",
        "Good for: AWS-focused code generation and security vulnerability scanning. "
        "Free tier available. Useful for the Code tab when working with cloud infrastructure.",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#ff9900"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">AWS</text>',
        "#ff9900",
        None,
    ),
    # ── General AI / Generate ─────────────────────────────────────────────────
    (
        "Google Gemini",
        "Gemini 1.5 Pro · Flash · Ultra",
        "api_key_gemini", "AIza…",
        "https://aistudio.google.com/app/apikey",
        "RECOMMENDED for Generate features. Gemini 1.5 Pro handles up to 1M tokens — "
        "ideal for Slide, HTML, and Video generation from long documents. "
        "Flash is extremely fast and cost-effective for Summary and Translate.",
        '<path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z" '
        'fill="#4285f4"/>',
        "#4285f4",
        "Recommended",
    ),
    (
        "Google AI Studio",
        "Gemini via AI Studio (free tier)",
        "api_key_aistudio", "AIza…",
        "https://aistudio.google.com/app/apikey",
        "Free-tier access to Gemini models. Same key as Gemini above. "
        "Generous free quota — ideal for testing all Generate and Summary features "
        "without any cost.",
        '<path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z" '
        'fill="#34a853"/>',
        "#34a853",
        None,
    ),
    (
        "Mistral AI",
        "Mistral Large · Small · Nemo",
        "api_key_mistral", "…",
        "https://console.mistral.ai/api-keys",
        "Fast, efficient text generation and code. Open-weight models. "
        "Great for Prompt, Caption, and Adjust generate modes at low cost.",
        '<path d="M4 6 H20 M4 12 H20 M4 18 H20" stroke="#ff7000" stroke-width="2.2" '
        'stroke-linecap="round"/>',
        "#ff7000",
        None,
    ),
    (
        "Cohere",
        "Command R+ · Command R",
        "api_key_cohere", "…",
        "https://dashboard.cohere.com/api-keys",
        "Best for RAG, summarisation, and translation. "
        "Command R+ is optimised for long-context document tasks — ideal for the Summary feature.",
        '<circle cx="12" cy="12" r="9" stroke="#39594d" stroke-width="2" fill="none"/>'
        '<path d="M8 12 Q12 7 16 12 Q12 17 8 12 Z" fill="#39594d"/>',
        "#39594d",
        None,
    ),
    (
        "Microsoft Copilot / Azure OpenAI",
        "GPT-4o via Azure · Copilot Studio",
        "api_key_azure_openai", "…",
        "https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub",
        "Enterprise-grade OpenAI models hosted on Azure. "
        "Same GPT-4o capability with data residency and compliance guarantees. "
        "Use for Generate, Code, and Summary in enterprise environments.",
        '<rect x="2" y="2" width="20" height="20" rx="3" fill="#0078d4"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="9" font-weight="bold" '
        'fill="white" font-family="Arial">Az</text>',
        "#0078d4",
        None,
    ),
    # ── Translation ───────────────────────────────────────────────────────────
    (
        "DeepL",
        "Translation API — best quality",
        "api_key_deepl", "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx",
        "https://www.deepl.com/account/summary",
        "HIGHLY RECOMMENDED for Translate tab. DeepL consistently produces the most "
        "natural, fluent translations — especially for European languages. "
        "Free tier: 500,000 chars/month.",
        '<path d="M12 3 C7 3 3 7 3 12 S7 21 12 21 S21 17 21 12 S17 3 12 3 Z" '
        'fill="#0f2b46"/>'
        '<text x="12" y="16" text-anchor="middle" font-size="9" font-weight="bold" '
        'fill="white" font-family="Arial">DL</text>',
        "#0f2b46",
        "Highly Recommended",
    ),
    (
        "LibreTranslate",
        "Self-hosted · Public endpoint · Free",
        "api_key_libretranslate", "optional — leave blank for public endpoint",
        "https://libretranslate.com",
        "Privacy-first translation — data never leaves your machine when self-hosted. "
        "Free public endpoint available. Good fallback when DeepL quota is exhausted.",
        '<rect x="3" y="3" width="18" height="18" rx="3" stroke="#3b82f6" '
        'stroke-width="1.8" fill="none"/>'
        '<path d="M7 12 H17 M12 7 V17" stroke="#3b82f6" stroke-width="1.8" '
        'stroke-linecap="round"/>',
        "#3b82f6",
        None,
    ),
    # ── Image / Media ─────────────────────────────────────────────────────────
    (
        "Stability AI",
        "Stable Diffusion · SDXL · SD3",
        "api_key_stability", "sk-…",
        "https://platform.stability.ai/account/keys",
        "Best for image generation in Generate → Poster and Generate → Slide. "
        "Produces high-quality images from text prompts. "
        "Connect to enable real AI-generated visuals in your exports.",
        '<circle cx="12" cy="12" r="9" fill="#6c2bd9"/>'
        '<path d="M8 12 Q10 8 12 12 Q14 16 16 12" stroke="white" stroke-width="1.8" '
        'fill="none" stroke-linecap="round"/>',
        "#6c2bd9",
        None,
    ),
    # ── Legal (Lawyer) ────────────────────────────────────────────────────────
    (
        "Harvey AI",
        "Legal research · Contract analysis · Drafting",
        "api_key_harvey", "…",
        "https://www.harvey.ai",
        "RECOMMENDED for legal professionals. Harvey is purpose-built for law — "
        "trained on legal corpora for contract review, due diligence, litigation research, "
        "and legal document drafting. Used by top law firms globally. "
        "Best for Generate → Instruction (legal briefs) and Summary (contracts).",
        '<rect x="3" y="3" width="18" height="18" rx="3" fill="#1a1a2e"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="#e8c97e" font-family="Arial">HV</text>',
        "#1a1a2e",
        "Recommended",
    ),
    (
        "Casetext CoCounsel",
        "Legal AI · Case law · Contract review",
        "api_key_casetext", "…",
        "https://casetext.com/cocounsel",
        "Best for: US case law research, deposition preparation, contract analysis, "
        "and legal document summarisation. Powered by GPT-4 with legal-specific fine-tuning. "
        "Ideal for the Summary tab when processing legal documents.",
        '<circle cx="12" cy="12" r="9" stroke="#2563eb" stroke-width="1.8" fill="none"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="7" font-weight="bold" '
        'fill="#2563eb" font-family="Arial">CC</text>',
        "#2563eb",
        None,
    ),
    (
        "Lexis+ AI",
        "Legal research · Brief drafting · LexisNexis",
        "api_key_lexis", "…",
        "https://www.lexisnexis.com/en-us/products/lexis-plus-ai.page",
        "Best for: comprehensive legal research backed by LexisNexis's full database. "
        "Drafts legal briefs, summarises case law, and answers legal questions with citations. "
        "Best for Generate → Instruction and Summary on legal content.",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#c41e3a"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">Lx</text>',
        "#c41e3a",
        None,
    ),
    # ── Medical (Doctor) ──────────────────────────────────────────────────────
    (
        "Microsoft Azure Health Bot",
        "Clinical NLP · Medical triage · HL7 FHIR",
        "api_key_azure_health", "…",
        "https://azure.microsoft.com/en-us/products/bot-services/health-bot",
        "RECOMMENDED for medical professionals. Azure Health Bot is HIPAA-compliant "
        "and trained on clinical data. Supports medical triage, symptom checking, "
        "and clinical document summarisation. "
        "Best for Summary (clinical notes) and Generate → Instruction (patient guides).",
        '<rect x="2" y="2" width="20" height="20" rx="3" fill="#0078d4"/>'
        '<path d="M12 7 V17 M7 12 H17" stroke="white" stroke-width="2.2" '
        'stroke-linecap="round"/>',
        "#0078d4",
        "Recommended",
    ),
    (
        "Google MedPaLM 2",
        "Medical Q&A · Clinical reasoning · PubMed",
        "api_key_medpalm", "AIza…",
        "https://cloud.google.com/vertex-ai/docs/generative-ai/medical",
        "Best for: medical question answering, clinical note summarisation, and "
        "evidence-based reasoning. MedPaLM 2 achieved expert-level performance on "
        "USMLE medical licensing exams. Access via Google Cloud Vertex AI. "
        "Ideal for Summary (clinical documents) and Code (medical data pipelines).",
        '<path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z" '
        'fill="#34a853"/>'
        '<circle cx="12" cy="12" r="3" fill="white"/>',
        "#34a853",
        None,
    ),
    (
        "Nuance DAX (Microsoft)",
        "Clinical documentation · Voice-to-note · EHR",
        "api_key_nuance_dax", "…",
        "https://www.nuance.com/healthcare/ambient-clinical-intelligence.html",
        "Best for: ambient clinical documentation — automatically generates clinical notes "
        "from doctor-patient conversations. Integrates with major EHR systems. "
        "Ideal for Generate → Instruction (discharge summaries, referral letters) "
        "and Summary (medical records).",
        '<rect x="3" y="3" width="18" height="18" rx="9" fill="#005eb8"/>'
        '<path d="M8 12 Q10 8 12 12 Q14 16 16 12" stroke="white" stroke-width="1.8" '
        'fill="none" stroke-linecap="round"/>',
        "#005eb8",
        None,
    ),
    (
        "AWS HealthLake",
        "FHIR data · Clinical NLP · Medical analytics",
        "api_key_aws_healthlake", "…",
        "https://aws.amazon.com/healthlake/",
        "Best for: storing, transforming and analysing health data in FHIR format. "
        "Includes medical NLP to extract entities from clinical text (diagnoses, medications). "
        "Useful for Summary (extracting key info from clinical notes) in healthcare workflows.",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#ff9900"/>'
        '<path d="M7 12 C7 9 9 7 12 7 C15 7 17 9 17 12 C17 15 15 17 12 17 C9 17 7 15 7 12 Z" '
        'stroke="white" stroke-width="1.5" fill="none"/>',
        "#ff9900",
        None,
    ),
    # ── Architecture / Engineering / CAD ──────────────────────────────────────
    (
        "Autodesk AI (Forma)",
        "Generative design · BIM · Structural analysis",
        "api_key_autodesk", "…",
        "https://aps.autodesk.com/",
        "RECOMMENDED for architects and engineers. Autodesk Platform Services (APS) "
        "provides AI-powered generative design, BIM data extraction, and structural analysis. "
        "Best for Generate → Slide (design presentations) and Summary (project specs).",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#0696d7"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="7" font-weight="bold" '
        'fill="white" font-family="Arial">ADS</text>',
        "#0696d7",
        "Recommended",
    ),
    (
        "Speckle AI",
        "AEC data · 3D model analysis · Collaboration",
        "api_key_speckle", "…",
        "https://speckle.systems/",
        "Best for: architecture, engineering and construction (AEC) data workflows. "
        "Speckle connects BIM tools and enables AI analysis of 3D models and project data. "
        "Useful for Code tab (AEC data pipelines) and Generate → Instruction (build guides).",
        '<circle cx="12" cy="12" r="9" stroke="#0480fb" stroke-width="1.8" fill="none"/>'
        '<circle cx="12" cy="12" r="3" fill="#0480fb"/>',
        "#0480fb",
        None,
    ),
    # ── Electronics / Hardware / IoT ──────────────────────────────────────────
    (
        "Arduino AI / Edge Impulse",
        "Embedded ML · IoT · TinyML",
        "api_key_edgeimpulse", "ei_…",
        "https://studio.edgeimpulse.com/",
        "RECOMMENDED for electronics and IoT engineers. Edge Impulse enables machine learning "
        "on microcontrollers and embedded devices. Best for Code tab (firmware analysis) "
        "and Generate → Instruction (hardware setup guides, circuit documentation).",
        '<rect x="3" y="3" width="18" height="18" rx="3" fill="#00979d"/>'
        '<path d="M8 12 H16 M12 8 V16" stroke="white" stroke-width="2" stroke-linecap="round"/>',
        "#00979d",
        "Recommended",
    ),
    (
        "AWS IoT / SageMaker",
        "IoT analytics · ML models · Edge AI",
        "api_key_aws_iot", "…",
        "https://aws.amazon.com/iot/",
        "Best for: IoT data processing, sensor analytics, and deploying ML models to edge devices. "
        "SageMaker provides full ML pipeline support. "
        "Useful for Code tab (IoT firmware) and Generate → Instruction (IoT setup docs).",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#ff9900"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="7" font-weight="bold" '
        'fill="white" font-family="Arial">IoT</text>',
        "#ff9900",
        None,
    ),
    # ── Art / Design / Creative ───────────────────────────────────────────────
    (
        "Adobe Firefly API",
        "Generative art · Image editing · Creative Cloud",
        "api_key_adobe_firefly", "…",
        "https://developer.adobe.com/firefly-api/",
        "RECOMMENDED for artists and designers. Adobe Firefly is trained on licensed content "
        "— safe for commercial use. Generates images, fills, and effects. "
        "Best for Generate → Poster and Generate → Slide visual assets.",
        '<rect x="3" y="3" width="18" height="18" rx="3" fill="#ff0000"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">Ff</text>',
        "#ff0000",
        "Recommended",
    ),
    (
        "Midjourney API",
        "AI art · Concept art · Illustration",
        "api_key_midjourney", "…",
        "https://docs.midjourney.com/",
        "Best for: high-quality AI art and concept illustration. "
        "Midjourney produces the most aesthetically refined AI images available. "
        "Ideal for Generate → Poster, Generate → Slide cover art, and creative projects.",
        '<circle cx="12" cy="12" r="9" fill="#1a1a1a"/>'
        '<path d="M7 16 L12 6 L17 16" stroke="white" stroke-width="1.8" '
        'fill="none" stroke-linejoin="round"/>',
        "#1a1a1a",
        None,
    ),
    (
        "RunwayML",
        "Video generation · Image-to-video · Creative AI",
        "api_key_runway", "…",
        "https://runwayml.com/api",
        "Best for: AI video generation from text or images. "
        "Powers Generate → Video with real AI-generated footage. "
        "Also useful for creative visual effects and motion graphics.",
        '<rect x="3" y="3" width="18" height="18" rx="9" fill="#000000"/>'
        '<path d="M9 8 L17 12 L9 16 Z" fill="white"/>',
        "#000000",
        None,
    ),
    # ── Finance / Business ────────────────────────────────────────────────────
    (
        "Bloomberg GPT / API",
        "Financial NLP · Market data · Analysis",
        "api_key_bloomberg", "…",
        "https://www.bloomberg.com/company/press/bloomberggpt-50-billion-parameter-llm-bloomberg/",
        "RECOMMENDED for finance professionals. BloombergGPT is trained on financial data "
        "for market analysis, earnings summaries, and financial document processing. "
        "Best for Summary (financial reports) and Generate → Instruction (investment briefs).",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#1a1a1a"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="7" font-weight="bold" '
        'fill="#f5a623" font-family="Arial">BBG</text>',
        "#1a1a1a",
        "Recommended",
    ),
    (
        "Alpaca / Financial Datasets",
        "Stock data · Trading AI · Market analysis",
        "api_key_alpaca", "PK…",
        "https://alpaca.markets/",
        "Best for: real-time and historical stock market data with AI analysis. "
        "Useful for Generate → Poster (financial infographics) and "
        "Summary (earnings reports, market news).",
        '<rect x="3" y="3" width="18" height="18" rx="3" fill="#ffb300"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">ALP</text>',
        "#ffb300",
        None,
    ),
    # ── Education / Research ──────────────────────────────────────────────────
    (
        "Semantic Scholar API",
        "Academic papers · Research summaries · Citations",
        "api_key_semantic_scholar", "…",
        "https://api.semanticscholar.org/",
        "RECOMMENDED for researchers and academics. Free API with access to 200M+ papers. "
        "Best for Summary (research papers), Generate → Instruction (literature reviews), "
        "and Code tab (understanding research code).",
        '<circle cx="12" cy="12" r="9" fill="#1857b6"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">SS</text>',
        "#1857b6",
        "Recommended",
    ),
    (
        "Wolfram Alpha API",
        "Computational knowledge · Math · Science",
        "api_key_wolfram", "…",
        "https://products.wolframalpha.com/api/",
        "Best for: computational answers, mathematical problem solving, and scientific data. "
        "Wolfram Alpha answers factual questions with step-by-step solutions. "
        "Ideal for Code tab (algorithm explanation) and Generate → Instruction (STEM guides).",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#dd1100"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">W</text>',
        "#dd1100",
        None,
    ),
    # ── Marketing / Content ───────────────────────────────────────────────────
    (
        "Jasper AI",
        "Marketing copy · Blog · Ad content",
        "api_key_jasper", "…",
        "https://developers.jasper.ai/",
        "Best for: marketing professionals and content creators. "
        "Jasper is fine-tuned for brand voice, ad copy, blog posts, and social media. "
        "Best for Generate → Caption, Generate → Poster, and Generate → Prompt.",
        '<rect x="3" y="3" width="18" height="18" rx="9" fill="#6c47ff"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">J</text>',
        "#6c47ff",
        None,
    ),
    (
        "Copy.ai API",
        "Sales copy · Email · Product descriptions",
        "api_key_copyai", "…",
        "https://www.copy.ai/tools",
        "Best for: e-commerce product descriptions, sales emails, and ad copy. "
        "Optimised for conversion-focused writing. "
        "Ideal for Generate → Caption and Generate → Poster body text.",
        '<rect x="3" y="3" width="18" height="18" rx="3" fill="#7c3aed"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="bold" '
        'fill="white" font-family="Arial">C</text>',
        "#7c3aed",
        None,
    ),
    # ── Science / Research Tools ──────────────────────────────────────────────
    (
        "Elsevier TDM API",
        "Scientific literature · Full-text mining",
        "api_key_elsevier", "…",
        "https://dev.elsevier.com/",
        "Best for: text and data mining of Elsevier's scientific journals (ScienceDirect). "
        "Access full-text research articles for Summary and Generate → Instruction. "
        "Ideal for researchers in medicine, engineering, and natural sciences.",
        '<rect x="3" y="3" width="18" height="18" rx="2" fill="#ff6200"/>'
        '<text x="12" y="15.5" text-anchor="middle" font-size="7" font-weight="bold" '
        'fill="white" font-family="Arial">ELS</text>',
        "#ff6200",
        None,
    ),
]


def _hash_pw(pw: str) -> str:
    """
    Half-password encryption:
    - Split password at midpoint
    - SHA-256 the first half  → stored as prefix (32 hex chars)
    - PBKDF2-HMAC-SHA256 the second half with the first half as salt → stored as suffix
    - Final stored value = prefix + ":" + suffix
    This means even if profile.json is read, neither half alone can verify the password.
    """
    import hashlib as _hl
    mid = max(1, len(pw) // 2)
    first, second = pw[:mid], pw[mid:]
    prefix = _hl.sha256(first.encode()).hexdigest()[:32]
    suffix = _hl.pbkdf2_hmac(
        "sha256", second.encode(), first.encode(), 100_000
    ).hex()[:32]
    return f"{prefix}:{suffix}"


def _pw_strength(pw: str) -> tuple[int, str, str]:
    """
    Returns (level, label, color).
    level: 0=Weak, 1=Medium, 2=Strong, 3=Very Strong
    Minimum required: level >= 1 (Medium)
    """
    import re
    score = 0
    if len(pw) >= 8:   score += 1
    if len(pw) >= 12:  score += 1
    if re.search(r"[A-Z]", pw): score += 1
    if re.search(r"[a-z]", pw): score += 1
    if re.search(r"\d",    pw): score += 1
    if re.search(r"[^A-Za-z0-9]", pw): score += 1

    if score <= 2:
        return 0, "Weak",        "#e53935"
    elif score <= 3:
        return 1, "Medium",      "#ff9500"
    elif score <= 4:
        return 2, "Strong",      "#4caf50"
    else:
        return 3, "Very Strong", "#1976d2"


class ApiKeysMixin:
    """Mixin providing the password-protected My API Key page."""

    # ── Page builder ──────────────────────────────────────────────────────────

    def _build_api_keys_page(self) -> QWidget:
        outer = QWidget()
        outer.setObjectName("contentPage")
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        self._api_page_stack = QStackedWidget()
        self._api_page_stack.addWidget(self._build_lock_screen())   # 0 — lock
        self._api_page_stack.addWidget(self._build_content_page())  # 1 — content
        outer_lay.addWidget(self._api_page_stack)

        # Inactivity timer — fires after _LOCK_TIMEOUT_MS of no interaction
        self._api_lock_timer = QTimer(outer)
        self._api_lock_timer.setSingleShot(True)
        self._api_lock_timer.setInterval(_LOCK_TIMEOUT_MS)
        self._api_lock_timer.timeout.connect(self._api_auto_lock)

        # Install app-level event filter so ALL child widget events are caught
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.installEventFilter(outer)
        outer.eventFilter = self._api_page_event_filter  # type: ignore[method-assign]

        return outer

    # ── Lock screen ───────────────────────────────────────────────────────────

    def _build_lock_screen(self) -> QWidget:
        lock = QWidget()
        lock.setObjectName("contentPage")
        lay = QVBoxLayout(lock)
        lay.setContentsMargins(40, 0, 40, 0)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        # Lock icon
        lock_icon = QLabel()
        lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_icon.setFixedSize(64, 64)
        lock_icon.setStyleSheet("background: transparent;")
        lock_icon.setPixmap(self._make_lock_pixmap(64))
        lay.addWidget(lock_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        self._lock_icon_lbl = lock_icon

        # Title
        self._lock_title = QLabel("My API Keys")
        self._lock_title.setObjectName("pageTitle")
        self._lock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lock_title, 0, Qt.AlignmentFlag.AlignHCenter)

        # Subtitle
        self._lock_subtitle = QLabel("Enter your password to access API keys")
        self._lock_subtitle.setObjectName("settingsLabel")
        self._lock_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lock_subtitle, 0, Qt.AlignmentFlag.AlignHCenter)

        lay.addSpacing(6)

        # Password field
        self._lock_pw_field = QLineEdit()
        self._lock_pw_field.setObjectName("settingsInput")
        self._lock_pw_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._lock_pw_field.setPlaceholderText("Password")
        self._lock_pw_field.setFixedSize(300, 38)
        self._lock_pw_field.returnPressed.connect(self._api_submit_password)
        lay.addWidget(self._lock_pw_field, 0, Qt.AlignmentFlag.AlignHCenter)

        # Confirm field (only shown when creating a new password)
        self._lock_confirm_field = QLineEdit()
        self._lock_confirm_field.setObjectName("settingsInput")
        self._lock_confirm_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._lock_confirm_field.setPlaceholderText("Confirm password")
        self._lock_confirm_field.setFixedSize(300, 38)
        self._lock_confirm_field.setVisible(False)
        self._lock_confirm_field.returnPressed.connect(self._api_submit_password)
        lay.addWidget(self._lock_confirm_field, 0, Qt.AlignmentFlag.AlignHCenter)

        # Strength meter (only shown when creating)
        self._lock_strength_lbl = QLabel("")
        self._lock_strength_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lock_strength_lbl.setStyleSheet("font-size: 11px; background: transparent;")
        self._lock_strength_lbl.setVisible(False)
        lay.addWidget(self._lock_strength_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        self._lock_pw_field.textChanged.connect(self._update_lock_strength_meter)

        # Error label
        self._lock_error_lbl = QLabel("")
        self._lock_error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lock_error_lbl.setStyleSheet("color: #e53935; font-size: 12px; background: transparent;")
        self._lock_error_lbl.setVisible(False)
        lay.addWidget(self._lock_error_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        # Submit button
        self._lock_submit_btn = QPushButton("Unlock")
        self._lock_submit_btn.setObjectName("btnPrimary")
        self._lock_submit_btn.setFixedSize(140, 38)
        self._lock_submit_btn.clicked.connect(self._api_submit_password)
        lay.addWidget(self._lock_submit_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        lay.addSpacing(8)

        # Forgot password link
        forgot_btn = QPushButton("Forgot password?")
        forgot_btn.setObjectName("forgotPwBtn")
        forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_btn.setStyleSheet(
            "QPushButton#forgotPwBtn { background: transparent; border: none; "
            "color: #888888; font-size: 12px; text-decoration: underline; }"
            "QPushButton#forgotPwBtn:hover { color: #aaaaaa; }"
        )
        forgot_btn.clicked.connect(self._open_password_manager)
        lay.addWidget(forgot_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        return lock

    # ── Content page ──────────────────────────────────────────────────────────

    def _build_content_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        self._api_content_page = page
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top action bar
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 14, 32, 10)

        title = QLabel("My API Keys")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        t_lay.addWidget(title)
        t_lay.addStretch()

        lock_btn = QPushButton("  Lock")
        lock_btn.setObjectName("btnOutline")
        lock_btn.setFixedSize(100, 32)
        lock_btn.setIcon(self._make_lock_icon(14))
        from PyQt6.QtCore import QSize as _QS
        lock_btn.setIconSize(_QS(14, 14))
        lock_btn.clicked.connect(self._api_lock_now)
        t_lay.addWidget(lock_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("btnOutline")
        save_btn.setFixedSize(90, 32)
        save_btn.clicked.connect(self._save_api_keys)
        t_lay.addWidget(save_btn)
        lay.addWidget(top)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 8, 32, 32)
        sc_lay.setSpacing(20)

        sub = QLabel(
            "Add your own API keys to unlock AI-powered Summary and Translation. "
            "Keys are stored locally on your device and never sent anywhere except "
            "the provider you choose."
        )
        sub.setObjectName("settingsLabel")
        sub.setWordWrap(True)
        sc_lay.addWidget(sub)

        def _badge_order(p):
            b = p[8]  # badge is index 8
            if b and "Highly" in b:
                return 0
            if b and "Recommended" in b:
                return 1
            return 2

        self._api_key_inputs: dict[str, QLineEdit] = {}
        for name, subtitle, profile_key, placeholder, docs_url, desc, logo_svg, logo_color, badge \
                in sorted(_PROVIDERS, key=_badge_order):
            sc_lay.addWidget(self._build_api_card(
                name, subtitle, profile_key, placeholder, docs_url, desc, logo_svg, logo_color, badge
            ))

        # ── Custom API cards (user-added) ─────────────────────────────────
        sep_lbl = QLabel("My Custom APIs")
        sep_lbl.setObjectName("shapeSectionLabel")
        sc_lay.addWidget(sep_lbl)

        self._custom_api_cards_lay = QVBoxLayout()
        self._custom_api_cards_lay.setSpacing(12)
        sc_lay.addLayout(self._custom_api_cards_lay)

        add_btn = QPushButton("＋  Add custom API")
        add_btn.setObjectName("btnOutline")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._add_custom_api_card)
        sc_lay.addWidget(add_btn)

        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _build_api_card(self, name: str, subtitle: str, key: str, placeholder: str,
                        url: str, desc: str, logo_svg: str, logo_color: str,
                        badge: str | None = None) -> QWidget:
        card = QWidget()
        card.setObjectName("infoCard")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(18, 14, 18, 14)
        c_lay.setSpacing(8)

        # Header: logo + name/subtitle/badge + Get key
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        logo_lbl = QLabel()
        logo_lbl.setFixedSize(28, 28)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent;")
        logo_lbl.setPixmap(self._make_provider_pixmap(logo_svg, 28))
        header_row.addWidget(logo_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_col.setContentsMargins(0, 0, 0, 0)

        # Name + badge pill on same row
        name_badge_row = QHBoxLayout()
        name_badge_row.setSpacing(8)
        name_badge_row.setContentsMargins(0, 0, 0, 0)
        name_lbl = QLabel(name)
        name_lbl.setObjectName("cardTitle")
        name_badge_row.addWidget(name_lbl)
        if badge:
            is_high = "Highly" in badge
            badge_lbl = QLabel(("⭐⭐ " if is_high else "⭐ ") + badge)
            badge_lbl.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 8px;"
                + ("background: #7c3aed; color: #ffffff;" if is_high
                   else "background: #0369a1; color: #ffffff;")
            )
            name_badge_row.addWidget(badge_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        name_badge_row.addStretch()
        name_col.addLayout(name_badge_row)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("settingsLabel")
        sub_lbl.setStyleSheet("font-size: 11px;")
        name_col.addWidget(sub_lbl)
        header_row.addLayout(name_col, 1)

        link_btn = QPushButton("Get key ↗")
        link_btn.setObjectName("btnOutline")
        link_btn.setFixedSize(100, 30)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(lambda _=False, u=url: self._open_url(u))
        header_row.addWidget(link_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        c_lay.addLayout(header_row)

        # See more / description
        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("cardBody")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; padding-top: 2px;")
        desc_lbl.setVisible(False)

        see_btn = QPushButton("See more ▾")
        see_btn.setObjectName("btnOutline")
        see_btn.setFixedHeight(24)
        see_btn.setStyleSheet("font-size: 11px; padding: 0 10px;")
        see_btn.clicked.connect(
            lambda _=False, d=desc_lbl, b=see_btn: self._toggle_desc(d, b)
        )
        see_row = QHBoxLayout()
        see_row.setContentsMargins(0, 0, 0, 0)
        see_row.addWidget(see_btn)
        see_row.addStretch()
        c_lay.addLayout(see_row)
        c_lay.addWidget(desc_lbl)

        # Key input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        field = QLineEdit()
        field.setObjectName("settingsInput")
        field.setPlaceholderText(placeholder)
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setFixedHeight(32)
        self._api_key_inputs[key] = field
        input_row.addWidget(field, 1)

        show_btn = QPushButton("Show")
        show_btn.setObjectName("btnOutline")
        show_btn.setFixedSize(70, 32)

        hide_btn = QPushButton("Hide")
        hide_btn.setObjectName("btnOutline")
        hide_btn.setFixedSize(70, 32)
        hide_btn.setVisible(False)

        show_btn.clicked.connect(
            lambda _=False, f=field, sb=show_btn, hb=hide_btn:
            self._api_confirm_then(lambda: self._api_reveal_field(f, sb, hb))
        )
        hide_btn.clicked.connect(
            lambda _=False, f=field, sb=show_btn, hb=hide_btn:
            self._api_hide_field(f, sb, hb)
        )
        input_row.addWidget(show_btn)
        input_row.addWidget(hide_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(70, 32)
        clear_btn.clicked.connect(
            lambda _=False, f=field, sb=show_btn, hb=hide_btn:
            self._api_confirm_then(lambda: self._api_clear_field(f, sb, hb))
        )
        input_row.addWidget(clear_btn)
        c_lay.addLayout(input_row)
        return card

    def _toggle_desc(self, desc_lbl: QLabel, btn: QPushButton):
        visible = not desc_lbl.isVisible()
        desc_lbl.setVisible(visible)
        btn.setText("See less ▴" if visible else "See more ▾")

    # ── Custom API card management ────────────────────────────────────────────

    def _add_custom_api_card(self):
        """Open a dialog to define a new custom API card."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
            QPushButton, QTextEdit, QFormLayout
        )
        dlg = QDialog()
        dlg.setWindowTitle("Add Custom API")
        dlg.setMinimumWidth(440)
        dlg.setModal(True)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Add your own API provider:", objectName="pageTitle"))

        form = QFormLayout()
        form.setSpacing(10)

        name_field = QLineEdit()
        name_field.setObjectName("settingsInput")
        name_field.setPlaceholderText("e.g. My Company AI")
        name_field.setFixedHeight(34)
        form.addRow("Name *", name_field)

        subtitle_field = QLineEdit()
        subtitle_field.setObjectName("settingsInput")
        subtitle_field.setPlaceholderText("e.g. Internal LLM · v2")
        subtitle_field.setFixedHeight(34)
        form.addRow("Subtitle", subtitle_field)

        key_field = QLineEdit()
        key_field.setObjectName("settingsInput")
        key_field.setPlaceholderText("Paste your API key here")
        key_field.setEchoMode(QLineEdit.EchoMode.Password)
        key_field.setFixedHeight(34)
        form.addRow("API Key", key_field)

        url_field = QLineEdit()
        url_field.setObjectName("settingsInput")
        url_field.setPlaceholderText("https://docs.yourapi.com/keys")
        url_field.setFixedHeight(34)
        form.addRow("Docs URL", url_field)

        desc_field = QTextEdit()
        desc_field.setObjectName("featureEdit")
        desc_field.setPlaceholderText("Describe what this API is best for, its strengths, and which Veaja features it powers…")
        desc_field.setFixedHeight(80)
        form.addRow("Description", desc_field)

        lay.addLayout(form)

        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #e53935; font-size: 11px;")
        err_lbl.setVisible(False)
        lay.addWidget(err_lbl)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btnOutline")
        cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Add")
        save_btn.setObjectName("btnPrimary")
        save_btn.setFixedHeight(32)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        def _save():
            name = name_field.text().strip()
            if not name:
                err_lbl.setText("Name is required.")
                err_lbl.setVisible(True)
                return
            custom = {
                "name":     name,
                "subtitle": subtitle_field.text().strip() or "Custom API",
                "key":      key_field.text().strip(),
                "url":      url_field.text().strip(),
                "desc":     desc_field.toPlainText().strip(),
            }
            dlg.accept()
            self._save_custom_api(custom)
            self._render_custom_api_card(custom)

        save_btn.clicked.connect(_save)
        name_field.returnPressed.connect(_save)
        dlg.exec()

    def _render_custom_api_card(self, custom: dict):
        """Build and insert a custom API card into the layout."""
        card = QWidget()
        card.setObjectName("infoCard")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(18, 14, 18, 14)
        c_lay.setSpacing(8)

        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        # Initials avatar
        initials = (custom["name"][:2]).upper()
        avatar = QLabel(initials)
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background: #6c47ff; color: white; border-radius: 6px; "
            "font-size: 11px; font-weight: 700;"
        )
        hdr.addWidget(avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name_col.setContentsMargins(0, 0, 0, 0)
        name_lbl = QLabel(custom["name"])
        name_lbl.setObjectName("cardTitle")
        sub_lbl = QLabel(custom.get("subtitle", "Custom API"))
        sub_lbl.setObjectName("settingsLabel")
        sub_lbl.setStyleSheet("font-size: 11px;")
        name_col.addWidget(name_lbl)
        name_col.addWidget(sub_lbl)
        hdr.addLayout(name_col, 1)

        # Docs link
        if custom.get("url"):
            link_btn = QPushButton("Docs ↗")
            link_btn.setObjectName("btnOutline")
            link_btn.setFixedSize(80, 28)
            link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            link_btn.clicked.connect(lambda _=False, u=custom["url"]: self._open_url(u))
            hdr.addWidget(link_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setObjectName("historyDel")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("Remove this custom API")
        del_btn.clicked.connect(lambda _=False, c=card, n=custom["name"]:
                                self._delete_custom_api(c, n))
        hdr.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        c_lay.addLayout(hdr)

        # See more / description
        if custom.get("desc"):
            desc_lbl = QLabel(custom["desc"])
            desc_lbl.setObjectName("cardBody")
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("font-size: 12px; padding-top: 2px;")
            desc_lbl.setVisible(False)

            see_btn = QPushButton("See more ▾")
            see_btn.setObjectName("btnOutline")
            see_btn.setFixedHeight(24)
            see_btn.setStyleSheet("font-size: 11px; padding: 0 10px;")
            see_btn.clicked.connect(
                lambda _=False, d=desc_lbl, b=see_btn: self._toggle_desc(d, b)
            )
            see_row = QHBoxLayout()
            see_row.setContentsMargins(0, 0, 0, 0)
            see_row.addWidget(see_btn)
            see_row.addStretch()
            c_lay.addLayout(see_row)
            c_lay.addWidget(desc_lbl)

        # Key input row
        if custom.get("key") is not None:
            input_row = QHBoxLayout()
            input_row.setSpacing(8)

            field = QLineEdit()
            field.setObjectName("settingsInput")
            field.setPlaceholderText("API key")
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setFixedHeight(32)
            field.setText(custom.get("key", ""))
            # Store with a unique key based on name
            safe_key = f"custom_{custom['name'].lower().replace(' ', '_')}"
            self._api_key_inputs[safe_key] = field
            input_row.addWidget(field, 1)

            show_btn = QPushButton("Show")
            show_btn.setObjectName("btnOutline")
            show_btn.setFixedSize(70, 32)
            hide_btn = QPushButton("Hide")
            hide_btn.setObjectName("btnOutline")
            hide_btn.setFixedSize(70, 32)
            hide_btn.setVisible(False)

            show_btn.clicked.connect(
                lambda _=False, f=field, sb=show_btn, hb=hide_btn:
                self._api_confirm_then(lambda: self._api_reveal_field(f, sb, hb))
            )
            hide_btn.clicked.connect(
                lambda _=False, f=field, sb=show_btn, hb=hide_btn:
                self._api_hide_field(f, sb, hb)
            )
            input_row.addWidget(show_btn)
            input_row.addWidget(hide_btn)
            c_lay.addLayout(input_row)

        self._custom_api_cards_lay.addWidget(card)

    def _save_custom_api(self, custom: dict):
        """Persist custom API list to profile."""
        existing = getattr(self, "_custom_apis", [])
        existing.append(custom)
        self._custom_apis = existing
        import json
        self.settings_save_requested.emit({
            "custom_apis": json.dumps(existing)
        })

    def _delete_custom_api(self, card: QWidget, name: str):
        """Remove a custom API card."""
        card.setParent(None)
        card.deleteLater()
        self._custom_apis = [
            c for c in getattr(self, "_custom_apis", [])
            if c.get("name") != name
        ]
        import json
        self.settings_save_requested.emit({
            "custom_apis": json.dumps(self._custom_apis)
        })

    def apply_custom_apis(self, profile: dict):
        """Restore custom API cards from profile on startup."""
        import json
        raw = profile.get("custom_apis", "[]")
        try:
            customs = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            customs = []
        self._custom_apis = customs
        if not hasattr(self, "_custom_api_cards_lay"):
            return
        # Clear existing custom cards
        while self._custom_api_cards_lay.count():
            item = self._custom_api_cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for custom in customs:
            self._render_custom_api_card(custom)

    def _make_provider_pixmap(self, svg_body: str, size: int):
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtWidgets import QApplication
        svg = (
            f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            f'{svg_body}</svg>'
        ).encode()
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(svg)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        px.setDevicePixelRatio(dpr)
        return px

    # ── Per-field actions ─────────────────────────────────────────────────────

    def _api_reveal_field(self, field: "QLineEdit", show_btn: "QPushButton",
                          hide_btn: "QPushButton"):
        field.setEchoMode(QLineEdit.EchoMode.Normal)
        show_btn.setVisible(False)
        hide_btn.setVisible(True)

    def _api_hide_field(self, field: "QLineEdit", show_btn: "QPushButton",
                        hide_btn: "QPushButton"):
        field.setEchoMode(QLineEdit.EchoMode.Password)
        hide_btn.setVisible(False)
        show_btn.setVisible(True)

    def _api_clear_field(self, field: "QLineEdit", show_btn: "QPushButton",
                         hide_btn: "QPushButton"):
        field.clear()
        self._api_hide_field(field, show_btn, hide_btn)

    def _api_confirm_then(self, action):
        """Show a password confirmation dialog, then run action() if correct."""
        from PyQt6.QtWidgets import QDialog
        dlg = QDialog()
        dlg.setWindowTitle("Confirm password")
        dlg.setFixedWidth(300)
        dlg.setModal(True)

        lay = QVBoxLayout(dlg)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("Enter your password to continue:")
        lbl.setObjectName("settingsLabel")
        lay.addWidget(lbl)

        pw_field = QLineEdit()
        pw_field.setObjectName("settingsInput")
        pw_field.setEchoMode(QLineEdit.EchoMode.Password)
        pw_field.setPlaceholderText("Password")
        pw_field.setFixedHeight(34)
        lay.addWidget(pw_field)

        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #e53935; font-size: 11px;")
        err_lbl.setVisible(False)
        lay.addWidget(err_lbl)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btnOutline")
        cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Confirm")
        ok_btn.setObjectName("btnPrimary")
        ok_btn.setFixedHeight(32)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

        def _submit():
            pw = pw_field.text()
            stored = self._api_get_stored_hash()
            if not stored or _hash_pw(pw) == stored:
                dlg.accept()
                action()
            else:
                err_lbl.setText("Incorrect password.")
                err_lbl.setVisible(True)
                pw_field.clear()
                pw_field.setFocus()

        ok_btn.clicked.connect(_submit)
        pw_field.returnPressed.connect(_submit)
        dlg.exec()

    # ── Lock SVG helpers ──────────────────────────────────────────────────────

    _LOCK_SVG = """
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
  <rect x="3" y="11" width="18" height="11" rx="2.5"
        stroke="{color}" stroke-width="1.8" fill="none"/>
  <path d="M7 11V7a5 5 0 0 1 10 0v4"
        stroke="{color}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <circle cx="12" cy="16" r="1.4" fill="{color}"/>
  <line x1="12" y1="17.4" x2="12" y2="19.2"
        stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>
</svg>"""

    def _lock_svg_color(self) -> str:
        return "#aaaaaa" if getattr(self, "_dark", False) else "#666666"

    def _make_lock_pixmap(self, size: int):
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtWidgets import QApplication
        color = self._lock_svg_color()
        svg = self._LOCK_SVG.replace("{color}", color).encode()
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(svg)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        px.setDevicePixelRatio(dpr)
        return px

    def _make_lock_icon(self, size: int):
        from PyQt6.QtGui import QIcon
        return QIcon(self._make_lock_pixmap(size))

    # ── Lock / unlock logic ───────────────────────────────────────────────────

    def _api_show_lock(self):
        """Show the lock screen and reset all fields to hidden state."""
        self._lock_pw_field.clear()
        self._lock_confirm_field.clear()
        self._lock_error_lbl.setVisible(False)
        self._api_lock_timer.stop()

        # Reset every key field back to hidden (Password echo mode)
        if hasattr(self, "_api_key_inputs"):
            for field in self._api_key_inputs.values():
                field.setEchoMode(QLineEdit.EchoMode.Password)
                # Find and reset Show/Hide buttons in the same row
                parent = field.parent()
                if parent:
                    lay = parent.layout()
                    if lay:
                        for i in range(lay.count()):
                            item = lay.itemAt(i)
                            if item and item.widget():
                                w = item.widget()
                                if isinstance(w, QPushButton):
                                    if w.text() == "Show":
                                        w.setVisible(True)
                                    elif w.text() == "Hide":
                                        w.setVisible(False)

        has_pw = bool(self._api_get_stored_hash())
        if has_pw:
            self._lock_subtitle.setText("Enter your password to access API keys")
            self._lock_submit_btn.setText("Unlock")
            self._lock_confirm_field.setVisible(False)
            if hasattr(self, "_lock_strength_lbl"):
                self._lock_strength_lbl.setVisible(False)
        else:
            self._lock_subtitle.setText("Create a password to protect your API keys")
            self._lock_submit_btn.setText("Create")
            self._lock_confirm_field.setVisible(True)

        self._api_page_stack.setCurrentIndex(0)
        self._lock_pw_field.setFocus()

    def _api_lock_now(self):
        """Manually lock the page."""
        self._api_show_lock()

    def _update_lock_strength_meter(self, pw: str):
        """Update the strength label on the lock screen (create mode only)."""
        if not hasattr(self, "_lock_strength_lbl"):
            return
        if not self._lock_confirm_field.isVisible():
            return  # only show in create mode
        if not pw:
            self._lock_strength_lbl.setVisible(False)
            return
        level, label, color = _pw_strength(pw)
        bars = "█" * (level + 1) + "░" * (3 - level)
        self._lock_strength_lbl.setText(f"{bars}  {label}")
        self._lock_strength_lbl.setStyleSheet(
            f"font-size: 11px; color: {color}; background: transparent; font-family: monospace;"
        )
        self._lock_strength_lbl.setVisible(True)

    def _api_auto_lock(self):
        """Called by inactivity timer — re-lock silently."""
        if self._api_page_stack.currentIndex() == 1:
            self._api_show_lock()

    def _api_submit_password(self):
        pw = self._lock_pw_field.text()
        if not pw:
            self._api_show_error("Password cannot be empty.")
            return

        stored_hash = self._api_get_stored_hash()

        if not stored_hash:
            # Creating a new password — enforce Medium+ strength
            level, label, color = _pw_strength(pw)
            if level < 1:
                self._api_show_error(
                    f"Password is too weak ({label}). "
                    "Use 8+ chars with uppercase, lowercase and numbers."
                )
                return
            confirm = self._lock_confirm_field.text()
            if pw != confirm:
                self._api_show_error("Passwords do not match.")
                return
            new_hash = _hash_pw(pw)
            self.settings_save_requested.emit({"api_key_password_hash": new_hash})
            self._api_pw_hash_cache = new_hash
            self._api_unlock()
        else:
            if _hash_pw(pw) != stored_hash:
                self._api_show_error("Incorrect password.")
                self._lock_pw_field.clear()
                self._lock_pw_field.setFocus()
                return
            self._api_unlock()

    def _api_unlock(self):
        self._lock_error_lbl.setVisible(False)
        self._api_page_stack.setCurrentIndex(1)
        self._api_reset_inactivity_timer()

    def _api_show_error(self, msg: str):
        self._lock_error_lbl.setText(msg)
        self._lock_error_lbl.setVisible(True)

    def _api_get_stored_hash(self) -> str:
        """Read the stored password hash from the last applied profile."""
        return getattr(self, "_api_pw_hash_cache", "")

    def _api_reset_inactivity_timer(self):
        """Restart the 5 s inactivity countdown."""
        if hasattr(self, "_api_lock_timer"):
            self._api_lock_timer.start(_LOCK_TIMEOUT_MS)

    def _api_page_event_filter(self, obj, event) -> bool:
        """
        App-level event filter — resets the inactivity timer whenever the user
        interacts with any widget that is a descendant of the unlocked content page.
        """
        if not hasattr(self, "_api_page_stack"):
            return False
        # Only care when the content (not lock screen) is visible
        if self._api_page_stack.currentIndex() != 1:
            return False
        if event.type() not in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            return False
        # Check the event target is inside our content page
        content = self._api_content_page
        widget = obj
        while widget is not None:
            if widget is content:
                self._api_reset_inactivity_timer()
                break
            widget = getattr(widget, "parent", lambda: None)()
        return False  # never consume the event

    # ── Called from _navigate when switching to page 8 ────────────────────────

    # ── Password management ───────────────────────────────────────────────────

    def _open_password_manager(self):
        """Open the Password Management dialog."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
            QPushButton, QListWidget, QListWidgetItem, QTabWidget,
            QWidget, QMessageBox
        )
        from PyQt6.QtCore import QSize

        dlg = QDialog()
        dlg.setWindowTitle("Password Management")
        dlg.setMinimumWidth(460)
        dlg.setModal(True)
        dlg.setObjectName("contentPage")

        root = QVBoxLayout(dlg)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Password Management")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.setObjectName("tabBar")

        # ── Tab 1: Recovery contacts ──────────────────────────────────────
        contacts_tab = QWidget()
        ct_lay = QVBoxLayout(contacts_tab)
        ct_lay.setSpacing(10)

        ct_lay.addWidget(QLabel(
            "Add email addresses or phone numbers for password recovery.\n"
            "We will send a reset code to the contact you choose.",
            objectName="settingsLabel"
        ))

        # Input row
        add_row = QHBoxLayout()
        contact_field = QLineEdit()
        contact_field.setObjectName("settingsInput")
        contact_field.setPlaceholderText("email@example.com  or  +1234567890")
        contact_field.setFixedHeight(34)
        add_row.addWidget(contact_field, 1)

        add_btn = QPushButton("Add")
        add_btn.setObjectName("btnPrimary")
        add_btn.setFixedSize(70, 34)
        add_row.addWidget(add_btn)
        ct_lay.addLayout(add_row)

        # Contact list
        contact_list = QListWidget()
        contact_list.setObjectName("settingsScroll")
        contact_list.setFixedHeight(140)
        # Load saved contacts
        for c in self._api_get_recovery_contacts():
            contact_list.addItem(QListWidgetItem(c))
        ct_lay.addWidget(contact_list)

        # Remove button
        remove_row = QHBoxLayout()
        remove_row.addStretch()
        remove_btn = QPushButton("Remove selected")
        remove_btn.setObjectName("btnOutline")
        remove_btn.setFixedHeight(30)
        remove_row.addWidget(remove_btn)
        ct_lay.addLayout(remove_row)

        def _add_contact():
            val = contact_field.text().strip()
            if not val:
                return
            # Check for duplicates
            existing = [contact_list.item(i).text()
                        for i in range(contact_list.count())]
            if val in existing:
                QMessageBox.information(dlg, "Already added", f"'{val}' is already in the list.")
                return
            contact_list.addItem(QListWidgetItem(val))
            contact_field.clear()
            self._api_save_recovery_contacts(
                [contact_list.item(i).text() for i in range(contact_list.count())]
            )

        def _remove_contact():
            row = contact_list.currentRow()
            if row >= 0:
                contact_list.takeItem(row)
                self._api_save_recovery_contacts(
                    [contact_list.item(i).text() for i in range(contact_list.count())]
                )

        add_btn.clicked.connect(_add_contact)
        contact_field.returnPressed.connect(_add_contact)
        remove_btn.clicked.connect(_remove_contact)

        tabs.addTab(contacts_tab, "Recovery Contacts")

        # ── Tab 2: Reset password ─────────────────────────────────────────
        reset_tab = QWidget()
        rt_lay = QVBoxLayout(reset_tab)
        rt_lay.setSpacing(10)

        contacts = self._api_get_recovery_contacts()
        if not contacts:
            rt_lay.addWidget(QLabel(
                "No recovery contacts saved yet.\n"
                "Add an email or phone in the Recovery Contacts tab first.",
                objectName="settingsLabel"
            ))
        else:
            rt_lay.addWidget(QLabel(
                "Select a contact to receive your reset code:",
                objectName="settingsLabel"
            ))

            contact_select = QListWidget()
            contact_select.setObjectName("settingsScroll")
            contact_select.setFixedHeight(120)
            for c in contacts:
                contact_select.addItem(QListWidgetItem(c))
            contact_select.setCurrentRow(0)
            rt_lay.addWidget(contact_select)

            send_btn = QPushButton("Send reset code")
            send_btn.setObjectName("btnPrimary")
            send_btn.setFixedHeight(36)
            rt_lay.addWidget(send_btn, 0, Qt.AlignmentFlag.AlignHCenter)

            rt_lay.addSpacing(8)
            rt_lay.addWidget(QLabel("Enter the code you received:", objectName="settingsLabel"))

            code_row = QHBoxLayout()
            code_field = QLineEdit()
            code_field.setObjectName("settingsInput")
            code_field.setPlaceholderText("6-digit code")
            code_field.setFixedHeight(34)
            code_row.addWidget(code_field, 1)
            rt_lay.addLayout(code_row)

            rt_lay.addWidget(QLabel("New password:", objectName="settingsLabel"))
            new_pw_field = QLineEdit()
            new_pw_field.setObjectName("settingsInput")
            new_pw_field.setEchoMode(QLineEdit.EchoMode.Password)
            new_pw_field.setPlaceholderText("New password (min 4 chars)")
            new_pw_field.setFixedHeight(34)
            rt_lay.addWidget(new_pw_field)

            confirm_pw_field = QLineEdit()
            confirm_pw_field.setObjectName("settingsInput")
            confirm_pw_field.setEchoMode(QLineEdit.EchoMode.Password)
            confirm_pw_field.setPlaceholderText("Confirm new password")
            confirm_pw_field.setFixedHeight(34)
            rt_lay.addWidget(confirm_pw_field)

            reset_err = QLabel("")
            reset_err.setStyleSheet("color: #e53935; font-size: 11px;")
            reset_err.setVisible(False)
            rt_lay.addWidget(reset_err)

            reset_pw_btn = QPushButton("Reset password")
            reset_pw_btn.setObjectName("btnPrimary")
            reset_pw_btn.setFixedHeight(36)
            rt_lay.addWidget(reset_pw_btn, 0, Qt.AlignmentFlag.AlignHCenter)

            # Store sent code in closure
            _sent_code = [None]

            def _send_code():
                row = contact_select.currentRow()
                if row < 0:
                    return
                contact = contact_select.item(row).text()
                import random, string
                code = "".join(random.choices(string.digits, k=6))
                _sent_code[0] = code
                ok, err = self._api_send_reset_code(contact, code)
                if ok:
                    QMessageBox.information(
                        dlg, "Code sent",
                        f"A reset code has been sent to:\n{contact}\n\n"
                        "Check your inbox (and spam folder)."
                    )
                else:
                    QMessageBox.warning(dlg, "Send failed", f"Could not send code:\n{err}")

            def _do_reset():
                code = code_field.text().strip()
                if not _sent_code[0]:
                    reset_err.setText("Please send a reset code first.")
                    reset_err.setVisible(True)
                    return
                if code != _sent_code[0]:
                    reset_err.setText("Incorrect code.")
                    reset_err.setVisible(True)
                    return
                new_pw = new_pw_field.text()
                confirm = confirm_pw_field.text()
                level, label, _ = _pw_strength(new_pw)
                if level < 1:
                    reset_err.setText(f"Password is too weak ({label}). Use 8+ chars with mixed case and numbers.")
                    reset_err.setVisible(True)
                    return
                if new_pw != confirm:
                    reset_err.setText("Passwords do not match.")
                    reset_err.setVisible(True)
                    return
                new_hash = _hash_pw(new_pw)
                self.settings_save_requested.emit({"api_key_password_hash": new_hash})
                self._api_pw_hash_cache = new_hash
                _sent_code[0] = None
                QMessageBox.information(dlg, "Password reset", "Your password has been reset.")
                dlg.accept()

            send_btn.clicked.connect(_send_code)
            reset_pw_btn.clicked.connect(_do_reset)

        tabs.addTab(reset_tab, "Reset Password")

        # ── Tab 3: Change password ────────────────────────────────────────
        change_tab = QWidget()
        ch_lay = QVBoxLayout(change_tab)
        ch_lay.setSpacing(10)

        ch_lay.addWidget(QLabel("Current password:", objectName="settingsLabel"))
        cur_pw = QLineEdit()
        cur_pw.setObjectName("settingsInput")
        cur_pw.setEchoMode(QLineEdit.EchoMode.Password)
        cur_pw.setFixedHeight(34)
        ch_lay.addWidget(cur_pw)

        ch_lay.addWidget(QLabel("New password:", objectName="settingsLabel"))
        new_pw = QLineEdit()
        new_pw.setObjectName("settingsInput")
        new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        new_pw.setFixedHeight(34)
        ch_lay.addWidget(new_pw)

        # Strength meter
        ch_strength = QLabel("")
        ch_strength.setStyleSheet("font-size: 11px; font-family: monospace;")
        ch_lay.addWidget(ch_strength)

        def _update_ch_strength(pw):
            if not pw:
                ch_strength.setText("")
                return
            level, label, color = _pw_strength(pw)
            bars = "█" * (level + 1) + "░" * (3 - level)
            ch_strength.setText(f"{bars}  {label}")
            ch_strength.setStyleSheet(
                f"font-size: 11px; color: {color}; font-family: monospace;"
            )
        new_pw.textChanged.connect(_update_ch_strength)

        ch_lay.addWidget(QLabel("Confirm new password:", objectName="settingsLabel"))
        conf_pw = QLineEdit()
        conf_pw.setObjectName("settingsInput")
        conf_pw.setEchoMode(QLineEdit.EchoMode.Password)
        conf_pw.setFixedHeight(34)
        ch_lay.addWidget(conf_pw)

        ch_err = QLabel("")
        ch_err.setStyleSheet("color: #e53935; font-size: 11px;")
        ch_err.setVisible(False)
        ch_lay.addWidget(ch_err)

        ch_btn = QPushButton("Change password")
        ch_btn.setObjectName("btnPrimary")
        ch_btn.setFixedHeight(36)
        ch_lay.addWidget(ch_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        ch_lay.addStretch()

        def _change_pw():
            stored = self._api_get_stored_hash()
            if stored and _hash_pw(cur_pw.text()) != stored:
                ch_err.setText("Current password is incorrect.")
                ch_err.setVisible(True)
                return
            level, label, _ = _pw_strength(new_pw.text())
            if level < 1:
                ch_err.setText(f"Password is too weak ({label}). Use 8+ chars with mixed case and numbers.")
                ch_err.setVisible(True)
                return
            if len(new_pw.text()) < 4:
                ch_err.setText("New password must be at least 4 characters.")
                ch_err.setVisible(True)
                return
            if new_pw.text() != conf_pw.text():
                ch_err.setText("Passwords do not match.")
                ch_err.setVisible(True)
                return
            new_hash = _hash_pw(new_pw.text())
            self.settings_save_requested.emit({"api_key_password_hash": new_hash})
            self._api_pw_hash_cache = new_hash
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(dlg, "Done", "Password changed successfully.")
            dlg.accept()

        ch_btn.clicked.connect(_change_pw)
        tabs.addTab(change_tab, "Change Password")

        root.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("btnOutline")
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(dlg.reject)
        root.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)

        dlg.exec()

    # ── Recovery contact persistence ──────────────────────────────────────────

    def _api_get_recovery_contacts(self) -> list[str]:
        raw = getattr(self, "_api_recovery_contacts_cache", "")
        if not raw:
            return []
        return [c.strip() for c in raw.split("||") if c.strip()]

    def _api_save_recovery_contacts(self, contacts: list[str]):
        raw = "||".join(contacts)
        self._api_recovery_contacts_cache = raw
        self.settings_save_requested.emit({"api_recovery_contacts": raw})

    # ── Send reset code via Gmail SMTP ────────────────────────────────────────

    _SENDER_EMAIL = "veaja.app.official@gmail.com"
    # App password stored as env var VEAJA_GMAIL_APP_PW (never hardcoded)

    def _api_send_reset_code(self, contact: str, code: str) -> tuple[bool, str]:
        """
        Send a 6-digit reset code to an email or phone (via email-to-SMS gateway).
        Returns (success, error_message).
        """
        import os, smtplib
        from email.mime.text import MIMEText

        app_pw = os.environ.get("VEAJA_GMAIL_APP_PW", "")
        if not app_pw:
            return False, (
                "Gmail app password not configured.\n"
                "Set the environment variable VEAJA_GMAIL_APP_PW to your Gmail app password."
            )

        # Determine destination — phone numbers use carrier email-to-SMS gateways
        dest = self._resolve_contact_address(contact)

        subject = "Veaja — Your password reset code"
        body = (
            f"Your Veaja API Key password reset code is:\n\n"
            f"  {code}\n\n"
            f"This code is valid for 10 minutes.\n"
            f"If you did not request this, ignore this message."
        )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = self._SENDER_EMAIL
        msg["To"]      = dest

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                server.login(self._SENDER_EMAIL, app_pw)
                server.sendmail(self._SENDER_EMAIL, [dest], msg.as_string())
            return True, ""
        except Exception as e:
            return False, str(e)

    def _resolve_contact_address(self, contact: str) -> str:
        """
        If contact looks like a phone number, map it to an email-to-SMS gateway address.
        Otherwise return as-is (already an email).
        """
        import re
        digits = re.sub(r"\D", "", contact)
        if len(digits) >= 7:
            # Default to generic SMS gateway — user can configure their carrier
            # Common US gateways: @txt.att.net, @vtext.com, @tmomail.net
            # We use a generic fallback; user should add their email instead for reliability
            return f"{digits}@tmomail.net"
        return contact

    def _api_on_page_enter(self):
        """Always show the lock screen when navigating to this page."""
        if hasattr(self, "_api_page_stack"):
            self._api_show_lock()

    def _api_on_page_leave(self):
        """Stop the timer when leaving the page."""
        if hasattr(self, "_api_lock_timer"):
            self._api_lock_timer.stop()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_api_keys(self):
        data = {k: field.text().strip() for k, field in self._api_key_inputs.items()}

        # If a custom card's name maps to a known provider, also write the
        # value into the standard slot so get_api_keys() picks it up directly.
        _CUSTOM_NAME_MAP = {
            "gemini":    "api_key_gemini",
            "google":    "api_key_gemini",
            "aistudio":  "api_key_gemini",
            "openai":    "api_key_openai",
            "gpt":       "api_key_openai",
            "claude":    "api_key_claude",
            "anthropic": "api_key_claude",
        }
        for k, v in list(data.items()):
            if not k.startswith("custom_") or not v:
                continue
            k_lower = k.lower()
            for keyword, std_key in _CUSTOM_NAME_MAP.items():
                if keyword in k_lower:
                    # Only fill the standard slot if it isn't already set
                    if not data.get(std_key):
                        data[std_key] = v
                    break

        import sys
        set_keys = [k for k, v in data.items() if v]
        print(f"[SAVE] Saving {len(set_keys)} keys: {set_keys}", file=sys.stderr)
        self.settings_save_requested.emit(data)
        # Visual confirmation
        self._api_show_save_confirmation()

    def _api_show_save_confirmation(self):
        """Briefly flash the Save button green to confirm the save worked."""
        # Find the save button by searching the content page top bar
        if not hasattr(self, "_api_content_page"):
            return
        from PyQt6.QtWidgets import QPushButton
        for btn in self._api_content_page.findChildren(QPushButton):
            if btn.text() == "Save":
                original_text  = btn.text()
                original_style = btn.styleSheet()
                btn.setText("✓ Saved")
                btn.setStyleSheet(
                    "QPushButton { background: #22c55e; color: #ffffff; "
                    "border: none; border-radius: 6px; font-weight: 600; }"
                )
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, lambda: (
                    btn.setText(original_text),
                    btn.setStyleSheet(original_style),
                ))
                break

    def _open_url(self, url: str):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))

    def apply_api_keys(self, profile: dict):
        if not hasattr(self, "_api_key_inputs"):
            return
        for key, field in self._api_key_inputs.items():
            field.setText(profile.get(key, ""))
        # Restore recovery contacts cache
        self._api_recovery_contacts_cache = profile.get("api_recovery_contacts", "")
