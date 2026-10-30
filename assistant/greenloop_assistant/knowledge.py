"""Load the markdown knowledge base and the crop calendar, and search them.

Retrieval is plain keyword scoring (BM25) so it runs with no extra services and
no embeddings bill. Swap `KnowledgeBase.search` for embeddings later if
keyword search stops being good enough; the eval set will show it.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

STOPWORDS = set(
    """a an and are as at be by can do does for from has have how i if in is it its
    my of on or should so that the their them then there these this to was what
    when where which who why will with you your me we our than into about
    le la les de des du un une et en est pour que qui dans au aux sur
    """.split()
)

COUNTRIES = {
    "LV": ["latvia", "latvian", "riga", "lettonie", "لاتفيا"],
    "DZ": ["algeria", "algerian", "algiers", "algérie", "algerie", "الجزائر"],
    "FR": ["france", "french"],
    "SE": ["sweden", "swedish", "suède", "suede", "السويد"],
    "MA": ["morocco", "moroccan", "maroc", "المغرب"],
}
COUNTRY_NAMES = {"LV": "Latvia", "DZ": "Algeria", "FR": "France", "SE": "Sweden", "MA": "Morocco"}

MONTHS = [
    ["january", "jan", "janvier", "يناير", "جانفي"],
    ["february", "feb", "février", "fevrier", "فبراير", "فيفري"],
    ["march", "mar", "mars", "مارس"],
    ["april", "apr", "avril", "أبريل", "افريل"],
    ["may", "mai", "ماي", "مايو"],
    ["june", "jun", "juin", "يونيو", "جوان"],
    ["july", "jul", "juillet", "يوليو", "جويلية"],
    ["august", "aug", "août", "aout", "أغسطس", "اوت"],
    ["september", "sep", "sept", "septembre", "سبتمبر"],
    ["october", "oct", "octobre", "أكتوبر"],
    ["november", "nov", "novembre", "نوفمبر"],
    ["december", "dec", "décembre", "decembre", "ديسمبر"],
]
MONTH_NAMES = [m[0].capitalize() for m in MONTHS]

CROP_WORDS = {
    "potato": ["potato", "potatoes", "pomme de terre", "pommes de terre", "بطاطا", "بطاطس"],
    "lettuce": ["lettuce", "salad", "laitue", "salade", "خس"],
    "tomato": ["tomato", "tomatoes", "tomate", "tomates", "طماطم"],
    "broad_bean": ["broad bean", "broad beans", "fava", "fève", "fèves", "فول"],
    "corn": ["corn", "maize", "sweetcorn", "maïs", "ذرة"],
    "mushroom": ["mushroom", "mushrooms", "champignon", "champignons", "فطر"],
    "pomegranate": ["pomegranate", "grenade", "رمان"],
    "apricot": ["apricot", "abricot", "مشمش"],
    "lemon": ["lemon", "citron", "ليمون"],
    "orange": ["orange", "oranges", "clementine", "برتقال"],
    "peach": ["peach", "pêche", "خوخ"],
    "mulberry": ["mulberry", "mûre", "توت"],
    "plum": ["plum", "plums", "برقوق"],
}

# Words that mean "what should I do this month", so the calendar is worth consulting.
CALENDAR_HINTS = {
    "sow", "plant", "harvest", "prune", "prepare", "when", "month", "season", "calendar",
    "semer", "planter", "récolter", "tailler", "quand", "mois",
    "أزرع", "ازرع", "زراعة", "حصاد", "متى", "شهر",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return text


# Map everyday, French and Arabic words onto the English words the notes use,
# so "chicken", "poules" or "دجاج" find the notes about hens.
SYNONYMS = {
    "chicken": "hen poultry", "chickens": "hen poultry", "flock": "hen poultry",
    "poule": "hen poultry", "poules": "hen poultry", "دجاج": "hen poultry",
    "caille": "quail", "cailles": "quail", "سمان": "quail", "سمانى": "quail",
    "abeille": "bee", "abeilles": "bee", "ruche": "hive bee", "نحل": "bee", "خلية": "hive bee",
    "essaim": "swarm", "essaimage": "swarm", "طرد": "swarm",
    "fumier": "manure", "سماد": "manure compost", "روث": "manure",
    "compost": "compost", "composter": "compost", "كمبوست": "compost",
    "arrosage": "water irrigation drip", "arroser": "water irrigation drip", "goutte": "drip",
    "ري": "water irrigation drip", "سقي": "water irrigation drip", "تنقيط": "drip",
    "mildiou": "blight", "لفحة": "blight", "pucerons": "aphid", "puceron": "aphid", "منّ": "aphid",
    "limace": "slug", "limaces": "slug", "escargot": "snail", "escargots": "snail", "حلزون": "snail",
    "maladie": "disease", "مرض": "disease", "ravageur": "pest", "آفة": "pest",
    "acarien": "mite", "acariens": "mite", "قراد": "mite", "varroa": "varroa", "فاروا": "varroa",
    "taille": "prune pruning", "tailler": "prune pruning", "تقليم": "prune pruning",
    "humidité": "moisture", "رطوبة": "moisture", "sol": "soil", "تربة": "soil",
    "azolla": "azolla", "أزولا": "azolla",
}
for _crop, _words in {
    "tomato": ["tomate", "tomates", "طماطم"], "potato": ["patate", "بطاطا", "بطاطس"],
    "lettuce": ["laitue", "salade", "خس"], "corn": ["maïs", "ذرة"], "mushroom": ["champignon", "champignons", "فطر"],
    "bean": ["fève", "fèves", "فول"], "peach": ["pêcher", "خوخ"],
}.items():
    for _w in _words:
        SYNONYMS[_w] = _crop


def stem(w: str) -> str:
    """Very light English stemming: plurals and -ing, enough for short notes."""
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("oes", "ches", "shes", "sses")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokenize(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[\w']+", normalize(text)):
        if len(w) > 4 and w.startswith("ال"):
            w = w[2:]  # Arabic definite article: النحل -> نحل
        if w in STOPWORDS or len(w) < 2:
            continue
        for part in SYNONYMS.get(w, w).split():
            out.append(stem(part))
    return out


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Parse the small YAML subset used in knowledge notes (strings and [lists])."""
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    for line in text[3:end].strip().splitlines():
        line = line.split(" #", 1)[0].rstrip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip().strip('"') for v in value[1:-1].split(",") if v.strip()]
        elif value in ("true", "false"):
            meta[key.strip()] = value == "true"
        else:
            meta[key.strip()] = value.strip('"')
    return meta, text[end + 4 :].lstrip("\n")


@dataclass
class Note:
    slug: str
    title: str
    body: str
    meta: dict = field(default_factory=dict)
    tokens: list[str] = field(default_factory=list)


@dataclass
class Hit:
    note: Note
    score: float


class KnowledgeBase:
    def __init__(self, notes: list[Note]):
        self.notes = notes
        self.df: Counter = Counter()
        for n in notes:
            self.df.update(set(n.tokens))
        self.avg_len = sum(len(n.tokens) for n in notes) / max(len(notes), 1)

    @classmethod
    def load(cls, folder: Path) -> "KnowledgeBase":
        notes = []
        for path in sorted(Path(folder).glob("*.md")):
            if path.name.startswith("_") or path.name.lower() == "readme.md":
                continue
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            title = meta.get("title", path.stem.replace("-", " "))
            # Title and crops count three times: they say what the note is about.
            boost = " ".join([title, " ".join(meta.get("crops", []))] * 3)
            notes.append(Note(path.stem, title, body, meta, tokenize(boost + " " + body)))
        return cls(notes)

    def search(self, query: str, k: int = 3, min_score: float = 3.0, relative: float = 0.4) -> list[Hit]:
        q = tokenize(query)
        if not q or not self.notes:
            return []
        n = len(self.notes)
        hits = []
        for note in self.notes:
            tf = Counter(note.tokens)
            score = 0.0
            for term in set(q):
                if term not in tf:
                    continue
                idf = math.log(1 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                f = tf[term]
                score += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(note.tokens) / self.avg_len))
            if score >= min_score:
                hits.append(Hit(note, score))
        hits.sort(key=lambda h: h.score, reverse=True)
        # Drop weak matches far below the best one; they only add noise to the prompt.
        return [h for h in hits if h.score >= relative * hits[0].score][:k] if hits else []


@dataclass
class CalendarQuery:
    country: str | None
    month: int | None
    crops: list[str]


class CropCalendar:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    @classmethod
    def load(cls, path: Path) -> "CropCalendar":
        path = Path(path)
        if not path.exists():
            return cls([])
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def parse(question: str) -> CalendarQuery:
        text = " " + normalize(question) + " "
        country = next(
            (c for c, words in COUNTRIES.items() if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words)),
            None,
        )
        month = None
        for i, words in enumerate(MONTHS):
            # whole words only, so "may" in "may I" is a false positive we accept
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words):
                month = i + 1
                break
        crops = [
            c for c, words in CROP_WORDS.items()
            if any(re.search(rf"(?<!\w)(ال)?{re.escape(w)}(?!\w)", text) for w in words)
        ]
        return CalendarQuery(country, month, crops)

    def lookup(self, question: str, today_month: int | None = None, limit: int = 25) -> tuple[CalendarQuery, list[dict]]:
        q = self.parse(question)
        wants_calendar = bool(set(tokenize(question)) & CALENDAR_HINTS) or q.month is not None
        if not self.rows or not q.country or not (wants_calendar or q.crops):
            return q, []
        month = q.month
        if month is None and not q.crops:
            month = today_month
        rows = [
            r
            for r in self.rows
            if r["country"] == q.country
            and (month is None or r["month"] == month)
            and (not q.crops or r["crop"] in q.crops)
        ]
        return CalendarQuery(q.country, month, q.crops), rows[:limit]
