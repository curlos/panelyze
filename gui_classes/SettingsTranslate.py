import threading

import flet as ft
from gui_classes import Nord
from gui_classes.ProgressPanel import report_progress
from gui_classes.DropdownTextOptions import DropdownTextOptions
from gui_classes.WrappingCheckbox import WrappingCheckbox
from gui_classes.SettingsBase import SettingsBase
from translate import (
    ENGINES, FONTS, OLLAMA_MODELS, SOURCE_LANGUAGES, TARGET_LANGUAGES, delete_ollama_model, download_ollama_model,
    get_api_key, get_default_model, get_free_disk_gb, get_model_size_gb, get_ram_gb, get_room_for_model_error, is_pair_supported, is_too_big, list_installed_ollama_models, list_models,
)

ENGINE_DESCRIPTIONS = {
    "ollama": "Free and private: runs on this computer. Needs Ollama (ollama.com). Pick one for your computer's memory. Best quality: Gemini, ChatGPT or Claude (with an API key).",
    "gemini": "Your Gemini API key. Has a free tier (Google may use what's sent to improve its products).",
    "chatgpt": "Your OpenAI API key (paid per use)",
    "claude": "Your Anthropic API key (paid per use). A Claude Pro subscription doesn't include API use.",
}


# The memory sizes the suggested Ollama models are grouped by (see "memory_gb" in OLLAMA_MODELS).
MEMORY_TIERS = (8, 16, 32)


class SettingsTranslate(SettingsBase):
    def __init__(self, page, parent_gui=None):
        super().__init__()
        self.page = page
        # For downloading and removing Ollama models: only one job at a time, shown in the Status view.
        self.parent_gui = parent_gui
        self.download_cancelled = threading.Event()
        # While a download runs, "Manage Ollama models" shows a Cancel button.
        self.is_downloading = False

        self.model_dropdown = DropdownTextOptions(label="Model", options=[], value=None, on_change=self.handle_model_picked)
        self.api_key_textfield = ft.TextField(
            border_radius=0,
            label="API Key",
            border_color=Nord.BLUE,
            password=True,
            can_reveal_password=True,
            value=(self.page.client_storage.get("translate_api_keys") or {}).get(self.get_engine(), ""),
            on_change=lambda e: self.save_api_key(e.data.strip()),
            # The model list is fetched again with the new key once it's typed in.
            on_blur=lambda e: self.refresh_models(),
        )
        self.honorifics_checkbox = WrappingCheckbox(
            label="Keep Japanese honorifics (-san, -chan, senpai)",
            value=self.page.client_storage.get("translate_keep_honorifics"),
            on_change=lambda e: self.change_setting("translate_keep_honorifics", e.data),
        )
        # The models that can see the page check who's speaking and fix reading mistakes from it. Without it, they're faster. Hidden for models that can't see images.
        self.send_page_image_checkbox = WrappingCheckbox(
            label="Send the page image (better translations, slower)",
            value=self.page.client_storage.get("translate_send_page_image"),
            on_change=lambda e: self.change_setting("translate_send_page_image", e.data),
        )
        self.manage_models_list = ft.Column(spacing=10)
        # Folded away: most people pick a model once.
        self.manage_models = ft.ExpansionTile(
            title=ft.Text("Manage Ollama models", color=Nord.TEXT, size=14),
            tile_padding=ft.padding.all(0),
            controls_padding=ft.padding.only(left=0, bottom=10),
            collapsed_icon_color=Nord.TEXT,
            icon_color=Nord.TEXT,
            controls=[self.manage_models_list],
            on_change=lambda e: self.refresh_manage_models(),
        )
        self.fill_model_dropdown()
        self.update_visibility()

        self.inner_content = [
            DropdownTextOptions(
                label="From",
                options=[ft.dropdown.Option(key=key, text=text) for key, text in SOURCE_LANGUAGES.items()],
                value=self.page.client_storage.get("translate_from"),
                on_change=self.handle_source_language_change,
            ),
            DropdownTextOptions(
                label="To",
                options=[ft.dropdown.Option(key=key, text=text) for key, text in TARGET_LANGUAGES.items()],
                value=self.page.client_storage.get("translate_to"),
                on_change=self.handle_target_language_change,
            ),
            self.honorifics_checkbox,
            DropdownTextOptions(
                label="Translator",
                options=[ft.dropdown.Option(key=key, text=text) for key, text in ENGINES.items()],
                value=self.get_engine(),
                on_change=self.handle_engine_change,
                descriptions=self.get_engine_descriptions(),
            ),
            self.api_key_textfield,
            self.model_dropdown,
            # A setting of the model (hidden for models that never see the page), then the occasional model downloads, then the lettering.
            self.send_page_image_checkbox,
            self.manage_models,
            DropdownTextOptions(
                label="Font",
                options=[ft.dropdown.Option(font) for font in FONTS],
                value=self.page.client_storage.get("translate_font"),
                on_change=lambda e: self.change_setting("translate_font", e.data),
            ),
        ]

        self.content = self.get_full_content()

    def get_engine_descriptions(self):
        descriptions = dict(ENGINE_DESCRIPTIONS)
        # A model that doesn't fit in memory runs very slowly or not at all.
        ram_gb = get_ram_gb()
        if ram_gb is not None and ram_gb < 15:
            descriptions["ollama"] += f" This computer has {ram_gb:.0f} GB, so it may be slow."
        return descriptions

    def get_ollama_model_text(self, model, installed, ram_gb):
        """
        A suggested Ollama model as it's shown in the list, and whether it can't be picked here (too big for this computer, or not for these languages).
        """
        info = OLLAMA_MODELS[model]
        # The size is the download (disk space); the headings are about memory (RAM).
        notes = [f"{info['size']} on disk"]
        if model in installed:
            notes.append("installed")
        too_big = is_too_big(get_model_size_gb(model), ram_gb)
        wrong_languages = not is_pair_supported(model, self.get_source_language(), self.get_target_language())
        if too_big:
            notes.append(f"too big for this computer's {ram_gb:.0f} GB of RAM")
        elif wrong_languages:
            notes.append("Japanese to English only")
        return f"{info['name']} ({', '.join(notes)})", too_big or wrong_languages

    @staticmethod
    def get_heading_option(key, text):
        # A heading in the list, which can't be picked.
        return ft.dropdown.Option(key=key, text=text, content=ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color=Nord.ACCENT), disabled=True)

    def get_model_options(self):
        """
        The models to pick from, and a hint shown under the list. Ollama: the suggested models, grouped by the memory they need (greyed out when they clearly won't fit in this computer's memory, or don't know the picked languages), then any others installed. The others: the models the API key can use, or just the default one until a key is entered.
        """
        engine = self.get_engine()
        options, hint = [], ""
        if engine == "ollama":
            installed = list_installed_ollama_models() or {}
            ram_gb = get_ram_gb()
            for memory_gb in MEMORY_TIERS:
                # A heading, which can't be picked.
                options.append(self.get_heading_option(f"heading-{memory_gb}", f"FOR {memory_gb} GB RAM OR MORE"))
                # Best first, but models that don't know the picked languages (PLaMo) at the bottom.
                tier = [model for model, info in OLLAMA_MODELS.items() if info["memory_gb"] == memory_gb]
                for model in sorted(tier, key=lambda model: not is_pair_supported(model, self.get_source_language(), self.get_target_language())):
                    text, disabled = self.get_ollama_model_text(model, installed, ram_gb)
                    # Flet draws a disabled choice like any other, so its text is greyed out by hand.
                    content = ft.Text(text, color=Nord.TEXT_MUTED, size=14) if disabled else None
                    options.append(ft.dropdown.Option(key=model, text=text, content=content, disabled=disabled))
            others = [model for model in installed if model not in OLLAMA_MODELS]
            if others:
                options.append(self.get_heading_option("heading-other", "OTHER INSTALLED MODELS"))
                options += [ft.dropdown.Option(key=model, text=f"{model} (installed)") for model in others]
            # A model the user downloaded with Ollama themselves.
            hint = OLLAMA_MODELS.get(self.get_model(), {}).get("about", "Downloaded with Ollama outside Panelyze, so it hasn't been tested here.")
        else:
            api_key = get_api_key(engine, (self.page.client_storage.get("translate_api_keys") or {}).get(engine, ""))
            available = list_models(engine, api_key)
            options = [ft.dropdown.Option(model) for model in available or [get_default_model(engine)]]
            if not available:
                hint = "Enter your API key to see every model it can use." if not api_key else "Couldn't get the list of models: check the API key and the internet connection."
        # The model picked before stays in the list, even if it isn't offered any more.
        if self.get_model() not in {option.key for option in options}:
            options.insert(0, ft.dropdown.Option(self.get_model()))
        return options, hint

    def fill_model_dropdown(self):
        options, hint = self.get_model_options()
        self.model_dropdown.options = options
        self.model_dropdown.value = self.get_model()
        self.model_dropdown.helper_text = hint
        self.model_dropdown.helper_max_lines = 4
        self.model_dropdown.helper_style = ft.TextStyle(size=12, color=Nord.TEXT_MUTED)

    def refresh_models(self):
        self.fill_model_dropdown()
        self.model_dropdown.update()

    def get_source_language(self):
        return self.page.client_storage.get("translate_from") or "japanese"

    def get_target_language(self):
        return self.page.client_storage.get("translate_to") or "english"

    def get_engine(self):
        return self.page.client_storage.get("translate_engine") or "ollama"

    def get_model(self):
        # Until one is picked, the best one for this computer and these languages (so it changes with the languages).
        return (self.page.client_storage.get("translate_models") or {}).get(self.get_engine()) or get_default_model(self.get_engine(), self.get_source_language(), self.get_target_language())

    def save_model(self, model):
        models = dict(self.page.client_storage.get("translate_models") or {})
        models[self.get_engine()] = model
        self.page.client_storage.set("translate_models", models)

    def save_api_key(self, api_key):
        api_keys = dict(self.page.client_storage.get("translate_api_keys") or {})
        api_keys[self.get_engine()] = api_key
        self.page.client_storage.set("translate_api_keys", api_keys)

    def update_visibility(self):
        self.api_key_textfield.visible = self.get_engine() != "ollama"
        self.manage_models.visible = self.get_engine() == "ollama"
        self.honorifics_checkbox.visible = self.page.client_storage.get("translate_from") == "japanese"
        # Line-by-line models never get the page.
        self.send_page_image_checkbox.visible = not OLLAMA_MODELS.get(self.get_model(), {}).get("line_by_line")

    def handle_engine_change(self, e):
        self.change_setting("translate_engine", e.data)
        self.api_key_textfield.value = (self.page.client_storage.get("translate_api_keys") or {}).get(self.get_engine(), "")
        self.fill_model_dropdown()
        self.update_visibility()
        self.update()

    def handle_model_picked(self, e):
        # A heading in the list is never a model.
        if e.data.startswith("heading-"):
            return
        self.save_model(e.data)
        # The line under the list says what the new model is good and bad at.
        self.fill_model_dropdown()
        self.update_visibility()
        self.update()
        self.refresh_manage_models_if_open()

    def refresh_manage_models_if_open(self):
        # Only when it's on screen: it asks Ollama for the downloaded models.
        if self.manage_models.visible and self.manage_models_list.controls:
            self.refresh_manage_models()

    def forget_model_for_other_languages(self):
        """
        A picked model that doesn't know the new languages (PLaMo after switching to Spanish) is dropped, so the best one for these languages is used instead.
        """
        models = dict(self.page.client_storage.get("translate_models") or {})
        if not is_pair_supported(models.get("ollama", ""), self.get_source_language(), self.get_target_language()):
            del models["ollama"]
            self.page.client_storage.set("translate_models", models)

    def handle_source_language_change(self, e):
        self.change_setting("translate_from", e.data)
        self.forget_model_for_other_languages()
        self.update_visibility()
        # Models that don't know the new languages (PLaMo) are greyed out.
        self.fill_model_dropdown()
        self.update()
        self.refresh_manage_models_if_open()

    def handle_target_language_change(self, e):
        self.change_setting("translate_to", e.data)
        self.forget_model_for_other_languages()
        # The default model may change with the languages.
        self.update_visibility()
        self.fill_model_dropdown()
        self.update()
        self.refresh_manage_models_if_open()

    def refresh_manage_models(self):
        """
        Fill "Manage Ollama models": every suggested model grouped by the memory it needs, with its size, whether it's downloaded, and a Download or Uninstall button. Then any other downloaded models (Uninstall only).
        """
        installed = list_installed_ollama_models()
        if installed is None:
            self.manage_models_list.controls = [ft.Text("Ollama isn't running. Install it from ollama.com and open it, then open this again.", color=Nord.TEXT_MUTED, size=12)]
            self.update()
            return
        ram_gb = get_ram_gb()
        controls = []
        if self.is_downloading:
            controls.append(ft.TextButton("Cancel the download", style=ft.ButtonStyle(color=Nord.RED_TEXT), on_click=lambda e: self.download_cancelled.set()))
        controls += [ft.Text(f"All free, and run on this computer. They're kept in your home folder, in .ollama/models. {get_free_disk_gb():.0f} GB free on this disk. Models you download yourself with Ollama (ollama pull) show up here too.", color=Nord.TEXT_MUTED, size=12)]
        for memory_gb in MEMORY_TIERS:
            controls.append(self.get_section_heading(f"For {memory_gb} GB RAM or more"))
            for model, info in OLLAMA_MODELS.items():
                if info["memory_gb"] == memory_gb:
                    controls.append(self.get_manage_model_row(model, f"{info['name']} · {info['size']} on disk", model in installed, is_too_big(get_model_size_gb(model), ram_gb)))
        others = [model for model in installed if model not in OLLAMA_MODELS]
        if others:
            controls.append(self.get_section_heading("Other downloaded models"))
            controls += [self.get_manage_model_row(model, f"{model} · {installed[model]:.1f} GB on disk", True, False) for model in others]
        self.manage_models_list.controls = controls
        self.update()

    @staticmethod
    def get_section_heading(text):
        # Space above each group of models, so the groups don't run together.
        return ft.Container(ft.Text(text, color=Nord.TEXT, size=13, weight=ft.FontWeight.BOLD), margin=ft.margin.only(top=14))

    def get_manage_model_row(self, model, text, is_installed, too_big):
        status = "Downloaded" if is_installed else "Too big for this computer's RAM" if too_big else "Not downloaded"
        # The model picked in the Model list stands out.
        is_selected = model == self.get_model()
        if is_selected:
            status += " · selected"
        # Nothing else can start while a model is downloaded or removed.
        busy = bool(self.parent_gui and self.parent_gui.is_job_running)
        if is_installed:
            button = ft.TextButton("Uninstall", style=ft.ButtonStyle(color=Nord.TEXT_MUTED), disabled=busy, on_click=lambda e: self.ask_to_uninstall(model))
        else:
            button = ft.TextButton("Download", disabled=too_big or busy, on_click=lambda e: self.download_model(model))
        return ft.Row(
            controls=[
                ft.Column([ft.Text(text, color=Nord.ACCENT if is_selected else Nord.TEXT, size=13, weight=ft.FontWeight.BOLD if is_selected else None), ft.Text(status, color=Nord.TEXT_MUTED, size=12)], spacing=0, expand=True),
                button,
            ],
        )

    def ask_to_uninstall(self, model):
        """
        Removing a model means downloading it again to use it, so a dialog asks to be sure, with how much space it frees.
        """
        # Its name as the list shows it, and the space it takes (Ollama's own count of what's downloaded).
        name = OLLAMA_MODELS.get(model, {}).get("name", model)
        size_gb = (list_installed_ollama_models() or {}).get(model)
        frees = f"This frees {size_gb:.1f} GB of disk space. " if size_gb else ""

        def close(e=None):
            self.page.close(dialog)

        def remove(e=None):
            close()
            self.uninstall_model(model, name, size_gb)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Remove {name}?"),
            content=ft.Text(f"{frees}Using it again means downloading it again."),
            actions=[ft.TextButton("Cancel", on_click=close), ft.TextButton("Remove", style=ft.ButtonStyle(color=Nord.RED_TEXT), on_click=remove)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dialog)

    def uninstall_model(self, model, name, size_gb):
        def remove():
            delete_ollama_model(model)
            return f"Removed {name}. " + (f"{size_gb:.1f} GB of disk space freed." if size_gb else "Its disk space is free again.")

        self.run_model_job(f"Removing {name}...", remove)

    def download_model(self, model):
        name = OLLAMA_MODELS.get(model, {}).get("name", model)

        def download():
            report_progress(chapter=1, chapters=1, group_label="Model", pages_done=0, pages_total=None, unit="GB", detail=None)
            try:
                # Stops with a clear message if there isn't the model's size + 2 GB free.
                finished = download_ollama_model(
                    model,
                    report=lambda done_gb, total_gb: report_progress(pages_done=round(done_gb, 1), pages_total=round(total_gb, 1)),
                    is_cancelled=self.download_cancelled.is_set,
                )
            finally:
                report_progress(chapter=None, chapters=None, pages_done=None, pages_total=None, unit=None)
            return f"Downloaded {name}." if finished else None

        self.run_model_job(f"Downloading {name} ({OLLAMA_MODELS.get(model, {}).get('size', '')})...", download, is_download=True)

    def run_model_job(self, loading_text, work, is_download=False):
        """
        Download or remove a model as a job: only when no other job runs, with its progress and result in the Status view (Cancel for a download is at the top of "Manage Ollama models"). "work" returns the result to show, or None if it was cancelled.
        """
        if not self.parent_gui.try_to_start_job("Ollama model"):
            return
        terminal_output = self.parent_gui.terminal_output
        terminal_output.show_loading_text(loading_text)
        self.download_cancelled.clear()
        self.is_downloading = is_download
        # Shows the Cancel button, and turns the other buttons off while it runs.
        self.refresh_manage_models()
        try:
            result = work()
            if result:
                terminal_output.hide_loading_text(result)
            else:
                terminal_output.hide_loading_text("Download cancelled. What was downloaded is kept, so downloading it again carries on.", success=False, cancelled=True)
        except Exception as error:
            terminal_output.hide_loading_text("Couldn't finish.", success=False)
            terminal_output.update_terminal_with_error_message(f"ERROR: {error}")
        finally:
            self.is_downloading = False
            self.parent_gui.set_job_running(False)
            self.refresh_manage_models()
            self.refresh_models()
