
import ast
import io
from pprint import pprint
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tokenize

class Stage(ttk.Frame):
    def __init__(self, title, master=None):
        super().__init__(master)
        self.title = title

        tk.Label(self, text=title).grid(row=0,column=0, padx=5, pady=5)
        self.init_layout()

    def init_layout(self):
        self.text = tk.Text(self)
        self.text.grid(row=1,column=0, padx=5, pady=5)

    def getvalue(self):
        return self.text.get(1.0, "end-1c")

    def replace_text(self, value):
        self.text.delete(1.0, "end-1c")
        self.text.insert(tk.INSERT, value or "")


class App(tk.Tk):

    DEFAULT_SOURCE = "print('Hello World!')"

    def __init__(self, master=None):
        super().__init__(master)
        self.title(f'CPython Codoscope {sys.version.split()[0]}')

        self.displays = ttk.Frame(self)
        self.controls = ttk.Frame(self)
        self.displays.grid(row=0, column=0)
        self.controls.grid(row=1, column=0)

        self.source = Stage('Source',
                            master=self.displays)
        self.tokens = Stage('Tokens',
                            master=self.displays)
        self.ast = Stage('AST',
                         master=self.displays)
        self.opt_ast = Stage('Optimized AST',
                             master=self.displays)

        self.source.grid(row=0, column=0, padx=10, pady=5)
        self.tokens.grid(row=0, column=1, padx=10, pady=5)
        self.ast.grid(row=1, column=0, padx=10, pady=5)
        self.opt_ast.grid(row=1, column=1, padx=10, pady=5)

        ttk.Button(text="refresh",
                   command=self.refresh,
                   master=self.controls).grid(row=0, column=0)
        ttk.Button(text="close",
                   command=self.close,
                   master=self.controls).grid(row=0, column=1)

        self.source.replace_text(self.DEFAULT_SOURCE)
        self.refresh()

    @staticmethod
    def _pretty(input):
        stream = io.StringIO()
        pprint(input, stream=stream)
        return stream.getvalue()

    def refresh(self):
        self.refresh_optimized_ast()
        self.refresh_ast()
        self.refresh_tokens()

    def refresh_tokens(self):
        src = self.source.getvalue()
        tokens = list(tokenize.tokenize(
                     io.BytesIO(src.encode('utf-8')).readline))
        self.tokens.replace_text(self._pretty(tokens))

    def refresh_ast(self):
        src = self.source.getvalue()
        self.ast.replace_text(
            self._pretty(ast.dump(ast.parse(src))))

    def refresh_optimized_ast(self):
        src = self.source.getvalue()
        self.opt_ast.replace_text(
            self._pretty(ast.dump(ast.parse(src, optimize=1))))

    def close(self):
        self.destroy()

window = App()

# Start the event loop.
window.mainloop()

