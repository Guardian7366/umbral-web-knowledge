"""Umbrely configuration and presentation events."""
import json
import os
import re
from pathlib import Path

from src.web.chatbot_view import HISTORY_KEY, REVISION_KEY


ASSETS = Path(__file__).resolve().parents[2] / "static" / "umbrely-local"
OPERATION = "umbrely_operation"
JOB = "umbrely_answer_job"
CLIPS = {
    "welcome": "activeAtlas", "processing": "activeAtlas", "answerFound": "activeAtlas",
    "sourceDiscovered": "expressionAtlas", "insufficientInformation": "expressionAtlas",
    "recoverableError": "expressionAtlas",
}


def validate_manifest(manifest):
    if manifest["version"] != "P06.5.2.1" or manifest["frameSize"] != {"width": 64, "height": 64}:
        raise ValueError("Invalid Umbrely version or frame size")
    assets, states = manifest["assets"], manifest["states"]
    if (set(assets) != {"neutral", "activeAtlas", "expressionAtlas"}
            or set(states) != {"ready", *CLIPS} or manifest["initialAsset"] != "neutral"
            or states["ready"]["image"] != "neutral" or states["ready"]["playback"] != "static"
            or manifest["controls"]["reducedMotion"]["image"] != "neutral"):
        raise ValueError("Invalid Umbrely runtime pack")
    for key, asset in assets.items():
        width, height = asset["width"], asset["height"]
        if (not re.fullmatch(r"umbrely-[a-z]+\.png", asset["path"]) or width <= 0 or height <= 0
                or width % 64 or height % 64 or (key == "neutral" and (width, height) != (64, 64))):
            raise ValueError("Invalid image dimensions or path")
        if key != "neutral" and (asset["columns"] != width // 64 or not 0 < asset["tiles"] <= width * height // 4096):
            raise ValueError("Invalid atlas grid")
    for key, atlas in CLIPS.items():
        clip = states[key]
        frames = clip["frames"]
        if (clip["atlas"] != atlas or not frames or clip["next"] != "ready"
                or clip["playback"] != ("while-processing" if key == "processing" else "once")
                or clip["repetitions"] != ("while-active" if key == "processing" else 1)
                or any(type(f["tile"]) is not int or not 0 <= f["tile"] < assets[atlas]["tiles"]
                       or type(f["ms"]) is not int or f["ms"] <= 0 for f in frames)
                or sum(f["ms"] for f in frames) != clip["totalMs"]):
            raise ValueError("Invalid frame sequence")
    return manifest


def local_manifest():
    if os.environ.get("UMBRAL_UMBRELY_LOCAL", "1") != "1":
        return None
    try:
        config = validate_manifest(json.loads((ASSETS / "umbrely-manifest.json").read_text(encoding="utf-8")))
        return config if (ASSETS / config["assets"]["neutral"]["path"]).is_file() else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def operation_event(state):
    operation = state.get(OPERATION)
    if not operation or operation["id"] != state[REVISION_KEY]:
        return None
    answer = state[HISTORY_KEY][2 * operation["turn"] + 1]
    response = answer.get("response")
    if answer["status"] == "processing":
        phase = "processing"
    elif answer["status"] == "error":
        phase = "recoverableError"
    else:
        phase = "answerFound" if response and response.answered and response.sources else "insufficientInformation"
    return {**operation, "phase": phase}


def schedule_answer(state, question, answer):
    turn = next(index for index, reply in enumerate(state[HISTORY_KEY][1::2]) if reply is answer)
    state[OPERATION] = {"id": state[REVISION_KEY], "turn": turn}
    state[JOB] = (question, answer)
