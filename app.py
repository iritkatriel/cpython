
import io
from pprint import pprint
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tokenize


class Stage(ttk.Frame):
    def __init__(self, title, refresh_action, editable=False,
                 master=None):
        super().__init__(master)
        self.title = title
        self.refresh_action = refresh_action
        self.text = tk.Text(self)
        self.text.grid(row=0,column=0, padx=5, pady=5)
        if editable:
            bottom_widget = ttk.Button(text="Refresh",
                                       command=self.do_refresh,
                                       master=self)
        else:
            bottom_widget = ttk.Label(text="", master=self)

        bottom_widget.grid(row=1, column=0, padx=5, pady=5)

    def do_refresh(self):
        text = self.text.get(1.0, "end-1c")
        self.refresh_action(text)

    def replace_text(self, value):
        self.text.delete(1.0, "end-1c")
        self.text.insert(tk.INSERT, value or "")
        self.do_refresh()

    def set_output(self, output):
        self.output = output

    def write_output(self, value):
       self.output.replace_text(value)


class App(tk.Tk):

    DEFAULT_SOURCE = "print('Hello World!')"

    def __init__(self, master=None):
        super().__init__(master)
        self.title(f'CPython Codoscope {sys.version.split()[0]}')

        self.displays = ttk.Frame(self)
        self.controls = ttk.Frame(self)
        self.displays.grid(row=0, column=0)
        self.controls.grid(row=1, column=0)

        self.source = Stage('source',
                            self.source_refreshed,
                            editable=True,
                            master=self.displays)
        self.tokens = Stage('tokens', self.tokens_refreshed, master=self.displays)
        self.source.set_output(self.tokens)

        self.source.grid(row=0, column=0, padx=10, pady=5)
        self.tokens.grid(row=0, column=1, padx=10, pady=5)

        self.source.replace_text(self.DEFAULT_SOURCE)
        ttk.Button(text="close",
                   command=self.close,
                   master=self.controls).grid(row=0, column=0)

    def source_refreshed(self, text):
        tokens = list(tokenize.tokenize(
                     io.BytesIO(text.encode('utf-8')).readline))
        s = io.StringIO()
        pprint(tokens, stream=s)
        self.source.write_output(s.getvalue())

    def tokens_refreshed(self, text):
        print('tokens_refreshed')

    def close(self):
        self.destroy()

window = App()

# Start the event loop.
window.mainloop()

