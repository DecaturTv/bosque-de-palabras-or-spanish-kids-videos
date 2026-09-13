"""Renders a Song (verses + refrain, from a lesson config) into a
sequence of timed clips: each line and each refrain becomes one
spoken-chant segment (TTS) synced to its matched-object flash, per
the shared `four_line_intro_plus_refrain` template every tier reuses.
"""
from __future__ import annotations

import numpy as np
from moviepy import AudioFileClip, VideoClip

from bosque.schema import Lesson, Song
from bosque.tts import synth
from bosque.visuals import FPS, all_objects_flash_frame, background_frame, draw_chispa, flash_object_frame


def _static_with_audio(frame_image, audio_path) -> VideoClip:
    audio = AudioFileClip(str(audio_path))
    arr = np.array(frame_image.convert("RGB"))
    video = VideoClip(lambda t: arr, duration=audio.duration).with_fps(FPS)
    return video.with_audio(audio)


def build_song_clips(lesson: Lesson, song: Song) -> list[VideoClip]:
    bg = background_frame(lesson.tier.value, lesson.clearing, lesson.visuals.background)
    vocab_by_id = {v.id: v for v in lesson.vocab}
    clips: list[VideoClip] = []

    for verse in song.verses:
        for i, line in enumerate(verse.lines):
            vocab = vocab_by_id[line.vocab_id]
            frame = draw_chispa(flash_object_frame(bg, vocab.spanish, color_index=i), bounce_phase=0.0)
            audio_path = synth(line.es, rate=lesson.tts.rate.value)
            clips.append(_static_with_audio(frame, audio_path))

        refrain_frame = draw_chispa(bg, bounce_phase=1.0)
        refrain_audio_path = synth(verse.refrain_es, rate=lesson.tts.rate.value)
        clips.append(_static_with_audio(refrain_frame, refrain_audio_path))

    if song.final_chorus.flash_all_objects:
        all_ids = [line.vocab_id for verse in song.verses for line in verse.lines]
        labels = [vocab_by_id[vid].spanish for vid in all_ids]
        frame = draw_chispa(all_objects_flash_frame(bg, labels), bounce_phase=2.0)
        audio_path = synth(song.verses[-1].refrain_es, rate=lesson.tts.rate.value)
        clips.append(_static_with_audio(frame, audio_path))

    return clips
