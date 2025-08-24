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
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
import httpx

class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.2, 0.3, 0.5, 1)  # Dark blue
        self.color = (1, 1, 1, 1)  # White text
        self.font_size = dp(14)
        self.bold = True
        
        with self.canvas.before:
            Color(0.2, 0.3, 0.5, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class ElementButton(Button):
    def __init__(self, element, **kwargs):
        super().__init__(**kwargs)
        self.element = element
        self.background_normal = ''
        self.background_color = (0.9, 0.9, 0.9, 0)  # Transparent
        self.color = (0.2, 0.2, 0.2, 1)  # Dark text
        self.font_size = dp(12)
        self.bold = True
        self.size_hint_y = None
        self.height = dp(50)
        
        # Element-specific colors
        element_colors = {
            'fire': (1, 0.4, 0.2, 0.8),
            'water': (0.2, 0.6, 1, 0.8),
            'air': (0.8, 0.9, 1, 0.8),
            'earth': (0.6, 0.4, 0.2, 0.8),
            'lightning': (1, 1, 0.2, 0.8),
            'steam': (0.7, 0.7, 0.9, 0.8),
            'storm': (0.4, 0.4, 0.7, 0.8),
            'wind': (0.9, 0.9, 0.9, 0.8),
            'clouds': (0.8, 0.8, 0.8, 0.8),
            'magma': (1, 0.2, 0, 0.8),
            'mud': (0.5, 0.3, 0.1, 0.8),
            'rain': (0.4, 0.7, 1, 0.8),
        }
        
        self.element_color = element_colors.get(element.lower(), (0.6, 0.7, 0.8, 0.8))
        
        with self.canvas.before:
            Color(*self.element_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(1, 1, 1, 0.3)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=dp(2))
            
        self.bind(pos=self.update_graphics, size=self.update_graphics)
    
    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12))
    
    def set_selected(self, selected=True):
        with self.canvas.before:
            self.canvas.before.clear()
            if selected:
                Color(1, 0.8, 0.2, 1)  # Golden selection
                self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
                Color(1, 0.6, 0, 1)
                self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=dp(3))
            else:
                Color(*self.element_color)
                self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
                Color(1, 1, 1, 0.3)
                self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=dp(2))
        self.update_graphics()

class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = (0.9, 0.9, 0.9, 1)  # Light text
        self.font_size = dp(14)
        self.text_size = (None, None)

class CraftingGameApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = "https://infinite-craft-api.onrender.com/combine"
        self.GAME_FILE = None
        self.recipes = {}
        self.inventory = set()
        self.selected_elements = []
        self.element_buttons = {}

    def build(self):
        # Set window properties for mobile
        if platform in ("android", "ios"):
            Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_expo'}
            Window.softinput_mode = "below_target"
        else:
            Window.size = (400, 700)  # Mobile-like aspect ratio for desktop testing

        self.title = "⚗️ Infinite Craft"
        
        # Setup data directory
        user_dir = Path(self.user_data_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        self.GAME_FILE = str(user_dir / "game_data.json")
        self.load_game()

        # Main layout with dark background
        main_layout = BoxLayout(orientation='vertical')
        with main_layout.canvas.before:
            Color(0.1, 0.1, 0.15, 1)  # Dark blue background
            self.bg_rect = RoundedRectangle(pos=main_layout.pos, size=main_layout.size)
        main_layout.bind(pos=self.update_bg, size=self.update_bg)

        # Content layout with padding
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        
        # Header section
        header_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120), spacing=dp(5))
        
        # Title
        title_label = StyledLabel(
            text='⚗️ Infinite Craft', 
            font_size=dp(24), 
            bold=True, 
            size_hint_y=None, 
            height=dp(40),
            color=(1, 0.9, 0.3, 1)  # Golden title
        )
        header_box.add_widget(title_label)
        
        # Status
        self.status_label = StyledLabel(
            text='Select 2 elements to combine', 
            size_hint_y=None, 
            height=dp(25),
            font_size=dp(12)
        )
        header_box.add_widget(self.status_label)
        
        # Selection display
        selection_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        
        self.selected_label1 = StyledLabel(text='Select first', font_size=dp(11), halign='center')
        self.selected_label1.bind(size=self.selected_label1.setter('text_size'))
        
        plus_label = StyledLabel(text='+', font_size=dp(18), size_hint_x=None, width=dp(20))
        
        self.selected_label2 = StyledLabel(text='Select second', font_size=dp(11), halign='center')
        self.selected_label2.bind(size=self.selected_label2.setter('text_size'))
        
        selection_box.add_widget(self.selected_label1)
        selection_box.add_widget(plus_label)
        selection_box.add_widget(self.selected_label2)
        header_box.add_widget(selection_box)
        
        layout.add_widget(header_box)

        # Action buttons
        button_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        self.combine_button = StyledButton(text='🔥 Combine', disabled=True)
        self.combine_button.bind(on_press=self.combine_elements)
        
        clear_button = StyledButton(text='🗑️ Clear', size_hint_x=0.4)
        clear_button.bind(on_press=self.clear_selection)
        
        button_box.add_widget(self.combine_button)
        button_box.add_widget(clear_button)
        layout.add_widget(button_box)

        # Result display
        self.result_label = StyledLabel(
            text='', 
            size_hint_y=None, 
            height=dp(60),
            font_size=dp(13),
            color=(0.3, 1, 0.3, 1),  # Green for results
            halign='center'
        )
        self.result_label.bind(size=self.result_label.setter('text_size'))
        layout.add_widget(self.result_label)

        # Inventory section
        inventory_header = StyledLabel(
            text=f'📦 Inventory ({len(self.inventory)} elements)', 
            size_hint_y=None, 
            height=dp(30),
            font_size=dp(16),
            bold=True
        )
        layout.add_widget(inventory_header)
        self.inventory_header = inventory_header

        # Scrollable inventory
        scroll = ScrollView(do_scroll_x=False)
        self.inventory_grid = GridLayout(
            cols=3 if platform in ("android", "ios") else 4, 
            spacing=dp(8), 
            size_hint_y=None,
            padding=dp(5)
        )
        self.inventory_grid.bind(minimum_height=self.inventory_grid.setter('height'))
        scroll.add_widget(self.inventory_grid)
        layout.add_widget(scroll)

        main_layout.add_widget(layout)
        
        self.update_inventory_display()
        return main_layout
    
    def update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def update_inventory_display(self):
        self.inventory_grid.clear_widgets()
        self.element_buttons.clear()

        for element in sorted(self.inventory):
            btn = ElementButton(element, text=element.title())
            btn.bind(on_press=partial(self.select_element, element))
            self.element_buttons[element] = btn
            self.inventory_grid.add_widget(btn)

        # Update inventory count
        self.inventory_header.text = f'📦 Inventory ({len(self.inventory)} elements)'
        self.update_status()

    def select_element(self, element, button):
        if len(self.selected_elements) < 2 and element not in self.selected_elements:
            self.selected_elements.append(element)
            button.set_selected(True)

            if len(self.selected_elements) == 1:
                self.selected_label1.text = f'🔹 {element.title()}'
                self.selected_label1.color = (0.3, 1, 0.3, 1)
            elif len(self.selected_elements) == 2:
                self.selected_label2.text = f'🔹 {element.title()}'
                self.selected_label2.color = (0.3, 1, 0.3, 1)
                self.combine_button.disabled = False

        self.update_status()

    def clear_selection(self, _btn):
        # Reset visual states
        for element in self.selected_elements:
            if element in self.element_buttons:
                self.element_buttons[element].set_selected(False)
        
        self.selected_elements.clear()
        self.selected_label1.text = 'Select first'
        self.selected_label1.color = (0.9, 0.9, 0.9, 1)
        self.selected_label2.text = 'Select second'
        self.selected_label2.color = (0.9, 0.9, 0.9, 1)
        self.combine_button.disabled = True
        self.result_label.text = ''

        self.update_status()

    def update_status(self):
        count = len(self.inventory)
        if len(self.selected_elements) == 0:
            status = f'📊 {count} elements | Select 2 to combine'
        elif len(self.selected_elements) == 1:
            status = f'📊 {count} elements | Select 1 more'
        else:
            a, b = self.selected_elements
            status = f'📊 {count} elements | Ready: {a.title()} + {b.title()}'
        self.status_label.text = status

    def combine_elements(self, _btn):
        a, b = self.selected_elements
        self.result_label.text = '⚡ Combining elements...'
        self.result_label.color = (1, 1, 0.3, 1)  # Yellow for processing
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

                if resp.status_code == 200 and "result" in data and data["result"]:
                    result = data["result"]
                    break

                error = data.get("error") or f"HTTP {resp.status_code}: {resp.text}"
                if attempt == 0:
                    import time; time.sleep(1.5)
                else:
                    break
        except Exception as e:
            error = f"Request error: {e}"

        Clock.schedule_once(partial(self.combination_done, a, b, result, error), 0)

    def combination_done(self, a, b, result, error, _dt):
        if result:
            is_new = result.lower() not in self.inventory
            self.inventory.add(result.lower())
            
            if is_new:
                self.result_label.text = f'✨ NEW: {a.title()} + {b.title()} = {result.title()}!'
                self.result_label.color = (0.3, 1, 0.3, 1)  # Bright green for new
            else:
                self.result_label.text = f'🔄 Known: {result.title()}'
                self.result_label.color = (1, 0.8, 0.3, 1)  # Orange for known
                
            self.save_game()
            self.update_inventory_display()
        else:
            self.result_label.text = f'❌ Failed: {error or "Unknown error"}'
            self.result_label.color = (1, 0.3, 0.3, 1)  # Red for error

        Clock.schedule_once(lambda dt: self.clear_selection(None), 3.0)

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
