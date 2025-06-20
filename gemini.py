#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import json
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox, font, filedialog
import threading
import datetime
import re
import math # For mathematical operations to draw the circle

class GeminiGUI:
    """
    A modern, Tkinter-based GUI for chatting with the Gemini API,
    inspired by a clean, two-panel layout.
    """
    BG_COLOR = "#F4F6F8"
    LEFT_PANEL_BG = "#FFFFFF"
    CHAT_BG_COLOR = "#FFFFFF"
    TEXT_COLOR = "#212121"
    INPUT_BG_COLOR = "#EAECEE"
    
    # Google Design Language 2013-ish Blue colors
    SEND_BUTTON_COLOR = "#4285F4"  # Vibrant Google Blue
    SEND_BUTTON_HOVER_COLOR = "#3367D6" # Darker shade for hover
    NEW_CHAT_BUTTON_COLOR = "#669DF6"  # Lighter Google Blue
    NEW_CHAT_BUTTON_HOVER_COLOR = "#4A90E2" # Slightly darker for hover
    
    SEPARATOR_COLOR = "#D5DBDB"
    USER_COLOR = "#007ACC"
    GEMINI_COLOR = "#2ECC71"
    ERROR_COLOR = "#E74C3C"
    ACTIVE_CHAT_BG = "#E8F0FE" # Very light blue for active chat highlight

    def __init__(self, root):
        """
        Initializes the main application window and its widgets.
        """
        self.root = root
        self.root.title("Gemini Chat")
        self.root.geometry("900x600")
        self.root.configure(bg=self.BG_COLOR)
        self.root.minsize(700, 500)

        # --- Font Configuration ---
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Arial", size=11) # Increased default font size for readability
        self.bold_font = font.Font(family="Arial", size=12, weight="bold") # Increased bold font size
        
        self.api_key = os.getenv("GEMINI_API_KEY")

        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        self.headers = {'Content-Type': 'application/json'}
        
        self.all_conversations = [] 
        self.current_chat_index = -1 
        self.conversation_history = [] 
        
        self.thinking_frame = None  # 
        self.thinking_canvas = None # 
        self.animation_job = None   #
        self.angle = 0              

        if not self.api_key:
            messagebox.showerror(
                "API Key Error",
                "The GEMINI_API_KEY environment variable is not set.\nPlease set it and restart the application."
            )
            self.root.destroy()
            sys.exit(1)
        
        self.create_main_layout()
        self.new_chat(initial_load=True) 

        self.chat_display.tag_config('user', foreground=self.USER_COLOR, font=self.bold_font, spacing1=2, spacing3=2) 
        self.chat_display.tag_config('gemini', foreground=self.GEMINI_COLOR, spacing1=2, spacing3=2) 
        self.chat_display.tag_config('error', foreground=self.ERROR_COLOR, font=("Arial", 10, "italic"))
        self.chat_display.tag_config('status', foreground="#AAAAAA", font=("Arial", 9, "italic"), justify='center') # Still keeping this tag for general status if needed
        self.chat_display.tag_config('code_block', background="#EFEFEF", font=("Consolas", 10), 
                                      borderwidth=1, relief="solid", lmargin1=10, lmargin2=10, rmargin=10)
        self.chat_display.tag_config('code_lang', font=("Consolas", 9, "bold"), foreground="#666666", 
                                     lmargin1=10, lmargin2=10, rmargin=10)


    def create_main_layout(self):
        """Creates the main two-panel layout."""
        paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, bg=self.SEPARATOR_COLOR, relief=tk.FLAT)
        paned_window.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(paned_window, bg=self.LEFT_PANEL_BG, width=220)
        self.create_left_panel(left_panel)
        paned_window.add(left_panel, stretch="never")

        right_panel = tk.Frame(paned_window, bg=self.BG_COLOR)
        self.create_right_panel(right_panel)
        paned_window.add(right_panel, stretch="always")
        
        paned_window.sash_place(0, 220, 0)

    def create_left_panel(self, parent):
        """Creates the widgets for the left 'Previous Chats' panel."""
        parent.pack_propagate(False) 
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        title_label = tk.Label(parent, text="Previous Chats", font=("Arial", 14, "bold"), bg=self.LEFT_PANEL_BG, fg=self.TEXT_COLOR, anchor="w")
        title_label.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))

        self.chat_list_frame = tk.Frame(parent, bg=self.LEFT_PANEL_BG)
        self.chat_list_frame.grid(row=1, column=0, sticky="nsew", padx=15)
        
        new_chat_button = tk.Button(
            parent,
            text="+ New Chat",
            command=self.new_chat,
            font=self.bold_font,
            bg=self.NEW_CHAT_BUTTON_COLOR, # New Google blue color
            fg="#ffffff", # Text color explicitly white for contrast
            activebackground=self.NEW_CHAT_BUTTON_HOVER_COLOR, # New Google blue hover color
            relief="flat", bd=0, padx=20, pady=10, cursor="hand2"
        )
        new_chat_button.grid(row=2, column=0, sticky="ew", padx=15, pady=15)

    def create_right_panel(self, parent):
        """Creates the widgets for the right chat panel."""
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, state='disabled', font=("Arial", 11),
            bg=self.CHAT_BG_COLOR, fg=self.TEXT_COLOR, padx=20, pady=20,
            bd=0, relief="flat", insertbackground=self.TEXT_COLOR
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=(0,15), pady=(15,0))
        
        bottom_frame = tk.Frame(parent, bg=self.BG_COLOR)
        bottom_frame.grid(row=1, column=0, sticky="ew", padx=(0,15), pady=15)
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        input_frame = tk.Frame(bottom_frame, bg=self.INPUT_BG_COLOR)
        input_frame.grid(row=0, column=0, sticky="ew", ipady=2, padx=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_entry = tk.Entry(
            input_frame, font=("Arial", 11), bg=self.INPUT_BG_COLOR, fg=self.TEXT_COLOR,
            bd=0, relief="flat", insertbackground=self.TEXT_COLOR
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=15, pady=8)
        self.input_entry.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(
            bottom_frame, text="Send", command=self.send_message_event, font=self.bold_font,
            bg=self.SEND_BUTTON_COLOR, # New Google blue color
            fg="#ffffff", # Text color explicitly white for contrast
            activebackground=self.SEND_BUTTON_HOVER_COLOR, # New Google blue hover color
            activeforeground="#ffffff", relief="flat", bd=0, padx=25, pady=8, cursor="hand2"
        )
        self.send_button.grid(row=0, column=1, sticky="e")

    def new_chat(self, initial_load=False):
        """
        Clears the conversation and starts a new one.
        If it's not the initial load, saves the current chat if it has content.
        """
        if not initial_load and self.current_chat_index != -1 and self.conversation_history:
            if self.all_conversations[self.current_chat_index]["title"].startswith("New Chat"):
                first_message_text = ""
                for msg_entry in self.conversation_history:
                    if msg_entry.get("role") == "user" and msg_entry.get("parts"):
                        for part in msg_entry["parts"]:
                            if part.get("text"):
                                first_message_text = part["text"]
                                break
                    if first_message_text:
                        break

                if first_message_text:
                    self.all_conversations[self.current_chat_index]["title"] = first_message_text[:30] + "..." if len(first_message_text) > 30 else first_message_text
                else:
                    self.all_conversations[self.current_chat_index]["title"] = f"Chat {datetime.datetime.now().strftime('%H:%M %b %d')}"
            
        new_chat_title = f"New Chat {len(self.all_conversations) + 1}"
        new_chat_entry = {"title": new_chat_title, "history": []}
        self.all_conversations.append(new_chat_entry)
        self.current_chat_index = len(self.all_conversations) - 1
        self.conversation_history = self.all_conversations[self.current_chat_index]["history"]

        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')
        self.input_entry.focus_set()
        
        self.update_chat_list_ui()

        if not initial_load:
            messagebox.showinfo("New Chat", "Previous conversation has been cleared and a new one started.")

    def load_chat_session(self, index):
        """
        Loads a selected chat session into the main chat display.
        Saves the current chat before loading a new one.
        """
        if self.current_chat_index == index:
            return

        # Ensure any active thinking indicator is hidden before loading new content
        self.hide_thinking_indicator()

        if self.current_chat_index != -1 and self.conversation_history:
            if self.all_conversations[self.current_chat_index]["title"].startswith("New Chat"):
                first_message_text = ""
                if self.conversation_history:
                    for msg_entry in self.conversation_history:
                        if msg_entry.get("role") == "user" and msg_entry.get("parts"):
                            for part in msg_entry["parts"]:
                                if part.get("text"):
                                    first_message_text = part["text"]
                                    break
                        if first_message_text:
                            break
                if first_message_text:
                    self.all_conversations[self.current_chat_index]["title"] = first_message_text[:30] + "..." if len(first_message_text) > 30 else first_message_text
                else:
                    self.all_conversations[self.current_chat_index]["title"] = f"Chat {datetime.datetime.now().strftime('%H:%M %b %d')}"


        self.current_chat_index = index
        self.conversation_history = self.all_conversations[index]["history"]

        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)

        for message_entry in self.conversation_history:
            role = message_entry['role']
            text_parts = [part['text'] for part in message_entry['parts'] if 'text' in part]
            message_text = "".join(text_parts)
            self._insert_message_directly_into_display(role, message_text)

        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
        self.input_entry.focus_set()
        
        self.update_chat_list_ui()

    def update_chat_list_ui(self):
        """
        Updates the buttons in the left panel to reflect the current list of chat sessions.
        Highlights the currently active chat.
        """
        for widget in self.chat_list_frame.winfo_children():
            widget.destroy()

        for i, chat_entry in enumerate(self.all_conversations):
            button_bg = self.ACTIVE_CHAT_BG if i == self.current_chat_index else self.NEW_CHAT_BUTTON_COLOR
            button_fg = self.TEXT_COLOR if i == self.current_chat_index else "#ffffff" # Text color
            button_hover_bg = self.ACTIVE_CHAT_BG if i == self.current_chat_index else self.NEW_CHAT_BUTTON_HOVER_COLOR

            chat_button = tk.Button(
                self.chat_list_frame, 
                text=chat_entry["title"],
                command=lambda idx=i: self.load_chat_session(idx),
                bg=button_bg, 
                fg=button_fg, # Set foreground dynamically
                relief="flat", 
                font=("Arial", 10), 
                anchor="w",
                activebackground=button_hover_bg,
                cursor="hand2"
            )
            chat_button.pack(fill=tk.X, pady=3)

    def _insert_message_directly_into_display(self, role, message_text):
        """
        A helper function to display a message directly into the ScrolledText widget.
        Used when loading existing history, it applies appropriate parsing for 'model' roles.
        """
        self.chat_display.config(state='normal')

        if role == 'model':
            self.chat_display.insert(tk.END, "Gemini: ", 'gemini')
            self._insert_gemini_parsed_message_content(message_text)
        elif role == 'user':
            prefix = "You: "
            self.chat_display.insert(tk.END, f"{prefix}{message_text}\n\n", (role,))
        else: # For status, error etc.
            self.chat_display.insert(tk.END, f"{message_text}\n\n", (role,))
            
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)


    def display_message(self, who, message, tags=None):
        """
        Displays a message in the chat window with appropriate styling.
        This also handles hiding the thinking indicator.
        """
        self.hide_thinking_indicator()

        self.chat_display.config(state='normal')

        if who == 'gemini':
            self.chat_display.insert(tk.END, "Gemini: ", 'gemini')
            self._insert_gemini_parsed_message_content(message)
        else:
            prefix = "You: " if who == 'user' else "" # No prefix for status/error messages
            current_tags = tags if tags else (who,)
            self.chat_display.insert(tk.END, f"{prefix}{message}\n\n", current_tags)
        
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def _insert_gemini_parsed_message_content(self, message):
        """
        Parses and inserts Gemini's response content, handling code block formatting and save buttons.
        This is a helper for display_message and _insert_message_directly_into_display for 'model' roles.
        """
        last_idx = 0
        CODE_BLOCK_REGEX = re.compile(r"```(?P<lang>\w*)\s*\n(?P<code>.*?)\n```", re.DOTALL)

        for match in CODE_BLOCK_REGEX.finditer(message):
            if match.start() > last_idx:
                self.chat_display.insert(tk.END, message[last_idx:match.start()], 'gemini')

            lang = match.group('lang')
            code_content = match.group('code').strip()

            self.chat_display.insert(tk.END, "\n", 'gemini') 

            if lang:
                self.chat_display.insert(tk.END, f"Language: {lang}\n", 'code_lang')
            
            self.chat_display.insert(tk.END, code_content + "\n", 'code_block')

            save_button = tk.Button(self.chat_display, text="Save Code to File",
                                    command=lambda c=code_content: self.save_code_to_file(c),
                                    bg=self.SEND_BUTTON_COLOR, fg="#ffffff",
                                    activebackground=self.SEND_BUTTON_HOVER_COLOR,
                                    relief="flat", bd=0, padx=10, pady=5, cursor="hand2")
            self.chat_display.window_create(tk.END, window=save_button)
            self.chat_display.insert(tk.END, "\n\n", 'gemini') 
            
            last_idx = match.end()

        if last_idx < len(message):
            self.chat_display.insert(tk.END, message[last_idx:], 'gemini')
        
        self.chat_display.insert(tk.END, "\n", 'gemini')

    def save_code_to_file(self, code_content):
        """
        Prompts the user to save the provided code content to a file.
        """
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("All Files", "*.*"), 
                ("Python files", "*.py"), 
                ("Text files", "*.txt"), 
                ("Markdown files", "*.md"),
                ("JavaScript files", "*.js"),
                ("HTML files", "*.html"),
                ("CSS files", "*.css")
                ("JSON files", "*.json"),
                ("XML files", "*.xml"),
                ("Java files", "*.java"),
                ("C files", "*.c"),
                ("C++ files", "*.cpp"),
                ("Ruby files", "*.rb"),
                ("Go files", "*.go"),
                ("PHP files", "*.php")
                ("Shell scripts", "*.sh"),
                ("SQL files", "*.sql"),
                ("YAML files", "*.yaml"),
                ("CSV files", "*.csv"),
            ]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code_content)
                messagebox.showinfo("Save Successful", f"Code saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file:\n{e}")

    def send_message_event(self, event=None):
        """Handles the send message action."""
        user_prompt = self.input_entry.get().strip()
        if not user_prompt or self.send_button['state'] == 'disabled':
            return
        
        if not self.conversation_history and self.current_chat_index != -1 and self.all_conversations[self.current_chat_index]["title"].startswith("New Chat"):
            self.all_conversations[self.current_chat_index]["title"] = user_prompt[:30] + "..." if len(user_prompt) > 30 else user_prompt
            self.update_chat_list_ui()

        self.display_message("user", user_prompt)
        self.input_entry.delete(0, tk.END)
        self.set_processing_state(True)
        
        thread = threading.Thread(target=self.get_gemini_response, args=(user_prompt,))
        thread.daemon = True
        thread.start()

    def get_gemini_response(self, user_prompt):
        """Sends prompt to API and displays response in a separate thread."""
        self.conversation_history.append({"role": "user", "parts": [{"text": user_prompt}]})
        payload = {"contents": self.conversation_history}

        try:
            response = requests.post(self.api_url, headers=self.headers, data=json.dumps(payload), timeout=75)
            response.raise_for_status()
            response_data = response.json()
            model_response = response_data['candidates'][0]['content']['parts'][0]['text']
            self.conversation_history.append({"role": "model", "parts": [{"text": model_response}]})
            self.root.after(0, self.display_message, "gemini", model_response)
        except requests.exceptions.RequestException as e:
            self.root.after(0, self.display_message, "error", f"Network or API error: {e}")
            if self.conversation_history and self.conversation_history[-1].get("role") == "user":
                self.conversation_history.pop()
        except (KeyError, IndexError) as e:
            self.root.after(0, self.display_message, "error", f"Could not parse API response: {e}")
            if self.conversation_history and self.conversation_history[-1].get("role") == "user":
                self.conversation_history.pop()
        finally:
            self.root.after(0, self.set_processing_state, False) # Hide thinking indicator

    def show_thinking_indicator(self):
        """Creates and displays a spinning circle indicator."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, "\n", 'status') # Add a newline for spacing

        self.thinking_frame = tk.Frame(self.chat_display, bg=self.CHAT_BG_COLOR, width=20, height=20)
        self.thinking_frame.pack_propagate(False) # Prevent frame from resizing to canvas
        
        self.thinking_canvas = tk.Canvas(self.thinking_frame, width=20, height=20, bg=self.CHAT_BG_COLOR, highlightthickness=0)
        self.thinking_canvas.pack(fill=tk.BOTH, expand=True) # Fill the frame
        
        self.chat_display.window_create(tk.END, window=self.thinking_frame, padx=5) # Embed the frame
        self.chat_display.insert(tk.END, "\n\n", 'status') # Add spacing after the indicator
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

        self.angle = 0 # Reset angle for a fresh animation
        self._animate_thinking_circle() # Start the animation

    def _animate_thinking_circle(self):
        """Animates the spinning circle."""
        if not self.thinking_canvas:
            return

        self.thinking_canvas.delete("all")
        center_x, center_y = 10, 10 
        radius = 8

        x1 = center_x + radius * math.cos(math.radians(self.angle))
        y1 = center_y + radius * math.sin(math.radians(self.angle))
        x2 = center_x + radius * math.cos(math.radians(self.angle + 180)) 
        y2 = center_y + radius * math.sin(math.radians(self.angle + 180))

        self.thinking_canvas.create_line(x1, y1, x2, y2, fill=self.SEND_BUTTON_COLOR, width=2, capstyle=tk.ROUND)

        self.angle = (self.angle + 15) % 360 
        self.animation_job = self.root.after(80, self._animate_thinking_circle) # Schedule next frame

    def hide_thinking_indicator(self):
        """Hides and destroys the spinning circle indicator."""
        if self.animation_job:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        if self.thinking_frame:
            self.thinking_frame.destroy()
            self.thinking_frame = None
            self.thinking_canvas = None 

    def set_processing_state(self, is_processing):
        """Toggles the UI state between processing and active."""
        if is_processing:
            self.input_entry.config(state='disabled')
            self.send_button.config(state='disabled')
            self.show_thinking_indicator()
        else:
            self.input_entry.config(state='normal')
            self.send_button.config(state='normal')
            self.input_entry.focus_set()
            self.hide_thinking_indicator() 

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = GeminiGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"An unexpected error occurred: {e}")
