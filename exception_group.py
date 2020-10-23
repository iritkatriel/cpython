import sys
import traceback

class Traceback:
    def __init__(self, frame, tb = None):
        self.tb_frame = frame
        self.tb = tb


class TracebackGroup(Traceback):
    def __init__(self, frame, tb_next_all = {}):
        super().__init__(frame)
        self.tb_next_all = tb_next_all

    def add(self, exc):
        ''' add an exception to this tb group '''
        self.tb_next_all[exc] = exc.__traceback__

    def split(self, excs):
        ''' remove excs from this tb group and return a
        new tb group for them, with same frame
        '''
        r = dict({(k,v) for k,v in self.tb_next_all.items() if k in excs})
        [self.tb_next_all.pop(k) for k in r]
        return TracebackGroup(self.tb_frame, r)


class ExceptionGroup(BaseException):

    def __init__(self, excs, tb=None):
        self.excs = excs
        if tb:
            self.tb = tb
        else:
            self.tb = TracebackGroup(sys._getframe())
            for e in excs:
                 self.tb.add(e)

    def add_exc(self, e):
        self.excs.add(e)
        self.tb.add(e)

    def exc_match(self, E):
        ''' remove the exceptions that match E
        and return them in a new ExceptionGroup
        '''
        matches = set()
        for e in self.excs:
            if isinstance(e, E):
                matches.add(e)
        [self.excs.remove(m) for m in matches]
        tb = self.tb.split(matches)
        return ExceptionGroup(matches, tb)

    def push_frame(self, frame):
        self.__traceback__ = TracebackGroup(frame, tb_next=self.__traceback__)


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

def propagator1():
    propagator()

def handle_type_errors():
    try:
        propagator1()
    except ExceptionGroup as e:
        TEs = e.exc_match(TypeError)
        raise e

def handle_value_errors():
    try:
        propagator1()
    except ExceptionGroup as e:
        VEs = e.exc_match(ValueError)
        raise e


def main():
    ## comment out the one you want to try:

    propagator1()
    # handle_type_errors()
    # handle_value_errors()

if __name__ == '__main__':
    main()
