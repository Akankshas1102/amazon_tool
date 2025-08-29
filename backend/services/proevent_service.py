from db import load_proevents, save_proevents
from models import ProEvent

def get_proevents():
    return load_proevents()

def add_proevent(proevent: ProEvent):
    events = load_proevents()
    events.append(proevent.dict())
    save_proevents(events)
    return proevent
