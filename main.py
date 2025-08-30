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
from kivy.uix.floatlayout import FloatLayout
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
FAVORITE_COLOR = (0.94, 0.33, 0.31, 1)  # Red for favorite star

FONT_PATH = "fonts/DejaVuSans.ttf"

class FlexGridLayout(FloatLayout):
    """Custom layout that arranges items in a flexible grid with proper spacing"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = dp(8)
        self.spacing = dp(8)
        self.min_item_width = dp(80)  # Smaller default width
        self.bind(size=self.do_layout, pos=self.do_layout)
        
    def add_widget(self, widget, *args, **kwargs):
        super().add_widget(widget, *args, **kwargs)
        Clock.schedule_once(lambda dt: self.do_layout(), 0.1)
        
    def remove_widget(self, widget, *args, **kwargs):
        super().remove_widget(widget, *args, **kwargs)
        Clock.schedule_once(lambda dt: self.do_layout(), 0.1)
        
    def clear_widgets(self, *args, **kwargs):
        super().clear_widgets(*args, **kwargs)
        self.height = dp(50)  # Reset height when cleared
        
    def do_layout(self, *args):
        if not self.children:
            self.height = dp(50)
            return
            
        # Calculate available width
        available_width = self.width - (2 * self.padding)
        if available_width <= 0:
            return
            
        # Calculate columns based on minimum item width
        cols = max(1, int(available_width / self.min_item_width))
        col_width = available_width / cols
        
        # Position items
        row = 0
        col = 0
        max_row_height = dp(50)  # Smaller default height
        current_row_height = dp(50)
        y_offset = 0
        
        # Sort children by their order (reverse because Kivy adds children in reverse)
        sorted_children = list(reversed(self.children))
        
        for child in sorted_children:
            # Position the child
            x = self.x + self.padding + (col * col_width)
            y = self.top - self.padding - y_offset - child.height
            
            child.pos = (x, y)
            child.width = col_width - self.spacing
            
            # Track the tallest item in current row
            current_row_height = max(current_row_height, child.height)
            
            # Move to next column
            col += 1
            
            # If we've filled the row, move to next row
            if col >= cols:
                col = 0
                row += 1
                y_offset += current_row_height + self.spacing
                max_row_height = max(max_row_height, current_row_height)
                current_row_height = dp(50)
        
        # Set the total height of the layout
        total_height = y_offset + current_row_height + (2 * self.padding)
        self.height = max(dp(50), total_height)

class CraftingGameApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = "https://infinite-craft-api.onrender.com/combine"

        self.GAME_FILE = None
        self.recipes = {}
        self.inventory = set()
        self.favorites = set()
        self.selected_elements = []
        self.element_buttons = {}
        self.min_chip_width_dp = 80  # Smaller minimum width

    def build(self):
        if platform not in ("android", "ios"):
            Window.size = (420, 800)
        Window.clearcolor = (0.06, 0.06, 0.07, 1)

        self.title = "Infinite alchemy"
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))  # Reduced spacing

        # storage path
        user_dir = Path(self.user_data_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        self.GAME_FILE = str(user_dir / "game_data.json")
        self.load_game()

        title = Label(text="Infinite alchemy", font_size=sp(22), bold=True,  # Smaller title
                      color=TEXT, size_hint_y=None, height=dp(30))  # Smaller height
        root.add_widget(title)

        self.status_label = Label(text='Select 2 elements to combine',
                                  font_size=sp(12), color=TEXT_DIM,  # Smaller font
                                  size_hint_y=None, height=dp(18), font_name=FONT_PATH)  # Smaller height
        root.add_widget(self.status_label)

        chip_row = BoxLayout(orientation="horizontal", spacing=dp(6),  # Reduced spacing
                             size_hint_y=None, height=dp(45))  # Smaller height
        self.selected_label1 = self._pill("[color=#969696]Select first element")
        self.selected_label2 = self._pill("[color=#969696]Select second element")
        self.selected_label1.markup = True
        self.selected_label2.markup = True
        chip_row.add_widget(self.selected_label1)
        chip_row.add_widget(self.selected_label2)
        root.add_widget(chip_row)

        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(4))
        self.inventory_grid = FlexGridLayout(size_hint_y=None)
        self.inventory_grid.bind(height=self.inventory_grid.setter('height'))
        scroll.add_widget(self.inventory_grid)
        root.add_widget(scroll)

        actions = BoxLayout(orientation="horizontal", spacing=dp(6),  # Reduced spacing
                            size_hint_y=None, height=dp(40))  # Smaller height
        self.combine_button = self._button("Combine", PRIMARY_ACCENT, disabled=True)
        self.combine_button.bind(on_press=self.combine_elements)
        clear_button = self._button("Clear", SURFACE_LIGHT)
        clear_button.bind(on_press=self.clear_selection)
        actions.add_widget(self.combine_button)
        actions.add_widget(clear_button)
        root.add_widget(actions)

        self.result_label = Label(text="", font_size=sp(13), color=TEXT,  # Smaller font
                                  size_hint_y=None, height=dp(45), halign='center',  # Smaller height
                                  text_size=(None, None))
        root.add_widget(self.result_label)

        self.update_inventory_display()

        # If httpx failed to import, show why (won't crash)
        if HTTPX_IMPORT_ERR:
            self.result_label.text = f"Network library missing: {HTTPX_IMPORT_ERR}"

        return root

    # ---- UI helpers
    def _pill(self, txt):
        btn = Button(text=txt, disabled=True,
                     background_normal="", background_down="",
                     background_color=SURFACE_LIGHT,
                     color=TEXT, font_size=sp(13),  # Smaller font
                     halign='center', valign='middle',
                     size_hint_y=None, height=dp(40))  # Fixed smaller height
        btn.text_size = (btn.width - dp(8), None)  # Less padding
        btn.bind(width=lambda btn, width: setattr(btn, 'text_size', (width - dp(8), None)))
        return btn

    def _button(self, txt, bg, disabled=False):
        btn = Button(text=txt, background_normal="", background_down="",
                     background_color=bg, color=TEXT, font_size=sp(14),  # Smaller font
                     size_hint_y=None, height=dp(40),  # Smaller height
                     halign='center', valign='middle', disabled=disabled)
        return btn

    def _chip(self, element):
        # Create a container for the element button and favorite star
        container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))  # Reduced spacing
        
        # Main element button with auto-sizing
        btn = Button(text=self._pretty(element), background_normal="", background_down="",
                     background_color=SURFACE_LIGHT, color=TEXT, font_size=sp(12),  # Smaller font
                     size_hint_y=None, halign='center', valign='middle')
        
        # Auto-size the button based on content
        self._auto_size_button(btn)
        btn.bind(width=lambda b, w: self._auto_size_button(b))
        btn.bind(on_press=partial(self.select_element, element))
        
        # Favorite star button - smaller
        is_favorite = element.lower() in self.favorites
        star_text = "★" if is_favorite else "☆"
        star_color = FAVORITE_COLOR if is_favorite else TEXT_DIM
        
        star_btn = Button(text=star_text, background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), color=star_color, font_size=sp(14),  # Smaller font
                         size_hint_y=None, height=dp(20), halign='center', valign='middle', font_name=FONT_PATH)  # Smaller height
        star_btn.bind(on_press=partial(self.toggle_favorite, element))
        
        container.add_widget(btn)
        container.add_widget(star_btn)
        
        # Set container height to sum of its children
        container.height = btn.height + star_btn.height + dp(2)  # Include spacing
        
        return container, btn

    def _auto_size_button(self, widget):
        """Auto-size button based on text content - more compact"""
        if not widget.text:
            widget.height = dp(32)  # Smaller minimum height
            widget.text_size = (widget.width - dp(8), None)  # Less padding
            return
        
        # Set text_size to constrain width but allow height to grow
        widget.text_size = (widget.width - dp(8), None)
        
        # Calculate required height based on text - more compact
        lines = widget.text.count('\n') + 1
        if hasattr(widget, 'markup') and widget.markup:
            import re
            clean_text = re.sub(r'\[.*?\]', '', widget.text)
            lines = clean_text.count('\n') + 1
        
        # Smaller, more compact sizing
        base_height = dp(32)  # Smaller base
        line_height = sp(widget.font_size) * 1.1  # Tighter line spacing
        calculated_height = max(base_height, line_height * lines + dp(8))  # Less padding
        
        widget.height = calculated_height

    def _pretty(self, name: str) -> str:
        # More aggressive text wrapping for smaller buttons
        if len(name) > 12:  # Wrap earlier
            if " " in name:
                words = name.split()
                if len(words) > 1:
                    mid = len(words) // 2
                    name = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
            else:
                # Wrap long single words earlier
                name = "\n".join(textwrap.wrap(name, 8))  # Smaller wrap width
        return name.title()

    # ---- Favorites system
    def toggle_favorite(self, element, star_button):
        """Toggle favorite status of an element"""
        element_lower = element.lower()
        if element_lower in self.favorites:
            self.favorites.remove(element_lower)
            star_button.text = "☆"
            star_button.color = TEXT_DIM
        else:
            self.favorites.add(element_lower)
            star_button.text = "★"
            star_button.color = FAVORITE_COLOR
        
        self.save_game()
        self.update_inventory_display()  # Refresh to reorder

    def get_sorted_inventory(self):
        """Return inventory sorted with favorites first, then alphabetically"""
        favorites_list = [elem for elem in self.inventory if elem in self.favorites]
        non_favorites_list = [elem for elem in self.inventory if elem not in self.favorites]
        
        # Sort each group alphabetically
        favorites_list.sort()
        non_favorites_list.sort()
        
        return favorites_list + non_favorites_list

    # ---- Inventory UI
    def update_inventory_display(self):
        self.inventory_grid.clear_widgets()
        self.element_buttons.clear()
        
        # Use sorted inventory with favorites first
        for element in self.get_sorted_inventory():
            container, btn = self._chip(element)
            self.element_buttons[element] = btn
            self.inventory_grid.add_widget(container)
        self.update_status()

    # ---- Selection / Status
    def select_element(self, element, button):
        if len(self.selected_elements) < 2:
            self.selected_elements.append(element)
            button.background_color = HIGHLIGHT
            self.selected_label1.markup = True
            self.selected_label2.markup = True
            if len(self.selected_elements) == 1:
                self.selected_label1.text = f"[color=#969696][b]{self._pretty(element)}[/b]"
            elif len(self.selected_elements) == 2:
                self.selected_label2.text = f"[color=#969696][b]{self._pretty(element)}[/b]"
                self.combine_button.disabled = False
        self.update_status()

    def clear_selection(self, _btn):
        self.selected_elements.clear()
        self.selected_label1.text = "[color=#969696]Select first element"
        self.selected_label2.text = "[color=#969696]Select second element"
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
        
        favorites_count = len(self.favorites)
        fav_text = f" | ★ {favorites_count}" if favorites_count > 0 else ""
        self.status_label.text = f"Inventory: {len(self.inventory)} elements{fav_text}"

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
            self.combination_done(a, b, result, None, True, 0)
            return

        # Check if we already know this recipe 2x
        if (b_lower, a_lower) in self.recipes:
            result = self.recipes[(b_lower, a_lower)]
            self.combination_done(a, b, result, None, True, 0)
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
        Clock.schedule_once(partial(self.combination_done, a, b, result, error, False), 0)

    def combination_done(self, a, b, result, error, known, _dt):
        if result:
            pretty = self._pretty(result)
            discovery = result.lower() not in self.inventory #if you just discovered this
            new = result.lower() in self.inventory and not known #if recipe is new but item is not
            self.inventory.add(result.lower())
            
            # Save the new recipe
            self.recipes[(a.lower(), b.lower())] = result.lower()
            
            self.save_game()
            self.update_inventory_display()
            self.result_label.markup = True
            if discovery:
                self.result_label.text = f"[color=#FFD700]New Discovery\n[b]{pretty}[/b]"
            elif new:
                self.result_label.text = f"[color=#6632a8]New Recipe\n{self._pretty(a)} + {self._pretty(b)} = [b]{pretty}[/b]"
            else:
                self.result_label.text = f"[color=#802c11]Already known\n{self._pretty(a)} + {self._pretty(b)} = [b]{pretty}[/b]"
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
            "inventory": sorted(list(self.inventory)),
            "favorites": sorted(list(self.favorites))
        }
        with open(self.GAME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load_game(self):
        # Load default starting inventory and recipes
        self.inventory = {"fire", "water", "air", "earth"}
        self.favorites = set()
        
        # Default recipes
        self.recipes = {
            ("fire", "water"): "steam",
            ("earth", "water"): "mud",
            ("earth", "plant"): "tree",
            ("fire", "air"): "smoke",
            ("air", "water"): "rain",
            ("air", "earth"): "dust",
            ("fire", "earth"): "lava",
            ("mud", "earth"): "soil",
            ("soil", "water"): "plant",
            ("lava", "water"): "stone",
            ("stone", "air"): "sand",
            ("sand", "water"): "clay",
            ("clay", "fire"): "brick",
            ("plant", "water"): "algae",
            ("algae", "air"): "life",
            ("life", "air"): "bacteria",
            ("bacteria", "air"): "virus",
            ("life", "water"): "fish",
            ("life", "earth"): "worm",
            ("worm", "earth"): "insect",
            ("fish", "air"): "bird",
            ("bird", "earth"): "chicken",
            ("chicken", "time"): "dinosaur",
            ("dinosaur", "meteor"): "extinction",
            ("life", "clay"): "human",
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
                
                # Load favorites
                fav = data.get("favorites")
                if fav:
                    self.favorites = set(fav)
                
                # Load recipes
                recipes_data = data.get("recipes", {})
                for key, result in recipes_data.items():
                    a, b = key.split('+')
                    self.recipes[(a, b)] = result
        except Exception as e:
            print(f"Error loading game: {e}")

if __name__ == "__main__":
    CraftingGameApp().run()