# ============================================================
# UNIVERSAL GAME AI
# Version 0.7.1
#
# Vision -> Perception -> Brain -> Action -> Learning
#
# Persistent brain memory:
#     memory.AI
#
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog
import threading
import time
import json
import os
import random
import ctypes
from ctypes import wintypes
from collections import deque, defaultdict

import keyboard
import pyautogui
import mss

# Voice control uses sounddevice directly; PyAudio is not required.
try:
    import sounddevice as sd
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    sd = None
    sr = None
    VOICE_AVAILABLE = False

from PIL import (
    Image,
    ImageTk,
    ImageOps,
    ImageEnhance,
    ImageFilter
)

import pytesseract


# ============================================================
# CONFIG
# ============================================================

VERSION = "0.8.7"
APP_TITLE = f"Universal Game AI v{VERSION}"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MEMORY_FILE = os.path.join(
    BASE_DIR,
    "memory.AI"
)

MEMORY_TEMP_FILE = os.path.join(
    BASE_DIR,
    "memory.AI.tmp"
)

# Your detected Tesseract installation
TESSERACT_PATH = (
    r"C:\Users\catni\AppData\Local\Tesseract-OCR\tesseract.exe"
)

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


VISION_INTERVAL = 0.033
PREVIEW_INTERVAL = 0.10
OCR_INTERVAL = 1.25
BRAIN_DECISION_INTERVAL = 0.35

ACTION_DURATION = 0.12

OCR_MIN_CONFIDENCE = 35

MAX_SYSTEM_LOG_LINES = 250
MAX_VISION_LOG_LINES = 150
MAX_OCR_LOG_LINES = 150
MAX_BRAIN_LOG_LINES = 300

SAVE_EVERY_ACTIONS = 20
SAVE_RETRY_COUNT = 12
SAVE_RETRY_DELAY = 0.50
SAVE_RETRY_MAX_DELAY = 2.0


# ============================================================
# ACTIONS
# ============================================================

ACTIONS = [
    "W",
    "A",
    "S",
    "D",
    "SPACE",
    "SHIFT",
    "LEFT_CLICK",
    "RIGHT_CLICK",
    "MOUSE_LEFT",
    "MOUSE_RIGHT",
    "MOUSE_UP",
    "MOUSE_DOWN",
    "WAIT"
]

# ============================================================
# VERSION 0.8 - GAME MODE SYSTEM
# ============================================================
# Each mode has its own action vocabulary and reward hints.
# The vision/OCR/brain pipeline stays shared, while the mode
# tells the brain which controls make sense for that game.
#
# Supported games from the project history:
#   Ultimate Custom Night, Subnautica, Subnautica 2,
#   Minecraft Bedrock, Roblox, Space Engineers, Fortnite,
#   Trackmania, Kerbal Space Program, Star Citizen.
#
# These are control/perception profiles, not game-specific
# cheat/integration APIs. The AI learns from the screen it sees.

GAME_MODES = {
    "Universal": {
        "description": "Generic keyboard + mouse",
        "actions": ACTIONS,
    },

    "Ultimate Custom Night": {
        "description": "Mouse-heavy survival / menu controls",
        "actions": [
            "LEFT_CLICK", "RIGHT_CLICK",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "W", "A", "S", "D", "SPACE", "CTRL", "SHIFT",
            "E", "Q", "Z", "X", "C", "R", "F", "TAB", "ESC", "WAIT"
        ],
    },

    "Subnautica": {
        "description": "First-person exploration / survival",
        "actions": [
            "W", "A", "S", "D", "SPACE", "CTRL", "SHIFT",
            "E", "F", "Q", "TAB",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "LEFT_CLICK", "RIGHT_CLICK", "WAIT"
        ],
    },

    "Subnautica 2": {
        "description": "First-person exploration / survival",
        "actions": [
            "W", "A", "S", "D", "SPACE", "CTRL", "SHIFT",
            "E", "F", "Q", "TAB",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "LEFT_CLICK", "RIGHT_CLICK", "WAIT"
        ],
    },

    "Minecraft Bedrock": {
        "description": "Block building / survival",
        "actions": [
            "W", "A", "S", "D", "SPACE", "SHIFT", "CTRL",
            "E", "F", "Q", "TAB",
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "LEFT_CLICK", "RIGHT_CLICK",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "WAIT"
        ],
    },

    "Roblox": {
        "description": "General Roblox keyboard + mouse",
        "actions": [
            "W", "A", "S", "D", "SPACE", "SHIFT", "CTRL",
            "E", "F", "Q", "R", "TAB", "ESC",
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "LEFT_CLICK", "RIGHT_CLICK",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "WAIT"
        ],
    },

    "Space Engineers": {
        "description": "Character / vehicle / toolbar controls",
        "actions": [
            "W", "A", "S", "D", "SPACE", "CTRL", "SHIFT",
            "E", "F", "G", "I", "K", "L", "R", "T", "Y",
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "LEFT_CLICK", "RIGHT_CLICK",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "WAIT"
        ],
    },

    "Fortnite": {
        "description": "Third-person shooter / building controls",
        "actions": [
            "W", "A", "S", "D", "SPACE", "CTRL", "SHIFT",
            "E", "F", "Q", "R", "TAB", "ESC",
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "LEFT_CLICK", "RIGHT_CLICK",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "WAIT"
        ],
    },

    "Trackmania": {
        "description": "Precision racing (gameplay controls only; menu/replay keys blocked)",
        "actions": [
            "UP", "DOWN", "LEFT", "RIGHT",
            "W", "A", "S", "D", "SPACE",
            "WAIT"
        ],
    },

    "Kerbal Space Program": {
        "description": "Flight / staging / spacecraft controls",
        "actions": [
            "W", "A", "S", "D", "Q", "E",
            "R", "F", "T", "G", "H", "J", "K", "L",
            "SHIFT", "CTRL", "SPACE", "X", "Z", "C", "V",
            "UP", "DOWN", "LEFT", "RIGHT",
            "WAIT"
        ],
    },

    "Star Citizen": {
        "description": "Space flight / FPS controls",
        "actions": [
            "W", "A", "S", "D", "Q", "E",
            "SPACE", "CTRL", "SHIFT", "ALT",
            "R", "F", "G", "H", "J", "K", "L", "TAB", "ESC",
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "LEFT_CLICK", "RIGHT_CLICK",
            "MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN",
            "WAIT"
        ],
    },
}

current_game_mode = "Universal"
mode_reward_scale = 1.0



# ============================================================
# GLOBAL STATE
# ============================================================

running = True

# Voice state
voice_active = False
voice_thread = None
voice_status = "⚪ OFF"
voice_last_heard = "—"
voice_last_command = "—"
voice_error = ""
voice_sample_rate = 16000
voice_record_seconds = 3.0
voice_lock = threading.RLock()

ai_active = False
brain_active = False
vision_active = False
ocr_active = False

emergency_stop = False

brain_test_mode = False
learning_enabled = True
current_game_mode = "Universal"
mode_reward_scale = 1.0

recording = False

current_action = "Idle"

last_state = None
last_action = None

last_movement_time = 0.0
last_movement_pos = None
movement_reward_total = 0.0

current_reward = 0.0
total_reward = 0.0

decision_count = 0
learning_count = 0

brain_action_in_progress = False

vision_frames = 0
vision_fps = 0.0

screen_width = 0
screen_height = 0

active_window_title = ""

latest_ocr_text = ""
latest_ocr_confidence = 0.0

notepad_detected = False

last_preview_time = 0
last_ocr_time = 0
last_brain_time = 0

last_save_time = "Never"
memory_status = "Not saved"
unsaved_learning = False
brain_memory_lock = threading.RLock()

recorded_actions = []

held_keys = set()

save_lock = threading.Lock()


# ============================================================
# BRAIN MEMORY
# ============================================================

brain_memory = defaultdict(
    lambda: {
        "actions": {}
    }
)


# ============================================================
# LOG QUEUES
# ============================================================

system_log_queue = deque(
    maxlen=MAX_SYSTEM_LOG_LINES
)

vision_log_queue = deque(
    maxlen=MAX_VISION_LOG_LINES
)

ocr_log_queue = deque(
    maxlen=MAX_OCR_LOG_LINES
)

brain_log_queue = deque(
    maxlen=MAX_BRAIN_LOG_LINES
)

ui_queue = deque()


# ============================================================
# UI QUEUE
# ============================================================

def queue_ui(function, *args, **kwargs):
    ui_queue.append(
        (
            function,
            args,
            kwargs
        )
    )


def process_ui_queue():

    # IMPORTANT:
    # Work from a snapshot instead of iterating over
    # the deque while other threads may modify it.

    while True:

        try:
            function, args, kwargs = (
                ui_queue.popleft()
            )
        except IndexError:
            break

        try:

            function(
                *args,
                **kwargs
            )

        except Exception as error:

            print(
                "UI callback error:",
                error
            )

    if running:

        root.after(
            30,
            process_ui_queue
        )


# ============================================================
# LOGGING
# ============================================================

def system_log(message):

    timestamp = time.strftime(
        "%H:%M:%S"
    )

    line = (
        f"[{timestamp}] {message}"
    )

    print(line)

    system_log_queue.append(
        line
    )

    queue_ui(
        update_system_log
    )


def vision_log(message):

    timestamp = time.strftime(
        "%H:%M:%S"
    )

    vision_log_queue.append(
        f"[{timestamp}] {message}"
    )

    queue_ui(
        update_vision_log
    )


def ocr_log(message):

    timestamp = time.strftime(
        "%H:%M:%S"
    )

    ocr_log_queue.append(
        f"[{timestamp}] {message}"
    )

    queue_ui(
        update_ocr_log
    )


def brain_log(message):

    timestamp = time.strftime(
        "%H:%M:%S"
    )

    brain_log_queue.append(
        f"[{timestamp}] {message}"
    )

    queue_ui(
        update_brain_log
    )


def update_text_box(box, lines):

    if not box.winfo_exists():
        return

    box.config(
        state="normal"
    )

    box.delete(
        "1.0",
        "end"
    )

    # FIX:
    # Copy the deque before iterating.
    # This prevents:
    #
    # deque mutated during iteration
    #
    for line in list(lines):

        box.insert(
            "end",
            line + "\n"
        )

    box.see(
        "end"
    )

    box.config(
        state="disabled"
    )


def update_system_log():

    update_text_box(
        system_log_box,
        list(system_log_queue)
    )


def update_vision_log():

    update_text_box(
        vision_log_box,
        list(vision_log_queue)
    )


def update_ocr_log():

    update_text_box(
        ocr_log_box,
        list(ocr_log_queue)
    )


def update_brain_log():

    update_text_box(
        brain_log_box,
        list(brain_log_queue)
    )


# ============================================================
# MEMORY HELPERS
# ============================================================

def serialize_memory():
    # Take a consistent snapshot so a learning thread cannot mutate the
    # dictionary while JSON serialization is walking through it.
    with brain_memory_lock:
        return {
            str(state): json.loads(json.dumps(data, ensure_ascii=False))
            for state, data in brain_memory.items()
        }


def memory_file_exists():
    try:
        return os.path.exists(MEMORY_FILE)
    except Exception:
        return False


def validate_memory_file(path):
    """Return parsed JSON if path contains valid brain memory, else None."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


# ============================================================
# LOAD BRAIN
# ============================================================

def _load_memory_data(data):
    global brain_memory

    fresh = defaultdict(lambda: {"actions": {}})

    if isinstance(data, dict):
        for state, state_data in data.items():
            if not isinstance(state_data, dict):
                continue

            actions = state_data.get("actions", {})
            if not isinstance(actions, dict):
                actions = {}

            fresh[str(state)] = {"actions": actions}

    with brain_memory_lock:
        brain_memory = fresh


def load_brain():
    global brain_memory
    global memory_status

    # If the normal file is missing, try a valid leftover temp file first.
    # This is important when OneDrive interrupted the previous replacement.
    if not memory_file_exists():
        temp_data = validate_memory_file(MEMORY_TEMP_FILE)
        if temp_data is not None:
            _load_memory_data(temp_data)
            memory_status = "Recovered from .tmp"
            brain_log("🧠 Recovered memory.AI from memory.AI.tmp")
            brain_log(f"🧠 States: {len(brain_memory)}")
            queue_ui(update_memory_display)

            # Turn the recovered temp file into the normal memory file.
            if save_brain():
                brain_log("✅ Recovered memory.AI saved successfully")
            return

        with brain_memory_lock:
            brain_memory = defaultdict(lambda: {"actions": {}})

        memory_status = "New brain"
        brain_log("🧠 No memory.AI found.")
        brain_log("🧠 Starting a fresh brain.")
        return

    data = validate_memory_file(MEMORY_FILE)

    if data is None:
        # The main file may be corrupt while the temp file is perfectly good.
        temp_data = validate_memory_file(MEMORY_TEMP_FILE)
        if temp_data is not None:
            _load_memory_data(temp_data)
            memory_status = "Recovered from .tmp"
            brain_log("⚠️ memory.AI was invalid; recovered valid memory.AI.tmp")
            brain_log(f"🧠 States: {len(brain_memory)}")
            queue_ui(update_memory_display)
            return

        with brain_memory_lock:
            brain_memory = defaultdict(lambda: {"actions": {}})

        if os.path.exists(MEMORY_FILE):
            # Distinguish permission errors from malformed JSON where possible.
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                    json.load(file)
            except PermissionError:
                memory_status = "Access denied"
                brain_log("⚠️ Windows denied access to memory.AI.")
                brain_log("🧠 Brain will continue learning in RAM.")
                return
            except json.JSONDecodeError:
                memory_status = "Corrupt"
                brain_log("⚠️ memory.AI contains invalid JSON.")
                brain_log("🧠 Starting safely with a fresh memory.")
                return
            except Exception as error:
                memory_status = "Load error"
                brain_log(f"❌ Memory load error: {error}")
                return

        memory_status = "Corrupt"
        brain_log("⚠️ Could not validate memory.AI.")
        brain_log("🧠 Starting safely with a fresh memory.")
        return

    _load_memory_data(data)
    memory_status = "Loaded"
    brain_log("🧠 memory.AI loaded")
    brain_log(f"🧠 States: {len(brain_memory)}")
    queue_ui(update_memory_display)


# ============================================================
# SAVE BRAIN
# ============================================================

def save_brain():
    global last_save_time
    global memory_status
    global unsaved_learning

    # Only one save operation at a time.
    if not save_lock.acquire(blocking=False):
        brain_log("⏳ Memory save already in progress")
        return False

    try:
        data = serialize_memory()
        encoded = json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )

        # --------------------------------------------------------
        # STEP 1: write a complete temporary file in the SAME folder.
        # --------------------------------------------------------
        try:
            with open(MEMORY_TEMP_FILE, "w", encoding="utf-8") as file:
                file.write(encoded)
                file.flush()
                try:
                    os.fsync(file.fileno())
                except Exception:
                    pass
        except Exception as error:
            memory_status = "Write failed"
            brain_log(f"❌ Memory temp write failed: {error}")
            queue_ui(update_memory_display)
            return False

        # --------------------------------------------------------
        # STEP 2: replace atomically.
        # NEVER delete memory.AI first.
        # --------------------------------------------------------
        delay = SAVE_RETRY_DELAY

        for attempt in range(1, SAVE_RETRY_COUNT + 1):
            try:
                # os.replace keeps the old file intact if Windows refuses
                # the replacement. This fixes the old delete-then-rename bug.
                os.replace(MEMORY_TEMP_FILE, MEMORY_FILE)

                last_save_time = time.strftime("%H:%M:%S")
                memory_status = "🟢 SAVED"
                unsaved_learning = False

                brain_log(
                    f"💾 Brain saved successfully (attempt {attempt})"
                )
                queue_ui(update_memory_display)
                return True

            except (PermissionError, OSError) as error:
                if attempt == SAVE_RETRY_COUNT:
                    memory_status = "⚠️ OneDrive locked"
                    brain_log(
                        f"⚠️ Could not replace memory.AI after {SAVE_RETRY_COUNT} attempts: {error}"
                    )
                    brain_log(
                        "🧠 Learning remains safe in RAM; memory.AI was NOT deleted."
                    )
                    queue_ui(update_memory_display)
                    return False

                time.sleep(delay)
                delay = min(delay * 1.5, SAVE_RETRY_MAX_DELAY)

        return False

    finally:
        save_lock.release()


# ============================================================
# PERIODIC MEMORY SAVE
# ============================================================

def memory_save_loop():

    while running:

        time.sleep(10)

        if not running:
            break

        if unsaved_learning:
            save_brain()


# ============================================================
# STATE
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    replacements = [
        "\n",
        "\r",
        "\t",
        ",",
        ".",
        ":",
        ";",
        "!",
        "?",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}"
    ]

    for character in replacements:

        text = text.replace(
            character,
            " "
        )

    words = text.split()

    # Keep states reasonably small.
    words = words[:25]

    return " ".join(
        words
    )


def build_state():

    window = normalize_text(
        active_window_title
    )

    if not window:
        window = "unknown_window"

    ocr = normalize_text(
        latest_ocr_text
    )

    if not ocr:
        ocr = "no_text"

    if notepad_detected:
        app = "notepad"
    else:
        app = "other"

    # Keep the selected mode in the state key so knowledge from
    # one game cannot accidentally teach another game.
    state = (
        f"mode={normalize_text(current_game_mode)}|"
        f"window={window}|"
        f"app={app}|"
        f"ocr={ocr}"
    )

    return state


# ============================================================
# MEMORY ACTION ENTRY
# ============================================================

def ensure_action_entry(
    state,
    action
):

    with brain_memory_lock:
        if state not in brain_memory:

            brain_memory[state] = {
                "actions": {}
            }

        actions = brain_memory[
            state
        ].setdefault(
            "actions",
            {}
        )

        if action not in actions:

            actions[action] = {
                "value": 0.0,
                "tries": 0,
                "successes": 0,
                "failures": 0
            }


# ============================================================
# BRAIN ACTION SELECTION
# ============================================================

def get_mode_actions():
    profile = GAME_MODES.get(
        current_game_mode,
        GAME_MODES["Universal"]
    )
    return list(profile.get("actions", ACTIONS))


def choose_action(state):

    mode_actions = get_mode_actions()

    # Hard filter: Trackmania mode never permits menu/replay keys.
    # This also protects against stale R/ESC entries in memory.AI.
    if current_game_mode == "Trackmania":
        mode_actions = [
            action for action in mode_actions
            if action not in {"R", "ESC", "ESCAPE"}
        ]

    for action in mode_actions:

        ensure_action_entry(
            state,
            action
        )

    actions = brain_memory[
        state
    ][
        "actions"
    ]

    total_tries = sum(
        int(
            info.get(
                "tries",
                0
            )
        )
        for info in actions.values()
    )

    # Exploration decreases as the brain learns.

    if total_tries < 20:

        exploration = 0.70

    elif total_tries < 100:

        exploration = 0.35

    else:

        exploration = 0.15

    # --------------------------------------------------------
    # Explore
    # --------------------------------------------------------

    if random.random() < exploration:

        action = random.choice(
            mode_actions
        )

        brain_log(
            f"🎲 Exploring → {action}"
        )

        return action

    # --------------------------------------------------------
    # Exploit
    # --------------------------------------------------------

    best_value = None
    best_actions = []

    for action, info in actions.items():

        if action not in mode_actions:
            continue

        value = float(
            info.get(
                "value",
                0.0
            )
        )

        if (
            best_value is None
            or
            value > best_value
        ):

            best_value = value

            best_actions = [
                action
            ]

        elif value == best_value:

            best_actions.append(
                action
            )

    if not best_actions:

        return "WAIT"

    action = random.choice(
        best_actions
    )

    brain_log(
        f"🎯 Best action → "
        f"{action} "
        f"({best_value:.2f})"
    )

    return action


# ============================================================
# LEARNING
# ============================================================

def learn(
    state,
    action,
    reward
):

    global current_reward
    global total_reward
    global learning_count
    global unsaved_learning

    if not state:
        return

    if not action:
        return

    with brain_memory_lock:
        ensure_action_entry(
            state,
            action
        )

        info = brain_memory[
            state
        ][
            "actions"
        ][action]

        info["tries"] = int(info.get("tries", 0)) + 1

        if reward > 0:
            info["successes"] = int(info.get("successes", 0)) + 1
        elif reward < 0:
            info["failures"] = int(info.get("failures", 0)) + 1

        old_value = float(info.get("value", 0.0))
        learning_rate = 0.25

        new_value = (
            old_value
            + learning_rate
            * (reward - old_value)
        )

        info["value"] = new_value

        current_reward = reward
        total_reward += reward
        learning_count += 1
        unsaved_learning = True

    brain_log(
        f"⭐ Learned {action} reward={reward:+.2f}"
    )

    brain_log(
        f"🧠 Value {old_value:.2f} → {new_value:.2f}"
    )

    queue_ui(
        update_brain_stats
    )

    # Don't constantly write to OneDrive.
    if learning_count % SAVE_EVERY_ACTIONS == 0:
        threading.Thread(
            target=save_brain,
            daemon=True
        ).start()


# ============================================================
# MANUAL REWARDS
# ============================================================

def give_reward(reward):

    if not last_state:

        brain_log(
            "⚠️ No previous state."
        )

        return

    if not last_action:

        brain_log(
            "⚠️ No previous action."
        )

        return

    learn(
        last_state,
        last_action,
        reward
    )


def reward_good():

    give_reward(
        1.0
    )


def reward_bad():

    give_reward(
        -1.0
    )


def reward_neutral():

    give_reward(
        0.0
    )


# ============================================================
# KEYBOARD
# ============================================================

def press_key(key):

    global current_action

    if emergency_stop:
        return

    try:

        keyboard.press(
            key
        )

        held_keys.add(
            key
        )

        current_action = (
            f"Pressing {key}"
        )

        if recording:

            recorded_actions.append({
                "type": "key_down",
                "key": key,
                "time": time.time()
            })

        queue_ui(
            update_action
        )

    except Exception as error:

        system_log(
            f"Keyboard error: {error}"
        )


def release_key(key):

    global current_action

    try:

        keyboard.release(
            key
        )

        held_keys.discard(
            key
        )

        current_action = (
            f"Released {key}"
        )

        if recording:

            recorded_actions.append({
                "type": "key_up",
                "key": key,
                "time": time.time()
            })

        queue_ui(
            update_action
        )

    except Exception as error:

        system_log(
            f"Keyboard release error: {error}"
        )


def tap_key(
    key,
    duration=ACTION_DURATION
):

    if emergency_stop:
        return

    press_key(
        key
    )

    time.sleep(
        duration
    )

    release_key(
        key
    )


def release_all_keys():

    for key in list(
        held_keys
    ):

        try:

            keyboard.release(
                key
            )

        except Exception:

            pass

    held_keys.clear()


# ============================================================
# MOUSE
# ============================================================

def move_mouse(
    x,
    y
):

    if emergency_stop:
        return

    try:

        pyautogui.moveTo(
            x,
            y,
            duration=0.08
        )

        if recording:

            recorded_actions.append({
                "type": "mouse_move",
                "x": x,
                "y": y,
                "time": time.time()
            })

        system_log(
            f"🖱️ Mouse → {x}, {y}"
        )

    except Exception as error:

        system_log(
            f"Mouse error: {error}"
        )


def click_mouse(
    button="left"
):

    if emergency_stop:
        return

    try:

        pyautogui.click(
            button=button
        )

        if recording:

            recorded_actions.append({
                "type": "mouse_click",
                "button": button,
                "time": time.time()
            })

        system_log(
            f"🖱️ {button} click"
        )

    except Exception as error:

        system_log(
            f"Mouse click error: {error}"
        )


# ============================================================
# BRAIN ACTION EXECUTOR
# ============================================================

def execute_action(
    action
):

    global brain_action_in_progress
    global current_action

    if emergency_stop:
        return

    # Trackmania hard block: R/ESC can leave gameplay and open replay/menu UI.
    if current_game_mode == "Trackmania" and action in {"R", "ESC", "ESCAPE"}:
        brain_log(f"🚫 Trackmania blocked menu/replay key → {action}")
        action = "WAIT"

    brain_action_in_progress = True

    try:

        brain_log(
            f"🎮 Execute → {action}"
        )

        if action == "W":

            tap_key(
                "w"
            )

        elif action == "A":

            tap_key(
                "a"
            )

        elif action == "S":

            tap_key(
                "s"
            )

        elif action == "D":

            tap_key(
                "d"
            )

        elif action == "SPACE":

            tap_key(
                "space"
            )

        elif action == "SHIFT":

            tap_key(
                "shift"
            )

        elif action == "LEFT_CLICK":

            click_mouse(
                "left"
            )

        elif action == "RIGHT_CLICK":

            click_mouse(
                "right"
            )

        elif action == "MOUSE_LEFT":

            pyautogui.moveRel(
                -75,
                0,
                duration=0.08
            )

        elif action == "MOUSE_RIGHT":

            pyautogui.moveRel(
                75,
                0,
                duration=0.08
            )

        elif action == "MOUSE_UP":

            pyautogui.moveRel(0, -75, duration=0.08)

        elif action == "MOUSE_DOWN":

            pyautogui.moveRel(0, 75, duration=0.08)

        elif action in {
            "CTRL", "ALT", "TAB", "ESC",
            "E", "F", "G", "H", "I", "J", "K", "L",
            "Q", "R", "T", "X", "Y", "Z", "C", "V",
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "UP", "DOWN", "LEFT", "RIGHT"
        }:
            tap_key(action.lower())

        elif action == "WAIT":

            time.sleep(
                ACTION_DURATION
            )

        current_action = (
            f"AI: {action}"
        )

        queue_ui(
            update_action
        )

    except Exception as error:

        brain_log(
            f"❌ Action error: {error}"
        )

    finally:

        brain_action_in_progress = False


# ============================================================
# BRAIN LOOP
# ============================================================

def automatic_movement_reward():
    """Reward movement actions when the cursor/screen position actually changes.
    This is deliberately small so movement is useful but does not dominate other rewards.
    """
    global last_movement_time, last_movement_pos, movement_reward_total
    if not learning_enabled or emergency_stop or not brain_active:
        return
    try:
        pos = pyautogui.position()
        now = time.time()
        if last_movement_pos is not None:
            dx = pos.x - last_movement_pos[0]
            dy = pos.y - last_movement_pos[1]
            distance = (dx * dx + dy * dy) ** 0.5
            if distance >= 8 and last_action in {"MOUSE_LEFT", "MOUSE_RIGHT", "MOUSE_UP", "MOUSE_DOWN"}:
                reward = min(0.20, 0.03 + distance / 5000.0)
                learn(last_state, last_action, reward)
                movement_reward_total += reward
                brain_log(f"🕹️ Movement detected → {distance:.0f}px, reward +{reward:.2f}")
        last_movement_pos = (pos.x, pos.y)
        last_movement_time = now
    except Exception:
        pass


def automatic_mode_reward(state):
    """
    Lightweight automatic reward shaping using OCR/state changes.
    It never assumes a specific game API. Positive/negative phrases
    are only hints; the normal transition reward still applies.
    """
    if not learning_enabled or not last_state or not last_action:
        return

    text = normalize_text(latest_ocr_text)
    if not text:
        return

    positive_words = (
        "victory", "victorious", "win", "won", "checkpoint",
        "completed", "complete", "success", "finished", "goal",
        "new best", "personal best", "level complete"
    )
    negative_words = (
        "game over", "you died", "dead", "defeat", "failed",
        "failure", "crashed", "eliminated", "destroyed"
    )

    reward = 0.0
    if any(word in text for word in positive_words):
        reward += 1.0 * mode_reward_scale
    if any(word in text for word in negative_words):
        reward -= 1.0 * mode_reward_scale

    if reward:
        learn(last_state, last_action, reward)
        brain_log(
            f"🤖 Auto reward [{current_game_mode}] "
            f"{reward:+.2f} from OCR"
        )


def set_game_mode(mode):
    global current_game_mode
    global mode_reward_scale

    if mode not in GAME_MODES:
        mode = "Universal"

    current_game_mode = mode

    # Small tuning differences only; the brain still learns from
    # actual observed outcomes.
    scales = {
        "Universal": 1.0,
        "Ultimate Custom Night": 1.15,
        "Subnautica": 1.0,
        "Subnautica 2": 1.0,
        "Minecraft Bedrock": 1.0,
        "Roblox": 1.0,
        "Space Engineers": 1.0,
        "Fortnite": 1.05,
        "Trackmania": 1.15,
        "Kerbal Space Program": 1.0,
        "Star Citizen": 1.0,
    }
    mode_reward_scale = scales.get(mode, 1.0)

    if "game_mode_var" in globals():
        game_mode_var.set(mode)

    if "game_mode_status_label" in globals():
        game_mode_status_label.config(
            text=f"🎮 Mode: {current_game_mode}"
        )

    system_log(
        f"🎮 Game mode selected → {current_game_mode}"
    )
    brain_log(
        f"🧠 Mode profile loaded: {current_game_mode} "
        f"({len(get_mode_actions())} actions)"
    )


def brain_loop():

    global last_state
    global last_action
    global last_brain_time
    global decision_count

    previous_state = None
    previous_action = None

    brain_log(
        "🧠 Brain loop started"
    )

    while (
        running
        and
        brain_active
    ):

        if emergency_stop:

            time.sleep(
                0.1
            )

            continue

        if not vision_active:

            time.sleep(
                0.25
            )

            continue

        if brain_action_in_progress:

            time.sleep(
                0.02
            )

            continue

        now = time.time()

        if (
            now
            -
            last_brain_time
            <
            BRAIN_DECISION_INTERVAL
        ):

            time.sleep(
                0.02
            )

            continue

        last_brain_time = now

        automatic_movement_reward()

        state = build_state()

        # Automatic game-aware reward hints from visible OCR.
        automatic_mode_reward(state)

        # ----------------------------------------------------
        # LEARN FROM PREVIOUS DECISION
        # ----------------------------------------------------

        if (
            previous_state
            and
            previous_action
            and
            learning_enabled
        ):

            if state != previous_state:

                learn(
                    previous_state,
                    previous_action,
                    0.25
                )

            else:

                learn(
                    previous_state,
                    previous_action,
                    -0.05
                )

        # ----------------------------------------------------
        # THINK
        # ----------------------------------------------------

        action = choose_action(
            state
        )

        last_state = state
        last_action = action

        previous_state = state
        previous_action = action

        decision_count += 1

        queue_ui(
            update_brain_stats
        )

        brain_log(
            f"👁️ State: "
            f"{state[:110]}"
        )

        brain_log(
            f"🧠 Decision #{decision_count}: "
            f"{action}"
        )

        # ----------------------------------------------------
        # TEST MODE
        # ----------------------------------------------------

        if brain_test_mode:

            brain_log(
                f"🧪 TEST — would execute "
                f"{action}"
            )

            time.sleep(
                BRAIN_DECISION_INTERVAL
            )

        else:

            threading.Thread(
                target=execute_action,
                args=(action,),
                daemon=True
            ).start()

    brain_log(
        "🧠 Brain loop stopped"
    )


# ============================================================
# BRAIN CONTROLS
# ============================================================

def activate_brain():

    global brain_active
    global emergency_stop

    if brain_active:
        return

    if not vision_active:

        system_log(
            "⚠️ Start Vision first."
        )

        return

    emergency_stop = False
    brain_active = True

    brain_status_label.config(
        text="BRAIN: 🟢 ACTIVE"
    )

    activate_brain_button.config(
        state="disabled"
    )

    deactivate_brain_button.config(
        state="normal"
    )

    brain_log(
        "🧠 Brain activated"
    )

    threading.Thread(
        target=brain_loop,
        daemon=True
    ).start()


def deactivate_brain():

    global brain_active

    brain_active = False

    release_all_keys()

    brain_status_label.config(
        text="BRAIN: ⚪ OFF"
    )

    activate_brain_button.config(
        state="normal"
    )

    deactivate_brain_button.config(
        state="disabled"
    )

    brain_log(
        "🧠 Brain stopped"
    )

    threading.Thread(
        target=save_brain,
        daemon=True
    ).start()


def toggle_test_mode():

    global brain_test_mode

    brain_test_mode = (
        not brain_test_mode
    )

    if brain_test_mode:

        brain_test_button.config(
            text="🧪 Brain Test: ON"
        )

        brain_log(
            "🧪 Test Mode ON"
        )

    else:

        brain_test_button.config(
            text="🧪 Brain Test: OFF"
        )

        brain_log(
            "🧪 Test Mode OFF"
        )


def toggle_learning():

    global learning_enabled

    learning_enabled = (
        not learning_enabled
    )

    if learning_enabled:

        learning_button.config(
            text="🧠 Learning: ON"
        )

        brain_log(
            "🧠 Learning enabled"
        )

    else:

        learning_button.config(
            text="🧠 Learning: OFF"
        )

        brain_log(
            "🧠 Learning disabled"
        )


# ============================================================
# AI CONTROLS
# ============================================================

def activate_ai():

    global ai_active
    global emergency_stop

    emergency_stop = False
    ai_active = True

    ai_status_label.config(
        text="AI STATUS: 🟢 ACTIVE"
    )

    ai_activate_button.config(
        state="disabled"
    )

    ai_deactivate_button.config(
        state="normal"
    )

    system_log(
        "🤖 AI activated"
    )


def deactivate_ai():

    global ai_active

    ai_active = False

    release_all_keys()

    ai_status_label.config(
        text="AI STATUS: ⚪ INACTIVE"
    )

    ai_activate_button.config(
        state="normal"
    )

    ai_deactivate_button.config(
        state="disabled"
    )

    system_log(
        "🤖 AI deactivated"
    )


def emergency_stop_ai():

    global ai_active
    global brain_active
    global emergency_stop

    emergency_stop = True

    ai_active = False
    brain_active = False

    release_all_keys()

    ai_status_label.config(
        text="AI STATUS: 🔴 EMERGENCY STOP"
    )

    brain_status_label.config(
        text="BRAIN: 🔴 STOPPED"
    )

    ai_activate_button.config(
        state="normal"
    )

    ai_deactivate_button.config(
        state="disabled"
    )

    activate_brain_button.config(
        state="normal"
    )

    deactivate_brain_button.config(
        state="disabled"
    )

    system_log(
        "🚨 EMERGENCY STOP"
    )

    brain_log(
        "🚨 Brain emergency stop"
    )


# ============================================================
# WINDOWS API
# ============================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    wintypes.HWND,
    wintypes.LPARAM
)


def get_window_title(hwnd):

    length = user32.GetWindowTextLengthW(
        hwnd
    )

    if length <= 0:
        return ""

    buffer = ctypes.create_unicode_buffer(
        length + 1
    )

    user32.GetWindowTextW(
        hwnd,
        buffer,
        length + 1
    )

    return buffer.value


def get_process_name(hwnd):

    try:

        process_id = wintypes.DWORD()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(
                process_id
            )
        )

        PROCESS_QUERY_LIMITED_INFORMATION = (
            0x1000
        )

        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            process_id.value
        )

        if not handle:
            return ""

        buffer = ctypes.create_unicode_buffer(
            1024
        )

        buffer_size = wintypes.DWORD(
            1024
        )

        result = (
            kernel32.QueryFullProcessImageNameW(
                handle,
                0,
                buffer,
                ctypes.byref(
                    buffer_size
                )
            )
        )

        kernel32.CloseHandle(
            handle
        )

        if result:

            return os.path.basename(
                buffer.value
            ).lower()

    except Exception:
        pass

    return ""


def get_windows():

    windows = []

    def callback(
        hwnd,
        lparam
    ):

        if user32.IsWindowVisible(
            hwnd
        ):

            title = get_window_title(
                hwnd
            )

            if title.strip():

                process = get_process_name(
                    hwnd
                )

                windows.append(
                    (
                        hwnd,
                        title,
                        process
                    )
                )

        return True

    user32.EnumWindows(
        EnumWindowsProc(callback),
        0
    )

    return windows


def get_active_window():

    hwnd = user32.GetForegroundWindow()

    if not hwnd:
        return ""

    return get_window_title(
        hwnd
    )


# ============================================================
# NOTEPAD
# ============================================================

def find_notepad():

    for hwnd, title, process in get_windows():

        if process == "notepad.exe":

            return hwnd, title

    return None, None


def focus_notepad():

    hwnd, title = find_notepad()

    if not hwnd:

        system_log(
            "❌ Notepad not found."
        )

        return False

    try:

        user32.ShowWindow(
            hwnd,
            9
        )

        time.sleep(
            0.2
        )

        user32.SetForegroundWindow(
            hwnd
        )

        time.sleep(
            0.4
        )

        system_log(
            "📝 Notepad focused"
        )

        return True

    except Exception as error:

        system_log(
            f"❌ Notepad focus error: {error}"
        )

        return False


def detect_notepad():

    global notepad_detected

    hwnd, title = find_notepad()

    notepad_detected = (
        hwnd is not None
    )

    queue_ui(
        update_detection
    )


def update_detection():

    if notepad_detected:

        notepad_status_label.config(
            text="Notepad: 🟢 DETECTED"
        )

    else:

        notepad_status_label.config(
            text="Notepad: ⚪ Not detected"
        )


# ============================================================
# HELLO TEST
# ============================================================

hello_test_running = False


def say_hello():

    global hello_test_running

    if hello_test_running:
        return

    hello_test_running = True

    def worker():

        global hello_test_running

        try:

            system_log(
                "👋 Starting Notepad test..."
            )

            hwnd, title = find_notepad()

            if not hwnd:

                system_log(
                    "❌ Open Notepad first."
                )

                queue_ui(
                    hello_status_label.config,
                    text=(
                        "Test Result: "
                        "❌ Notepad not found"
                    )
                )

                return

            if not focus_notepad():
                return

            time.sleep(
                0.5
            )

            pyautogui.click()

            time.sleep(
                0.2
            )

            pyautogui.write(
                "hello!",
                interval=0.07
            )

            system_log(
                '✅ Typed "hello!"'
            )

            queue_ui(
                hello_status_label.config,
                text=(
                    'Test Result: '
                    '✅ "hello!" typed'
                )
            )

        except Exception as error:

            system_log(
                f"❌ Hello test error: {error}"
            )

        finally:

            hello_test_running = False

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


# ============================================================
# OCR
# ============================================================

def preprocess_for_ocr(image):

    gray = ImageOps.grayscale(
        image
    )

    gray = ImageEnhance.Contrast(
        gray
    ).enhance(
        1.8
    )

    gray = ImageEnhance.Sharpness(
        gray
    ).enhance(
        1.5
    )

    gray = gray.filter(
        ImageFilter.SHARPEN
    )

    return gray


def run_ocr(image):

    global latest_ocr_text
    global latest_ocr_confidence

    if not ocr_active:
        return

    try:

        processed = preprocess_for_ocr(
            image
        )

        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config="--psm 6"
        )

        words = []
        confidences = []

        for index, text in enumerate(
            data["text"]
        ):

            text = text.strip()

            if not text:
                continue

            try:

                confidence = float(
                    data["conf"][index]
                )

            except Exception:

                confidence = 0

            if (
                confidence
                >=
                OCR_MIN_CONFIDENCE
            ):

                words.append(
                    text
                )

                confidences.append(
                    confidence
                )

        if words:

            result = " ".join(
                words
            )

            confidence = (
                sum(confidences)
                /
                len(confidences)
            )

            latest_ocr_text = result

            latest_ocr_confidence = confidence

            queue_ui(
                update_ocr_status
            )

            ocr_log(
                f"Detected: {result}"
            )

            ocr_log(
                f"Confidence: "
                f"{confidence:.1f}%"
            )

        else:

            latest_ocr_text = ""

            latest_ocr_confidence = 0

            queue_ui(
                update_ocr_status
            )

    except pytesseract.TesseractNotFoundError:

        ocr_log(
            "❌ Tesseract not found."
        )

    except Exception as error:

        ocr_log(
            f"OCR error: {error}"
        )


def update_ocr_status():

    if not latest_ocr_text:

        ocr_label.config(
            text="Latest OCR: —"
        )

        ocr_confidence_label.config(
            text="Confidence: —"
        )

        return

    text = latest_ocr_text

    if len(text) > 80:

        text = (
            text[:77]
            +
            "..."
        )

    ocr_label.config(
        text=(
            f"Latest OCR: {text}"
        )
    )

    ocr_confidence_label.config(
        text=(
            f"Confidence: "
            f"{latest_ocr_confidence:.1f}%"
        )
    )


# ============================================================
# VISION
# ============================================================

def update_preview(image):

    try:

        preview = image.copy()

        preview.thumbnail(
            (520, 290)
        )

        photo = ImageTk.PhotoImage(
            preview
        )

        preview_label.config(
            image=photo
        )

        preview_label.image = photo

    except Exception:
        pass


def update_perception():

    perception_label.config(
        text=(
            f"Frames: {vision_frames}\n"
            f"FPS: {vision_fps:.1f}\n"
            f"Screen: "
            f"{screen_width} × "
            f"{screen_height}\n"
            f"Window: "
            f"{active_window_title or 'Unknown'}"
        )
    )


def vision_loop():

    global vision_frames
    global vision_fps
    global screen_width
    global screen_height
    global active_window_title
    global last_preview_time
    global last_ocr_time

    frame_times = deque(
        maxlen=30
    )

    try:

        with mss.mss() as capture:

            monitor = capture.monitors[1]

            screen_width = monitor[
                "width"
            ]

            screen_height = monitor[
                "height"
            ]

            system_log(
                "👁️ Vision capture started"
            )

            while (
                vision_active
                and
                running
            ):

                start = time.perf_counter()

                try:

                    screenshot = capture.grab(
                        monitor
                    )

                    image = Image.frombytes(
                        "RGB",
                        screenshot.size,
                        screenshot.rgb
                    )

                    vision_frames += 1

                    active_window_title = (
                        get_active_window()
                    )

                    now = time.perf_counter()

                    frame_times.append(
                        now
                    )

                    if len(
                        frame_times
                    ) >= 2:

                        elapsed = (
                            frame_times[-1]
                            -
                            frame_times[0]
                        )

                        if elapsed > 0:

                            vision_fps = (
                                (
                                    len(
                                        frame_times
                                    )
                                    -
                                    1
                                )
                                /
                                elapsed
                            )

                    detect_notepad()

                    queue_ui(
                        update_perception
                    )

                    # Preview
                    if (
                        now
                        -
                        last_preview_time
                        >=
                        PREVIEW_INTERVAL
                    ):

                        last_preview_time = now

                        queue_ui(
                            update_preview,
                            image.copy()
                        )

                    # OCR
                    if (
                        ocr_active
                        and
                        now
                        -
                        last_ocr_time
                        >=
                        OCR_INTERVAL
                    ):

                        last_ocr_time = now

                        threading.Thread(
                            target=run_ocr,
                            args=(
                                image.copy(),
                            ),
                            daemon=True
                        ).start()

                    elapsed = (
                        time.perf_counter()
                        -
                        start
                    )

                    delay = (
                        VISION_INTERVAL
                        -
                        elapsed
                    )

                    if delay > 0:

                        time.sleep(
                            delay
                        )

                except Exception as error:

                    vision_log(
                        f"Vision error: {error}"
                    )

                    time.sleep(
                        0.1
                    )

    except Exception as error:

        system_log(
            f"❌ Vision startup error: {error}"
        )

    system_log(
        "👁️ Vision capture stopped"
    )


def start_vision():

    global vision_active

    if vision_active:
        return

    vision_active = True

    vision_status_label.config(
        text="VISION: 🟢 ACTIVE"
    )

    start_vision_button.config(
        state="disabled"
    )

    stop_vision_button.config(
        state="normal"
    )

    system_log(
        "▶ Starting vision..."
    )

    threading.Thread(
        target=vision_loop,
        daemon=True
    ).start()


def stop_vision():

    global vision_active

    vision_active = False

    vision_status_label.config(
        text="VISION: ⚪ OFF"
    )

    start_vision_button.config(
        state="normal"
    )

    stop_vision_button.config(
        state="disabled"
    )

    system_log(
        "⏹ Vision stopped"
    )


# ============================================================
# OCR TOGGLE
# ============================================================

def toggle_ocr():

    global ocr_active
    global voice_active

    ocr_active = (
        not ocr_active
    )

    if ocr_active:

        ocr_button.config(
            text="🔍 OCR: ON"
        )

        ocr_status_small.config(
            text="OCR running"
        )

        system_log(
            "🔍 OCR activated"
        )

    else:

        ocr_button.config(
            text="🔍 OCR: OFF"
        )

        ocr_status_small.config(
            text="OCR stopped"
        )

        system_log(
            "🔍 OCR stopped"
        )


# ============================================================
# BRAIN STATS
# ============================================================

def get_total_memory_states():

    with brain_memory_lock:
        return len(
            brain_memory
        )


def get_total_action_entries():

    total = 0

    with brain_memory_lock:
        for state_data in brain_memory.values():

            total += len(
                state_data.get(
                    "actions",
                    {}
                )
            )

    return total


def update_brain_stats():

    memory_states_label.config(
        text=(
            f"Learned States: "
            f"{get_total_memory_states()}"
        )
    )

    learned_actions_label.config(
        text=(
            f"Action Entries: "
            f"{get_total_action_entries()}"
        )
    )

    decision_label.config(
        text=(
            f"Decisions: "
            f"{decision_count}"
        )
    )

    learning_label.config(
        text=(
            f"Learning Events: "
            f"{learning_count}"
        )
    )

    reward_label.config(
        text=(
            f"Last Reward: "
            f"{current_reward:+.2f}"
        )
    )

    total_reward_label.config(
        text=(
            f"Total Reward: "
            f"{total_reward:+.2f}"
        )
    )


def update_memory_display():

    memory_status_label.config(
        text=(
            f"Memory: "
            f"{memory_status}"
        )
    )

    memory_file_label.config(
        text=(
            f"File: memory.AI\n"
            f"Last Save: {last_save_time}"
        )
    )

    update_brain_stats()


# ============================================================
# RECORDING
# ============================================================

def toggle_recording():

    global recording

    recording = (
        not recording
    )

    if recording:

        record_button.config(
            text="⏹ Stop Recording"
        )

        recording_status_label.config(
            text="Recording: 🟢"
        )

        system_log(
            "🎥 Recording started"
        )

    else:

        record_button.config(
            text="🔴 Start Recording"
        )

        recording_status_label.config(
            text="Recording: ⚪"
        )

        system_log(
            "🎥 Recording stopped"
        )


def save_recording():

    if not recorded_actions:

        system_log(
            "⚠️ No recorded actions."
        )

        return

    filename = filedialog.asksaveasfilename(
        title="Save Recording",
        defaultextension=".json",
        filetypes=[
            (
                "JSON files",
                "*.json"
            )
        ]
    )

    if not filename:
        return

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                recorded_actions,
                file,
                indent=4
            )

        system_log(
            "💾 Recording saved."
        )

    except Exception as error:

        system_log(
            f"❌ Recording save error: {error}"
        )


# ============================================================
# TEST BUTTONS
# ============================================================

def test_w():

    def worker():

        press_key(
            "w"
        )

        time.sleep(
            1
        )

        release_key(
            "w"
        )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def test_space():

    threading.Thread(
        target=tap_key,
        args=("space",),
        daemon=True
    ).start()


def test_left():

    threading.Thread(
        target=tap_key,
        args=("left",),
        daemon=True
    ).start()


def test_right():

    threading.Thread(
        target=tap_key,
        args=("right",),
        daemon=True
    ).start()


# ============================================================
# MEMORY CONTROLS
# ============================================================

def manual_save_brain():
    system_log("💾 Manual brain save requested")
    threading.Thread(
        target=save_brain,
        daemon=True
    ).start()


def test_memory_save():
    """Write the current brain and report whether the file is readable."""
    system_log("🧪 Testing brain memory save...")
    if not save_brain():
        system_log("❌ Memory save test FAILED")
        return

    data = validate_memory_file(MEMORY_FILE)
    if data is None:
        system_log("❌ Memory file was written but could not be verified")
        return

    system_log(
        f"✅ Memory save test PASSED — {len(data)} states verified"
    )


# ============================================================
# UI
# ============================================================

def update_action():

    action_label.config(
        text=(
            f"Current Action: "
            f"{current_action}"
        )
    )


# ============================================================
# CLOSE
# ============================================================

def close_app():

    global running
    global vision_active
    global ai_active
    global brain_active
    global ocr_active

    system_log(
        "Closing Universal Game AI..."
    )

    running = False

    vision_active = False
    ai_active = False
    brain_active = False
    ocr_active = False
    voice_active = False
    try:
        if VOICE_AVAILABLE and sd is not None: sd.stop()
    except Exception: pass

    release_all_keys()

    # Final synchronous save. The new saver never deletes memory.AI first.
    if unsaved_learning:
        if not save_brain():
            system_log(
                "⚠️ Final brain save did not complete; memory.AI was preserved."
            )
    else:
        system_log("💾 No unsaved learning changes.")

    try:

        root.destroy()

    except Exception:

        pass


# ============================================================
# VOICE CONTROL - VERSION 0.8.7
# ============================================================

def _set_voice_state(status=None, heard=None, command=None, error=None):
    global voice_status, voice_last_heard, voice_last_command, voice_error
    with voice_lock:
        if status is not None: voice_status = status
        if heard is not None: voice_last_heard = heard
        if command is not None: voice_last_command = command
        if error is not None: voice_error = error
    if "voice_status_label" in globals():
        queue_ui(update_voice_ui)


def _normalise_voice_text(text):
    text = (text or "").lower().strip()
    for char in ",.!?_-":
        text = text.replace(char, " ")
    return " ".join(text.split())


def _voice_command(text):
    text = _normalise_voice_text(text)
    on = {
        "turn ai on", "turn the ai on", "turn on ai", "turn on the ai",
        "ai on", "switch ai on", "switch the ai on",
        "turn eye on", "turn the eye on", "turn on eye", "turn on the eye", "eye on",
    }
    off = {
        "turn ai off", "turn the ai off", "turn off ai", "turn off the ai",
        "ai off", "switch ai off", "switch the ai off",
        "turn eye off", "turn the eye off", "turn off eye", "turn off the eye", "eye off",
    }
    if text in on: return "ON"
    if text in off: return "OFF"
    return None


def _record_voice_sample():
    if not VOICE_AVAILABLE or sd is None:
        raise RuntimeError("Voice packages are unavailable")
    frames = int(voice_sample_rate * voice_record_seconds)
    data = sd.rec(frames, samplerate=voice_sample_rate, channels=1, dtype="int16", blocking=True)
    sd.wait()
    return data.tobytes()


def voice_loop():
    global voice_active
    if not VOICE_AVAILABLE:
        _set_voice_state(status="🔴 ERROR", error="Voice packages are unavailable.")
        return
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.6
    recognizer.non_speaking_duration = 0.4
    _set_voice_state(status="🟢 LISTENING", error="")
    system_log("🎙️ Voice active — say TURN AI ON or TURN AI OFF")
    while running and voice_active:
        try:
            raw = _record_voice_sample()
            audio = sr.AudioData(raw, voice_sample_rate, 2)
            try:
                heard = recognizer.recognize_google(audio, language="en-GB")
            except sr.UnknownValueError:
                continue
            except sr.RequestError as error:
                _set_voice_state(status="🟡 RETRYING", error=f"Speech service: {error}")
                system_log(f"⚠️ Voice service error — retrying: {error}")
                time.sleep(2)
                if voice_active: _set_voice_state(status="🟢 LISTENING", error="")
                continue
            command = _voice_command(heard)
            _set_voice_state(status="🟢 LISTENING", heard=heard, command=command or "—", error="")
            system_log(f"🎙️ Heard: {heard}")
            if command == "ON":
                queue_ui(activate_ai)
                _set_voice_state(command="TURN AI ON → ACTIVATED")
                system_log("🎙️ Voice command: TURN AI ON")
            elif command == "OFF":
                queue_ui(deactivate_ai)
                _set_voice_state(command="TURN AI OFF → DEACTIVATED")
                system_log("🎙️ Voice command: TURN AI OFF")
        except Exception as error:
            _set_voice_state(status="🟡 RETRYING", error=f"{type(error).__name__}: {error}")
            system_log(f"⚠️ Voice listener error (recovering): {type(error).__name__}: {error}")
            time.sleep(1)
            if voice_active: _set_voice_state(status="🟢 LISTENING", error="")
    _set_voice_state(status="⚪ OFF")


def update_voice_ui():
    if "voice_status_label" not in globals(): return
    with voice_lock:
        status, heard, command, error = voice_status, voice_last_heard, voice_last_command, voice_error
    voice_status_label.config(text=f"VOICE: {status}")
    voice_heard_label.config(text=f"Heard: {heard}")
    voice_command_label.config(text=f"Last command: {command}")
    voice_error_label.config(text=f"Error: {error}" if error else "Error: —")


def start_voice():
    global voice_active, voice_thread
    if voice_active: return
    if not VOICE_AVAILABLE:
        _set_voice_state(status="🔴 ERROR", error="Missing voice packages: SpeechRecognition + sounddevice + numpy")
        return
    try:
        default_input = sd.default.device[0]
        if default_input is None or int(default_input) < 0:
            raise RuntimeError("No default microphone is selected in Windows.")
        info = sd.query_devices(int(default_input))
        if int(info.get("max_input_channels", 0)) < 1:
            raise RuntimeError("The selected default audio device has no microphone input.")
        voice_active = True
        voice_device_label.config(text=f"Microphone: {info.get('name', 'Default input')}")
        start_voice_button.config(state="disabled")
        stop_voice_button.config(state="normal")
        _set_voice_state(status="🟡 STARTING...", error="")
        voice_thread = threading.Thread(target=voice_loop, name="VoiceControl", daemon=True)
        voice_thread.start()
    except Exception as error:
        voice_active = False
        _set_voice_state(status="🔴 ERROR", error=f"Microphone start failed: {error}")


def stop_voice():
    global voice_active
    voice_active = False
    try:
        if VOICE_AVAILABLE and sd is not None: sd.stop()
    except Exception: pass
    _set_voice_state(status="⚪ OFF", error="")
    if "start_voice_button" in globals(): start_voice_button.config(state="normal")
    if "stop_voice_button" in globals(): stop_voice_button.config(state="disabled")
    system_log("⏹ Voice control stopped")


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()

root.title(
    APP_TITLE
)

root.geometry(
    "1280x900"
)

root.minsize(
    1050,
    650
)

root.protocol(
    "WM_DELETE_WINDOW",
    close_app
)


# ============================================================
# STYLE
# ============================================================

style = ttk.Style()

try:

    style.theme_use(
        "clam"
    )

except Exception:

    pass

style.configure(
    "Title.TLabel",
    font=(
        "Segoe UI",
        18,
        "bold"
    )
)

style.configure(
    "Status.TLabel",
    font=(
        "Segoe UI",
        10,
        "bold"
    )
)


# ============================================================
# TITLE
# ============================================================

title_frame = ttk.Frame(
    root,
    padding=(
        12,
        10,
        12,
        5
    )
)

title_frame.pack(
    fill="x"
)

ttk.Label(
    title_frame,
    text=APP_TITLE,
    style="Title.TLabel"
).pack(
    side="left"
)

ttk.Label(
    title_frame,
    text=(
        "Vision → Brain → Action → Learning"
    )
).pack(
    side="right"
)


# ============================================================
# MAIN
# ============================================================

main_frame = ttk.Frame(
    root,
    padding=10
)

main_frame.pack(
    fill="both",
    expand=True
)

main_frame.columnconfigure(
    0,
    weight=1
)

main_frame.columnconfigure(
    1,
    weight=1
)

main_frame.rowconfigure(
    0,
    weight=1
)


# ============================================================
# LEFT
# ============================================================

left_panel = ttk.Frame(
    main_frame
)

left_panel.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 5)
)


# ============================================================
# VISION PREVIEW
# ============================================================

vision_frame = ttk.LabelFrame(
    left_panel,
    text="👁️ Live Vision",
    padding=8
)

vision_frame.pack(
    fill="x",
    pady=(0, 8)
)

preview_label = ttk.Label(
    vision_frame,
    text="Vision preview unavailable",
    anchor="center"
)

preview_label.pack(
    fill="both",
    expand=True
)

vision_status_label = ttk.Label(
    vision_frame,
    text="VISION: ⚪ OFF",
    style="Status.TLabel"
)

vision_status_label.pack(
    pady=(8, 0)
)


# ============================================================
# VISION LOG
# ============================================================

vision_log_frame = ttk.LabelFrame(
    left_panel,
    text="👁️ Vision Log",
    padding=5
)

vision_log_frame.pack(
    fill="both",
    expand=True
)

vision_scroll = ttk.Scrollbar(
    vision_log_frame,
    orient="vertical"
)

vision_scroll.pack(
    side="right",
    fill="y"
)

vision_log_box = tk.Text(
    vision_log_frame,
    height=8,
    wrap="word",
    state="disabled",
    yscrollcommand=vision_scroll.set
)

vision_log_box.pack(
    side="left",
    fill="both",
    expand=True
)

vision_scroll.config(
    command=vision_log_box.yview
)


# ============================================================
# RIGHT SCROLLABLE PANEL
# ============================================================

right_container = ttk.Frame(
    main_frame
)

right_container.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=(5, 0)
)

right_container.rowconfigure(
    0,
    weight=1
)

right_container.columnconfigure(
    0,
    weight=1
)

right_canvas = tk.Canvas(
    right_container,
    highlightthickness=0,
    borderwidth=0
)

right_scrollbar = ttk.Scrollbar(
    right_container,
    orient="vertical",
    command=right_canvas.yview
)

right_canvas.configure(
    yscrollcommand=right_scrollbar.set
)

right_canvas.grid(
    row=0,
    column=0,
    sticky="nsew"
)

right_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns"
)

right_panel = ttk.Frame(
    right_canvas
)

right_window = right_canvas.create_window(
    0,
    0,
    window=right_panel,
    anchor="nw"
)

# ============================================================
# VOICE CONTROL - VERSION 0.8.7
# ============================================================
voice_frame = ttk.LabelFrame(right_panel, text="🎙️ Voice Control", padding=8)
voice_frame.pack(fill="x", pady=(0, 8))
voice_status_label = ttk.Label(voice_frame, text="VOICE: ⚪ OFF", style="Status.TLabel")
voice_status_label.pack(anchor="w", pady=(0, 4))
voice_device_label = ttk.Label(voice_frame, text="Microphone: —")
voice_device_label.pack(anchor="w")
voice_heard_label = ttk.Label(voice_frame, text="Heard: —")
voice_heard_label.pack(anchor="w")
voice_command_label = ttk.Label(voice_frame, text="Last command: —")
voice_command_label.pack(anchor="w")
voice_error_label = ttk.Label(voice_frame, text="Error: —", wraplength=430)
voice_error_label.pack(anchor="w", pady=(2, 5))
voice_buttons = ttk.Frame(voice_frame)
voice_buttons.pack(fill="x")
start_voice_button = ttk.Button(voice_buttons, text="🎙️ Start Voice", command=start_voice)
start_voice_button.pack(side="left", fill="x", expand=True, padx=(0, 3))
stop_voice_button = ttk.Button(voice_buttons, text="⏹ Stop Voice", command=stop_voice, state="disabled")
stop_voice_button.pack(side="left", fill="x", expand=True, padx=(3, 0))


# ============================================================
# GAME MODE SELECTOR - VERSION 0.8
# ============================================================

game_mode_frame = ttk.LabelFrame(
    right_panel,
    text="🎮 Game Mode",
    padding=8
)
game_mode_frame.pack(
    fill="x",
    pady=(0, 8)
)

game_mode_var = tk.StringVar(value=current_game_mode)

game_mode_combo = ttk.Combobox(
    game_mode_frame,
    textvariable=game_mode_var,
    values=list(GAME_MODES.keys()),
    state="readonly"
)
game_mode_combo.pack(
    fill="x",
    pady=(0, 5)
)

game_mode_status_label = ttk.Label(
    game_mode_frame,
    text=f"🎮 Mode: {current_game_mode}"
)
game_mode_status_label.pack(
    anchor="w"
)

game_mode_description_label = ttk.Label(
    game_mode_frame,
    text=GAME_MODES[current_game_mode]["description"],
    wraplength=430
)
game_mode_description_label.pack(
    anchor="w",
    pady=(3, 0)
)

def on_game_mode_changed(event=None):
    mode = game_mode_var.get()
    set_game_mode(mode)
    game_mode_description_label.config(
        text=GAME_MODES[mode]["description"]
    )

game_mode_combo.bind(
    "<<ComboboxSelected>>",
    on_game_mode_changed
)



def update_right_scroll_region(
    event=None
):

    right_canvas.configure(
        scrollregion=right_canvas.bbox(
            "all"
        )
    )


def resize_right_panel(event):

    right_canvas.itemconfigure(
        right_window,
        width=event.width
    )


right_panel.bind(
    "<Configure>",
    update_right_scroll_region
)

right_canvas.bind(
    "<Configure>",
    resize_right_panel
)


def scroll_right_panel(event):

    right_canvas.yview_scroll(
        int(
            -1 *
            (
                event.delta
                /
                120
            )
        ),
        "units"
    )


right_canvas.bind(
    "<MouseWheel>",
    scroll_right_panel
)


# ============================================================
# PERCEPTION
# ============================================================

perception_frame = ttk.LabelFrame(
    right_panel,
    text="🧠 Perception",
    padding=8
)

perception_frame.pack(
    fill="x",
    pady=(0, 8)
)

perception_label = ttk.Label(
    perception_frame,
    text=(
        "Frames: 0\n"
        "FPS: 0.0\n"
        "Screen: —\n"
        "Window: —"
    )
)

perception_label.pack(
    anchor="w"
)


# ============================================================
# DETECTION
# ============================================================

detection_frame = ttk.LabelFrame(
    right_panel,
    text="🎯 Detection",
    padding=8
)

detection_frame.pack(
    fill="x",
    pady=(0, 8)
)

notepad_status_label = ttk.Label(
    detection_frame,
    text="Notepad: ⚪ Not detected"
)

notepad_status_label.pack(
    anchor="w"
)


# ============================================================
# OCR
# ============================================================

ocr_frame = ttk.LabelFrame(
    right_panel,
    text="🔍 OCR",
    padding=8
)

ocr_frame.pack(
    fill="x",
    pady=(0, 8)
)

ocr_label = ttk.Label(
    ocr_frame,
    text="Latest OCR: —",
    wraplength=430
)

ocr_label.pack(
    anchor="w"
)

ocr_confidence_label = ttk.Label(
    ocr_frame,
    text="Confidence: —"
)

ocr_confidence_label.pack(
    anchor="w"
)

ocr_status_small = ttk.Label(
    ocr_frame,
    text="OCR stopped"
)

ocr_status_small.pack(
    anchor="w"
)


# ============================================================
# OCR LOG
# ============================================================

ocr_log_frame = ttk.LabelFrame(
    right_panel,
    text="📜 OCR Output",
    padding=5
)

ocr_log_frame.pack(
    fill="x",
    pady=(0, 8)
)

ocr_scroll = ttk.Scrollbar(
    ocr_log_frame,
    orient="vertical"
)

ocr_scroll.pack(
    side="right",
    fill="y"
)

ocr_log_box = tk.Text(
    ocr_log_frame,
    height=7,
    wrap="word",
    state="disabled",
    yscrollcommand=ocr_scroll.set
)

ocr_log_box.pack(
    side="left",
    fill="both",
    expand=True
)

ocr_scroll.config(
    command=ocr_log_box.yview
)


# ============================================================
# BRAIN
# ============================================================

brain_frame = ttk.LabelFrame(
    right_panel,
    text="🧠 Brain",
    padding=8
)

brain_frame.pack(
    fill="x",
    pady=(0, 8)
)

brain_status_label = ttk.Label(
    brain_frame,
    text="BRAIN: ⚪ OFF",
    style="Status.TLabel"
)

brain_status_label.grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="w"
)

activate_brain_button = ttk.Button(
    brain_frame,
    text="🧠 Activate Brain",
    command=activate_brain
)

activate_brain_button.grid(
    row=1,
    column=0,
    padx=3,
    pady=5,
    sticky="ew"
)

deactivate_brain_button = ttk.Button(
    brain_frame,
    text="⏹ Stop Brain",
    command=deactivate_brain,
    state="disabled"
)

deactivate_brain_button.grid(
    row=1,
    column=1,
    padx=3,
    pady=5,
    sticky="ew"
)

brain_test_button = ttk.Button(
    brain_frame,
    text="🧪 Brain Test: OFF",
    command=toggle_test_mode
)

brain_test_button.grid(
    row=2,
    column=0,
    padx=3,
    pady=3,
    sticky="ew"
)

learning_button = ttk.Button(
    brain_frame,
    text="🧠 Learning: ON",
    command=toggle_learning
)

learning_button.grid(
    row=2,
    column=1,
    padx=3,
    pady=3,
    sticky="ew"
)

brain_frame.columnconfigure(
    0,
    weight=1
)

brain_frame.columnconfigure(
    1,
    weight=1
)


# ============================================================
# MEMORY
# ============================================================

memory_frame = ttk.LabelFrame(
    right_panel,
    text="💾 Brain Memory",
    padding=8
)

memory_frame.pack(
    fill="x",
    pady=(0, 8)
)

memory_status_label = ttk.Label(
    memory_frame,
    text="Memory: Not saved"
)

memory_status_label.pack(
    anchor="w"
)

memory_file_label = ttk.Label(
    memory_frame,
    text=(
        "File: memory.AI\n"
        "Last Save: Never"
    )
)

memory_file_label.pack(
    anchor="w"
)

memory_button_frame = ttk.Frame(memory_frame)
memory_button_frame.pack(
    fill="x",
    pady=(6, 0)
)

manual_save_button = ttk.Button(
    memory_button_frame,
    text="💾 Save Brain Now",
    command=manual_save_brain
)
manual_save_button.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(0, 3)
)

memory_test_button = ttk.Button(
    memory_button_frame,
    text="🧪 Test Save",
    command=test_memory_save
)
memory_test_button.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(3, 0)
)


# ============================================================
# STATS
# ============================================================

brain_stats_frame = ttk.LabelFrame(
    right_panel,
    text="📊 Brain Statistics",
    padding=8
)

brain_stats_frame.pack(
    fill="x",
    pady=(0, 8)
)

memory_states_label = ttk.Label(
    brain_stats_frame,
    text="Learned States: 0"
)

memory_states_label.pack(
    anchor="w"
)

learned_actions_label = ttk.Label(
    brain_stats_frame,
    text="Action Entries: 0"
)

learned_actions_label.pack(
    anchor="w"
)

decision_label = ttk.Label(
    brain_stats_frame,
    text="Decisions: 0"
)

decision_label.pack(
    anchor="w"
)

learning_label = ttk.Label(
    brain_stats_frame,
    text="Learning Events: 0"
)

learning_label.pack(
    anchor="w"
)

reward_label = ttk.Label(
    brain_stats_frame,
    text="Last Reward: +0.00"
)

reward_label.pack(
    anchor="w"
)

total_reward_label = ttk.Label(
    brain_stats_frame,
    text="Total Reward: +0.00"
)

total_reward_label.pack(
    anchor="w"
)


# ============================================================
# BRAIN LOG
# ============================================================

brain_log_frame = ttk.LabelFrame(
    right_panel,
    text="🧠 Brain Log",
    padding=5
)

brain_log_frame.pack(
    fill="x",
    pady=(0, 8)
)

brain_log_scroll = ttk.Scrollbar(
    brain_log_frame,
    orient="vertical"
)

brain_log_scroll.pack(
    side="right",
    fill="y"
)

brain_log_box = tk.Text(
    brain_log_frame,
    height=10,
    wrap="word",
    state="disabled",
    yscrollcommand=brain_log_scroll.set
)

brain_log_box.pack(
    side="left",
    fill="both",
    expand=True
)

brain_log_scroll.config(
    command=brain_log_box.yview
)


# ============================================================
# TEACH BRAIN
# ============================================================

reward_frame = ttk.LabelFrame(
    right_panel,
    text="⭐ Teach The Brain",
    padding=8
)

reward_frame.pack(
    fill="x",
    pady=(0, 8)
)

ttk.Label(
    reward_frame,
    text="Rate the brain's last action."
).pack(
    anchor="w",
    pady=(0, 5)
)

reward_good_button = ttk.Button(
    reward_frame,
    text="👍 Good (+1)",
    command=reward_good
)

reward_good_button.pack(
    side="left",
    padx=3
)

reward_bad_button = ttk.Button(
    reward_frame,
    text="👎 Bad (-1)",
    command=reward_bad
)

reward_bad_button.pack(
    side="left",
    padx=3
)

reward_neutral_button = ttk.Button(
    reward_frame,
    text="😐 Neutral (0)",
    command=reward_neutral
)

reward_neutral_button.pack(
    side="left",
    padx=3
)


# ============================================================
# VISION CONTROLS
# ============================================================

vision_controls_frame = ttk.LabelFrame(
    right_panel,
    text="👁️ Vision Controls",
    padding=8
)

vision_controls_frame.pack(
    fill="x",
    pady=(0, 8)
)

start_vision_button = ttk.Button(
    vision_controls_frame,
    text="▶ Start Vision",
    command=start_vision
)

start_vision_button.grid(
    row=0,
    column=0,
    padx=3,
    pady=3,
    sticky="ew"
)

stop_vision_button = ttk.Button(
    vision_controls_frame,
    text="⏹ Stop Vision",
    command=stop_vision,
    state="disabled"
)

stop_vision_button.grid(
    row=0,
    column=1,
    padx=3,
    pady=3,
    sticky="ew"
)

ocr_button = ttk.Button(
    vision_controls_frame,
    text="🔍 OCR: OFF",
    command=toggle_ocr
)

ocr_button.grid(
    row=1,
    column=0,
    columnspan=2,
    padx=3,
    pady=3,
    sticky="ew"
)

vision_controls_frame.columnconfigure(
    0,
    weight=1
)

vision_controls_frame.columnconfigure(
    1,
    weight=1
)


# ============================================================
# AI CONTROLS
# ============================================================

ai_controls_frame = ttk.LabelFrame(
    right_panel,
    text="🤖 AI Controls",
    padding=8
)

ai_controls_frame.pack(
    fill="x",
    pady=(0, 8)
)

ai_status_label = ttk.Label(
    ai_controls_frame,
    text="AI STATUS: ⚪ INACTIVE",
    style="Status.TLabel"
)

ai_status_label.grid(
    row=0,
    column=0,
    columnspan=3,
    sticky="w",
    pady=(0, 5)
)

ai_activate_button = ttk.Button(
    ai_controls_frame,
    text="▶ Activate AI",
    command=activate_ai
)

ai_activate_button.grid(
    row=1,
    column=0,
    padx=3,
    sticky="ew"
)

ai_deactivate_button = ttk.Button(
    ai_controls_frame,
    text="⏹ Deactivate",
    command=deactivate_ai,
    state="disabled"
)

ai_deactivate_button.grid(
    row=1,
    column=1,
    padx=3,
    sticky="ew"
)

emergency_button = ttk.Button(
    ai_controls_frame,
    text="🚨 EMERGENCY STOP",
    command=emergency_stop_ai
)

emergency_button.grid(
    row=1,
    column=2,
    padx=3,
    sticky="ew"
)

for column in range(3):

    ai_controls_frame.columnconfigure(
        column,
        weight=1
    )


# ============================================================
# RECORDING
# ============================================================

recording_frame = ttk.LabelFrame(
    right_panel,
    text="🎥 Recording",
    padding=8
)

recording_frame.pack(
    fill="x",
    pady=(0, 8)
)

recording_status_label = ttk.Label(
    recording_frame,
    text="Recording: ⚪"
)

recording_status_label.grid(
    row=0,
    column=0,
    sticky="w"
)

record_button = ttk.Button(
    recording_frame,
    text="🔴 Start Recording",
    command=toggle_recording
)

record_button.grid(
    row=0,
    column=1,
    padx=5
)

save_record_button = ttk.Button(
    recording_frame,
    text="💾 Save",
    command=save_recording
)

save_record_button.grid(
    row=0,
    column=2
)


# ============================================================
# ACTION
# ============================================================

action_frame = ttk.LabelFrame(
    right_panel,
    text="⚡ Current Action",
    padding=8
)

action_frame.pack(
    fill="x",
    pady=(0, 8)
)

action_label = ttk.Label(
    action_frame,
    text="Current Action: Idle"
)

action_label.pack(
    anchor="w"
)


# ============================================================
# KEYBOARD TEST
# ============================================================

keyboard_frame = ttk.LabelFrame(
    right_panel,
    text="⌨️ Keyboard Test",
    padding=8
)

keyboard_frame.pack(
    fill="x",
    pady=(0, 8)
)

test_w_button = ttk.Button(
    keyboard_frame,
    text="W",
    command=test_w
)

test_w_button.grid(
    row=0,
    column=0,
    padx=3
)

test_space_button = ttk.Button(
    keyboard_frame,
    text="SPACE",
    command=test_space
)

test_space_button.grid(
    row=0,
    column=1,
    padx=3
)

test_left_button = ttk.Button(
    keyboard_frame,
    text="←",
    command=test_left
)

test_left_button.grid(
    row=0,
    column=2,
    padx=3
)

test_right_button = ttk.Button(
    keyboard_frame,
    text="→",
    command=test_right
)

test_right_button.grid(
    row=0,
    column=3,
    padx=3
)


# ============================================================
# MOUSE
# ============================================================

mouse_frame = ttk.LabelFrame(
    right_panel,
    text="🖱️ Mouse",
    padding=8
)

mouse_frame.pack(
    fill="x",
    pady=(0, 8)
)

mouse_move_button = ttk.Button(
    mouse_frame,
    text="Move Mouse",
    command=lambda:
        move_mouse(
            screen_width // 2,
            screen_height // 2
        )
)

mouse_move_button.pack(
    side="left",
    padx=3
)

mouse_click_button = ttk.Button(
    mouse_frame,
    text="Click",
    command=click_mouse
)

mouse_click_button.pack(
    side="left",
    padx=3
)


# ============================================================
# VISION TEST
# ============================================================

hello_frame = ttk.LabelFrame(
    right_panel,
    text="🧪 Vision Test",
    padding=8
)

hello_frame.pack(
    fill="x",
    pady=(0, 8)
)

hello_button = ttk.Button(
    hello_frame,
    text='👋 Type "hello!" into Notepad',
    command=say_hello
)

hello_button.pack(
    fill="x"
)

hello_status_label = ttk.Label(
    hello_frame,
    text="Test Result: —"
)

hello_status_label.pack(
    anchor="w",
    pady=(5, 0)
)


# ============================================================
# SYSTEM LOG
# ============================================================

system_frame = ttk.LabelFrame(
    root,
    text="🖥️ System Log",
    padding=5
)

system_frame.pack(
    fill="x",
    padx=10,
    pady=(0, 10)
)

system_scroll = ttk.Scrollbar(
    system_frame,
    orient="vertical"
)

system_scroll.pack(
    side="right",
    fill="y"
)

system_log_box = tk.Text(
    system_frame,
    height=5,
    wrap="word",
    state="disabled",
    yscrollcommand=system_scroll.set
)

system_log_box.pack(
    side="left",
    fill="both",
    expand=True
)

system_scroll.config(
    command=system_log_box.yview
)


# ============================================================
# INITIALIZE BRAIN
# ============================================================

load_brain()

brain_log(f"🧠 Brain initialized with {len(brain_memory)} states")
update_memory_display()


# ============================================================
# STARTUP INFORMATION
# ============================================================

system_log(
    f"🚀 Universal Game AI v{VERSION}"
)

system_log(
    "👁️ Vision → 🧠 Brain → 🎮 Action"
)

system_log(
    "💾 Persistent memory enabled"
)

if VOICE_AVAILABLE:
    system_log("🎙️ Voice subsystem ready (sounddevice — no PyAudio)")
else:
    system_log("⚠️ Voice subsystem unavailable")

system_log(
    f"💾 Memory path: {MEMORY_FILE}"
)

if os.path.exists(
    TESSERACT_PATH
):

    system_log(
        "✅ Tesseract detected"
    )

else:

    system_log(
        "⚠️ Tesseract executable not found"
    )


# ============================================================
# BACKGROUND MEMORY SAVER
# ============================================================

threading.Thread(
    target=memory_save_loop,
    daemon=True
).start()


# ============================================================
# UI UPDATE LOOPS
# ============================================================

root.after(
    30,
    process_ui_queue
)

root.after(
    100,
    update_perception
)

root.after(
    100,
    update_brain_stats
)

root.after(
    500,
    update_memory_display
)


# F9 is an independent emergency hook. It is registered separately from
# the F8 master toggle so a broken/stuck AI loop cannot disable the stop key.
def _global_emergency_hotkey():
    try:
        emergency_stop_ai()
    except Exception as error:
        system_log(f"🚨 Emergency hotkey error: {error}")

try:
    keyboard.add_hotkey("f8", activate_ai, suppress=False, trigger_on_release=False)
    system_log("⌨️ F8 global AI start hotkey ready")
except Exception as error:
    system_log(f"⚠️ Could not register F8: {error}")

try:
    keyboard.add_hotkey("f9", _global_emergency_hotkey, suppress=False, trigger_on_release=False)
    system_log("🚨 F9 emergency stop hotkey ready")
except Exception as error:
    system_log(f"⚠️ Could not register F9 emergency stop: {error}")


# ============================================================
# RUN
# ============================================================

root.mainloop()