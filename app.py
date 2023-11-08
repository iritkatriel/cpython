
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
        self.pack()
        self.title = title
        self.refresh_action = refresh_action
        self.text = tk.Text(self) #, wrap=WORD)
        self.text.pack()
        if editable:
            self.refresh = ttk.Button(text="Refresh",
                                      command=self.do_refresh)
            self.refresh.pack()

    def do_refresh(self):
        text = self.text.get(1.0, "end-1c")
        print(f'{self.title}: {text}')
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
        ttk.Label(text="Hello, Tkinter").pack()
        self.source = Stage('source',
                            self.source_refreshed,
                            editable=True,
                            master=master)
        self.tokens = Stage('tokens', self.tokens_refreshed, master=master)
        self.source.set_output(self.tokens)

        self.source.replace_text(self.DEFAULT_SOURCE)
        ttk.Button(text="close", command=self.close).pack()

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

