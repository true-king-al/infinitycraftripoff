import os
import json
import threading
from functools import partial
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
import httpx

class CraftingGameApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = "https://infinite-craft-api.onrender.com/combine"  # ← update this
        self.GAME_FILE = None
        self.recipes = {}
        self.inventory = set()
        self.selected_elements = []
        self.element_buttons = {}

    def build(self):
        if platform not in ("android", "ios"):
            Window.size = (800, 600)

        self.title = "Infinite Craft Game"
        user_dir = Path(self.user_data_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        self.GAME_FILE = str(user_dir / "game_data.json")
        self.load_game()

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.status_label = Label(text='Select 2 elements to combine', size_hint_y=None, height=30)
        layout.add_widget(self.status_label)

        self.selected_label1 = Label(text='Select first element', size_hint_y=None, height=30)
        self.selected_label2 = Label(text='Select second element', size_hint_y=None, height=30)
        layout.add_widget(self.selected_label1)
        layout.add_widget(self.selected_label2)

        self.combine_button = Button(text='Combine Elements', size_hint_y=None, height=50, disabled=True)
        self.combine_button.bind(on_press=self.combine_elements)
        layout.add_widget(self.combine_button)

        clear_button = Button(text='Clear Selection', size_hint_y=None, height=40)
        clear_button.bind(on_press=self.clear_selection)
        layout.add_widget(clear_button)

        inventory_label = Label(text='Inventory (Tap to select):', size_hint_y=None, height=30)
        layout.add_widget(inventory_label)

        scroll = ScrollView()
        self.inventory_grid = GridLayout(cols=4, spacing=5, size_hint_y=None)
        self.inventory_grid.bind(minimum_height=self.inventory_grid.setter('height'))
        scroll.add_widget(self.inventory_grid)
        layout.add_widget(scroll)

        self.result_label = Label(text='', size_hint_y=None, height=60)
        layout.add_widget(self.result_label)

        self.update_inventory_display()
        return layout

    def update_inventory_display(self):
        self.inventory_grid.clear_widgets()
        self.element_buttons.clear()

        for element in sorted(self.inventory):
            btn = Button(text=element.title(), size_hint_y=None, height=60)
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

        for btn in self.element_buttons.values():
            btn.background_color = (1, 1, 1, 1)

        self.update_status()

    def update_status(self):
        status = f'Inventory: {len(self.inventory)} elements | '
        if len(self.selected_elements) == 0:
            status += 'Select 2 elements'
        elif len(self.selected_elements) == 1:
            status += f'Selected: {self.selected_elements[0]}'
        else:
            status += f'Selected: {self.selected_elements[0]} + {self.selected_elements[1]}'
        self.status_label.text = status

    def combine_elements(self, _btn):
        a, b = self.selected_elements
        self.result_label.text = 'Combining...'
        self.combine_button.disabled = True
        threading.Thread(target=self.combine_api_call, args=(a, b), daemon=True).start()

    def combine_api_call(self, a, b):
        result = None
        error = None
        try:
            # Render free plans sometimes cold-start; give it a generous timeout + one retry
            for attempt in range(2):
                resp = httpx.post(self.api_url, json={"a": a, "b": b}, timeout=60)
                try:
                    data = resp.json()
                except Exception:
                    data = {}

                if resp.status_code == 200 and "result" in data and data["result"]:
                    result = data["result"]
                    break

                # capture server-reported error if present
                error = data.get("error") or f"HTTP {resp.status_code}: {resp.text}"
                if attempt == 0:
                    # brief backoff then try once more (helps with cold starts)
                    import time; time.sleep(1.5)
                else:
                    break
        except Exception as e:
            error = f"Request error: {e}"

        Clock.schedule_once(partial(self.combination_done, a, b, result, error), 0)

    def combination_done(self, a, b, result, error, _dt):
        if result:
            if result.lower() not in self.inventory:
                self.result_label.text = f'New Discovery: {a} + {b} = {result}'
            else:
                self.result_label.text = f'Already known: {result}'
            self.inventory.add(result.lower())
            self.save_game()
            self.update_inventory_display()
        else:
            # show why it failed so we can actually debug
            self.result_label.text = f"Combination failed: {error or 'Unknown error'}"

        Clock.schedule_once(lambda dt: self.clear_selection(None), 2.5)

    def save_game(self):
        data = {
            "recipes": {},
            "inventory": sorted(list(self.inventory))
        }
        with open(self.GAME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load_game(self):
        self.inventory = {"fire", "water", "air", "earth"}
        try:
            if self.GAME_FILE and os.path.exists(self.GAME_FILE):
                with open(self.GAME_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                inv = data.get("inventory")
                if inv:
                    self.inventory = set(inv)
        except:
            pass

if __name__ == '__main__':
    CraftingGameApp().run()
