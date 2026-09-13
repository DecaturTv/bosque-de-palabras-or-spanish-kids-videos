"""Orchestrates one lesson config into one rendered .mp4.

Scene order follows the spec's per-video structure:
intro hook -> new vocab -> repetition song -> quiz -> recap.
"""
from __future__ import annotations

from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip, VideoClip, concatenate_audioclips, concatenate_videoclips

from bosque import audio_fx
from bosque.schema import Lesson, load_lesson
from bosque.song import build_song_clips
from bosque.style import load_style
from bosque.tts import synth
from bosque.visuals import (
    FPS,
    background_frame,
    draw_chispa,
    pop_in_clip,
    quiz_frame,
    static_clip,
    text_card_frame,
    vocab_card_frame,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _line_clip(bg, phase: float, lines_es: list[str], line_en: str | None, text: str, rate: str) -> VideoClip:
    frame = text_card_frame(draw_chispa(bg, phase), lines_es, line_en)
    audio = AudioFileClip(str(synth(text, rate=rate)))
    return static_clip(frame, audio.duration).with_audio(audio)


def _build_intro(lesson: Lesson, bg) -> list[VideoClip]:
    style = load_style()
    catchphrase = style["mascot"]["catchphrase_es"]
    rate = lesson.tts.rate.value
    return [
        _line_clip(bg, 0.0, [catchphrase], None, catchphrase, rate),
        _line_clip(bg, 0.5, [lesson.intro.hook_line_es], lesson.intro.hook_line_en, lesson.intro.hook_line_es, rate),
        _line_clip(
            bg, 1.0, [lesson.intro.topic_tease_es], lesson.intro.topic_tease_en, lesson.intro.topic_tease_es, rate
        ),
    ]


def _build_vocab_scene(lesson: Lesson, bg) -> list[VideoClip]:
    rate = lesson.tts.rate.value
    clips: list[VideoClip] = []
    for i, vocab in enumerate(lesson.vocab):
        bg_with_chispa = draw_chispa(bg, bounce_phase=i * 0.7)
        card_frame = vocab_card_frame(bg_with_chispa, vocab.spanish, vocab.english, vocab.phonetic_hint, i)

        word_audio = AudioFileClip(str(synth(vocab.spanish, rate=rate)))
        chime_audio = audio_fx.chime()
        pop_audio = concatenate_audioclips([chime_audio, word_audio])
        pop_clip = pop_in_clip(card_frame, duration=pop_audio.duration, pop_duration=chime_audio.duration)
        clips.append(pop_clip.with_audio(pop_audio))

        example_audio = AudioFileClip(str(synth(vocab.example_sentence_es, rate=rate)))
        clips.append(static_clip(card_frame, example_audio.duration).with_audio(example_audio))
    return clips


def _build_quiz_scene(lesson: Lesson, bg) -> list[VideoClip]:
    rate = lesson.tts.rate.value
    clips: list[VideoClip] = []
    for i, q in enumerate(lesson.quiz):
        bg_with_chispa = draw_chispa(bg, bounce_phase=i * 0.9)
        prompt_frame = quiz_frame(bg_with_chispa, q.prompt_es, q.options, correct=q.correct, reveal=False)
        prompt_audio = AudioFileClip(str(synth(q.prompt_es, rate=rate)))
        clips.append(static_clip(prompt_frame, prompt_audio.duration).with_audio(prompt_audio))

        reveal_frame = quiz_frame(bg_with_chispa, q.prompt_es, q.options, correct=q.correct, reveal=True)
        reveal_audio = audio_fx.starburst()
        clips.append(static_clip(reveal_frame, reveal_audio.duration).with_audio(reveal_audio))
    return clips


def _build_recap(lesson: Lesson, bg) -> list[VideoClip]:
    rate = lesson.tts.rate.value
    return [
        _line_clip(
            bg, 0.0, [lesson.recap.summary_line_es], lesson.recap.summary_line_en, lesson.recap.summary_line_es, rate
        )
    ]


def render_lesson(lesson: Lesson, output_dir: Path | None = None) -> Path:
    bg = background_frame(lesson.tier.value, lesson.clearing, lesson.visuals.background)

    scenes: list[VideoClip] = []
    scenes += _build_intro(lesson, bg)
    scenes += _build_vocab_scene(lesson, bg)
    scenes += build_song_clips(lesson, lesson.song)
    scenes += _build_quiz_scene(lesson, bg)
    scenes += _build_recap(lesson, bg)

    video = concatenate_videoclips(scenes, method="compose").with_fps(FPS)

    bed = audio_fx.music_bed(lesson.tier.value, video.duration)
    mixed_audio = CompositeAudioClip([video.audio, bed])
    video = video.with_audio(mixed_audio)

    output_dir = Path(output_dir) if output_dir else REPO_ROOT / "output" / lesson.tier.value
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{lesson.lesson_id}.mp4"
    video.write_videofile(str(out_path), fps=FPS, codec="libx264", audio_codec="aac")
    return out_path


def render_lesson_file(path: str | Path, output_dir: Path | None = None) -> Path:
    lesson = load_lesson(path)
    return render_lesson(lesson, output_dir)
