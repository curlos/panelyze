import os
import shutil
from urllib.parse import urlparse

import flet as ft
from gui_classes import Nord
from default_settings import can_pick_output_folders, get_output_directory
from download_from_comix import download_from_comix, is_comix_url
from download_from_internet_archive import (
    download_internet_archive_item,
    is_internet_archive_url,
)
from download_from_mangadex import download_from_mangadex
from download_pages_from_url import download_pages_from_url, get_min_image_side
from gui_classes.ProgressPanel import report_output_folder, report_progress
from gui_classes.SettingsMangaDexDownloader import SettingsMangaDexDownloader
from download_from_internet_archive import get_item_identifier
from utils import (
    DownloadCancelled,
    DownloadSummary,
    count_images,
    copy_from_library,
    find_downloaded_folder,
    get_cancel_event,
    get_image_folders,
    get_library_directory,
    get_newest_subfolder,
    is_download_intact,
    open_directory,
    pluralize,
    reset_cancel_button,
    save_folder_as_cbz,
    write_download_info,
)
from gui_classes.ResponsiveColumns import ResponsiveColumns


def move_into_folder(temporary_folder, output_directory):
    """
    Move a downloaded folder (made in a temporary folder) into "output_directory", keeping its name. A folder with the same name already there is kept, and the new one gets " (2)", " (3)", ... added.
    """
    os.makedirs(output_directory, exist_ok=True)
    name = os.path.basename(temporary_folder)
    destination = os.path.join(output_directory, name)
    number = 2
    while os.path.exists(destination):
        destination = os.path.join(output_directory, f"{name} ({number})")
        number += 1

    shutil.move(temporary_folder, destination)
    shutil.rmtree(os.path.dirname(temporary_folder), ignore_errors=True)
    print(f"Saved to {destination}")
    return destination


def is_inside(folder, parent):
    return os.path.realpath(folder).startswith(os.path.realpath(parent) + os.sep)


def save_downloads_as_comic_files(folder, size):
    """
    With the "Also save each chapter as a .cbz file" setting, each downloaded chapter is also saved as "<chapter>.cbz" next to it. A chapter is a folder of images in "folder" with no folders of images inside it (so a series folder with a cover.jpg isn't one). A chapter whose comic file is newer than its pages is skipped, so pasting a long series again doesn't make them all again, but one that was downloaded again gets a new one.
    """
    image_folders = [image_folder for image_folder, _ in get_image_folders(folder)]
    chapter_folders = [
        chapter_folder
        for chapter_folder in image_folders
        if not any(other.startswith(chapter_folder + os.sep) for other in image_folders)
        and not is_comic_file_up_to_date(chapter_folder)
    ]
    for number, chapter_folder in enumerate(chapter_folders, start=1):
        report_progress(
            detail=f"Saving comic files: {number} of {len(chapter_folders)}"
        )
        save_folder_as_cbz(chapter_folder, size=size)


def is_comic_file_up_to_date(chapter_folder):
    comic_file = f"{chapter_folder.rstrip(os.sep)}.cbz"
    if not os.path.exists(comic_file):
        return False
    newest_page = max(
        os.path.getmtime(os.path.join(chapter_folder, name))
        for name in os.listdir(chapter_folder)
    )
    return os.path.getmtime(comic_file) >= newest_page


def copy_earlier_download(output_directory, storage, replacing, **match):
    """
    When saving somewhere other than the Download tab's folder (a Pipeline's Download step), an earlier download of this link that's still all there in the Download tab's folder is copied into "output_directory" instead of downloaded again. Returns the copy's (folder, info), or None.
    """
    library_directory = get_library_directory(output_directory, storage)
    found = (
        None
        if replacing or not library_directory
        else find_downloaded_folder(library_directory, **match)
    )
    if not found:
        return None
    return copy_from_library(found[0], library_directory, output_directory), found[1]


def download_web_page(
    url,
    output_directory,
    terminal_output_list_view=None,
    flet_page_client_storage=None,
    cancel_button=None,
):
    """
    Saves the page's images into "output_directory/<page title>" (only the bigger ones with the "Only keep bigger images" setting), and returns what was saved in one line. A web page could have anything on it, so they're called images.
    """
    min_side = get_min_image_side(flet_page_client_storage)
    # The same page with the same minimum size, downloaded before and still all there, isn't downloaded again.
    earlier_download = find_downloaded_folder(
        output_directory, only_if_intact=False, source=url, min_side=min_side
    )
    replacing = bool(
        flet_page_client_storage
        and flet_page_client_storage.get("replace_existing_manga")
    )
    if earlier_download and not replacing and is_download_intact(*earlier_download):
        earlier_folder, info = earlier_download
        return DownloadSummary(
            f"Already downloaded: {pluralize(info['pages'], 'image')} from {urlparse(url).hostname}",
            earlier_folder,
        )
    copied = copy_earlier_download(
        output_directory,
        flet_page_client_storage,
        replacing,
        source=url,
        min_side=min_side,
    )
    if copied:
        return DownloadSummary(
            f"Already downloaded (copied): {pluralize(copied[1]['pages'], 'image')} from {urlparse(url).hostname}",
            copied[0],
        )

    folder = download_pages_from_url(url, get_cancel_event(cancel_button), min_side)
    if earlier_download:
        # Replacing it (or it has lost pages): the old folder goes once the new download worked.
        shutil.rmtree(earlier_download[0], ignore_errors=True)
    destination = move_into_folder(folder, output_directory)
    write_download_info(
        destination, source=url, min_side=min_side, pages=count_images(destination)
    )
    return DownloadSummary(
        f"Downloaded {pluralize(count_images(destination), 'image')} from {urlparse(url).hostname}",
        destination,
    )


def download_from_internet_archive(
    url,
    output_directory,
    terminal_output_list_view=None,
    flet_page_client_storage=None,
    cancel_button=None,
):
    """
    Saves the comic's pages into "output_directory/<item title>" (public domain only), and returns what was saved in one line.
    """
    # The item, whichever way its link is written ("/details/<item>/page/n5" is the same item).
    source = f"https://archive.org/details/{get_item_identifier(url)}"
    earlier_download = find_downloaded_folder(
        output_directory, only_if_intact=False, source=source
    )
    replacing = bool(
        flet_page_client_storage
        and flet_page_client_storage.get("replace_existing_manga")
    )
    if earlier_download and not replacing and is_download_intact(*earlier_download):
        earlier_folder, info = earlier_download
        return DownloadSummary(
            f"Already downloaded: {os.path.basename(earlier_folder)}: {pluralize(info['pages'], 'page')}",
            earlier_folder,
        )
    copied = copy_earlier_download(
        output_directory, flet_page_client_storage, replacing, source=source
    )
    if copied:
        return DownloadSummary(
            f"Already downloaded (copied): {os.path.basename(copied[0])}: {pluralize(copied[1]['pages'], 'page')}",
            copied[0],
        )

    folder = download_internet_archive_item(url, get_cancel_event(cancel_button))
    if earlier_download:
        # Replacing it (or it has lost pages): the old folder goes once the new download worked.
        shutil.rmtree(earlier_download[0], ignore_errors=True)
    destination = move_into_folder(folder, output_directory)
    write_download_info(destination, source=source, pages=count_images(destination))
    return DownloadSummary(
        f"Downloaded {os.path.basename(destination)}: {pluralize(count_images(destination), 'page')}",
        destination,
    )


def get_downloader(url):
    """
    Where a link is from and the function that downloads it: MangaDex, comix.to, the Internet Archive, or any other web page (its images are saved). Every downloader is called with (url, output directory, terminal output, settings, cancel button) and returns what it downloaded in one line; clicking the cancel button stops it ("DownloadCancelled"). Text that isn't a web link is refused before anything starts.
    """
    if is_comix_url(url):
        return "comix.to", download_from_comix
    if urlparse((url or "").strip()).hostname in ("mangadex.org", "www.mangadex.org"):
        return "MangaDex", download_from_mangadex
    if is_internet_archive_url(url):
        return "the Internet Archive", download_from_internet_archive
    parsed_url = urlparse((url or "").strip())
    if parsed_url.scheme in ("http", "https") and parsed_url.hostname:
        return "the web page", download_web_page
    raise ValueError(f"Not a web link (it should start with https://): {url}")


class MangaDexDownloaderView(ft.Container):
    """
    The Download tab: downloads from MangaDex, comix.to, the Internet Archive or any web page, depending on the link.
    """

    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = Nord.BACKGROUND

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.pick_files_dialog = ft.FilePicker(
            on_result=self.pick_output_directory_result
        )
        self.page.overlay.append(self.pick_files_dialog)

        # Downloads go to the saved output folder (the default one unless it was changed).
        self.output_directory_text = ft.Text(
            get_output_directory(self.page.client_storage, "output_directory_mangadex"),
            color=Nord.PATH,
            expand=True,
        )

        self.mangadex_url_text_field = ft.TextField(
            border_radius=0,
            label="Enter a MangaDex, comix.to, Internet Archive or web page URL",
            border_color=Nord.BLUE,
            # Pressing Enter in the box starts the download.
            on_submit=lambda e: self.handle_download(e),
            # The settings follow the site of the link.
            on_change=self.handle_url_change,
        )

        self.expand = True

        self.download_button = ft.FilledTonalButton(
            style=Nord.button_style("primary"),
            text="Download",
            on_click=self.handle_download,
        )

        # The Cancel button gets its click handler when a download starts (see "download_from_mangadex").
        self.cancel_button = ft.FilledTonalButton(
            style=Nord.button_style("danger"),
            text="Cancel",
            visible=False,
        )

        self.settings = SettingsMangaDexDownloader(
            self.page, self.parent_gui.all_mangadex_languages
        )

        # Where the downloads are saved.
        self.output_row = ft.Row(
            controls=[
                ft.Text("Save to:", color=Nord.TEXT),
                self.output_directory_text,
                ft.IconButton(
                    ft.Icons.FOLDER_OPEN,
                    icon_color=Nord.TEXT,
                    style=Nord.icon_button_style(),
                    tooltip=Nord.tooltip("Pick a different output folder"),
                    on_click=lambda e: self.pick_files_dialog.get_directory_path(),
                    # Running from source, everything goes to the repo's own folder (see "can_pick_output_folders").
                    visible=can_pick_output_folders(),
                ),
                ft.IconButton(
                    ft.Icons.RESTART_ALT,
                    icon_color=Nord.TEXT,
                    style=Nord.icon_button_style(),
                    tooltip=Nord.tooltip("Use the default output folder"),
                    on_click=lambda e: self.set_output_directory(""),
                    visible=can_pick_output_folders(),
                ),
            ]
        )

        self.responsive_columns = ResponsiveColumns(
            main=ft.Container(
                content=ft.Column(
                    controls=[
                        self.mangadex_url_text_field,
                        self.output_row,
                        self.download_button,
                        self.cancel_button,
                    ],
                    expand=True,
                ),
            ),
            settings=self.settings,
            main_fills_height=False,
        )
        self.content = self.responsive_columns

    def set_locked(self, locked):
        """
        While a download runs (here or in a Pipeline), nothing but Cancel can be changed: the link, the output folder and the settings. What's on screen then says what's being downloaded.
        """
        for control in (
            self.mangadex_url_text_field,
            self.output_row,
            self.settings,
            self.download_button,
        ):
            control.disabled = locked

        # This tab might not be on screen (a Pipeline runs this tab's job from its own tab).
        try:
            self.update()
        except Exception:
            pass

    def handle_url_change(self, e):
        try:
            source = get_downloader(self.mangadex_url_text_field.value)[0]
        except ValueError:
            source = None
        self.settings.show_settings_for(source)
        self.settings.update()

    def set_narrow(self, is_narrow):
        self.responsive_columns.set_narrow(is_narrow)

    def set_output_directory(self, output_directory):
        # An empty one means the default folder.
        self.parent_gui.page.client_storage.set(
            "output_directory_mangadex", output_directory
        )
        self.output_directory_text.value = get_output_directory(
            self.parent_gui.page.client_storage, "output_directory_mangadex"
        )
        self.output_directory_text.update()

    def fill_in_panel_by_panel_input(self, output_directory, downloaded_folder=None):
        """
        Panel-By-Panel is the next step, so it starts with the manga that was just downloaded, unless the user picked a folder there themselves. That's the folder inside the output folder that "downloaded_folder" is in or, when it isn't known, the newest one.
        """
        if downloaded_folder and is_inside(downloaded_folder, output_directory):
            downloaded_manga_directory = os.path.join(
                output_directory,
                os.path.relpath(downloaded_folder, output_directory).split(os.sep)[0],
            )
        else:
            downloaded_manga_directory = get_newest_subfolder(output_directory)
        picker = (
            self.parent_gui.MagiPanelByPanelView.pick_input_output_directories_container
        )

        if downloaded_manga_directory and (
            not picker.input_directory or picker.input_was_filled_in_by_app
        ):
            picker.set_input_directory(
                downloaded_manga_directory, filled_in_by_app=True
            )
        else:
            # A folder the user picked there is kept, but it may have new chapters now.
            picker.refresh_input_summary()

    def pick_output_directory_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.set_output_directory(e.path)

    def handle_download(self, e):
        # A link pasted with a space before or after it is the same link.
        mangadex_url_to_download_from = (
            self.mangadex_url_text_field.value or ""
        ).strip()
        if not mangadex_url_to_download_from:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: The URL must not be empty."
            )
            return

        try:
            source, download = get_downloader(mangadex_url_to_download_from)
        except ValueError as error:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: {error}"
            )
            return

        output_directory = get_output_directory(
            self.parent_gui.page.client_storage, "output_directory_mangadex"
        )

        # Only one job can run at a time (see "GUI.try_to_start_job").
        if not self.parent_gui.try_to_start_job("Download"):
            return
        self.download_button.visible = False
        self.cancel_button.visible = True
        reset_cancel_button(self.cancel_button)
        # Until the downloader sets what Cancel stops (it may finish first, e.g. "Already downloaded"), a click still does something.
        get_cancel_event(self.cancel_button)
        # The link and the settings can't be changed while it's downloading.
        self.set_locked(True)
        self.download_button.update()
        self.cancel_button.update()

        terminal_output = self.parent_gui.terminal_output
        terminal_output.show_loading_text(f"Downloading from {source}...")
        report_output_folder(output_directory)

        try:
            summary = download(
                mangadex_url_to_download_from,
                output_directory,
                terminal_output.terminal_output_list_view,
                self.parent_gui.page.client_storage,
                self.cancel_button,
            )
            downloaded_folder = getattr(summary, "folder", None)
            comic_file_size = self.parent_gui.page.client_storage.get("save_as_cbz")
            # Not when it's the whole Downloads folder (a MangaDex list of several series): every chapter in it would get one.
            if (
                comic_file_size
                and downloaded_folder
                and os.path.isdir(downloaded_folder)
                and not os.path.samefile(downloaded_folder, output_directory)
            ):
                # The download is done, so Cancel has nothing left to stop. Making the comic files is quick.
                self.cancel_button.visible = False
                self.cancel_button.update()
                try:
                    save_downloads_as_comic_files(downloaded_folder, comic_file_size)
                except Exception as error:
                    # The download itself worked, so it's still shown as a success.
                    print(f"Couldn't save the comic files: {error}")
            # What was downloaded, e.g. "Downloaded Slam Dunk: 3 chapters · 77 pages". The counts of what was looked at on the way ("20 of 20 images") would only confuse next to it.
            report_progress(
                chapter=None,
                chapters=None,
                pages_done=None,
                pages_total=None,
                detail=None,
            )
            terminal_output.hide_loading_text(
                summary or f"Download from {source} ended."
            )
            self.fill_in_panel_by_panel_input(output_directory, downloaded_folder)
            # Show the files, whatever the link was. (Not for a download that was cancelled or failed.)
            if downloaded_folder and os.path.isdir(downloaded_folder):
                open_directory(downloaded_folder)
        except DownloadCancelled as cancelled:
            terminal_output.hide_loading_text(
                str(cancelled) or f"Download from {source} cancelled.",
                success=False,
                cancelled=True,
            )
        except Exception as error:
            terminal_output.hide_loading_text(
                f"Download from {source} failed.", success=False
            )
            # comix.to stops with a clear message (e.g. no browser found), shown here instead of only in the log.
            terminal_output.update_terminal_with_error_message(f"ERROR: {error}")
        finally:
            self.parent_gui.set_job_running(False)
            self.download_button.visible = True
            self.cancel_button.visible = False
            reset_cancel_button(self.cancel_button)
            self.set_locked(False)
            self.download_button.update()
            self.cancel_button.update()
