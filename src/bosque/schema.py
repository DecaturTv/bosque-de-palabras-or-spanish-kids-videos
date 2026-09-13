"""Pydantic models + validation for lesson config YAML files.

A lesson is valid syntax (parses as YAML) but may still violate the
pedagogical/style rules in the spec (e.g. too many new words for a
beginner video). Loading via `load_lesson` / `load_lesson_library`
catches both.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

STYLE_PATH = Path(__file__).resolve().parents[2] / "config" / "style.yaml"


class Tier(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class TTSRate(str, Enum):
    slow = "slow"
    natural = "natural"


class VocabItem(BaseModel):
    id: str
    spanish: str
    english: str
    phonetic_hint: str | None = None
    image_asset: str
    audio_cue: str
    example_sentence_es: str
    example_sentence_en: str


class Intro(BaseModel):
    hook_line_es: str
    hook_line_en: str
    topic_tease_es: str
    topic_tease_en: str


class SpacedRepetition(BaseModel):
    recycle_vocab_ids: list[str] = Field(default_factory=list)


class SongLine(BaseModel):
    es: str
    vocab_id: str
    match_object_asset: str


class SongVerse(BaseModel):
    lines: list[SongLine]
    refrain_es: str


class FinalChorus(BaseModel):
    flash_all_objects: bool = True


class Song(BaseModel):
    template: str
    bpm: int
    verses: list[SongVerse]
    final_chorus: FinalChorus


class QuizQuestion(BaseModel):
    type: str
    prompt_es: str
    options: list[str]
    correct: str
    reward_animation: str

    @model_validator(mode="after")
    def correct_is_an_option(self) -> "QuizQuestion":
        if self.correct not in self.options:
            raise ValueError(
                f"quiz answer '{self.correct}' is not among options {self.options}"
            )
        return self


class Recap(BaseModel):
    summary_line_es: str
    summary_line_en: str
    vocab_ids: list[str]


class TTSConfig(BaseModel):
    rate: TTSRate
    voice: str


class Visuals(BaseModel):
    background: str
    palette: str = "default"


class Lesson(BaseModel):
    lesson_id: str
    tier: Tier
    order: int
    topic: str
    clearing: str
    duration_target_seconds: int

    intro: Intro
    vocab: list[VocabItem]
    spaced_repetition: SpacedRepetition
    song: Song
    quiz: list[QuizQuestion]
    recap: Recap
    tts: TTSConfig
    visuals: Visuals

    @model_validator(mode="after")
    def vocab_ids_are_unique(self) -> "Lesson":
        ids = [v.id for v in self.vocab]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate vocab ids: {dupes}")
        return self

    @model_validator(mode="after")
    def song_and_recap_reference_real_vocab(self) -> "Lesson":
        known = {v.id for v in self.vocab}
        for verse in self.song.verses:
            for line in verse.lines:
                if line.vocab_id not in known:
                    raise ValueError(
                        f"song line references unknown vocab_id '{line.vocab_id}'"
                    )
        unknown_recap = [v for v in self.recap.vocab_ids if v not in known]
        if unknown_recap:
            raise ValueError(f"recap references unknown vocab ids: {unknown_recap}")
        return self


def _load_style() -> dict:
    with open(STYLE_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_lesson(path: str | Path) -> Lesson:
    """Parse + validate a single lesson file against the schema and
    the tier-specific pedagogical rules in config/style.yaml.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    lesson = Lesson.model_validate(raw)

    style = _load_style()
    tier_rules = style["tiers"][lesson.tier.value]

    vocab_count = len(lesson.vocab)
    lo, hi = tier_rules["vocab_per_video_min"], tier_rules["vocab_per_video_max"]
    if not (lo <= vocab_count <= hi):
        raise ValueError(
            f"{path}: {lesson.tier.value} tier requires {lo}-{hi} new vocab words, "
            f"got {vocab_count}"
        )

    if tier_rules["requires_phonetic_hints"]:
        missing = [v.id for v in lesson.vocab if not v.phonetic_hint]
        if missing:
            raise ValueError(
                f"{path}: {lesson.tier.value} tier requires phonetic_hint on every "
                f"vocab item, missing on: {missing}"
            )

    expected_rate = TTSRate(style["tts"]["rate_by_tier"][lesson.tier.value])
    if lesson.tts.rate != expected_rate:
        raise ValueError(
            f"{path}: {lesson.tier.value} tier expects tts.rate='{expected_rate.value}', "
            f"got '{lesson.tts.rate.value}'"
        )

    return lesson


def load_lesson_library(lessons_dir: str | Path) -> dict[str, Lesson]:
    """Load every lesson under lessons_dir and cross-validate
    spaced-repetition references against earlier-order lessons in the
    same tier.
    """
    lessons_dir = Path(lessons_dir)
    lessons: dict[str, Lesson] = {}
    for path in sorted(lessons_dir.glob("*/*.yaml")):
        lesson = load_lesson(path)
        if lesson.lesson_id in lessons:
            raise ValueError(f"duplicate lesson_id '{lesson.lesson_id}' at {path}")
        lessons[lesson.lesson_id] = lesson

    vocab_by_tier_and_order: dict[Tier, list[tuple[int, set[str]]]] = {t: [] for t in Tier}
    for lesson in lessons.values():
        vocab_by_tier_and_order[lesson.tier].append(
            (lesson.order, {v.id for v in lesson.vocab})
        )

    for lesson in lessons.values():
        available = {
            vid
            for order, ids in vocab_by_tier_and_order[lesson.tier]
            if order < lesson.order
            for vid in ids
        }
        unknown = [v for v in lesson.spaced_repetition.recycle_vocab_ids if v not in available]
        if unknown:
            raise ValueError(
                f"{lesson.lesson_id}: spaced_repetition references vocab not taught "
                f"in an earlier lesson: {unknown}"
            )

    return lessons
