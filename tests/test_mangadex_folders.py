import os

from default_settings import DEFAULT_SETTINGS
from download_from_mangadex import (
    CHAPTER_FOLDER_NAME_WITH_TITLE,
    get_additional_terminal_options,
    get_download_folder,
    get_tidy_chapter_folder_name,
    tidy_chapter_folder_names,
)
from tests.fake_gui import FakeClientStorage


def get_storage(**settings):
    storage = FakeClientStorage()
    storage.values.update(DEFAULT_SETTINGS)
    storage.values.update(settings)
    return storage


def test_chapter_titles_are_in_the_chapter_folder_names_by_default():
    options = get_additional_terminal_options(get_storage())

    assert options[options.index("--filename-chapter") + 1] == "{chapter.simple_name} - {chapter.title}"
    assert CHAPTER_FOLDER_NAME_WITH_TITLE == "{chapter.simple_name} - {chapter.title}"


def test_chapter_titles_can_be_left_out_of_the_folder_names():
    options = get_additional_terminal_options(get_storage(use_chapter_title=False))

    assert "--filename-chapter" not in options


def test_each_manga_gets_its_own_folder_in_the_output_folder():
    assert get_download_folder("/Users/me/Panelyze/MangaDex Downloads") == os.path.join(
        "/Users/me/Panelyze/MangaDex Downloads", "{manga.title}"
    )


def test_braces_in_the_output_folder_are_not_mistaken_for_placeholders():
    assert get_download_folder("/Users/me/{odd}") == os.path.join("/Users/me/{{odd}}", "{manga.title}")


def test_a_dash_with_no_title_after_it_is_dropped():
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3 - ") == "Vol. 1 Ch. 3"
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3 -") == "Vol. 1 Ch. 3"
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3 - Boss and The Panda") == "Vol. 1 Ch. 3 - Boss and The Panda"
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3") == "Vol. 1 Ch. 3"


def test_titleless_chapter_folders_are_renamed_and_the_others_are_left_alone(tmp_path):
    manga = tmp_path / "Some Manga"
    for name in ["Vol. 1 Ch. 1 - ", "Vol. 1 Ch. 2 - A Title", "Vol. 1 Ch. 3"]:
        (manga / name).mkdir(parents=True)

    tidy_chapter_folder_names(str(tmp_path))

    assert sorted(os.listdir(manga)) == ["Vol. 1 Ch. 1", "Vol. 1 Ch. 2 - A Title", "Vol. 1 Ch. 3"]


def test_a_folder_is_not_renamed_over_one_that_already_exists(tmp_path):
    manga = tmp_path / "Some Manga"
    (manga / "Vol. 1 Ch. 1 - ").mkdir(parents=True)
    (manga / "Vol. 1 Ch. 1").mkdir()

    tidy_chapter_folder_names(str(tmp_path))

    assert sorted(os.listdir(manga)) == ["Vol. 1 Ch. 1", "Vol. 1 Ch. 1 - "]


def test_tidying_a_missing_output_folder_does_nothing(tmp_path):
    tidy_chapter_folder_names(str(tmp_path / "missing"))
