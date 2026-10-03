from app.services.llm_service import parse_analysis, clean_instructions
from app.config import Settings


def test_parses_json():
    a = parse_analysis('{"summary": "Good quarter.", "sentiment": "Bullish", "key_points": ["a", " ", "b"], '
                       '"risks": ["r"], "changes": "Price up."}')
    assert a.summary == "Good quarter."
    assert a.sentiment == "bullish"
    assert a.key_points == ["a", "b"]
    assert a.risks == ["r"]
    assert a.changes == "Price up."


def test_parses_json_inside_fences_and_after_thinking():
    text = '<think>hmm {not json}</think>\n```json\n{"summary": "S", "sentiment": "mixed", "changes": null}\n```'
    a = parse_analysis(text)
    assert (a.summary, a.sentiment, a.changes) == ("S", "mixed", None)


def test_unknown_sentiment_becomes_neutral_and_lists_are_capped():
    a = parse_analysis('{"summary": "S", "sentiment": "very good", "key_points": ["1","2","3","4","5"]}')
    assert a.sentiment == "neutral"
    assert len(a.key_points) == 4


def test_falls_back_to_old_text_format():
    a = parse_analysis("SUMMARY:\nRevenue grew.\n\nSENTIMENT: bearish")
    assert (a.summary, a.sentiment) == ("Revenue grew.", "bearish")


def test_plain_text_is_kept_as_summary():
    assert parse_analysis("Just prose.").summary == "Just prose."


def test_unusable_reply_is_none():
    assert parse_analysis("") is None
    assert parse_analysis('{"sentiment": "bullish"}') is None


def test_old_saved_instructions_lose_their_format_section():
    old = (
        "Based on the information above, provide a summary.\n\n"
        "Format your response EXACTLY as follows:\n\nSUMMARY:\n[...]\n\nSENTIMENT: [one word]"
    )
    assert clean_instructions(old) == "Based on the information above, provide a summary."
    assert clean_instructions("Focus on cash flow.") == "Focus on cash flow."
    assert clean_instructions("  ") is None
    assert "SUMMARY:" not in Settings().ai_prompt_instructions
