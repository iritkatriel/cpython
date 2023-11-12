
import ast
import dis
import io
import opcode
from pprint import pprint
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tokenize
from _testinternalcapi import compiler_codegen, optimize_cfg, assemble_code_object

class Stage(ttk.Frame):
    def __init__(self, title, master=None):
        super().__init__(master)
        self.title = title

        tk.Label(self, text=title).grid(row=0,column=0, padx=5, pady=5)
        self.init_layout()

    def init_layout(self):
        self.text = tk.Text(self)
        self.text.grid(row=1,column=0, padx=5, pady=5)
        vscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        vscroll.grid(row=1, column=1, sticky='nsew')
        self.text['yscrollcommand'] = vscroll.set

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
        self.controls.grid(row=0, column=0)
        self.displays.grid(row=1, column=0)

        self.source = Stage('Source', master=self.displays)
        self.tokens = Stage('Tokens', master=self.displays)
        self.ast = Stage('AST', master=self.displays)
        self.opt_ast = Stage('Optimized AST', master=self.displays)
        self.pseudo_bytecode = Stage('Pseudo Bytecode', master=self.displays)
        self.opt_pseudo_bytecode = Stage('Optimized Pseudo Bytecode', master=self.displays)
        self.code_object = Stage('Code Object', master=self.displays)

        self.source.grid(row=0, column=0, padx=10, pady=5)
        self.tokens.grid(row=0, column=1, padx=10, pady=5)
        self.ast.grid(row=0, column=2, padx=10, pady=5)
        self.opt_ast.grid(row=1, column=0, padx=10, pady=5)
        self.pseudo_bytecode.grid(row=1, column=1, padx=10, pady=5)
        self.opt_pseudo_bytecode.grid(row=1, column=2, padx=10, pady=5)
        self.code_object.grid(row=2, column=1, padx=10, pady=5)

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
        self.refresh_bytecode()

    def refresh_tokens(self):
        src = self.source.getvalue()
        tokens = list(tokenize.tokenize(
                     io.BytesIO(src.encode('utf-8')).readline))
        self.tokens.replace_text(self._pretty(tokens))

    def refresh_ast(self):
        src = self.source.getvalue()
        self.ast.replace_text(
            ast.dump(ast.parse(src), indent=3))

    def refresh_optimized_ast(self):
        src = self.source.getvalue()
        self.opt_ast.replace_text(
            ast.dump(ast.parse(src, optimize=1), indent=3))

    def refresh_bytecode(self):
        print('refresh_bytecode')
        def display_insts(insts):
            jump_targets = [inst[1] for inst in insts if inst[0] in dis.hasjump]
            prev_line = None
            for offset, inst in enumerate(insts):
                op, arg = inst[:2]
                start_offset = 0
                positions = dis.Positions(*inst[2:])
                line_number = positions.lineno
                starts_line = line_number != prev_line
                prev_line = line_number
                is_jump_target = offset in jump_targets
                if op in dis.hasjump:
                    argval, argrepr = arg, f"to {arg}"
                    instr = dis.Instruction(dis._all_opname[op], op, arg,
                           argval, argrepr, offset, start_offset, starts_line,
                           line_number, is_jump_target, positions)
                else:
                    instr = dis.Instruction._create(op, arg, offset, start_offset,
                                                    starts_line, line_number,
                                                    is_jump_target, positions)
                yield instr._disassemble()

        print('codegen ...')
        src = self.source.getvalue()
        filename = "<src>"
        insts, metadata  = compiler_codegen(ast.parse(src, optimize=1), filename, 0)
        self.pseudo_bytecode.replace_text("\n".join(display_insts(insts)))

        print('optimization ...')
        consts = [v[1] for v in sorted([(v, k) for k, v in metadata['consts'].items()])]
        nlocals = 0
        insts = optimize_cfg(insts, consts, nlocals)
        self.opt_pseudo_bytecode.replace_text("\n".join(display_insts(insts)))

        print('assembly ...')
        from test.test_compiler_assemble import IsolatedAssembleTests
        IsolatedAssembleTests().complete_metadata(metadata)
        co = assemble_code_object(filename, insts, metadata)
        stream = io.StringIO()
        dis.dis(co, file=stream)
        self.code_object.replace_text(stream.getvalue())

    def close(self):
        self.destroy()

window = App()

# Start the event loop.
window.mainloop()

