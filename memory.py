import json
import os


MEMORY_FILE = "memory.json"


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r")as f:
            return json.load(f)
    return{}

def memory_save(memory):
    with open(MEMORY_FILE, "w")as f:
        json.dump(memory, f, indent=2)

def update_memory(new_info):
    memory = load_memory()
    memory.update(new_info)
    memory_save(memory)

def get_memory_text():
    memory = load_memory()

    if not memory:
        return "You don't know anything about Senaa yet."
    
    text = ""
    for category, values in memory.items():
        if category == "corrections":
            continue
        if isinstance(values, dict):
            text += f"\n{category.upper()}:\n"
            for k, v in values.items():
                text += f"  - {k}: {v}\n"
            else:
                text += f"- {category}: {values}\n"
    return text
    
def save_correction(wrong, correct):
    memory = load_memory()
    if "corrections" not in memory:
        memory["corrections"] = {}
    memory["corrections"][wrong] = correct
    memory_save(memory)

def apply_corrections(text):
    memory = load_memory()
    corrections = memory.get("corrections", {})

    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
        
    return text