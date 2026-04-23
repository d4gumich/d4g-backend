from src.summary.service import combine_all_metadata_into_input


def test_combine_all_metadata_into_input():
    sentences = ["High winds", "Heavy rain"]
    themes = ["Weather"]
    locations = [{"country": "USA"}]
    disasters = ["Hurricane"]

    combined = combine_all_metadata_into_input(sentences, themes, locations, disasters)

    assert "High winds" in combined
    assert "Weather" in combined
    assert "USA" in combined
    assert "Hurricane" in combined
