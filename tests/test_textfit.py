from babel86 import textfit


def mono(s: str) -> float:
    """10 px per character, for predictable wrapping."""
    return 10 * len(s)


def test_wraps_on_spaces():
    assert textfit.wrap("aaa bbb ccc", mono, 70) == ["aaa bbb", "ccc"]


def test_short_text_is_one_line_and_empty_text_is_one_empty_line():
    assert textfit.wrap("hello", mono, 100) == ["hello"]
    assert textfit.wrap("", mono, 100) == [""]


def test_long_unspaced_runs_are_split_by_cluster():
    lines = textfit.wrap("abcdefghij", mono, 40)
    assert lines == ["abcd", "efgh", "ij"]


def test_combining_marks_stay_with_their_base():
    khmer = "ក្រ"  # KA + COENG + RO: one cluster
    assert textfit.clusters(khmer) == [khmer]
    e_acute = "e\u0301x"
    assert textfit.clusters(e_acute) == ["e\u0301", "x"]
    thai = "\u0e01\u0e34\u0e49"  # KO KAI + SARA I + MAI THO
    assert textfit.clusters(thai) == [thai]


def test_wrapping_never_splits_a_khmer_cluster():
    word = "ក្រ" * 5
    for line in textfit.wrap(word, lambda s: 10 * len(textfit.clusters(s)), 20):
        assert len(textfit.clusters(line)) <= 2
        assert line.count("\u17d2") == len(textfit.clusters(line))


def test_keeps_the_newest_two_lines_and_marks_the_trim():
    text = "one two three four five six"
    lines = textfit.newest_lines(text, mono, 80)
    assert len(lines) == 2
    assert lines[-1] == "five six"
    assert lines[0].startswith(textfit.ELLIPSIS)
    assert mono(lines[0]) <= 80


def test_text_that_fits_in_two_lines_is_untouched():
    assert textfit.newest_lines("aa bb cc", mono, 50) == ["aa bb", "cc"]
    assert textfit.newest_lines("", mono, 50) == []


def test_ellipsize_trims_the_end():
    assert textfit.ellipsize("short", mono, 100) == "short"
    out = textfit.ellipsize("a long label here", mono, 80)
    assert out.endswith(textfit.ELLIPSIS)
    assert mono(out) <= 80
