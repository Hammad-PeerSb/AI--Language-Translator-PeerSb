#
# IMPORT REQUIRED LIBRARIES
#

import re
from datetime import datetime

import requests
import streamlit as st
from langdetect import DetectorFactory, detect

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except Exception:
    DEEP_TRANSLATOR_AVAILABLE = False


#
# PAGE CONFIGURATION
#

st.set_page_config(
    page_title="AI Language Translator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)


#
# LANGUAGE DETECTOR
#

DetectorFactory.seed = 0


#
# SUPPORTED LANGUAGES
#

LANGUAGES = {
    "english": "en",
    "urdu": "ur",
    "pashto": "ps",
    "hindi": "hi",
    "arabic": "ar",
    "persian": "fa",
    "french": "fr",
    "spanish": "es",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh-CN",
    "turkish": "tr",
    "dutch": "nl",
    "gujarati": "gu",
    "marathi": "mr",
    "tamil": "ta",
    "bengali": "bn",
    "punjabi": "pa",
}

LANGUAGE_DISPLAY_NAMES = {
    "english": "English",
    "urdu": "Urdu",
    "pashto": "Pashto",
    "hindi": "Hindi",
    "arabic": "Arabic",
    "persian": "Persian",
    "french": "French",
    "spanish": "Spanish",
    "german": "German",
    "italian": "Italian",
    "portuguese": "Portuguese",
    "russian": "Russian",
    "japanese": "Japanese",
    "korean": "Korean",
    "chinese": "Chinese",
    "turkish": "Turkish",
    "dutch": "Dutch",
    "gujarati": "Gujarati",
    "marathi": "Marathi",
    "tamil": "Tamil",
    "bengali": "Bengali",
    "punjabi": "Punjabi",
}


#
# SESSION STATE
#

DEFAULT_STATE = {
    "history": [],
    "translated_text": "",
    "dark_mode": False,
    "selected_source": "english",
    "selected_target": "urdu",
    "input_text": "",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


#
# LANGUAGE DETECTION DATA
#

COMMON_ENGLISH = {
    "i", "am", "is", "are", "was", "were", "the", "a", "an",
    "you", "your", "we", "they", "he", "she", "it", "this",
    "that", "these", "those", "what", "when", "where", "why",
    "how", "who", "can", "could", "will", "would", "should",
    "have", "has", "had", "do", "does", "did", "my", "me",
    "to", "of", "in", "on", "for", "with", "and", "or", "but",
    "not", "hello", "hi", "good", "morning", "evening", "night",
    "thank", "thanks", "please", "name", "want", "need",
    "translate", "language",
}

PASHTO_STRONG_CHARS = set("ټځڅډړږښڼېۍ")
PASHTO_COMMON_CHARS = set("ګ")

URDU_STRONG_CHARS = set("ٹڈڑںھہۓ")
PERSIAN_STRONG_CHARS = set("کگی")
ARABIC_STRONG_CHARS = set("ثذضظصط")

PASHTO_WORDS = {
    "زه", "ته", "تاسو", "مونږ", "موږ", "هغه", "دا", "دی", "ده",
    "دوی", "څه", "څنګه", "ولې", "چېرته", "چرته", "کله", "څوک",
    "کوم", "کومه", "زما", "ستا", "ستاسو", "زموږ", "ورور", "خور",
    "مور", "پلار", "کور", "هلک", "جلۍ", "جینۍ", "ماشوم", "اوس",
    "سبا", "پرون", "سحر", "مننه", "مهرباني", "ښه", "نه", "هو",
    "کړم", "کړې", "کړی", "کوي", "کول", "لرم", "لري", "لرې",
    "راځه", "راځم", "ځم", "ځي", "شوم", "شو", "شي", "کې", "سره",
    "لپاره", "چې", "او", "خو",
}

URDU_WORDS = {
    "میں", "میری", "میرا", "میرے", "آپ", "تم", "ہم", "وہ", "یہ",
    "کیا", "کیسے", "کیوں", "کہاں", "کب", "کون", "کونسا", "ہے",
    "ہیں", "تھا", "تھی", "تھے", "ہوں", "ہو", "نہیں", "اور",
    "لیکن", "سے", "کو", "کا", "کی", "کے", "پر", "لئے", "لیے",
    "آپکا", "آپکی", "نام", "شکریہ", "مہربانی", "بھائی", "بہن",
    "والد", "والدہ", "گھر", "اچھا", "اچھی",
}

PERSIAN_WORDS = {
    "من", "تو", "شما", "ما", "او", "این", "آن", "چه", "چرا",
    "کجا", "کی", "چطور", "هست", "است", "هستم", "هستی", "نیست",
    "برای", "با", "از", "در", "و", "اما", "خوب", "ممنون",
    "خانه", "برادر", "خواهر",
}

ARABIC_WORDS = {
    "أنا", "أنت", "أنتَ", "أنتِ", "نحن", "هو", "هي", "هذا",
    "هذه", "ذلك", "ماذا", "كيف", "لماذا", "أين", "متى", "من",
    "نعم", "لا", "شكرا", "شكراً", "مرحبا", "السلام", "عليكم",
    "البيت", "أخي", "أختي",
}


#
# LANGUAGE DETECTION
#

def detect_language(text: str) -> str:
    text = text.strip()

    if not text:
        return "Waiting..."

    english_words = set(
        re.findall(r"[a-zA-Z]+", text.lower())
    )

    english_score = len(
        english_words.intersection(COMMON_ENGLISH)
    )

    if english_score >= 1 and not re.search(
        r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]",
        text,
    ):
        try:
            detected_code = detect(text).lower()

            if detected_code == "en":
                return "English"
        except Exception:
            return "English"

    if re.search(r"[\u0900-\u097F]", text):
        try:
            detected_code = detect(text).lower()

            if detected_code == "mr":
                return "Marathi"

            if detected_code == "hi":
                return "Hindi"
        except Exception:
            pass

        return "Hindi"

    if re.search(r"[\u0A80-\u0AFF]", text):
        return "Gujarati"

    if re.search(r"[\u0980-\u09FF]", text):
        return "Bengali"

    if re.search(r"[\u0B80-\u0BFF]", text):
        return "Tamil"

    if re.search(r"[\u3040-\u30FF]", text):
        return "Japanese"

    if re.search(r"[\uAC00-\uD7AF]", text):
        return "Korean"

    if re.search(r"[\u4E00-\u9FFF]", text):
        return "Chinese"

    arabic_script = re.findall(
        r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]",
        text,
    )

    if arabic_script:
        words = set(
            re.findall(
                r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+",
                text,
            )
        )

        pashto_score = (
            sum(char in PASHTO_STRONG_CHARS for char in text) * 5
            + sum(char in PASHTO_COMMON_CHARS for char in text) * 2
            + len(words.intersection(PASHTO_WORDS)) * 8
        )

        urdu_score = (
            sum(char in URDU_STRONG_CHARS for char in text) * 5
            + len(words.intersection(URDU_WORDS)) * 8
        )

        persian_score = (
            sum(char in PERSIAN_STRONG_CHARS for char in text)
            + len(words.intersection(PERSIAN_WORDS)) * 8
        )

        arabic_score = (
            sum(char in ARABIC_STRONG_CHARS for char in text) * 4
            + len(words.intersection(ARABIC_WORDS)) * 8
        )

        scores = {
            "Pashto": pashto_score,
            "Urdu": urdu_score,
            "Persian": persian_score,
            "Arabic": arabic_score,
        }

        best_language = max(
            scores,
            key=scores.get,
        )

        if scores[best_language] > 0:
            return best_language

    try:
        detected_code = detect(text).lower()

        detected_names = {
            "en": "English",
            "ur": "Urdu",
            "ps": "Pashto",
            "hi": "Hindi",
            "ar": "Arabic",
            "fa": "Persian",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh-cn": "Chinese",
            "zh-tw": "Chinese",
            "zh": "Chinese",
            "tr": "Turkish",
            "nl": "Dutch",
            "gu": "Gujarati",
            "mr": "Marathi",
            "ta": "Tamil",
            "bn": "Bengali",
            "pa": "Punjabi",
        }

        return detected_names.get(
            detected_code,
            "Unknown Language",
        )

    except Exception:
        return "Unknown Language"


#
# TEXT CHUNKING
#

def split_into_chunks(
    text: str,
    max_len: int = 450,
):
    text = text.strip()

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?۔؟])\s+",
        text,
    )

    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(sentence) <= max_len:
            candidate = f"{current} {sentence}".strip()

            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    chunks.append(current)

                current = sentence

        else:
            if current:
                chunks.append(current)
                current = ""

            words = sentence.split()
            piece = ""

            for word in words:
                candidate = f"{piece} {word}".strip()

                if len(candidate) <= max_len:
                    piece = candidate
                else:
                    if piece:
                        chunks.append(piece)

                    piece = word

            if piece:
                chunks.append(piece)

    if current:
        chunks.append(current)

    return chunks


#
# FORMAT OUTPUT
#

def format_output_text(text: str) -> str:
    if not text or not text.strip():
        return ""

    sentences = re.split(
        r"(?<=[.!?۔؟])\s+",
        text.strip(),
    )

    cleaned = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

    return "\n\n".join(cleaned)


#
# NORMALIZE LANGUAGE CODE
#

def normalize_language_code(code: str) -> str:
    if not code:
        return ""

    code = code.strip()

    special_codes = {
        "zh-cn": "zh-CN",
        "zh-tw": "zh-TW",
    }

    if code.lower() in special_codes:
        return special_codes[code.lower()]

    return code.split("-")[0].lower()


#
# GOOGLE PUBLIC TRANSLATION
#

def google_public_translate(
    text,
    source_code,
    target_code,
):
    source = normalize_language_code(source_code)
    target = normalize_language_code(target_code)

    chunks = split_into_chunks(text)

    if not chunks:
        raise Exception("No text available.")

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            )
        }
    )

    results = []

    for chunk in chunks:
        url = (
            "https://translate.googleapis.com/"
            "translate_a/single"
        )

        params = {
            "client": "gtx",
            "sl": source,
            "tl": target,
            "dt": "t",
            "q": chunk,
        }

        response = session.get(
            url,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        translated_parts = []

        if (
            isinstance(data, list)
            and len(data) > 0
            and isinstance(data[0], list)
        ):
            for item in data[0]:
                if (
                    isinstance(item, list)
                    and len(item) > 0
                    and item[0]
                ):
                    translated_parts.append(
                        str(item[0])
                    )

        translated = "".join(
            translated_parts
        ).strip()

        if not translated:
            raise Exception(
                "Google returned an empty translation."
            )

        results.append(translated)

    return " ".join(results).strip()


#
# MYMEMORY API TRANSLATION
#

def mymemory_api_translate(
    text,
    source_code,
    target_code,
):
    source = normalize_language_code(source_code)
    target = normalize_language_code(target_code)

    chunks = split_into_chunks(text)

    if not chunks:
        raise Exception("No text available.")

    session = requests.Session()

    results = []

    for chunk in chunks:
        response = session.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": chunk,
                "langpair": f"{source}|{target}",
            },
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        status = data.get("responseStatus")

        if status not in [200, "200"]:
            raise Exception(
                data.get(
                    "responseDetails",
                    "MyMemory rejected the request.",
                )
            )

        response_data = data.get(
            "responseData",
            {},
        )

        translated = str(
            response_data.get(
                "translatedText",
                "",
            )
        ).strip()

        if not translated:
            raise Exception(
                "MyMemory returned no translation."
            )

        results.append(translated)

    return " ".join(results).strip()


#
# DEEP TRANSLATOR OF GOOGLE
#

def deep_google_translate(
    text,
    source_code,
    target_code,
):
    if not DEEP_TRANSLATOR_AVAILABLE:
        raise Exception(
            "deep-translator is not installed."
        )

    source = normalize_language_code(source_code)
    target = normalize_language_code(target_code)

    chunks = split_into_chunks(text)

    if not chunks:
        raise Exception("No text available.")

    translator = GoogleTranslator(
        source=source,
        target=target,
    )

    results = []

    for chunk in chunks:
        result = translator.translate(chunk)

        if not result:
            raise Exception(
                "Google Translator returned no result."
            )

        results.append(
            str(result).strip()
        )

    return " ".join(results).strip()


#
# DEEP TRANSLATOR MYMEMORY
#

def deep_mymemory_translate(
    text,
    source_code,
    target_code,
):
    if not DEEP_TRANSLATOR_AVAILABLE:
        raise Exception(
            "deep-translator is not installed."
        )

    source = normalize_language_code(source_code)
    target = normalize_language_code(target_code)

    chunks = split_into_chunks(text)

    if not chunks:
        raise Exception("No text available.")

    translator = MyMemoryTranslator(
        source=source,
        target=target,
    )

    results = []

    for chunk in chunks:
        result = translator.translate(chunk)

        if not result:
            raise Exception(
                "MyMemory Translator returned no result."
            )

        results.append(
            str(result).strip()
        )

    return " ".join(results).strip()


#
# TRANSLATION ROUTER
#

def translate_text(
    text,
    source_code,
    target_code,
):
    if not text.strip():
        return (
            "",
            "None",
            ["Input text is empty."],
        )

    source = normalize_language_code(
        source_code
    )

    target = normalize_language_code(
        target_code
    )

    if source == target:
        return (
            text.strip(),
            "Same Language",
            [],
        )

    engines = [
        (
            "Google Public API",
            google_public_translate,
        ),
        (
            "MyMemory API",
            mymemory_api_translate,
        ),
    ]

    if DEEP_TRANSLATOR_AVAILABLE:
        engines.extend(
            [
                (
                    "Google Translator",
                    deep_google_translate,
                ),
                (
                    "MyMemory Translator",
                    deep_mymemory_translate,
                ),
            ]
        )

    errors = []

    for name, function in engines:
        try:
            result = function(
                text,
                source,
                target,
            )

            if result:
                return (
                    result,
                    name,
                    errors,
                )

        except Exception as error:
            errors.append(
                f"{name}: {error}"
            )

    return (
        "",
        "Failed",
        errors,
    )


#
# SWAP LANGUAGES
#

def swap_languages():
    source = st.session_state.selected_source
    target = st.session_state.selected_target

    st.session_state.selected_source = target
    st.session_state.selected_target = source

    if st.session_state.translated_text:
        st.session_state.input_text = (
            st.session_state.translated_text
        )

    st.session_state.translated_text = ""


#
# THEME
#

if st.session_state.dark_mode:
    APP_BG = "#0B0F19"
    CARD_BG = "#141B2D"
    SIDEBAR_BG = "#0F1524"
    INPUT_BG = "#1A2236"
    TEXT = "#F1F5F9"
    SECONDARY = "#94A3B8"
    BORDER = "#28324A"
    PRIMARY = "#6366F1"
    ACCENT = "#4F46E5"
    SHADOW = "rgba(0,0,0,0.45)"
else:
    APP_BG = "#F7F9FC"
    CARD_BG = "#FFFFFF"
    SIDEBAR_BG = "#F0F3FA"
    INPUT_BG = "#FFFFFF"
    TEXT = "#1E293B"
    SECONDARY = "#64748B"
    BORDER = "#E2E8F0"
    PRIMARY = "#4F46E5"
    ACCENT = "#3730A3"
    SHADOW = "rgba(30,41,89,0.08)"


#
# CUSTOM CSS
#

st.markdown(
    f"""
<style>

.stApp {{
    background:
        radial-gradient(
            circle at top right,
            rgba(79,70,229,0.06),
            transparent 40%
        ),
        {APP_BG} !important;
    color: {TEXT} !important;
}}

.main .block-container {{
    max-width: 1200px;
    padding-top: 1.8rem;
    padding-bottom: 4rem;
}}

.main-title {{
    text-align: center;
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
    background:
        linear-gradient(
            90deg,
            {ACCENT},
            {PRIMARY}
        );
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.main-subtitle {{
    text-align: center;
    color: {SECONDARY} !important;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.3px;
    margin-bottom: 30px;
}}

.section-title {{
    color: {TEXT} !important;
    font-size: 19px;
    font-weight: 700;
    margin-top: 20px;
    margin-bottom: 12px;
}}

[data-testid="stSidebar"] {{
    background: {SIDEBAR_BG} !important;
    border-right: 1px solid {BORDER};
}}

.sidebar-title {{
    color: {TEXT} !important;
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 18px;
}}

/* SIDEBAR CARDS */

.sidebar-card {{
    position: relative;
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 13px 15px;
    margin: 0 0 11px 0;
    color: {TEXT} !important;
    box-shadow:
        0 3px 10px {SHADOW};
    transform: translate3d(0, 0, 0);
    transition:
        transform 0.25s ease,
        box-shadow 0.25s ease,
        border-color 0.25s ease;
    overflow: hidden;
    isolation: isolate;
}}

/* RGB BORDER */

.sidebar-card::before {{
    content: "";
    position: absolute;
    inset: -2px;

    border-radius: 16px;

    background:
        linear-gradient(
            90deg,
            #ff0080,
            #7928ca,
            #00d4ff,
            #00ff88,
            #ff0080
        );

    background-size: 300% 300%;

    opacity: 0;

    z-index: -2;

    animation:
        rgbMove 4s linear infinite;

    transition:
        opacity 0.25s ease;
}}

/* INNER BOX */

.sidebar-card::after {{
    content: "";
    position: absolute;
    inset: 2px;

    border-radius: 12px;

    background: {CARD_BG};

    z-index: -1;
}}

/* HOVER */

.sidebar-card:hover {{
    transform: translate3d(4px, -3px, 0);

    border-color: transparent !important;

    box-shadow:
        0 0 6px rgba(255, 0, 128, 0.50),
        0 0 14px rgba(121, 40, 202, 0.45),
        0 0 22px rgba(0, 212, 255, 0.40),
        0 8px 24px rgba(0, 0, 0, 0.16);

    cursor: pointer;
}}

.sidebar-card:hover::before {{
    opacity: 1;
}}

/* CLICK / PRESS */

.sidebar-card:active {{
    transform: translate3d(5px, -1px, 0) scale(0.97);

    box-shadow:
        0 0 8px rgba(255, 0, 128, 0.70),
        0 0 17px rgba(121, 40, 202, 0.60),
        0 0 27px rgba(0, 212, 255, 0.55),
        0 0 34px rgba(0, 255, 136, 0.35);
}}

.sidebar-card:active::before {{
    opacity: 1;
}}

/* RGB ANIMATION */

@keyframes rgbMove {{
    0% {{
        background-position: 0% 50%;
    }}

    50% {{
        background-position: 100% 50%;
    }}

    100% {{
        background-position: 0% 50%;
    }}
}}

/* CARD TEXT */

.card-title {{
    position: relative;
    z-index: 2;

    color: {TEXT} !important;

    font-size: 14px;
    font-weight: 650;

    transition:
        transform 0.25s ease,
        color 0.25s ease;
}}

.sidebar-card:hover .card-title {{
    transform: translateX(3px);
}}

.sidebar-card:active .card-title {{
    transform: translateX(5px);
}}

.lang-label {{
    font-size: 13px;
    font-weight: 600;
    color: {SECONDARY} !important;
    height: 20px;
    display: flex;
    align-items: center;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

div[data-baseweb="select"] > div {{
    background: {INPUT_BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    min-height: 46px !important;
    box-shadow: 0 2px 8px {SHADOW} !important;
}}

div[data-baseweb="select"] > div:hover {{
    border-color: {PRIMARY} !important;
}}

div[data-baseweb="select"] span {{
    color: {TEXT} !important;
}}

.st-key-swap_button {{
    width: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
}}

.st-key-swap_button button {{
    width: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    padding: 0 !important;
    margin: 0 auto !important;
    border-radius: 50% !important;
    background: {CARD_BG} !important;
    color: {PRIMARY} !important;
    border: 1.5px solid {PRIMARY} !important;
    font-size: 18px !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 10px {SHADOW} !important;
    transition:
        transform 0.2s ease,
        background 0.2s ease,
        color 0.2s ease !important;
}}

.st-key-swap_button button:hover {{
    transform: rotate(180deg) !important;
    background: {PRIMARY} !important;
    color: #FFFFFF !important;
}}

textarea {{
    background-color: {INPUT_BG} !important;
    color: {TEXT} !important;
    -webkit-text-fill-color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 10px {SHADOW} !important;
    line-height: 1.8 !important;
    font-size: 15px !important;
}}

textarea::placeholder {{
    color: {SECONDARY} !important;
    opacity: 1 !important;
}}

textarea:disabled {{
    color: {TEXT} !important;
    -webkit-text-fill-color: {TEXT} !important;
    opacity: 1 !important;
    background: {INPUT_BG} !important;
}}

textarea:focus {{
    border-color: {PRIMARY} !important;
    box-shadow:
        0 0 0 3px
        rgba(79,70,229,0.12)
        !important;
}}

.stTextArea label {{
    color: {TEXT} !important;
    font-weight: 600 !important;
}}

.stButton > button {{
    border: none !important;
    border-radius: 10px !important;
    min-height: 44px !important;
    font-size: 15px !important;
    font-weight: 700 !important;

    background:
        linear-gradient(
            90deg,
            {ACCENT},
            {PRIMARY}
        ) !important;

    color: white !important;

    box-shadow:
        0 4px 14px
        rgba(79,70,229,0.22)
        !important;

    transition:
        box-shadow 0.2s ease,
        transform 0.2s ease !important;
}}

.stButton > button:hover {{
    transform: translateY(-1px) !important;

    box-shadow:
        0 8px 20px
        rgba(79,70,229,0.28)
        !important;
}}

.detection-box {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-left: 3px solid {PRIMARY};
    border-radius: 10px;
    padding: 12px 17px;
    margin: 12px 0 20px 0;
    color: {TEXT} !important;
    box-shadow: 0 2px 8px {SHADOW};
}}

div[data-testid="stMetric"] {{
    background: {CARD_BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    padding: 12px !important;
    box-shadow: 0 2px 8px {SHADOW} !important;
}}

div[data-testid="stMetricLabel"] {{
    color: {SECONDARY} !important;
}}

div[data-testid="stMetricValue"] {{
    color: {TEXT} !important;
}}

.stDownloadButton > button {{
    border: none !important;
    border-radius: 10px !important;
    min-height: 44px !important;
    font-size: 14px !important;
    font-weight: 700 !important;

    background:
        linear-gradient(
            90deg,
            {ACCENT},
            {PRIMARY}
        ) !important;

    color: white !important;

    box-shadow:
        0 4px 14px
        rgba(79,70,229,0.22)
        !important;
}}

div[data-testid="stAlert"] {{
    border-radius: 10px !important;
}}

[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    background: {CARD_BG} !important;
}}

.custom-footer {{
    width: 100%;
    text-align: center;
    padding: 30px 15px 20px 15px;
    margin-top: 40px;
    border-top: 1px solid {BORDER};
}}

.footer-title {{
    color: {TEXT} !important;
    font-size: 20px !important;
    font-weight: 800 !important;
    margin-bottom: 8px;
}}

.footer-text {{
    color: {SECONDARY} !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    margin-bottom: 10px;
}}

.footer-author {{
    color: {SECONDARY} !important;
    font-size: 15px !important;
    font-weight: 700 !important;
}}

.footer-author strong {{
    color: {PRIMARY} !important;
    font-size: 18px !important;
    font-weight: 900 !important;
}}

.footer-credit {{
    color: {SECONDARY} !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    margin-top: 8px;
    opacity: 0.85;
}}

@media (max-width: 768px) {{

    .main .block-container {{
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }}

    .main-title {{
        font-size: 30px;
    }}

    .main-subtitle {{
        font-size: 12px;
    }}

    .section-title {{
        font-size: 17px;
    }}

    .st-key-swap_button button {{
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        font-size: 15px !important;
    }}
}}

</style>
""",
    unsafe_allow_html=True,
)


#
# SIDEBAR
#

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">⚙️ Settings</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("### 🌐 Supported Languages")

    st.markdown(
        f"""
        <div class="sidebar-card">
            <div class="card-title">
                🌍 {len(LANGUAGES)} Languages
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("### ✨ Features")

    features = [
        "🌍 Multi-language translation",
        "🔎 Smart language detection",
        "🔄 Language swapping",
        "📥 Download translation",
        "🕘 Translation history",
    ]

    for feature in features:

        st.markdown(
            f"""
            <div class="sidebar-card">
                <div class="card-title">
                    {feature}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 🎨 Mode")

    selected_mode = st.radio(
        "Appearance",
        ["☀️ Light", "🌙 Dark"],
        index=(
            1
            if st.session_state.dark_mode
            else 0
        ),
        horizontal=True,
    )

    new_dark_mode = (
        selected_mode == "🌙 Dark"
    )

    if new_dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = new_dark_mode
        st.rerun()

    st.markdown("### ℹ️ About")

    st.info(
        "**AI Language Translator**\n\n"
        "A multilingual NLP application "
        "built with Python and Streamlit.\n\n"
        "**Developer:** PeerSb"
    )


#
# MAIN HEADER
#

st.markdown(
    '<div class="main-title">'
    '🌐 AI Language Translator'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-subtitle">'
    'Intelligent • Fast • Simple • Multilingual'
    '</div>',
    unsafe_allow_html=True,
)


#
# LANGUAGE SELECTION
#

st.markdown(
    '<div class="section-title">'
    '🌐 Translate Language'
    '</div>',
    unsafe_allow_html=True,
)

col_from, col_swap, col_to = st.columns(
    [5, 0.8, 5],
    gap="small",
)


#
# SOURCE LANGUAGE
#

with col_from:

    st.markdown(
        '<div class="lang-label">From</div>',
        unsafe_allow_html=True,
    )

    source_language = st.selectbox(
        "Source Language",
        list(LANGUAGES.keys()),
        format_func=lambda x: (
            LANGUAGE_DISPLAY_NAMES[x]
        ),
        key="selected_source",
        label_visibility="collapsed",
    )


#
# SWAP BUTTON
#

with col_swap:

    st.markdown(
        '<div class="lang-label">&nbsp;</div>',
        unsafe_allow_html=True,
    )

    st.button(
        "🔄",
        key="swap_button",
        help="Swap source and target languages",
        on_click=swap_languages,
        use_container_width=True,
    )


#
# TARGET LANGUAGE
#

with col_to:

    st.markdown(
        '<div class="lang-label">To</div>',
        unsafe_allow_html=True,
    )

    target_language = st.selectbox(
        "Target Language",
        list(LANGUAGES.keys()),
        format_func=lambda x: (
            LANGUAGE_DISPLAY_NAMES[x]
        ),
        key="selected_target",
        label_visibility="collapsed",
    )


#
# TEXT WORKSPACE
#

text_col, result_col = st.columns(
    2,
    gap="large",
)


#
# INPUT TEXT
#

with text_col:

    st.markdown("### ✍️ Text Here")

    text = st.text_area(
        "Original Text",
        height=160,
        placeholder=(
            "Type or paste your text here..."
        ),
        label_visibility="visible",
        key="input_text",
    )


#
# OUTPUT TEXT
#

with result_col:

    st.markdown("### 📄 Translation")

    st.text_area(
        "Translated Text",
        value=format_output_text(
            st.session_state.translated_text
        ),
        height=160,
        placeholder=(
            "Your translation will appear here..."
        ),
        disabled=False,
        label_visibility="visible",
    )


#
# LANGUAGE DETECTION
#

detected_language = detect_language(text)

st.markdown(
    f"""
    <div class="detection-box">
        🔎 <b>Detected Language:</b>
        {detected_language}
    </div>
    """,
    unsafe_allow_html=True,
)


#
# TRANSLATION STATISTICS
#

st.markdown(
    '<div class="section-title">'
    '📊 Translation Statistics'
    '</div>',
    unsafe_allow_html=True,
)

word_count = (
    len(text.split())
    if text.strip()
    else 0
)

character_count = (
    len(text)
    if text
    else 0
)

direction = (
    f"{LANGUAGE_DISPLAY_NAMES[source_language]}"
    f" → "
    f"{LANGUAGE_DISPLAY_NAMES[target_language]}"
)

stat1, stat2, stat3 = st.columns(
    3,
    gap="small",
)

with stat1:

    st.metric(
        "📝 Words",
        word_count,
    )

with stat2:

    st.metric(
        "🔤 Characters",
        character_count,
    )

with stat3:

    st.metric(
        "🧭 Direction",
        direction,
    )


#
# TRANSLATION BUTTON
#

st.write("")

translate_clicked = st.button(
    "✨ Translate",
    use_container_width=True,
)


#
# TRANSLATION PROCESS
#

if translate_clicked:

    if not text.strip():

        st.warning(
            "⚠️ Please enter some text first."
        )

    elif source_language == target_language:

        st.session_state.translated_text = (
            text.strip()
        )

        st.info(
            "ℹ️ Source and target languages "
            "are the same."
        )

        st.rerun()

    else:

        source_code = LANGUAGES[
            source_language
        ]

        target_code = LANGUAGES[
            target_language
        ]

        with st.spinner(
            "🔄 Translating..."
        ):

            result, engine, errors = (
                translate_text(
                    text,
                    source_code,
                    target_code,
                )
            )

        if result:

            st.session_state.translated_text = (
                result
            )

            history_item = {
                "time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "source": (
                    LANGUAGE_DISPLAY_NAMES[
                        source_language
                    ]
                ),
                "target": (
                    LANGUAGE_DISPLAY_NAMES[
                        target_language
                    ]
                ),
                "original": text,
                "translation": result,
                "engine": engine,
            }

            st.session_state.history.insert(
                0,
                history_item,
            )

            st.session_state.history = (
                st.session_state.history[:15]
            )

            st.success(
                f"✅ Translation successful • "
                f"{engine}"
            )

            st.rerun()

        else:

            st.error(
                "❌ Translation failed."
            )

            st.warning(
                "The translation services could "
                "not complete the request. "
                "Please check your internet "
                "connection and try again."
            )

            if errors:

                with st.expander(
                    "🔧 Technical Details"
                ):

                    for error in errors:
                        st.code(error)


#
# TRANSLATION TOOLS
#

if st.session_state.translated_text:

    st.markdown(
        '<div class="section-title">'
        '🛠️ Translation Tools'
        '</div>',
        unsafe_allow_html=True,
    )

    tool1, tool2 = st.columns(
        2,
        gap="medium",
    )

    with tool1:

        st.download_button(
            "📥 Download Translation",
            data=format_output_text(
                st.session_state.translated_text
            ),
            file_name="translation.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with tool2:

        clear_translation = st.button(
            "🗑️ Clear Translation",
            use_container_width=True,
        )

        if clear_translation:

            st.session_state.translated_text = ""

            st.rerun()


#
# HISTORY OF TRANSLATION
#

st.markdown(
    '<div class="section-title">'
    '🕘 Translation History'
    '</div>',
    unsafe_allow_html=True,
)

if st.session_state.history:

    for index, item in enumerate(
        st.session_state.history
    ):

        with st.expander(
            f"🌐 "
            f"{item['source']} → "
            f"{item['target']} • "
            f"{item['time']}"
        ):

            st.markdown(
                "**Original:**"
            )

            st.write(
                item["original"]
            )

            st.markdown(
                "**Translation:**"
            )

            st.write(
                format_output_text(
                    item["translation"]
                )
            )

            st.caption(
                "Translation engine: "
                + item.get(
                    "engine",
                    "Unknown",
                )
            )

            delete_history = st.button(
                "🗑️ Delete",
                key=f"delete_history_{index}",
            )

            if delete_history:

                st.session_state.history.pop(
                    index
                )

                st.rerun()

    clear_history = st.button(
        "🗑️ Clear All History",
        use_container_width=True,
    )

    if clear_history:

        st.session_state.history = []

        st.rerun()

else:

    st.info(
        "🕘 No translation history yet."
    )


#
# FOOTER
#

st.markdown(
    "##### 🌐 AI Language Translator"
)

st.info(
    "**Built with Python • Streamlit • NLP • Google Translator**"
)