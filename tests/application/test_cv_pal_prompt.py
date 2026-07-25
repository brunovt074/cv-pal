from cvpal.application.prompts.cv_pal import cv_pal_prompt
from cvpal.domain.knowledge.voice import VoiceProfile


def test_prompt_contains_material_language_and_posting():
    prompt = cv_pal_prompt("MATERIAL_MARKER", "POSTING_MARKER", "es", voice_profile=None)
    assert "MATERIAL_MARKER" in prompt
    assert "POSTING_MARKER" in prompt
    assert "Write in es" in prompt


def test_prompt_instructs_printing_the_cv_in_the_conversation():
    prompt = cv_pal_prompt("material", "posting", "en", voice_profile=None)
    assert "PRINT" in prompt


def test_prompt_without_voice_profile_asks_for_tone_or_essence():
    prompt = cv_pal_prompt("material", "posting", "en", voice_profile=None)
    assert "No voice profile has been captured" in prompt
    assert "tone" in prompt.lower()


def test_prompt_with_voice_profile_confirms_captured_essence():
    voice = VoiceProfile(opening_style="Direct enthusiasm", tone_summary=["direct", "technical"])
    prompt = cv_pal_prompt("material", "posting", "en", voice_profile=voice)
    assert "A voice profile IS already captured" in prompt
    assert "direct, technical" in prompt
    assert "Direct enthusiasm" in prompt
    assert "No voice profile has been captured" not in prompt


def test_prompt_never_allows_fabrication():
    prompt = cv_pal_prompt("material", "posting", "en", voice_profile=None)
    assert "Never invent" in prompt
