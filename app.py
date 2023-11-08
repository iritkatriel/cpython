
import tkinter as tk
import tkinter.ttk as ttk


class Stage(ttk.Frame):
    def __init__(self, title, refresh_action, value=None, master=None):
        super().__init__(master)
        self.pack()
        self.title = title
        self.refresh_action = refresh_action
        self.text = tk.Text(self)
        self.text.pack()
        if value is not None:
            self.text.insert(tk.INSERT, value)
        self.refresh = ttk.Button(text="Refresh", command=self.do_refresh)
        self.refresh.pack()

    def do_refresh(self):
        self.refresh_action(self.text.get(1.0, "end-1c"))

class App(tk.Tk):
    DEFAULT_SOURCE = "print('Hello World!')"

    def __init__(self, master=None):
        super().__init__(master)
        self.title("Hello World")
        ttk.Label(text="Hello, Tkinter").pack()
        self.source = Stage('source',
                            self.refresh_source,
                            value=self.DEFAULT_SOURCE,
                            master=master)
        ttk.Button(text="exit", command=self.exit).pack()

    def refresh_source(self, text):
        print(f'source:', text)

    def exit(self):
        self.destroy()

window = App()

# Start the event loop.
window.mainloop()

