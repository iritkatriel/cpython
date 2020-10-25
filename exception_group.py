import sys
import traceback
import types


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
    raise types.ExceptionGroup(excs)

def propagator():
    aggregator()

def get_exception_group():
    try:
        propagator()
    except types.ExceptionGroup as e:
        return e

def handle_type_errors():
    try:
        propagator()
    except types.ExceptionGroup as e:
        TEs = e.split(TypeError)
        return e, TEs

def handle_value_errors():
    try:
        propagator()
    except types.ExceptionGroup as e:
        VEs = e.split(ValueError)
        return e, VEs


def main():
    print (">>>>>>>>>>>>>>>>>> get_exception_group <<<<<<<<<<<<<<<<<<<<")
    e = get_exception_group()
    types.ExceptionGroup.render(e)

    print (">>>>>>>>>>>>>>>>>> handle_type_errors <<<<<<<<<<<<<<<<<<<<")

    e, TEs = handle_type_errors()
    print ("\n\n\n ------------- The split-off Type Errors:")
    types.ExceptionGroup.render(TEs)
    print ("\n\n\n ------------- The remaining unhandled:")
    types.ExceptionGroup.render(e)

    print (">>>>>>>>>>>>>>>>>> handle_value_errors <<<<<<<<<<<<<<<<<<<<")
    e, VEs = handle_value_errors()
    print ("\n\n\n ------------- The split-off Value Errors:")
    types.ExceptionGroup.render(VEs)
    print ("\n\n\n ------------- The remaining unhandled:")
    types.ExceptionGroup.render(e)

if __name__ == '__main__':
    main()
