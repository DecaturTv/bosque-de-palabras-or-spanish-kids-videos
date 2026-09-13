from pathlib import Path

import pytest

from bosque.schema import Lesson, load_lesson, load_lesson_library

REPO_ROOT = Path(__file__).resolve().parents[1]
LESSONS_DIR = REPO_ROOT / "lessons"


def test_colors_lesson_loads():
    lesson = load_lesson(LESSONS_DIR / "beginner" / "02_colors.yaml")
    assert lesson.lesson_id == "beginner_02_colors"
    assert len(lesson.vocab) == 5


def test_greetings_lesson_loads():
    lesson = load_lesson(LESSONS_DIR / "beginner" / "01_greetings.yaml")
    assert lesson.spaced_repetition.recycle_vocab_ids == []


def test_library_cross_validates_spaced_repetition():
    lessons = load_lesson_library(LESSONS_DIR)
    assert "beginner_01_greetings" in lessons
    assert "beginner_02_colors" in lessons


def test_beginner_tier_rejects_too_many_vocab(tmp_path):
    lesson_dict = _base_lesson_dict()
    lesson_dict["vocab"] += [_vocab_item(f"w{i}") for i in range(4)]  # 5 + 4 = 9, over the cap of 8
    lesson_path = tmp_path / "bad.yaml"
    _write_yaml(lesson_path, lesson_dict)
    with pytest.raises(ValueError, match="requires 5-8 new vocab"):
        load_lesson(lesson_path)


def test_beginner_tier_requires_phonetic_hints(tmp_path):
    lesson_dict = _base_lesson_dict()
    lesson_dict["vocab"][0]["phonetic_hint"] = None
    lesson_path = tmp_path / "bad.yaml"
    _write_yaml(lesson_path, lesson_dict)
    with pytest.raises(ValueError, match="requires phonetic_hint"):
        load_lesson(lesson_path)


def test_quiz_answer_must_be_an_option():
    with pytest.raises(Exception):
        Lesson.model_validate(
            {**_base_lesson_dict(), "quiz": [{
                "type": "multiple_choice",
                "prompt_es": "?",
                "options": ["a", "b"],
                "correct": "c",
                "reward_animation": "yellow_starburst",
            }]}
        )


def _vocab_item(vid: str) -> dict:
    return {
        "id": vid,
        "spanish": vid,
        "english": vid,
        "phonetic_hint": "hint",
        "image_asset": "assets/icons/x.svg",
        "audio_cue": "chime_soft",
        "example_sentence_es": "x",
        "example_sentence_en": "x",
    }


def _base_lesson_dict() -> dict:
    vocab = [_vocab_item(f"v{i}") for i in range(5)]
    return {
        "lesson_id": "test_lesson",
        "tier": "beginner",
        "order": 1,
        "topic": "Test",
        "clearing": "Test Clearing",
        "duration_target_seconds": 120,
        "intro": {
            "hook_line_es": "x",
            "hook_line_en": "x",
            "topic_tease_es": "x",
            "topic_tease_en": "x",
        },
        "vocab": vocab,
        "spaced_repetition": {"recycle_vocab_ids": []},
        "song": {
            "template": "four_line_intro_plus_refrain",
            "bpm": 90,
            "verses": [{
                "lines": [{"es": "x", "vocab_id": "v0", "match_object_asset": "x.svg"}],
                "refrain_es": "x",
            }],
            "final_chorus": {"flash_all_objects": True},
        },
        "quiz": [{
            "type": "multiple_choice",
            "prompt_es": "x",
            "options": ["v0", "v1"],
            "correct": "v0",
            "reward_animation": "yellow_starburst",
        }],
        "recap": {"summary_line_es": "x", "summary_line_en": "x", "vocab_ids": ["v0"]},
        "tts": {"rate": "slow", "voice": "es-ES-standard"},
        "visuals": {"background": "x.png", "palette": "default"},
    }


def _write_yaml(path: Path, data: dict) -> None:
    import yaml

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
