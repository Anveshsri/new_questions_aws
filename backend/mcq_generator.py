from typing import List, Tuple
import re
import random
from collections import Counter
from backend.schemas import QuestionCreate

# Lighter stopword list keeps domain terms intact
STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","by","with","as","is","are","was","were","be",
    "this","that","these","those","it","its","at","from","into","than","then","but","if","so","such","their",
    "has","have","had","not","no","yes","can","may","might","will","would","should","could","do","does","did",
}

def _paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return paras

def _sentences(paragraph: str) -> List[str]:
    paragraph = re.sub(r"\s+", " ", paragraph)
    parts = re.split(r"(?<=[.!?])\s+", paragraph)
    return [s.strip() for s in parts if 12 <= len(s.split()) <= 35]

def _tokens(s: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-]{2,}", s)

def _candidate_terms(sentence: str) -> List[str]:
    words = _tokens(sentence)
    candidates = [w.strip("-.,()[]{}'\"\u2019").strip() for w in words]
    candidates = [w for w in candidates if w.lower() not in STOPWORDS and len(w) >= 4]
    seen = set()
    uniq = []
    for w in candidates:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            uniq.append(w)
    return uniq

def _pick_answer(sentence: str, para_terms: Counter) -> str | None:
    terms = _candidate_terms(sentence)
    if not terms:
        return None
    def score(w: str) -> tuple[int, int, int]:
        return (1 if w[0].isupper() else 0, len(w), -para_terms[w.lower()])
    terms.sort(key=score, reverse=True)
    return terms[0]

def _distractors(answer: str, paragraph: str, global_pool: List[str]) -> Tuple[str, str, str, str, str]:
    cand = [w for w in _candidate_terms(paragraph) if w.lower() != answer.lower()]
    if len(cand) < 3:
        cand.extend([w for w in global_pool if w.lower() != answer.lower()])
    cand.sort(key=lambda w: (abs(len(w) - len(answer)), w[0].isupper()), reverse=False)
    uniq = []
    seen = set()
    for w in cand:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            uniq.append(w)
    opts = uniq[:3]
    while len(opts) < 3:
        opts.append(random.choice(["other", "none", "unknown"]))
    options = [answer, opts[0], opts[1], opts[2]]
    random.shuffle(options)
    correct_index = options.index(answer)
    correct_letter = ["A","B","C","D"][correct_index]
    return options[0], options[1], options[2], options[3], correct_letter

def generate_mcqs_from_text(text: str) -> List[QuestionCreate]:
    paras = _paragraphs(text)
    if not paras:
        return []

    all_terms = []
    for p in paras:
        all_terms.extend([t.lower() for t in _candidate_terms(p)])
    term_counter = Counter(all_terms)

    questions: List[QuestionCreate] = []
    sets = ["A", "B", "C", "D"]
    desired_count = 40
    random.seed(11)

    for para in paras:
        if len(questions) >= desired_count:
            break
        sentences = _sentences(para)
        if not sentences:
            continue
        para_terms = Counter([t.lower() for t in _candidate_terms(para)])
        picked = None
        answer = None
        for s in sentences:
            a = _pick_answer(s, para_terms or term_counter)
            if a:
                picked = s
                answer = a
                break
        if not picked or not answer:
            continue

        cloze = re.sub(rf"\b{re.escape(answer)}\b", "____", picked, flags=re.IGNORECASE)
        oa, ob, oc, od, correct = _distractors(answer, para, list(term_counter.keys()))
        set_label = sets[len(questions) % 4]
        questions.append(QuestionCreate(
            question_text=f"Fill in the blank: {cloze}",
            option_a=oa,
            option_b=ob,
            option_c=oc,
            option_d=od,
            correct_answer=correct,
            set_label=set_label,
        ))

    idx = 0
    while len(questions) < desired_count and paras:
        para = paras[idx % len(paras)]
        sentences = _sentences(para)
        if sentences:
            para_terms = Counter([t.lower() for t in _candidate_terms(para)])
            for s in sentences:
                a = _pick_answer(s, para_terms or term_counter)
                if not a:
                    continue
                cloze = re.sub(rf"\b{re.escape(a)}\b", "____", s, flags=re.IGNORECASE)
                oa, ob, oc, od, correct = _distractors(a, para, list(term_counter.keys()))
                set_label = sets[len(questions) % 4]
                questions.append(QuestionCreate(
                    question_text=f"Fill in the blank: {cloze}",
                    option_a=oa,
                    option_b=ob,
                    option_c=oc,
                    option_d=od,
                    correct_answer=correct,
                    set_label=set_label,
                ))
                if len(questions) >= desired_count:
                    break
        idx += 1

    return questions
