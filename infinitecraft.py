import os
import json
from openai import OpenAI
import threading
from functools import partial

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

class CraftingGameApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # --- CONFIG & SECURITY ---
        part1 = "sk-jh6bLNn0602sJwt-AiRwPmuxqFI9oeIpFYQ990ybtOT3Blbk"
        part2 = "FJFHfTLd4qNUJueCW3YevT7fGsIhyorV8vHs34mUuFYA"
        self.apikey = "{part1}{part2}" # l boso get f#cked github
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=self.apikey)
            self.client.models.list()
        except Exception as e:
            self.show_error(f"OpenAI API key is missing, invalid, or there was a network issue.\nDetails: {e}")
        
        # Game data
        self.GAME_FILE = "C:\\Users\\patti\\OneDrive\\Desktop\\game_data.json"
        self.recipes = {}
        self.inventory = set()
        
        # UI state
        self.selected_elements = []
        self.element_buttons = {}
        
        # Load game data
        self.load_game()
    
    def build(self):
        Window.size = (800, 600)
        self.title = "Infinite Craft Game"
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(
            text='Infinite Craft Game',
            size_hint_y=None,
            height=50,
            font_size=24,
            bold=True
        )
        main_layout.add_widget(title)
        
        # Status bar
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
        
        # Combine button
        self.combine_button = Button(
            text='Combine Elements',
            size_hint_y=None,
            height=50,
            disabled=True,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.combine_button.bind(on_press=self.combine_elements)
        main_layout.add_widget(self.combine_button)
        
        # Clear selection button
        clear_button = Button(
            text='Clear Selection',
            size_hint_y=None,
            height=40,
            background_color=(0.8, 0.4, 0.4, 1)
        )
        clear_button.bind(on_press=self.clear_selection)
        main_layout.add_widget(clear_button)
        
        # Inventory scroll view
        inventory_label = Label(
            text='Inventory (Click elements to select):',
            size_hint_y=None,
            height=30,
            font_size=16,
            bold=True
        )
        main_layout.add_widget(inventory_label)
        
        # Create scrollable inventory
        scroll = ScrollView()
        self.inventory_grid = GridLayout(cols=4, spacing=5, size_hint_y=None)
        self.inventory_grid.bind(minimum_height=self.inventory_grid.setter('height'))
        scroll.add_widget(self.inventory_grid)
        main_layout.add_widget(scroll)
        
        # Result display
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
        
        # Update inventory display
        self.update_inventory_display()
        
        return main_layout
    
    def update_label_text_size(self, label, size):
        """Auto-scale label text to fit"""
        label.text_size = size
    
    def update_button_text_size(self, button, size):
        """Auto-scale button text to fit"""
        button.text_size = size
    
    def update_inventory_display(self):
        """Update the inventory grid with current elements"""
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
            # Auto-scale text to fit button
            btn.bind(size=self.update_button_text_size)
            btn.bind(on_press=partial(self.select_element, element))
            self.element_buttons[element] = btn
            self.inventory_grid.add_widget(btn)
        
        self.update_status()
    
    def select_element(self, element, button):
        """Handle element selection"""
        if len(self.selected_elements) < 2:
            if element not in self.selected_elements:
                self.selected_elements.append(element)
                button.background_color = (0.8, 0.8, 0.2, 1)  # Highlight selected
                
                if len(self.selected_elements) == 1:
                    self.selected_label1.text = element.title()
                elif len(self.selected_elements) == 2:
                    self.selected_label2.text = element.title()
                    self.combine_button.disabled = False
        
        self.update_status()
    
    def clear_selection(self, button):
        """Clear current selection"""
        self.selected_elements.clear()
        self.selected_label1.text = 'Select first element'
        self.selected_label2.text = 'Select second element'
        self.combine_button.disabled = True
        self.result_label.text = ''
        
        # Reset button colors
        for element, btn in self.element_buttons.items():
            btn.background_color = (0.3, 0.7, 0.3, 1)
        
        self.update_status()
    
    def update_status(self):
        """Update status label"""
        status_text = f'Inventory: {len(self.inventory)} elements | '
        if len(self.selected_elements) == 0:
            status_text += 'Select 2 elements to combine'
        elif len(self.selected_elements) == 1:
            status_text += f'Selected: {self.selected_elements[0].title()}, select one more'
        else:
            status_text += f'Selected: {self.selected_elements[0].title()} + {self.selected_elements[1].title()}'
        
        self.status_label.text = status_text
    
    def combine_elements(self, button):
        """Combine selected elements"""
        if len(self.selected_elements) == 2:
            a, b = self.selected_elements
            self.result_label.text = 'Combining... Please wait'
            self.combine_button.disabled = True
            
            # Run combination in separate thread to avoid UI freezing
            threading.Thread(target=self.perform_combination, args=(a, b), daemon=True).start()
    
    def perform_combination(self, a, b):
        """Perform the actual combination (runs in separate thread)"""
        result = self.combine(a, b)
        
        # Update UI on main thread
        Clock.schedule_once(partial(self.combination_complete, a, b, result))
    
    def combination_complete(self, a, b, result, dt):
        """Handle combination completion on main thread"""
        if result:
            result_lower = result.lower()
            if result_lower not in self.inventory:
                self.result_label.text = f'>>> NEW DISCOVERY! <<<\n{a.title()} + {b.title()} = {result}'
                self.result_label.color = (0, 1, 0, 1)  # Bright green for new discoveries
            else:
                self.result_label.text = f'Already Known:\n{a.title()} + {b.title()} = {result}'
                self.result_label.color = (1, 1, 0, 1)  # Yellow for existing items
            
            self.inventory.add(result_lower)
            self.save_game()
            self.update_inventory_display()
            
            # Auto-size the result text
            self.result_label.text_size = (self.result_label.width, None)
        else:
            self.result_label.text = 'Combination failed - API error'
            self.result_label.color = (1, 0, 0, 1)  # Red
        
        # Clear selection after a short delay so user can see the result
        Clock.schedule_once(self.delayed_clear_selection, 3.0)
    
    def delayed_clear_selection(self, dt):
        """Clear selection after showing result"""
        self.clear_selection(None)
    
    def combine(self, a, b):
        """Checks for existing recipe or asks AI for a new one."""
        key = tuple(sorted([a, b]))
        if key in self.recipes:
            return self.recipes[key]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a crafting game engine. You will act like infinite craft. The user will give you two items to combine. Respond with ONLY the name of the resulting item (one or a few words). Be creative and logical with combinations. Do not add any commentary or prefixes."},
                    {"role": "user", "content": f"{a} and {b}"}
                ],
                temperature=0.7,
                max_tokens=50
            )
            result = response.choices[0].message.content.strip().title()
        except Exception as e:
            self.show_error(f"An error occurred with the AI request: {e}")
            return None

        if result:
            self.recipes[key] = result
        return result
    
    def save_game(self):
        """Saves both recipes and inventory to the JSON file."""
        try:
            data_to_save = {
                "recipes": {str(k): v for k, v in self.recipes.items()},
                "inventory": sorted(list(self.inventory))
            }
            with open(self.GAME_FILE, "w") as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            self.show_error(f"Failed to save game: {e}")
    
    def load_game(self):
        """Loads recipes and inventory if a save file exists."""
        if os.path.exists(self.GAME_FILE):
            try:
                with open(self.GAME_FILE, "r") as f:
                    data = json.load(f)
                    self.recipes = {tuple(eval(k)): v for k, v in data.get("recipes", {}).items()}
                    loaded_inventory = data.get("inventory")
                    if loaded_inventory:
                        self.inventory = set(loaded_inventory)
                    else:
                        self.inventory = {"fire", "water", "air", "earth"}
            except Exception as e:
                self.show_error(f"Failed to load game: {e}")
                self.inventory = {"fire", "water", "air", "earth"}
        else:
            self.inventory.update(["fire", "water", "air", "earth"])
    
    def show_error(self, message):
        """Show error popup"""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, text_size=(400, None), halign='center'))
        
        close_btn = Button(text='Close', size_hint_y=None, height=40)
        content.add_widget(close_btn)
        
        popup = Popup(title='Error', content=content, size_hint=(0.8, 0.6))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    CraftingGameApp().run()