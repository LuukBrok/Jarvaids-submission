"""Addressed commands from final ASR text, without a second audio model.

Recognition is metadata only. Execution still needs an authorised handler.
Keep the transcript intact so people can inspect what recognition was based on.
"""
import re


# Explicit ASR alternatives. Avoid fuzzy matching arbitrary names in conversation.
ACTIVATION_NAMES = {'jarvaids', 'jarvates', 'jarvaides', 'jarvades', 'jarvais', 'jarvis', 'jarvite'}
ACTIVATION_NAMES.update({'jarveds', "jarvan's", 'jarvan’s'})
ACTIVATION_NAMES.update({'jarvedes', "jarvade's", 'jarvade’s'})
# Exact mishearings observed in the laptop trial, not general fuzzy names.
ACTIVATION_ALIASES = (r'hey[\s,:-]+jarf[\s-]+aids', r'hey[\s,:-]+jarfaids',
                      r'hrfates', r'hate[\s,:-]+jarfades',
                      r'hey[\s,:-]+r\.?\s*v\.?\s*d\.?s',
                      r'h[.\s-]*r[.\s-]*v[.\s-]*d\.?(?:[\x27’]s|s)')
CONTINUATION_WINDOW_MS = 5000
POLL_CONTROLS = {
    'close voting': 'close', 'close the poll': 'close', 'end voting': 'close',
    'stop voting': 'close', 'finish voting': 'close',
    'accept voting results': 'finalise', 'accept the results': 'finalise',
    'confirm voting results': 'finalise', 'cancel voting': 'cancel', 'cancel the poll': 'cancel',
}
POLL_CONTROLS.update({f'{verb} {article}{noun}': action
    for action, verbs, nouns in (
        ('close', ('close','end','stop','finish','conclude'), ('voting','voting list','poll','vote')),
        ('finalise', ('accept','confirm','finalise','finalize','save'), ('voting results','poll results','results')),
        ('cancel', ('cancel','discard','abandon'), ('voting','poll','vote','voting list')))
    for verb in verbs for article in ('','the ','our ') for noun in nouns})
# Exact ASR strings supplied by Luuk's microphone trial. Direct address is still
# required. These stop voting, never cancel it or fabricate a vote.
POLL_CONTROLS.update(dict.fromkeys(('close to voting list','clothe voting','no voting','news voting'), 'close'))
POLL_CONTROLS['abandon our pole'] = 'cancel'
POLL_CONTROLS['abandon our pool'] = 'cancel'
DOCUMENT_CONTROLS = {
    f'{verb} {article}{noun}': action
    for verb, action in (('close', 'close'), ('finish', 'close'), ('stop collecting', 'close'),
                         ('accept', 'accept'), ('confirm', 'accept'), ('reopen', 'reopen'),
                         ('cancel', 'cancel'), ('refresh', 'refresh'))
    for article in ('', 'the ', 'our ')
    for noun in ('to do list', 'todo list', 'task list')
}
REQUIREMENTS_CONTROLS = {
    f'{verb} {article}{noun}': action
    for verb, action in (('close', 'close'), ('finish', 'close'), ('stop collecting', 'close'),
                         ('accept', 'accept'), ('confirm', 'accept'), ('reopen', 'reopen'),
                         ('cancel', 'cancel'), ('refresh', 'refresh'))
    for article in ('', 'the ', 'our ')
    for noun in ('requirements', 'wishes', 'requirements list', 'wish list', 'requirements and wishes',
                 'list of requirements', 'list of requirements and wishes', 'requirements and wishes list')
}


CALENDAR_CONTROLS = {
    f'{verb} {article}{noun}': action
    for verb, action in (('close', 'close'), ('finish', 'close'), ('stop collecting', 'close'),
                         ('accept', 'accept'), ('confirm', 'accept'), ('reopen', 'reopen'),
                         ('cancel', 'cancel'), ('refresh', 'refresh'))
    for article in ('', 'the ', 'our ')
    for noun in ('calendar', 'agenda', 'planning', 'schedule')
}

for controls in (DOCUMENT_CONTROLS, REQUIREMENTS_CONTROLS, CALENDAR_CONTROLS):
    nouns = {phrase.split(' ',1)[1] for phrase in controls if phrase.startswith('close ')}
    for verbs, action in ((('end','stop','conclude','finish collecting'),'close'),
                          (('approve','save','finalise','finalize'),'accept'),
                          (('resume','continue','restart'),'reopen'),
                          (('discard','abandon'),'cancel'),
                          (('update','refresh','recheck'),'refresh')):
        controls.update({f'{verb} {noun}':action for verb in verbs for noun in nouns})

# Ten public examples per creation intent; these are executable contracts, not
# promises that the four still-missing executors exist.
COMMAND_EXAMPLES = {
    'summary': ('make a summary','create a recap','generate an overview','prepare a short summary',
        'summarise this discussion','sum up this meeting','recap our discussion','give us the main points',
        'show me the key points','write a rundown'),
    'visualisation': ('make a visual','create a diagram','generate a visualisation','prepare a visual overview',
        'visualise this idea','show the idea visually','represent this concept visually','turn this into a diagram',
        'draw a picture','help us picture this concept'),
    'comparison': ('make a comparison','create a comparison','generate a side by side comparison','compare these ideas',
        'compare concept A with concept B','show us the differences','list the similarities','give me the differences between these ideas',
        'what are the differences between A and B','what are the similarities between A and B'),
    'voting': ('make a voting list','create a poll','generate a vote','prepare a list to vote on','let us vote',
        'start a poll','set up a vote','organise a poll','help us vote on these options','make a list we can vote on'),
    'suggestions': ('make suggestions','create a suggestion','generate suggestions','prepare suggestions','give us suggestions',
        'show me suggestions','build suggestions','write suggestions','produce suggestions','give me a suggestion'),
    'todo': ('make a to do list','create a task list','generate an action list','prepare a list of tasks','write a todo list',
        'produce a task list','build a to do list','give us an action list','give me a task list','show us a todo list'),
    'requirements': ('make a requirements list','create a list of requirements','generate requirements','prepare wishes',
        'write requirements and wishes','produce a wish list','build a list of requirements and wishes',
        'give us requirements','give me a requirements list','show us a wish list'),
    'planning': ('make an agenda','create a calendar','generate a visual calendar','prepare planning','write a schedule',
        'build a timeline','give us a plan','plan our next meeting','schedule this workshop','organise our next steps into a plan'),
}
CALENDAR_VIEW_EXAMPLES = {unit:tuple(phrase.format(unit=unit) for phrase in (
    'show {unit}', 'show {unit} view', 'show {unit} calendar', 'show the {unit}',
    'show the {unit} view', 'show the {unit} calendar', 'switch to {unit}',
    'switch to {unit} view', 'switch to the {unit} view', 'use {unit} view'))
    for unit in ('day','week','month','year')}


def lifecycle_examples():
    """Ten distinct accepted forms per lifecycle operation and calendar view."""
    groups = {'voting':('poll_action',POLL_CONTROLS), 'todo':('document_action',DOCUMENT_CONTROLS),
        'requirements':('document_action',REQUIREMENTS_CONTROLS),'planning':('document_action',CALENDAR_CONTROLS)}
    result = {}
    for intent,(field,controls) in groups.items():
        for action in sorted(set(controls.values())):
            phrases=sorted(p for p,a in controls.items() if a==action)
            result[(intent,field,action)]=phrases[:10]
    return result


def normalise_activation_phrase(text, *, status='final', synthetic=False):
    """Canonical display for explicit, observed name spellings only.

    Keep ASR text unchanged in the record. Sentence-start direct address is
    required, so mentions and uncertain sound-alikes are never rewritten.
    """
    if status!='final' or synthetic or not isinstance(text,str):
        return None
    names='|'.join(re.escape(name) for name in sorted(ACTIVATION_NAMES,key=len,reverse=True))
    phrases = r"hey\b[\s,:-]+(?:" + names + r")|" + "|".join(ACTIVATION_ALIASES)
    match=re.search(r"(?:^|[.!?])\s*(?P<phrase>(?:"+phrases+r"))(?![\w'’])",
                    text,re.I)
    if not match:
        return None
    start,end=match.span('phrase')
    original=match.group('phrase')
    return {'text':text[:start]+'Hey Jarvaids'+text[end:],
            'original_phrase':original,'corrected':original!='Hey Jarvaids'}


def recognise_continuation(current, previous):
    """Complete an addressed unfinished request in the preceding capture chunk.

    Capture timestamps are client-declared monotonic times, not ASR completion
    times. Recognition stays provisional and never authorises an action.
    """
    if (not previous or not current.get('capture_id')
            or current.get('capture_id') != previous.get('capture_id')
            or current.get('capture_revision') != previous.get('capture_revision')
            or current.get('speaker_actor_id') != previous.get('speaker_actor_id')):
        return None
    earlier = previous.get('captured_at_ms')
    now = current.get('captured_at_ms')
    if earlier is None or now is None or not 0 < now - earlier <= CONTINUATION_WINDOW_MS:
        return None
    activation = recognise_command(previous.get('text'), status=previous.get('status'),
                                   synthetic=previous.get('provenance', {}).get('synthetic', True))
    if not activation or activation['status'] != 'incomplete':
        return None
    return recognise_command(previous['text'] + ' ' + (current.get('text') or ''),
                             status=current.get('status'),
                             synthetic=current.get('provenance', {}).get('synthetic', True))


BUILD = r'(?:make|create|generate|prepare|write|produce|build|give (?:us|me)|show (?:us|me))'
ARTICLE = r'(?:(?:a|an|the|our) )?'
DETAIL = r'(?: (?:of|for|about|from|on|with|between) .+)?'
SHORT = r'(?:(?:brief|short|quick|detailed) )?'
COMMANDS = {
    'summary': (
        rf'{BUILD} {ARTICLE}{SHORT}(?:summary|recap|overview|rundown){DETAIL}',
        r'(?:summari[sz]e|recap|sum up)(?: .+)?',
        r'sum .+ up',
        r'(?:pull out|give (?:us|me)|show (?:us|me)|tell (?:us|me)) (?:the )?(?:main|key) points(?: (?:of|from|about) .+)?',
    ),
    'visualisation': (
        rf'{BUILD} {ARTICLE}(?:visuali[sz]ation|visual|diagram|visual overview){DETAIL}',
        r'visuali[sz]e(?: .+)?',
        r'(?:show|represent) .+ visually',
        r'turn .+ into (?:a )?(?:visual|diagram|visuali[sz]ation)',
        rf'draw {ARTICLE}(?:diagram|visual|picture){DETAIL}',
        r'help (?:us|me) (?:picture|visuali[sz]e) .+',
    ),
    'comparison': (
        rf'{BUILD} {ARTICLE}comparison{DETAIL}',
        r'compare(?: .+)?',
        r'(?:(?:show|give) (?:us|me)|list) (?:the )?(?:differences|similarities)(?: between .+)?',
        rf'{BUILD} {ARTICLE}side by side comparison{DETAIL}',
        r'what are (?:the )?(?:differences|similarities) between .+',
    ),
    'voting': (
        rf'{BUILD} {ARTICLE}(?:voting list|vote|poll|list (?:to vote on|for voting)){DETAIL}',
        r'(?:let s|let us|we want to|we would like to|we d like to|can we) vote(?: (?:on|for) .+)?',
        r'(?:start|set up|organise|organize) (?:a |the )?(?:vote|voting|poll)(?: (?:on|for) .+)?',
        rf'{BUILD} {ARTICLE}list (?:we|i) can vote on',
        r'help (?:us|me) vote(?: on .+)?',
        r'prepare .+ for voting',
    ),
    'suggestions': (
        rf'{BUILD} {ARTICLE}suggestions?{DETAIL}',
        rf'{BUILD} (?:some|a few|several) suggestions{DETAIL}',
        r'(?:give|offer|show) (?:us|me) (?:(?:a few|some|a couple of|three|several) )?(?:suggestions|ideas|options)(?: (?:for|about|on) .+| to consider)?',
        r'suggest(?: .+)?',
        r'(?:what (?:would|do) you suggest|do you have (?:any|some) suggestions)(?: (?:for|about|on) .+)?',
    ),
    'todo': (
        rf'{BUILD} {ARTICLE}(?:to do list|todo list|task list|action list|list of (?:tasks|action items|next steps)){DETAIL}',
        r'list (?:our|the) (?:tasks|action items|next steps)',
        r'what (?:do we|should we) (?:need to )?do next',
        r'turn .+ into (?:a |an |our )?(?:to do list|todo list|task list|action list)',
        r'list (?:the |our )?tasks (?:we|i) (?:still )?need to complete',
    ),
    'requirements': (
        rf'{BUILD} {ARTICLE}(?:list of )?(?:requirements|requirements list|wishes|requirements and wishes|wishes and requirements|wish list){DETAIL}',
        r'list (?:our|the) (?:requirements|wishes|requirements and wishes|wishes and requirements)',
        r'what (?:requirements|wishes) have (?:we|i) discussed',
        rf'{BUILD} {ARTICLE}list of must haves{DETAIL}',
        r'collect (?:our|the) (?:requirements|wishes) into (?:a |one )?list',
    ),
    'planning': (
        rf'{BUILD} {ARTICLE}(?:agenda|calendar|visual calendar|planning|plan|schedule|timeline){DETAIL}',
        r'(?:plan|schedule) (?:(?:our|the|a|this) )?(?:next )?(?:meeting|session|workshop|week|project)',
        r'organi[sz]e (?:our|the) next steps into (?:a |our )?plan',
    ),
}


def strip_request_wrappers(command):
    """Polite framing is independent of intent; retain the original elsewhere."""
    prefix = r'^(?:please |briefly |quickly |(?:(?:can|could|would|will) you |(?:we|i) (?:want|would like|d like) you to ))'
    while True:
        reduced = re.sub(prefix, '', command)
        reduced = re.sub(rf'^(?:let s|lets|let us) (?={BUILD}\b)', '', reduced)
        reduced = re.sub(r' (?:please|thanks|thank you)$', '', reduced)
        if reduced == command:
            return command
        command = reduced


def match_intent(command):
    # Never treat a negated, deferred or compound request as one action.
    # Yes/No are legitimate poll choices. Only exempt this explicit option pair;
    # negated requests and other commands retain the original refusal behaviour.
    guard_command = re.sub(r'\byes (?:or|and) no\b', 'binary choices', command) if any(
        re.fullmatch(pattern, strip_request_wrappers(command)) for pattern in COMMANDS.get('voting', ())) else command
    if re.search(r'\b(?:not|never|don t|dont|no|stop|cancel|later)\b', guard_command):
        return None
    if re.search(r'\b(?:and|then|also|instead|or) (?:(?:please|can you|could you) )*(?:make|create|generate|prepare|write|give|show|summari[sz]e|visuali[sz]e|compare|suggest|start|delete|let s|vote|tell|draw|help|turn|collect|list|organi[sz]e|plan|schedule|what|do you)\b', command):
        return None
    command = strip_request_wrappers(command)
    matches = {intent for intent, patterns in COMMANDS.items()
               if any(re.fullmatch(pattern, command) for pattern in patterns)}
    # Ambiguous patterns cannot choose a handler by dictionary order.
    return next(iter(matches)) if len(matches) == 1 else None


def recognise_command(text, *, status='final', synthetic=False):
    # Fixtures and gaps cannot establish a person's spoken request.
    if status != 'final' or synthetic or not isinstance(text, str):
        return None
    activation=normalise_activation_phrase(text,status=status,synthetic=synthetic)
    if activation is None:
        return None
    text=activation['text']
    # ASR can put a lead-in sentence in the same chunk as the addressed request.
    address = re.search(r'(?:^|[.!?])\s*(hey\b.*)', text.casefold(), re.S)
    words = re.findall(r"\w+", address.group(1) if address else text.casefold())
    # Require direct address at a sentence start, not a mention inside a sentence.
    if len(words) < 2 or words[0] != 'hey' or words[1] not in ACTIVATION_NAMES:
        return None
    command = ' '.join(words[2:])
    if not command:
        return {'phrase': 'Hey Jarvaids', 'command': '', 'intent': None, 'status': 'incomplete'}
    document_action = DOCUMENT_CONTROLS.get(strip_request_wrappers(command))
    if document_action:
        return {'phrase': 'Hey Jarvaids', 'command': command, 'intent': 'todo',
                'status': 'recognised', 'document_action': document_action}
    requirements_action = REQUIREMENTS_CONTROLS.get(strip_request_wrappers(command))
    if requirements_action:
        return {'phrase': 'Hey Jarvaids', 'command': command, 'intent': 'requirements',
                'status': 'recognised', 'document_action': requirements_action}
    calendar_action = CALENDAR_CONTROLS.get(strip_request_wrappers(command))
    if calendar_action:
        return {'phrase': 'Hey Jarvaids', 'command': command, 'intent': 'planning',
                'status': 'recognised', 'document_action': calendar_action}
    view = re.fullmatch(r'(?:show|switch to|use) (?:the )?(day|week|month|year)(?: view| calendar)?', strip_request_wrappers(command))
    period = re.fullmatch(r'show (today|tomorrow|this week|next week|this month|next month|this year|next year)', strip_request_wrappers(command))
    if view or period:
        phrase = period[1] if period else ''
        unit = view[1] if view else next((unit for unit in ('week', 'month', 'year') if unit in phrase), 'day')
        return {'phrase': 'Hey Jarvaids', 'command': command, 'intent': 'planning', 'status': 'recognised',
                'document_action': 'view', 'calendar_view': unit, 'calendar_period': phrase}
    poll_action = POLL_CONTROLS.get(strip_request_wrappers(command))
    if poll_action:
        return {'phrase': 'Hey Jarvaids', 'command': command, 'intent': 'voting',
                'status': 'recognised', 'poll_action': poll_action}
    intent = match_intent(command)
    unfinished = re.fullmatch(rf'{BUILD}(?: (?:a|an|the|our))?(?: list(?: of)?)?', strip_request_wrappers(command))
    return {'phrase': 'Hey Jarvaids', 'command': command, 'intent': intent,
            'status': 'recognised' if intent else 'incomplete' if unfinished else 'unsupported'}
