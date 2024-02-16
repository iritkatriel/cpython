
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
        self.visible = tk.IntVar()

        tk.Label(self, text=title).grid(row=0,column=0, padx=5, pady=5)
        self.init_layout()

    def init_layout(self):
        self.text = tk.Text(self, wrap=tk.NONE)
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
    DEFAULT_SOURCE = """
if x:
    y = 12
else:
    y = 14
"""

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

        self.stages = [self.source, self.tokens, self.ast, self.opt_ast,
                       self.pseudo_bytecode, self.opt_pseudo_bytecode, self.code_object]

        ttk.Button(text="refresh",
                   command=self.refresh,
                   master=self.controls).grid(row=0, column=3)

        ttk.Button(text="close",
                   command=self.close,
                   master=self.controls).grid(row=0, column=4)

        for i, stage in enumerate(self.stages):
            tk.Checkbutton(self.controls,
                           text=stage.title,
                           variable=stage.visible,
                           command=self.refresh,
                           onvalue=1,
                           offvalue=0).grid(row=1, column=i)

        self.source.visible.set(1)
        self.source.replace_text(self.DEFAULT_SOURCE)
        self.refresh()

    def show_stages(self):
        i = 0
        [stage.grid_forget() for stage in self.stages]
        for stage in self.stages:
            if stage.visible.get():
                stage.grid(row=i//3, column=i%3, padx=10, pady=5)
                i += 1

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
        self.show_stages()

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

        class PseudoInstrsArgResolver(dis.ArgResolver):
            def offset_from_jump_arg(self, op, arg, offset):
                if op in dis.hasjump or op in dis.hasexc:
                    return arg
                return super().offset_from_jump_arg(op, arg, offset)

        def display_insts(insts, co_consts, arg_resolver=None):

            jump_targets = [inst[1] for inst in insts if inst[0] in dis.hasjump]
            labels_map = {offset : (i+1) for i, offset in enumerate(jump_targets)}
            arg_resolver = PseudoInstrsArgResolver(co_consts=co_consts, labels_map=labels_map)

            prev_line = None
            offset_width = len(str(len(insts))) + 2
            for offset, inst in enumerate(insts):
                op, arg = inst[:2]
                start_offset = 0
                positions = dis.Positions(*inst[2:])
                line_number = positions.lineno if positions.lineno > 0 else None
                starts_line = line_number != prev_line
                prev_line = line_number
                is_jump_target = offset in jump_targets
                label = labels_map.get(offset, None)
                argval, argrepr = arg_resolver.get_argval_argrepr(op, arg, offset)
                instr = dis.Instruction(dis._all_opname[op], op, arg, argval, argrepr,
                                        offset, start_offset, starts_line, line_number,
                                        label, positions)
                stream = io.StringIO()
                formatter = dis.Formatter(file=stream)
                formatter.print_instruction(instr)
                yield stream.getvalue()

        print('codegen ...')
        src = self.source.getvalue()
        filename = "<src>"
        insts, metadata  = compiler_codegen(ast.parse(src, optimize=1), filename, 0)
        co_consts = [p[1] for p in sorted([(v, k) for k, v in metadata['consts'].items()])]

        self.pseudo_bytecode.replace_text("".join(display_insts(insts, co_consts)))

        print('optimization ...')
        nlocals = 0
        insts = optimize_cfg(insts, co_consts, nlocals)
        self.opt_pseudo_bytecode.replace_text("".join(display_insts(insts, co_consts)))

        print('assembly ...')
        metadata['consts'] = {name : i for i, name in enumerate(co_consts)}
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

