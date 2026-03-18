import json
import os


MEMORY_FILE = "memory.json"


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def memory_save(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def update_memory(new_info):
    memory = load_memory()
    memory.update(new_info)
    memory_save(memory)

def iter_memory_entries():
    memory = load_memory()

    for category, values in memory.items():
        if category == "corrections":
            continue

        if isinstance(values, dict):
            for key, value in values.items():
                yield category, key, value
        else:
            yield "root", category, values

def get_memory_text():
    entries = list(iter_memory_entries())
    if not entries:
        return "You don't know anything about Senaa yet."

    grouped = {}
    root_values = {}

    for category, key, value in entries:
        if category == "root":
            root_values[key] = value
            continue
        grouped.setdefault(category, {})[key] = value

    text = ""
    for category, values in grouped.items():
        text += f"\n{category.upper()}:\n"
        for key, value in values.items():
            text += f"  - {key}: {value}\n"

    for key, value in root_values.items():
        text += f"- {key}: {value}\n"

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
