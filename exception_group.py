import sys
import traceback
import types


class ExceptionGroup(BaseException):

    def __init__(self, excs, tb=None):
        self.excs = set(excs)
        if tb:
            self.__traceback__ = tb
        else:
            self.__traceback__ = types.TracebackType(None, sys._getframe(), 0, 0)
            for e in excs:
                 self.add_exc(e)

    def add_exc(self, e):
        self.excs.add(e)
        self.__traceback__.next_map_add(e, e.__traceback__)

    def split(self, E):
        ''' remove the exceptions that match E
        and return them in a new ExceptionGroup
        '''
        matches = []
        for e in self.excs:
            if isinstance(e, E):
                matches.append(e)
        [self.excs.remove(m) for m in matches]
        gtb = self.__traceback__
        while gtb.tb_next: # there could be normal tbs is the ExceptionGroup propagated
            gtb = gtb.tb_next
        tb = gtb.group_split(matches)

        return ExceptionGroup(matches, tb)

    def push_frame(self, frame):
        self.__traceback__ = types.TracebackType(self.__traceback__, frame, 0, 0)

    def __str__(self):
        return f"ExceptionGroup({self.excs})"

    def __repr__(self):
        return str(self)

def render_exception(exc, tb=None, indent=0):
    print(exc)
    tb = tb or exc.__traceback__
    while tb:
        print(' '*indent, tb.tb_frame)
        if tb.tb_next: # single traceback
            tb = tb.tb_next
        elif tb.tb_next_map:
            indent += 4
            for e, t in tb.tb_next_map.items():
                print('---------------------------------------')
                render_exception(e, t, indent)
            tb = None
        else:
            tb = None


def f(): raise ValueError('bad value: f')
def f1(): f()

def g(): raise ValueError('bad value: g')
def g1(): g()

def h(): raise TypeError('bad type: h')
def h1(): h()

def aggregator():
    excs = set()
    for c in (f1, g1, h1):
        try:
            c()
        except Exception as e:
            excs.add(e)
    raise ExceptionGroup(excs)

def propagator():
    aggregator()

def get_exception_group():
    try:
        propagator()
    except ExceptionGroup as e:
        return e

def handle_type_errors():
    try:
        propagator()
    except ExceptionGroup as e:
        TEs = e.split(TypeError)
        return e, TEs

def handle_value_errors():
    try:
        propagator()
    except ExceptionGroup as e:
        VEs = e.split(ValueError)
        return e, VEs


def main():
    print (">>>>>>>>>>>>>>>>>> get_exception_group <<<<<<<<<<<<<<<<<<<<")
    e = get_exception_group()
    render_exception(e)

    print (">>>>>>>>>>>>>>>>>> handle_type_errors <<<<<<<<<<<<<<<<<<<<")

    e, TEs = handle_type_errors()
    print ("\n\n\n ------------- The split-off Type Errors:")
    render_exception(TEs)
    print ("\n\n\n ------------- The remaining unhandled:")
    render_exception(e)

    print (">>>>>>>>>>>>>>>>>> handle_value_errors <<<<<<<<<<<<<<<<<<<<")
    e, VEs = handle_value_errors()
    print ("\n\n\n ------------- The split-off Value Errors:")
    render_exception(VEs)
    print ("\n\n\n ------------- The remaining unhandled:")
    render_exception(e)

if __name__ == '__main__':
    main()
