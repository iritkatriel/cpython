
import collections.abc
import functools
import traceback
import unittest
from exception_group import ExceptionGroupHelper
from io import StringIO


def newEG(msg, raisers, cls=ExceptionGroup):
    excs = []
    for r in raisers:
        try:
            r()
        except (Exception, ExceptionGroup) as e:
            excs.append(e)
    try:
        raise cls(msg, *excs)
    except ExceptionGroup as e:
        return e

def newVE(v):
    raise ValueError(v)

def newTE(t):
    raise TypeError(t)

def newSimpleEG(msg=None):
    bind = functools.partial
    return newEG(msg, [bind(newVE, 1), bind(newTE, int), bind(newVE, 2)])

class MyExceptionGroup(ExceptionGroup):
    pass

def newNestedEG(arg, msg=None):
    bind = functools.partial

    def level1(i):
        return newEG(
            'msg1',
            [bind(newVE, i), bind(newTE, int), bind(newVE, i+1)])

    def raiseExc(e):
        raise e

    def level2(i):
        return newEG(
            'msg2',
            [bind(raiseExc, level1(i)),
                bind(raiseExc, level1(i+1)),
                bind(newVE, i+2),
            ],
            cls=MyExceptionGroup)

    def level3(i):
        return newEG(
            'msg3',
            [bind(raiseExc, level2(i+1)), bind(newVE, i+2)])

    return level3(arg)

def extract_traceback(exc, eg):
    """ returns the traceback of a single exception

    If exc is in the exception group, return its
    traceback as the concatenation of the outputs
    of traceback.extract_tb() on each segment of
    it traceback (one per each ExceptionGroup that
    it belongs to).
    """
    if exc not in ExceptionGroupHelper.flatten(eg):
        return None
    e = ExceptionGroupHelper.subgroup(eg, [exc])
    result = None
    while e is not None:
        if isinstance(e, ExceptionGroup):
            assert len(e.excs) == 1 and exc in ExceptionGroupHelper.flatten(e)
        r = traceback.extract_tb(e.__traceback__)
        if result is not None:
            result.extend(r)
        else:
            result = r
        e = e.excs[0] if isinstance(e, ExceptionGroup) else None
    return result


class ExceptionGroupTestBadInputs(unittest.TestCase):
    def test_simple_group_bad_constructor_args(self):
        msg = 'Expected msg followed by the nested exceptions'
        with self.assertRaisesRegex(TypeError, msg):
            _ = ExceptionGroup('no errors')
        with self.assertRaisesRegex(TypeError, msg):
            _ = ExceptionGroup(ValueError(12))
        with self.assertRaisesRegex(TypeError, msg):
            _ = ExceptionGroup(ValueError(12), SyntaxError('bad syntax'))


class ExceptionGroupTestBase(unittest.TestCase):
    def assertMatchesTemplate(self, exc, template):
        """ Assert that the exception matches the template """
        if isinstance(exc, ExceptionGroup):
            self.assertIsInstance(template, collections.abc.Sequence)
            self.assertEqual(len(exc.excs), len(template))
            for e, t in zip(exc.excs, template):
                self.assertMatchesTemplate(e, t)
        else:
            self.assertIsInstance(template, BaseException)
            self.assertEqual(type(exc), type(template))
            self.assertEqual(exc.args, template.args)


class ExceptionGroupBasicsTests(ExceptionGroupTestBase):
    def test_simple_group(self):
        eg = newSimpleEG('simple EG')

        self.assertMatchesTemplate(
            eg, [ValueError(1), TypeError(int), ValueError(2)])

        self.assertEqual(list(ExceptionGroupHelper.flatten(eg)), list(eg.excs))  # check iteration

        # check msg
        self.assertEqual(eg.msg, 'simple EG')
        self.assertEqual(eg.args[0], 'simple EG')

        # check tracebacks
        for e in ExceptionGroupHelper.flatten(eg):
            fname = 'new' + ''.join(filter(str.isupper, type(e).__name__))
            self.assertEqual(
                ['newEG', 'newEG', fname],
                [f.name for f in extract_traceback(e, eg)])

    def test_nested_group(self):
        eg = newNestedEG(5)

        self.assertMatchesTemplate(
            eg,
            [
                [
                    [ValueError(6), TypeError(int), ValueError(7)],
                    [ValueError(7), TypeError(int), ValueError(8)],
                    ValueError(8),
                ],
                ValueError(7)
            ])

        self.assertEqual(len(list(ExceptionGroupHelper.flatten(eg))), 8)  # check iteration

        # check tracebacks
        all_excs = list(ExceptionGroupHelper.flatten(eg))
        for e in all_excs[0:6]:
            fname = 'new' + ''.join(filter(str.isupper, type(e).__name__))
            self.assertEqual(
                [
                    'newEG', 'newEG', 'raiseExc',
                    'newEG', 'newEG', 'raiseExc',
                    'newEG', 'newEG', fname,
                ],
                [f.name for f in extract_traceback(e, eg)])

        self.assertEqual([
            'newEG', 'newEG', 'raiseExc', 'newEG', 'newEG', 'newVE'],
            [f.name for f in extract_traceback(all_excs[6], eg)])

        self.assertEqual(
            ['newEG', 'newEG', 'newVE'],
            [f.name for f in extract_traceback(all_excs[7], eg)])


class ExceptionGroupSplitTests(ExceptionGroupTestBase):
    def _split_exception_group(self, eg, types):
        """ Split an EG and do some sanity checks on the result """
        self.assertIsInstance(eg, ExceptionGroup)
        fnames = [t.name for t in traceback.extract_tb(eg.__traceback__)]
        all_excs = list(ExceptionGroupHelper.flatten(eg))

        match, rest = ExceptionGroupHelper.split(eg, types)

        if match is not None:
            self.assertIsInstance(match, ExceptionGroup)
            for e in ExceptionGroupHelper.flatten(match):
                self.assertIsInstance(e, types)

        if rest is not None:
            self.assertIsInstance(rest, ExceptionGroup)
            for e in ExceptionGroupHelper.flatten(rest):
                self.assertNotIsInstance(e, types)

        match_len = len(list(ExceptionGroupHelper.flatten(match))) if match is not None else 0
        rest_len = len(list(ExceptionGroupHelper.flatten(rest))) if rest is not None else 0
        self.assertEqual(len(list(all_excs)), match_len + rest_len)

        for e in all_excs:
            # each exception is in eg and exactly one of match and rest
            self.assertIn(e, ExceptionGroupHelper.flatten(eg))
            self.assertNotEqual(match and e in ExceptionGroupHelper.flatten(match),
                                rest and e in ExceptionGroupHelper.flatten(rest))

        for part in [match, rest]:
            if part is not None:
                self.assertEqual(eg.msg, part.msg)                
                for e in ExceptionGroupHelper.flatten(part):
                    self.assertEqual(
                        extract_traceback(e, eg),
                        extract_traceback(e, part))

        return match, rest

    def test_split_nested(self):
        try:
            raise newNestedEG(25)
        except ExceptionGroup as e:
            eg = e

        fnames = ['test_split_nested', 'newEG']
        tb = traceback.extract_tb(eg.__traceback__)
        self.assertEqual(fnames, [t.name for t in tb])

        eg_template = [
                        [
                            [ValueError(26), TypeError(int), ValueError(27)],
                            [ValueError(27), TypeError(int), ValueError(28)],
                            ValueError(28),
                        ],
                        ValueError(27)
                      ]
        self.assertMatchesTemplate(eg, eg_template)

        valueErrors_template = [
                                   [
                                        [ValueError(26), ValueError(27)],
                                        [ValueError(27), ValueError(28)],
                                        ValueError(28),
                                   ],
                                   ValueError(27)
                               ]

        typeErrors_template = [[[TypeError(int)], [TypeError(int)]]]

        # Match Nothing
        match, rest = self._split_exception_group(eg, SyntaxError)
        self.assertTrue(match is None)
        self.assertMatchesTemplate(rest, eg_template)

        # Match Everything
        match, rest = self._split_exception_group(eg, BaseException)
        self.assertMatchesTemplate(match, eg_template)
        self.assertTrue(rest is None)
        match, rest = self._split_exception_group(eg, (ValueError, TypeError))
        self.assertMatchesTemplate(match, eg_template)
        self.assertTrue(rest is None)

        # Match ValueErrors
        match, rest = self._split_exception_group(eg, ValueError)
        self.assertMatchesTemplate(match, valueErrors_template)
        self.assertMatchesTemplate(rest, typeErrors_template)

        # Match TypeErrors
        match, rest = self._split_exception_group(eg, (TypeError, SyntaxError))
        self.assertMatchesTemplate(match, typeErrors_template)
        self.assertMatchesTemplate(rest, valueErrors_template)

        # Match ExceptionGroup
        match, rest = ExceptionGroupHelper.split(eg, ExceptionGroup)
        self.assertIs(match, eg)
        self.assertIsNone(rest)

        # Match MyExceptionGroup (ExceptionGroup subclass)
        match, rest = ExceptionGroupHelper.split(eg, MyExceptionGroup)
        self.assertMatchesTemplate(match, [eg_template[0]])
        self.assertMatchesTemplate(rest, [eg_template[1]])

class ExceptionGroupCatchTests(ExceptionGroupTestBase):
    def setUp(self):
        super().setUp()

        try:
            raise newNestedEG(35)
        except ExceptionGroup as e:
            self.eg = e

        fnames = ['setUp', 'newEG']
        tb = traceback.extract_tb(self.eg.__traceback__)
        self.assertEqual(fnames, [t.name for t in tb])

        # templates
        self.eg_template = [
            [
                [ValueError(36), TypeError(int), ValueError(37)],
                [ValueError(37), TypeError(int), ValueError(38)],
                ValueError(38),
            ],
            ValueError(37)
        ]

        self.valueErrors_template = [
            [
                [ValueError(36), ValueError(37)],
                [ValueError(37), ValueError(38)],
                ValueError(38),
            ],
            ValueError(37)
        ]

        self.typeErrors_template = [[[TypeError(int)], [TypeError(int)]]]

    def checkMatch(self, exc, template, orig_eg):
        self.assertMatchesTemplate(exc, template)
        for e in ExceptionGroupHelper.flatten(exc):
            def f_data(f):
                return [f.name, f.lineno]

            new = list(map(f_data, extract_traceback(e, exc)))
            if e in ExceptionGroupHelper.flatten(orig_eg):
                old = list(map(f_data, extract_traceback(e, orig_eg)))
                self.assertSequenceEqual(old, new[-len(old):])

    class BaseHandler:
        def __init__(self):
            self.caught = None

        def __call__(self, eg):
            self.caught = eg
            return self.handle(eg)

    def apply_catcher(self, catch, handler_cls, eg):
        try:
            raised = None
            handler = handler_cls()
            with ExceptionGroupHelper.catch(catch, handler):
                raise eg
        except ExceptionGroup as e:
            raised = e
        return handler.caught, raised

    def test_catch_handler_raises_nothing(self):
        eg = self.eg
        eg_template = self.eg_template
        valueErrors_template = self.valueErrors_template
        typeErrors_template = self.typeErrors_template

        class Handler(self.BaseHandler):
            def handle(self, eg):
                pass

        # ######## Catch nothing:
        caught, raised = self.apply_catcher(SyntaxError, Handler, eg)
        self.checkMatch(raised, eg_template, eg)
        self.assertIsNone(caught)

        # ######## Catch everything:
        error_types = (ValueError, TypeError)
        caught, raised = self.apply_catcher(error_types, Handler, eg)
        self.assertIsNone(raised)
        self.checkMatch(caught, eg_template, eg)

        # ######## Catch TypeErrors:
        caught, raised = self.apply_catcher(TypeError, Handler, eg)
        self.checkMatch(raised, valueErrors_template, eg)
        self.checkMatch(caught, typeErrors_template, eg)

        # ######## Catch ValueErrors:
        error_types = (ValueError, SyntaxError)
        caught, raised = self.apply_catcher(error_types, Handler, eg)
        self.checkMatch(raised, typeErrors_template, eg)
        self.checkMatch(caught, valueErrors_template, eg)

    def test_catch_handler_adds_new_exceptions(self):
        # create a nested exception group
        eg = self.eg
        eg_template = self.eg_template
        valueErrors_template = self.valueErrors_template
        typeErrors_template = self.typeErrors_template

        class Handler(self.BaseHandler):
            def handle(self, eg):
                raise ExceptionGroup(
                      "msg1",
                      ValueError('foo'),
                      ExceptionGroup(
                          "msg2",SyntaxError('bar'), ValueError('baz')))

        newErrors_template = [
            ValueError('foo'), [SyntaxError('bar'), ValueError('baz')]]

        # ######## Catch nothing:
        caught, raised = self.apply_catcher(SyntaxError, Handler, eg)
        self.checkMatch(raised, eg_template, eg)
        self.assertIsNone(caught)

        # ######## Catch everything:
        error_types = (ValueError, TypeError)
        caught, raised = self.apply_catcher(error_types, Handler, eg)
        self.checkMatch(raised, newErrors_template, eg)
        self.checkMatch(caught, eg_template, eg)

        # ######## Catch TypeErrors:
        caught, raised = self.apply_catcher(TypeError, Handler, eg)
        self.checkMatch(raised, [valueErrors_template, newErrors_template], eg)
        self.checkMatch(caught, typeErrors_template, eg)

        # ######## Catch ValueErrors:
        caught, raised = self.apply_catcher((ValueError, OSError), Handler, eg)
        self.checkMatch(raised, [typeErrors_template, newErrors_template], eg)
        self.checkMatch(caught, valueErrors_template, eg)

    def test_catch_handler_reraise_all_matched(self):
        eg = self.eg
        eg_template = self.eg_template
        valueErrors_template = self.valueErrors_template
        typeErrors_template = self.typeErrors_template

        # There are two ways to do this
        class Handler1(self.BaseHandler):
            def handle(self, eg):
                return True

        class Handler2(self.BaseHandler):
            def handle(self, eg):
                raise eg

        for handler in [Handler1, Handler2]:
            # ######## Catch nothing:
            caught, raised = self.apply_catcher(SyntaxError, handler, eg)
            # handler is never called
            self.checkMatch(raised, eg_template, eg)
            self.assertIsNone(caught)

            # ######## Catch everything:
            error_types = (ValueError, TypeError)
            caught, raised = self.apply_catcher(error_types, handler, eg)
            self.checkMatch(raised, eg_template, eg)
            self.checkMatch(caught, eg_template, eg)

            # ######## Catch TypeErrors:
            caught, raised = self.apply_catcher(TypeError, handler, eg)
            self.checkMatch(raised, eg_template, eg)
            self.checkMatch(caught, typeErrors_template, eg)

            # ######## Catch ValueErrors:
            catch = (ValueError, SyntaxError)
            caught, raised = self.apply_catcher(catch, handler, eg)
            self.checkMatch(raised, eg_template, eg)
            self.checkMatch(caught, valueErrors_template, eg)

    def test_catch_handler_reraise_new_and_all_old(self):
        eg = self.eg
        eg_template = self.eg_template
        valueErrors_template = self.valueErrors_template
        typeErrors_template = self.typeErrors_template

        class Handler(self.BaseHandler):
            def handle(self, eg):
                raise ExceptionGroup(
                      "msg1",
                      eg,
                      ValueError('foo'),
                      ExceptionGroup(
                          "msg2", SyntaxError('bar'), ValueError('baz')))

        newErrors_template = [
            ValueError('foo'), [SyntaxError('bar'), ValueError('baz')]]

        # ######## Catch TypeErrors:
        caught, raised = self.apply_catcher(TypeError, Handler, eg)
        self.checkMatch(raised, [eg_template, newErrors_template], eg)
        self.checkMatch(caught, typeErrors_template, eg)

        # ######## Catch ValueErrors:
        caught, raised = self.apply_catcher(ValueError, Handler, eg)
        self.checkMatch(raised, [eg_template, newErrors_template], eg)
        self.checkMatch(caught, valueErrors_template, eg)

    def test_catch_handler_reraise_new_and_some_old(self):
        eg = self.eg
        eg_template = self.eg_template
        valueErrors_template = self.valueErrors_template
        typeErrors_template = self.typeErrors_template

        class Handler(self.BaseHandler):
            def handle(self, eg):
                raise ExceptionGroup(
                    "msg1",
                    eg.excs[0],
                    ValueError('foo'),
                    ExceptionGroup(
                        "msg2", SyntaxError('bar'), ValueError('baz')))

        newErrors_template = [
            ValueError('foo'), [SyntaxError('bar'), ValueError('baz')]]

        # ######## Catch TypeErrors:
        caught, raised = self.apply_catcher(TypeError, Handler, eg)
        self.checkMatch(raised, [eg_template, newErrors_template], eg)
        self.checkMatch(caught, typeErrors_template, eg)

        # ######## Catch ValueErrors:
        caught, raised = self.apply_catcher(ValueError, Handler, eg)
        # eg.excs[0] is reraised and eg.excs[1] is consumed
        self.checkMatch(raised, [[eg_template[0]], newErrors_template], eg)
        self.checkMatch(caught, valueErrors_template, eg)

if __name__ == '__main__':
    unittest.main()
