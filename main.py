# main.py
import os, json, threading, textwrap
from functools import partial
from pathlib import Path

# --- safe httpx import so missing deps won't crash on launch
HTTPX_IMPORT_ERR = None
try:
    import httpx
except Exception as e:
    httpx = None
    HTTPX_IMPORT_ERR = str(e)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.utils import platform


PRIMARY = (0.16, 0.24, 0.33, 1)
PRIMARY_ACCENT = (0.22, 0.48, 0.70, 1)
SURFACE = (0.10, 0.10, 0.10, 1)
SURFACE_LIGHT = (0.20, 0.20, 0.20, 1)
TEXT = (1, 1, 1, 1)
TEXT_DIM = (0.85, 0.85, 0.85, 1)
HIGHLIGHT = (0.84, 0.73, 0.22, 1)


class CraftingGameApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = "https://infinite-craft-api.onrender.com/combine"

        self.GAME_FILE = None
        self.recipes = {}
        self.inventory = set()
        self.selected_elements = []
        self.element_buttons = {}
        self.min_chip_width_dp = 120

    def build(self):
        if platform not in ("android", "ios"):
            Window.size = (420, 800)
        Window.clearcolor = (0.06, 0.06, 0.07, 1)

        self.title = "Infinite Craft"
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        # storage path
        user_dir = Path(self.user_data_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        self.GAME_FILE = str(user_dir / "game_data.json")
        self.load_game()

        title = Label(text="Infinite Craft", font_size=sp(24), bold=True,
                      color=TEXT, size_hint_y=None, height=dp(34))
        root.add_widget(title)

        self.status_label = Label(text='Select 2 elements to combine',
                                  font_size=sp(14), color=TEXT_DIM,
                                  size_hint_y=None, height=dp(22))
        root.add_widget(self.status_label)

        chip_row = BoxLayout(orientation="horizontal", spacing=dp(8),
                             size_hint_y=None, height=dp(40))
        self.selected_label1 = self._pill("Select first element")
        self.selected_label2 = self._pill("Select second element")
        chip_row.add_widget(self.selected_label1)
        chip_row.add_widget(self.selected_label2)
        root.add_widget(chip_row)

        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(4))
        self.inventory_grid = GridLayout(cols=2, spacing=dp(8),
                                         padding=(0, dp(4)), size_hint_y=None)
        self.inventory_grid.bind(minimum_height=self.inventory_grid.setter('height'))
        scroll.add_widget(self.inventory_grid)
        root.add_widget(scroll)

        actions = BoxLayout(orientation="horizontal", spacing=dp(8),
                            size_hint_y=None, height=dp(50))
        self.combine_button = self._button("Combine", PRIMARY_ACCENT, disabled=True)
        self.combine_button.bind(on_press=self.combine_elements)
        clear_button = self._button("Clear", SURFACE_LIGHT)
        clear_button.bind(on_press=self.clear_selection)
        actions.add_widget(self.combine_button)
        actions.add_widget(clear_button)
        root.add_widget(actions)

        self.result_label = Label(text="", font_size=sp(15), color=TEXT,
                                  size_hint_y=None, height=dp(40))
        root.add_widget(self.result_label)

        self.update_inventory_display()
        Window.bind(size=lambda *_: self._reflow_columns())

        # If httpx failed to import, show why (won't crash)
        if HTTPX_IMPORT_ERR:
            self.result_label.text = f"Network library missing: {HTTPX_IMPORT_ERR}"

        return root

    # ---- UI helpers
    def _pill(self, txt):
        btn = Button(text=txt, disabled=True,
                     background_normal="", background_down="",
                     background_color=SURFACE_LIGHT,
                     color=TEXT, font_size=sp(15),
                     halign='center', valign='middle')
        btn.bind(size=lambda b, _: self._wrap_text(b))
        return btn

    def _button(self, txt, bg, disabled=False):
        btn = Button(text=txt, background_normal="", background_down="",
                     background_color=bg, color=TEXT, font_size=sp(16),
                     size_hint_y=None, height=dp(50),
                     halign='center', valign='middle', disabled=disabled)
        btn.bind(size=lambda b, _: self._wrap_text(b))
        return btn

    def _chip(self, element):
        btn = Button(text=self._pretty(element), background_normal="", background_down="",
                     background_color=SURFACE_LIGHT, color=TEXT, font_size=sp(16),
                     size_hint_y=None, height=dp(52), halign='center', valign='middle')
        btn.bind(size=lambda b, _: self._wrap_text(b))
        btn.bind(on_press=partial(self.select_element, element))
        return btn

    def _wrap_text(self, widget):
        widget.text_size = (widget.width - dp(16), None)

    def _pretty(self, name: str) -> str:
        if len(name) > 18 and " " not in name:
            name = "\n".join(textwrap.wrap(name, 12))
        return name.title()

    def _reflow_columns(self):
        cols = max(2, int(Window.width / dp(self.min_chip_width_dp)))
        self.inventory_grid.cols = cols

    # ---- Inventory UI
    def update_inventory_display(self):
        self._reflow_columns()
        self.inventory_grid.clear_widgets()
        self.element_buttons.clear()
        for element in sorted(self.inventory):
            btn = self._chip(element)
            self.element_buttons[element] = btn
            self.inventory_grid.add_widget(btn)
        self.update_status()

    # ---- Selection / Status
    def select_element(self, element, button):
        if len(self.selected_elements) < 2 and element not in self.selected_elements:
            self.selected_elements.append(element)
            button.background_color = HIGHLIGHT
            if len(self.selected_elements) == 1:
                self.selected_label1.text = self._pretty(element)
            elif len(self.selected_elements) == 2:
                self.selected_label2.text = self._pretty(element)
                self.combine_button.disabled = False
        self.update_status()

    def clear_selection(self, _btn):
        self.selected_elements.clear()
        self.selected_label1.text = "Select first element"
        self.selected_label2.text = "Select second element"
        self.combine_button.disabled = True
        self.result_label.text = ""
        self.result_label.markup = False
        for btn in self.element_buttons.values():
            btn.background_color = SURFACE_LIGHT
        self.update_status()

    def update_status(self):
        if len(self.selected_elements) == 0:
            suffix = "Select 2 elements"
        elif len(self.selected_elements) == 1:
            suffix = f"Selected: {self._pretty(self.selected_elements[0])}"
        else:
            a, b = self.selected_elements
            suffix = f"Selected: {self._pretty(a)} + {self._pretty(b)}"
        self.status_label.text = f"Inventory: {len(self.inventory)} elements | {suffix}"

    # ---- Combine flow
    def combine_elements(self, _btn):
        if HTTPX_IMPORT_ERR:
            self.result_label.text = f"Combination failed: {HTTPX_IMPORT_ERR}"
            return
            
        a, b = self.selected_elements
        a_lower, b_lower = a.lower(), b.lower()
        
        # Check if we already know this recipe
        if (a_lower, b_lower) in self.recipes:
            result = self.recipes[(a_lower, b_lower)]
            self.combination_done(a, b, result, None, 0)
            return
            
        self.result_label.text = "Combining…"
        self.combine_button.disabled = True
        threading.Thread(target=self.combine_api_call, args=(a, b), daemon=True).start()

    def combine_api_call(self, a, b):
        result = None
        error = None
        try:
            for attempt in range(2):
                resp = httpx.post(self.api_url, json={"a": a, "b": b}, timeout=60)
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                if resp.status_code == 200 and data.get("result"):
                    result = data["result"]
                    break
                error = data.get("error") or f"HTTP {resp.status_code}: {resp.text}"
                if attempt == 0:
                    import time; time.sleep(1.2)
        except Exception as e:
            error = f"Request error: {e}"
        Clock.schedule_once(partial(self.combination_done, a, b, result, error), 0)

    def combination_done(self, a, b, result, error, _dt):
        if result:
            pretty = self._pretty(result)
            new = result.lower() not in self.inventory
            self.inventory.add(result.lower())
            
            # Save the new recipe
            self.recipes[(a.lower(), b.lower())] = result.lower()
            
            self.save_game()
            self.update_inventory_display()
            self.result_label.markup = True
            self.result_label.text = f"{'New' if new else 'Known'}: {self._pretty(a)} + {self._pretty(b)} = [b]{pretty}[/b]"
        else:
            self.result_label.markup = False
            self.result_label.text = f"Combination failed: {error or 'Unknown error'}"
        Clock.schedule_once(lambda dt: self.clear_selection(None), 2.4)

    # ---- Persistence
    def save_game(self):
        # Convert tuple keys to string format for JSON compatibility
        recipes_dict = {}
        for (a, b), result in self.recipes.items():
            recipes_dict[f"{a}+{b}"] = result
        
        data = {
            "recipes": recipes_dict, 
            "inventory": sorted(list(self.inventory))
        }
        with open(self.GAME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load_game(self):
        # Load default starting inventory and recipes
        self.inventory = {"fire", "water", "air", "earth"}
        
        # Default recipes
        self.recipes = {
            ("fire", "water"): "steam",
            ("earth", "water"): "mud",
            ("earth", "plant"): "tree",
            ("fire", "air"): "smoke",
            ("air", "water"): "rain",
            ("air", "earth": "dust",
            ("fire", "earth"): "lava",
            ("mud", "earth"): "soil",
            ("soil", "water"): "plant",
            ("lava", "water"): "stone",
            ("stone", "air"): "sand",
            ("sand", "water"): "clay",
            ("clay", "fire"): "brick",
            ("plant", "water"): "algae",
            ("algae", "air"): "life",
            ("life", "earth"): "bacteria",
            ("bacteria", "air"): "virus",
            ("life", "water"): "fish",
            ("life", "earth"): "worm",
            ("worm", "earth"): "insect",
            ("fish", "air"): "bird",
            ("bird", "earth"): "chicken",
            ("chicken", "time"): "dinosaur",
            ("dinosaur", "meteor"): "extinction",
            ("life", "fire"): "human",
            ("human", "air"): "idea",
            ("human", "earth"): "home",
            ("human", "water"): "sweat",
            ("human", "tool"): "builder",
            ("builder", "stone"): "house",
            ("house", "fire"): "chimney",
            ("fire", "tree"): "campfire"
        }

        try:
            if self.GAME_FILE and os.path.exists(self.GAME_FILE):
                with open(self.GAME_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Load inventory
                inv = data.get("inventory")
                if inv:
                    self.inventory = set(inv)
                
                # Load recipes
                recipes_data = data.get("recipes", {})
                for key, result in recipes_data.items():
                    a, b = key.split('+')
                    self.recipes[(a, b)] = result
        except Exception as e:
            print(f"Error loading game: {e}")

if __name__ == "__main__":
    CraftingGameApp().run()
