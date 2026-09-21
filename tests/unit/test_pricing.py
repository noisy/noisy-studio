from noisy_studio.listener import pricing


def test_stt_cost_is_ten_cents_per_audio_hour():
    assert pricing.stt_cost_usd(3600) == 0.10


def test_tts_cost_is_four_twenty_per_million_chars():
    assert pricing.tts_cost_usd(1_000_000) == 4.20
