"""The language catalogue: every target language, and which models can speak it.

Pure data, with no Tk. Sources, checked on 31 October 2026 (both services are in preview,
so re-check before Milestone 4):

- Gemini 3.5 Live Translate: the supported-languages table at
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-live-translate
- Qwen 3.8 LiveTranslate: the 29 "audio + text" output languages at
  https://qwen.ai/blog?id=qwen3.8-livetranslate (the other 31 are text only, so not listed)

Pass-thru sends the original audio, so it "speaks" every language.
"""

from __future__ import annotations

from dataclasses import dataclass

GEMINI, QWEN, PASS = "gemini", "qwen", "pass"


@dataclass(frozen=True)
class Language:
    code2: str  # the 2-letter code shown on the big display
    tag: str  # BCP-47 tag, as saved and sent to the provider
    native: str  # the default label
    models: frozenset[str]
    sample: str | None = None  # mock translated line, until real sessions exist


_G = frozenset({GEMINI, PASS})
_GQ = frozenset({GEMINI, QWEN, PASS})

# Sorted by tag. Every model also includes "pass".
CATALOGUE: tuple[Language, ...] = (
    Language("AF", "af", "Afrikaans", _G),
    Language("AK", "ak", "Akan", _G),
    Language("AM", "am", "አማርኛ", _G),
    Language("AR", "ar", "العربية", _GQ),
    Language("AZ", "az", "Azərbaycanca", _G),
    Language("BE", "be", "Беларуская", _G),
    Language("BG", "bg", "Български", _G),
    Language("BN", "bn", "বাংলা", _G),
    Language("CA", "ca", "Català", _G),
    Language("CS", "cs", "Čeština", _GQ),
    Language("DA", "da", "Dansk", _GQ),
    Language("DE", "de", "Deutsch", _GQ, "Guten Abend und willkommen zur heutigen Sitzung."),
    Language("EL", "el", "Ελληνικά", _G),
    Language("EN", "en", "English", _GQ, "Good evening, and welcome to tonight's session."),
    Language("ES", "es", "Español", _GQ, "Buenas noches y bienvenidos a la sesión de esta noche."),
    Language("ET", "et", "Eesti", _G),
    Language("EU", "eu", "Euskara", _G),
    Language("FA", "fa", "فارسی", _GQ),
    Language("FI", "fi", "Suomi", _GQ),
    Language("TL", "fil", "Filipino", _GQ),
    Language("FR", "fr", "Français", _GQ, "Bonsoir et bienvenue à la séance de ce soir."),
    Language("GL", "gl", "Galego", _G),
    Language("GU", "gu", "ગુજરાતી", _G),
    Language("HA", "ha", "Hausa", _G),
    Language("HE", "he", "עברית", _GQ),
    Language("HI", "hi", "हिन्दी", _GQ),
    Language("HR", "hr", "Hrvatski", _G),
    Language("HU", "hu", "Magyar", _G),
    Language("HY", "hy", "Հայերեն", _G),
    Language("ID", "id", "Bahasa Indonesia", _GQ),
    Language("IS", "is", "Íslenska", _GQ),
    Language("IT", "it", "Italiano", _GQ, "Buonasera e benvenuti alla sessione di stasera."),
    Language("JA", "ja", "日本語", _GQ),
    Language("JV", "jv", "Basa Jawa", _G),
    Language("KA", "ka", "ქართული", _G),
    Language("KK", "kk", "Қазақ тілі", _G),
    Language("KM", "km", "ខ្មែរ", _G),
    Language("KN", "kn", "ಕನ್ನಡ", _G),
    Language("KO", "ko", "한국어", _GQ),
    Language("LO", "lo", "ລາວ", _G),
    Language("LT", "lt", "Lietuvių", _G),
    Language("LV", "lv", "Latviešu", _G),
    Language("MK", "mk", "Македонски", _G),
    Language("ML", "ml", "മലയാളം", _G),
    Language("MN", "mn", "Монгол", _G),
    Language("MR", "mr", "मराठी", _G),
    Language("MS", "ms", "Bahasa Melayu", _GQ),
    Language("MY", "my", "မြန်မာ", _G),
    Language("NB", "nb", "Norsk bokmål", _GQ),
    Language("NE", "ne", "नेपाली", _G),
    Language("NL", "nl", "Nederlands", _GQ, "Goedenavond en welkom bij de sessie van vanavond."),
    Language("PA", "pa", "ਪੰਜਾਬੀ", _G),
    Language("PL", "pl", "Polski", _GQ, "Dobry wieczór i witamy na dzisiejszej sesji."),
    Language(
        "PT",
        "pt-BR",
        "Português",
        _GQ,
        "Boa noite e bem-vindos à sessão desta noite.",
    ),
    Language("PT", "pt-PT", "Português (Portugal)", _G),
    Language("RO", "ro", "Română", _G),
    Language("RU", "ru", "Русский", _GQ),
    Language("RW", "rw", "Kinyarwanda", _G),
    Language("SD", "sd", "سنڌي", _G),
    Language("SI", "si", "සිංහල", _G),
    Language("SK", "sk", "Slovenčina", _G),
    Language("SL", "sl", "Slovenščina", _G),
    Language("SQ", "sq", "Shqip", _G),
    Language("SR", "sr", "Српски", _G),
    Language("SU", "su", "Basa Sunda", _G),
    Language("SV", "sv", "Svenska", _GQ, "God kväll och välkomna till kvällens session."),
    Language("SW", "sw", "Kiswahili", _G),
    Language("TA", "ta", "தமிழ்", _G),
    Language("TE", "te", "తెలుగు", _G),
    Language("TH", "th", "ไทย", _GQ),
    Language("TR", "tr", "Türkçe", _GQ),
    Language("UK", "uk", "Українська", _G),
    Language("UR", "ur", "اردو", _GQ),
    Language("UZ", "uz", "Oʻzbekcha", _G),
    Language("VI", "vi", "Tiếng Việt", _GQ),
    Language("ZH", "zh-Hans", "简体中文", _GQ),
    Language("ZH", "zh-Hant", "繁體中文", _G),
    Language("ZU", "zu", "isiZulu", _G),
)

# The order "first language not already in the rack" tries before the rest of the catalogue.
PREFERRED: tuple[str, ...] = ("es", "fr", "de", "pt-BR", "it", "nl", "pl", "sv")

_BY_TAG = {lang.tag: lang for lang in CATALOGUE}


def by_tag(tag: str) -> Language | None:
    return _BY_TAG.get(tag)


def supports(model: str, tag: str) -> bool:
    lang = _BY_TAG.get(tag)
    return lang is not None and model in lang.models


def for_model(model: str) -> list[Language]:
    """The languages a model can speak, in catalogue order."""
    return [lang for lang in CATALOGUE if model in lang.models]


def next_free(model: str, used: set[str] | frozenset[str]) -> Language:
    """The first language the model speaks that is not in `used`: preferred ones first."""
    order = [_BY_TAG[t] for t in PREFERRED] + list(CATALOGUE)
    spoken = [lang for lang in order if model in lang.models]
    return next((lang for lang in spoken if lang.tag not in used), spoken[0])


def code_of(tag: str) -> str:
    lang = _BY_TAG.get(tag)
    return lang.code2 if lang else tag[:2].upper()


def native_of(tag: str) -> str:
    lang = _BY_TAG.get(tag)
    return lang.native if lang else tag
