import os
import time
from types import SimpleNamespace

import pytest
import requests

import download_from_mangadex
from default_settings import DEFAULT_SETTINGS
from download_from_mangadex import (
    CHAPTER_FOLDER_NAME_WITH_TITLE,
    get_additional_terminal_options,
    get_chapter_folders,
    get_download_folder,
    get_reading_direction_from_manga,
    get_reading_direction_from_mangadex,
    get_tidy_chapter_folder_name,
    save_reading_direction,
    tidy_chapter_folder_names,
)
from utils import READING_DIRECTION_FILE_NAME
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


MANGA_ID = "a1c7c817-4e59-43b7-9365-09675a149a6f"
CHAPTER_ID = "0b2b5c3a-1111-4222-8333-944455556666"


def get_manga_attributes(original_language, *format_tags):
    return {
        "originalLanguage": original_language,
        "tags": [{"attributes": {"name": {"en": tag}, "group": "format"}} for tag in format_tags],
    }


@pytest.mark.parametrize(
    "original_language, format_tags, reading_direction",
    [
        ("ja", [], "rtl"),
        ("ar", [], "rtl"),
        ("zh", [], "ltr"),
        ("en", ["Full Color"], "ltr"),
        ("ja", ["Long Strip"], "webtoon"),
        ("ko", ["Long Strip", "4-Koma"], "webtoon"),
        ("ja", ["4-Koma"], "4koma"),
        ("en", ["4-Koma"], "ltr"),
    ],
)
def test_reading_direction_from_the_series_language_and_format(original_language, format_tags, reading_direction):
    assert get_reading_direction_from_manga(get_manga_attributes(original_language, *format_tags)) == reading_direction


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


def fake_mangadex_api(monkeypatch, manga_attributes):
    asked_urls = []

    def get(url, timeout):
        asked_urls.append(url)
        if "/chapter/" in url:
            return FakeResponse({"data": {"relationships": [{"type": "scanlation_group", "id": "x"}, {"type": "manga", "id": MANGA_ID}]}})
        return FakeResponse({"data": {"attributes": manga_attributes}})

    monkeypatch.setattr(download_from_mangadex.requests, "get", get)
    return asked_urls


def test_a_series_url_looks_up_the_series(monkeypatch):
    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("zh"))

    assert get_reading_direction_from_mangadex(f"https://mangadex.org/title/{MANGA_ID}/some-title") == "ltr"
    assert asked_urls == [f"https://api.mangadex.org/manga/{MANGA_ID}"]


def test_a_chapter_url_looks_up_its_series(monkeypatch):
    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("ja"))

    assert get_reading_direction_from_mangadex(f"https://mangadex.org/chapter/{CHAPTER_ID}") == "rtl"
    assert asked_urls == [f"https://api.mangadex.org/chapter/{CHAPTER_ID}", f"https://api.mangadex.org/manga/{MANGA_ID}"]


def test_other_urls_are_not_looked_up(monkeypatch):
    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("ja"))

    assert get_reading_direction_from_mangadex("https://mangadex.org/list/whatever") is None
    assert asked_urls == []


def test_no_internet_means_no_reading_direction(monkeypatch):
    def get(url, timeout):
        raise requests.ConnectionError("no internet")

    monkeypatch.setattr(download_from_mangadex.requests, "get", get)

    assert get_reading_direction_from_mangadex(f"https://mangadex.org/title/{MANGA_ID}") is None


def test_the_reading_direction_is_saved_only_in_chapters_from_this_download(tmp_path):
    old_chapter = tmp_path / "Old Manga" / "Ch. 1"
    changed_chapter = tmp_path / "Old Manga" / "Ch. 2"
    new_chapter = tmp_path / "New Manga" / "Ch. 1"
    old_chapter.mkdir(parents=True)
    changed_chapter.mkdir()
    an_hour_ago = time.time() - 3600
    os.utime(changed_chapter, (an_hour_ago, an_hour_ago))
    before = get_chapter_folders(str(tmp_path))

    # The download adds a page to "Ch. 2" and makes a new chapter.
    (changed_chapter / "page_1.png").write_bytes(b"")
    new_chapter.mkdir(parents=True)
    save_reading_direction(str(tmp_path), "ltr", before)

    assert (new_chapter / READING_DIRECTION_FILE_NAME).read_text() == "ltr"
    assert (changed_chapter / READING_DIRECTION_FILE_NAME).read_text() == "ltr"
    assert not (old_chapter / READING_DIRECTION_FILE_NAME).exists()


def test_no_chapter_folders_in_a_missing_output_folder(tmp_path):
    assert get_chapter_folders(str(tmp_path / "missing")) == {}


@pytest.mark.parametrize("returncode, saved", [(0, "ltr"), (1, None), (-15, None)])
def test_the_reading_direction_is_saved_only_after_a_finished_download(tmp_path, monkeypatch, returncode, saved):
    chapter = tmp_path / "Some Manga" / "Ch. 1"

    class FakeProcessManager:
        process = None

        def monitor_terminal_output(self, *args, **kwargs):
            chapter.mkdir(parents=True)
            self.process = SimpleNamespace(returncode=returncode)

    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("zh"))
    monkeypatch.setattr(download_from_mangadex, "ProcessManager", FakeProcessManager)

    download_from_mangadex.download_from_mangadex(f"https://mangadex.org/title/{MANGA_ID}", str(tmp_path))

    saved_file = chapter / READING_DIRECTION_FILE_NAME
    assert (saved_file.read_text() if saved_file.exists() else None) == saved
    assert bool(asked_urls) == (returncode == 0)
