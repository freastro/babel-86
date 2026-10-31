from babel86 import languages


def test_every_entry_has_a_unique_tag_and_a_two_letter_code():
    tags = [lang.tag for lang in languages.CATALOGUE]
    assert len(tags) == len(set(tags))
    assert tags == sorted(tags, key=str.lower)
    for lang in languages.CATALOGUE:
        assert len(lang.code2) == 2 and lang.code2.isupper(), lang
        assert lang.native


def test_gemini_speaks_seventy_plus_and_qwen_a_subset():
    gemini = {lang.tag for lang in languages.for_model("gemini")}
    qwen = {lang.tag for lang in languages.for_model("qwen")}
    assert len(gemini) >= 70
    assert qwen <= gemini
    # 29 spoken languages; Portuguese appears once, as pt-BR.
    assert len(qwen) == 29


def test_pass_thru_supports_every_language():
    assert languages.for_model("pass") == list(languages.CATALOGUE)
    assert all(languages.supports("pass", lang.tag) for lang in languages.CATALOGUE)


def test_supports_and_lookup():
    assert languages.supports("qwen", "ja")
    assert not languages.supports("qwen", "sw")
    assert not languages.supports("gemini", "xx")
    assert languages.by_tag("fr").native == "Français"
    assert languages.code_of("zh-Hant") == "ZH"
    assert languages.code_of("xx-YY") == "XX"  # unknown tags still get a code


def test_next_free_prefers_the_common_languages_then_the_catalogue():
    assert languages.next_free("gemini", set()).tag == "es"
    assert languages.next_free("gemini", {"es", "fr"}).tag == "de"
    used = set(languages.PREFERRED)
    assert languages.next_free("qwen", used).tag == "ar"
    everything = {lang.tag for lang in languages.CATALOGUE}
    assert languages.next_free("gemini", everything).tag == "es"  # nothing free: first one
