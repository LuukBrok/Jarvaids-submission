"""Turn an already-made brainstorm summary into compact sticky-note candidates.

This module deliberately does not summarise a transcript.  It is the bridge
between that separate responsibility and the shared canvas, and stays
deterministic so the input/output contract can be tested offline.
"""
import re


MAX_NOTES = 6


def _category(value):
    lowered=value.lower()
    if re.search(r'\b(decid(?:e|ed|ing)|decision|agreed?|choose|chosen)\b',lowered):return 'Decision',4
    if re.search(r'\b(must|need(?:s|ed)?|action|next step|owner|deadline|follow[- ]?up)\b',lowered):return 'Action',4
    if re.search(r'\b(risk|problem|block(?:er|ed)?|concern|fail(?:ure|ed)?)\b',lowered):return 'Risk',4
    if re.search(r'\b(question|unknown|explore|investigate|validate|test)\b',lowered):return 'Open question',3
    if re.search(r'\b(key|important|main|because|therefore|insight)\b',lowered):return 'Key insight',3
    return 'Insight',1


def _headline(value):
    clean=re.sub(r'^(?:we\s+)?(?:decided|agreed|noted|identified|discussed|suggested|proposed)\s+(?:that\s+)?','',value.strip(),flags=re.I)
    clean=re.split(r'\s+(?:because|so that|which means|while)\s+|[;:]',clean,maxsplit=1,flags=re.I)[0]
    words=clean.split()
    title=' '.join(words[:7]).strip(' .,:;-')
    return title or 'Untitled idea'


def ideas_from_summary(value):
    """Return the user's existing classification, headline and importance rules."""
    lines=[re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*','',line).strip() for line in value.splitlines()]
    lines=[line for line in lines if line]
    if len(lines)<=1:
        lines=[part.strip() for part in re.split(r'(?<=[.!?])\s+',value.strip()) if part.strip()]
    ideas=[]
    for order,body in enumerate(lines):
        category,importance=_category(body)
        ideas.append({'title':_headline(body),'body':body,'category':category,
                      'importance':importance,'order':order})
    ideas.sort(key=lambda idea:(-idea['importance'],idea['order']))
    return ideas[:MAX_NOTES]
