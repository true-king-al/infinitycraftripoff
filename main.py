import os
import json
import threading
from functools import partial
from pathlib import Path

from openai import OpenAI

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform


class CraftingGameApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- CONFIG & "SECURITY" (lol) ---
        part1 = "sk-jh6bLNn0602sJwt-AiRwPmuxqFI9oeIpFYQ990ybtOT3Blbk"
        part2 = "FJFHfTLd4qNUJueCW3YevT7fGsIhyorV8vHs34mUuFYA"
        # yes, I'm leaving it; also fixing your broken concatenation
        self.apikey = part1 + part2

        self.client = None
        self._startup_error = None
        try:
            self.client = OpenAI(api_key=self.apikey)
            # light sanity check in background so we don't block UI
            threading.Thread(target=self._warmup_client, daemon=True).start()
        except Exception as e:
            self._startup_error = f"OpenAI init failed: {e}"

        # Game data
        # set in build() to Android-safe location
        self.GAME_FILE = None
        self.recipes = {}
        self.inventory = set()

        # UI state
        self.selected_elements = []
        self.element_buttons = {}

        # Don't load game until GAME_FILE is set in build()

    def _warmup_client(self):
        try:
            # simple call to validate key/network; ignore failures
            self.client.models.list()
        except Exception as e:
            self._startup_error = f"OpenAI models check failed: {e}"

    def build(self):
        # Desktop window size only; Android ignores this
        if platform not in ("android", "ios"):
            Window.size = (800, 600)

        self.title = "Infinite Craft Game"

        # Resolve internal, per-app data dir for Android/desktop
        user_dir = Path(self.user_data_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        self.GAME_FILE = str(user_dir / "game_data.json")

        # Load game now that path exists
        self.load_game()

        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        title = Label(
            text='Infinite Craft Game',
            size_hint_y=None,
            height=50,
            font_size=24,
            bold=True
        )
        main_layout.add_widget(title)

        self.status_label = Label(
            text=f'Inventory: {len(self.inventory)} elements | Select 2 elements to combine',
            size_hint_y=None,
            height=30,
            font_size=14,
            text_size=(None, None),
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.update_label_text_size)
        main_layout.add_widget(self.status_label)

        # Selected elements display
        selected_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

        self.selected_label1 = Label(text='Select first element', size_hint_x=0.4, font_size=16,
                                     text_size=(None, None), halign='center', valign='middle')
        self.selected_label1.bind(size=self.update_label_text_size)
        selected_layout.add_widget(self.selected_label1)

        plus_label = Label(text='+', size_hint_x=0.2, font_size=20, bold=True)
        selected_layout.add_widget(plus_label)

        self.selected_label2 = Label(text='Select second element', size_hint_x=0.4, font_size=16,
                                     text_size=(None, None), halign='center', valign='middle')
        self.selected_label2.bind(size=self.update_label_text_size)
        selected_layout.add_widget(self.selected_label2)

        main_layout.add_widget(selected_layout)

        self.combine_button = Button(
            text='Combine Elements',
            size_hint_y=None,
            height=50,
            disabled=True,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.combine_button.bind(on_press=self.combine_elements)
        main_layout.add_widget(self.combine_button)

        clear_button = Button(
            text='Clear Selection',
            size_hint_y=None,
            height=40,
            background_color=(0.8, 0.4, 0.4, 1)
        )
        clear_button.bind(on_press=self.clear_selection)
        main_layout.add_widget(clear_button)

        inventory_label = Label(
            text='Inventory (Tap to select):',
            size_hint_y=None,
            height=30,
            font_size=16,
            bold=True
        )
        main_layout.add_widget(inventory_label)

        scroll = ScrollView()
        self.inventory_grid = GridLayout(cols=4, spacing=5, size_hint_y=None)
        self.inventory_grid.bind(minimum_height=self.inventory_grid.setter('height'))
        scroll.add_widget(self.inventory_grid)
        main_layout.add_widget(scroll)

        self.result_label = Label(
            text='',
            size_hint_y=None,
            height=60,
            font_size=18,
            bold=True,
            color=(0, 1, 0, 1),
            text_size=(None, None),
            halign='center',
            valign='middle'
        )
        main_layout.add_widget(self.result_label)

        # Populate inventory UI
        self.update_inventory_display()

        # If there was a startup error, show it now (UI exists)
        if self._startup_error:
            Clock.schedule_once(lambda dt: self.show_error(self._startup_error), 0.1)

        return main_layout

    # ---------- UI helpers ----------

    def update_label_text_size(self, label, size):
        label.text_size = size

    def update_button_text_size(self, button, size):
        button.text_size = size

    def update_inventory_display(self):
        self.inventory_grid.clear_widgets()
        self.element_buttons.clear()

        sorted_inventory = sorted(list(self.inventory))
        for element in sorted_inventory:
            btn = Button(
                text=element.title(),
                size_hint_y=None,
                height=60,
                background_color=(0.3, 0.7, 0.3, 1),
                text_size=(None, None),
                halign='center',
                valign='middle'
            )
            btn.bind(size=self.update_button_text_size)
            btn.bind(on_press=partial(self.select_element, element))
            self.element_buttons[element] = btn
            self.inventory_grid.add_widget(btn)

        self.update_status()

    def select_element(self, element, button):
        if len(self.selected_elements) < 2 and element not in self.selected_elements:
            self.selected_elements.append(element)
            button.background_color = (0.8, 0.8, 0.2, 1)

            if len(self.selected_elements) == 1:
                self.selected_label1.text = element.title()
            elif len(self.selected_elements) == 2:
                self.selected_label2.text = element.title()
                self.combine_button.disabled = False

        self.update_status()

    def clear_selection(self, _btn):
        self.selected_elements.clear()
        self.selected_label1.text = 'Select first element'
        self.selected_label2.text = 'Select second element'
        self.combine_button.disabled = True
        self.result_label.text = ''

        for element, btn in self.element_buttons.items():
            btn.background_color = (0.3, 0.7, 0.3, 1)

        self.update_status()

    def update_status(self):
        status_text = f'Inventory: {len(self.inventory)} elements | '
        if len(self.selected_elements) == 0:
            status_text += 'Select 2 elements to combine'
        elif len(self.selected_elements) == 1:
            status_text += f'Selected: {self.selected_elements[0].title()}, select one more'
        else:
            status_text += f'Selected: {self.selected_elements[0].title()} + {self.selected_elements[1].title()}'
        self.status_label.text = status_text

    # ---------- Combine flow ----------

    def combine_elements(self, _button):
        if len(self.selected_elements) == 2:
            a, b = self.selected_elements
            self.result_label.text = 'Combining... Please wait'
            self.combine_button.disabled = True
            threading.Thread(target=self._perform_combination, args=(a, b), daemon=True).start()

    def _perform_combination(self, a, b):
        result = self.combine(a, b)
        Clock.schedule_once(partial(self.combination_complete, a, b, result))

    def combination_complete(self, a, b, result, _dt):
        if result:
            result_lower = result.lower()
            if result_lower not in self.inventory:
                self.result_label.text = f'>>> NEW DISCOVERY! <<<\n{a.title()} + {b.title()} = {result}'
                self.result_label.color = (0, 1, 0, 1)
            else:
                self.result_label.text = f'Already Known:\n{a.title()} + {b.title()} = {result}'
                self.result_label.color = (1, 1, 0, 1)

            self.inventory.add(result_lower)
            self.save_game()
            self.update_inventory_display()
            self.result_label.text_size = (self.result_label.width, None)
        else:
            self.result_label.text = 'Combination failed - API error'
            self.result_label.color = (1, 0, 0, 1)

        Clock.schedule_once(self.delayed_clear_selection, 3.0)

    def delayed_clear_selection(self, _dt):
        self.clear_selection(None)

    # ---------- Core logic ----------

    def combine(self, a, b):
        key = tuple(sorted([a, b]))
        if key in self.recipes:
            return self.recipes[key]

        if not self.client:
            self.show_error("OpenAI client not ready. Check your network or API key.")
            return None

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a crafting game engine. You will act like infinite craft. The user will give you two items to combine. Respond with ONLY the name of the resulting item (one or a few words). Be creative and logical with combinations. Do not add any commentary or prefixes."},
                    {"role": "user", "content": f"{a} and {b}"}
                ],
                temperature=0.7,
                max_tokens=50,
                timeout=30.0,  # be defensive on Android networks
            )
            result = response.choices[0].message.content.strip().title()
        except Exception as e:
            self.show_error(f"OpenAI request error: {e}")
            return None

        if result:
            self.recipes[key] = result
        return result

    # ---------- Persistence ----------

    def save_game(self):
        try:
            # save keys as "a|b" to avoid eval later
            recipes_serial = {"|".join(k): v for k, v in self.recipes.items()}
            data_to_save = {
                "recipes": recipes_serial,
                "inventory": sorted(list(self.inventory)) if self.inventory else ["fire", "water", "air", "earth"]
            }
            with open(self.GAME_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.show_error(f"Failed to save game: {e}")

    def load_game(self):
        self.inventory = {"fire", "water", "air", "earth"}
        self.recipes = {}
        try:
            if self.GAME_FILE and os.path.exists(self.GAME_FILE):
                with open(self.GAME_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # recipes, either new "a|b" or legacy "('a','b')"
                parsed = {}
                for k, v in data.get("recipes", {}).items():
                    if isinstance(k, str) and "|" in k:
                        a, b = k.split("|", 1)
                        parsed[tuple(sorted([a, b]))] = v
                    else:
                        # legacy path: extremely restricted eval
                        try:
                            t = tuple(eval(k, {"__builtins__": {}}))
                            if len(t) == 2 and all(isinstance(x, str) for x in t):
                                parsed[tuple(sorted(t))] = v
                        except Exception:
                            pass
                self.recipes = parsed
                inv = data.get("inventory")
                if inv:
                    self.inventory = set(inv)
        except Exception as e:
            # fall back to defaults, show error in UI after build
            self._startup_error = f"Failed to load save: {e}"

    # ---------- Popups ----------

    def show_error(self, message):
        # Always schedule on main thread to avoid cross-thread UI access
        def _open(_dt):
            content = BoxLayout(orientation='vertical', padding=10, spacing=10)
            content.add_widget(Label(text=message, text_size=(400, None), halign='center'))
            close_btn = Button(text='Close', size_hint_y=None, height=40)
            content.add_widget(close_btn)
            popup = Popup(title='Error', content=content, size_hint=(0.9, 0.6))
            close_btn.bind(on_press=popup.dismiss)
            popup.open()
        Clock.schedule_once(_open, 0)

if __name__ == '__main__':
    CraftingGameApp().run()
