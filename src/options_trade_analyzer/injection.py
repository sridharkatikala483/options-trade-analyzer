"""Prompt-injection monitor for outside text (Checkpoint 6, Lab 6.2).

News headlines are the only text in a run that nobody on the project wrote: they come from public RSS
feeds, so a headline (or its source name) could carry instructions aimed at the agents. Every headline is
scanned before the agents see it; a flagged one is withheld (the agents get its source, date and the
reason, never its text) and the run is held for human review.

The patterns look for text addressed to an AI or a system, not for market language: real headlines say
"buy" and "sell" all the time ("3 stocks to buy now"), and that is news, not an attack. On the 914
recorded headlines in the evaluation snapshot the monitor flags none; scripts/injection_eval.py measures
the catch rate on planted headlines. It catches the usual injection forms, but plain-language paraphrases
mostly slip past (1 of 6 held-out ones caught), so the other layers matter more: headlines are framed as
information only, and the report checks reject advice, certainty and untraced numbers whatever the cause.
"""

import re

PATTERNS = {
    "override": re.compile(
        r"\b(ignore|disregard|forget|override|bypass)\b[^.!?]{0,40}"
        r"\b(instructions?|prompts?|rules|guidelines|guardrails|previous|prior|above)\b", re.I),
    "role_marker": re.compile(
        r"(^|[\s\"'(\[])(system|assistant|developer)\s*:|<\|?\s*(im_start|im_end|system|endoftext)\s*\|?>"
        r"|\[/?INST\]|###\s*(instruction|system)", re.I),
    "addressed_to_ai": re.compile(
        r"\b(note|message|attention|instructions?|reminder)\s+(to|for)\s+(any\s+|all\s+|the\s+)?"
        r"(ai|a\.i\.|assistants?|models?|agents?|llms?|bots?|chatbots?)\b"
        r"|\bif you are an?\s+(ai|assistant|language model|llm|bot|agent)\b"
        r"|\b(ai|assistant|llm|agent|model)s?\s*(,|:)\s*(you|please|always|never|do|tell|write|include|say|add)\b", re.I),
    "role_change": re.compile(
        r"\byou are now\b|\bnew (system )?instructions?\b|\bsystem prompt\b|\bjailbreak\b|\bdeveloper mode\b"
        r"|\bpretend (to be|you are)\b", re.I),
    "steer_reader": re.compile(
        r"\b(tell|inform|advise|assure|convince)\s+(the\s+)?(user|reader)s?\s+(to|that)\b", re.I),
    "exfiltrate": re.compile(
        r"\b(send|post|email|upload|reveal|print|share|leak)\b[^.!?]{0,40}"
        r"\b(api[ _-]?keys?|passwords?|credentials?|(access|auth|api|bearer) tokens?|secret keys?|system prompt"
        r"|\.env)\b", re.I),  # not bare "secret" or "token": "share secret wedding news" is gossip, not an attack
    "addressed_to_automation": re.compile(
        r"\b(automated|automatic|machine[- ]generated|ai[- ]generated)\s+(reports?|summar\w+|briefs?|analys[ie]s)\b"
        r"[^.!?]{0,40}\b(should|must|are expected|need to|are told|have to)\b"
        r"|\b(whoever|anyone|anything)\s+(\w+\s+)?(summariz|process|read|condens)\w*\b"
        r"|\bsummar(y|ies)\s+(of\s+this\s+\w+\s+)?(tools?|bots?|engines?)?\s*(:|should|must|are expected)", re.I),
    "hidden_text": re.compile(r"[​-‏⁠﻿]|\b[A-Za-z0-9+/]{40,}={0,2}"),
}


LEET = str.maketrans("013457@$", "oieastas")
MIXED = re.compile(r"\b(?=\w*[a-z])(?=\w*[0-9])\w+\b", re.I)


def normalize(text: str) -> str:
    """Undo digit-for-letter swaps inside words ("1gnore pr3vious" -> "ignore previous"). Only words that mix
    letters and digits change; plain words and numbers ("2026", "S&P 500") are left as they are."""
    return MIXED.sub(lambda m: m.group(0).translate(LEET), text)


def scan(text: str) -> list[str]:
    """Names of the patterns `text` matches; empty when it reads as ordinary news."""
    text = text or ""
    variants = {text, normalize(text)}
    return [name for name, pattern in PATTERNS.items() if any(pattern.search(v) for v in variants)]
