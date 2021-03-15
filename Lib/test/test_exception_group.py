
import collections.abc
import functools
import traceback
import unittest
from io import StringIO


class ExceptionGroupHelper:
    @staticmethod
    def subgroup(exc, keep):
        """ Split an ExceptionGroup to extract only exceptions in keep

        keep: List[BaseException]
        """
        return exc.subgroup(lambda e: e in keep)

    @staticmethod
    def flatten(exc):
        ''' iterate over the individual exceptions (flattens the tree) '''
        if isinstance(exc, BaseExceptionGroup):
            for e in exc.errors:
                for e_ in ExceptionGroupHelper.flatten(e):
                    yield e_
        else:
            yield exc


def newEG(msg, raisers, cls=ExceptionGroup):
    excs = []
    for r in raisers:
        try:
            r()
        except (Exception, ExceptionGroup) as e:
            excs.append(e)
    try:
        raise cls(msg, excs)
    except ExceptionGroup as e:
        return e


def newVE(v):
    raise ValueError(v)


def newTE(t):
    raise TypeError(t)


def newSimpleEG(msg):
    bind = functools.partial
    return newEG(msg, [bind(newVE, 1), bind(newTE, int), bind(newVE, 2)])

class MyExceptionGroup(ExceptionGroup):
    pass


def newNestedEG(arg):
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
    result = None
    e = ExceptionGroupHelper.subgroup(eg, [exc])
    while e is not None:
        if isinstance(e, ExceptionGroup):
            assert len(e.errors) == 1 and exc in ExceptionGroupHelper.flatten(e)
        r = traceback.extract_tb(e.__traceback__)
        if result is None:
            result = []
        result.extend(r)
        e = e.errors[0] if isinstance(e, ExceptionGroup) else None
    return result


class ExceptionGroupTestBadInputs(unittest.TestCase):
    def test_simple_group_bad_constructor_args(self):
        not_seq1 = 'Expected msg followed by a sequence of the nested exceptions'
        not_seq2 = 'Expected a sequence of the nested exceptions'
        not_seq3 = 'Expected a message'
        not_exc = 'Nested exception must derive from BaseException'
        empty_seq = 'Expected non-empty sequence of nested exceptions'
        with self.assertRaisesRegex(TypeError, not_seq1):
            _ = ExceptionGroup('no errors')
        with self.assertRaisesRegex(TypeError, not_seq2):
            _ = ExceptionGroup('errors not sequence', {ValueError(42)})
        with self.assertRaisesRegex(TypeError, not_exc):
            _ = ExceptionGroup('bad error', ["not an exception"])
        with self.assertRaisesRegex(ValueError, empty_seq):
            _ = ExceptionGroup("eg", [])
        with self.assertRaisesRegex(TypeError, not_seq1):
            _ = ExceptionGroup(ValueError(12))
        with self.assertRaisesRegex(TypeError, not_seq3):
            _ = ExceptionGroup(ValueError(12), SyntaxError('bad syntax'))


class BaseExceptionGroupInstanceCreation(unittest.TestCase):
    def test_without_BaseException_create_ExceptionGroup(self):
        self.assertIsInstance(
            BaseExceptionGroup("beg", [ValueError(12), TypeError(42)]),
            ExceptionGroup)

        self.assertIsInstance(
            ExceptionGroup("eg", [ValueError(12), TypeError(42)]),
            ExceptionGroup)

    def test_with_BaseException_create_BaseExceptionGroup(self):
        beg = BaseExceptionGroup("beg", [ValueError(12), KeyboardInterrupt(42)])
        self.assertIsInstance(beg, BaseExceptionGroup)
        self.assertFalse(isinstance(beg, ExceptionGroup))

        msg = "Cannot nest BaseExceptions in an ExceptionGroup"
        with self.assertRaisesRegex(TypeError, msg):
            ExceptionGroup("eg", [ValueError(12), KeyboardInterrupt(42)])


class ExceptionGroupTestBase(unittest.TestCase):
    def assertMatchesTemplate(self, exc, template):
        """ Assert that the exception matches the template """
        if isinstance(exc, BaseExceptionGroup):
            self.assertIsInstance(template, collections.abc.Sequence)
            self.assertEqual(len(exc.errors), len(template))
            for e, t in zip(exc.errors, template):
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

        self.assertEqual(list(ExceptionGroupHelper.flatten(eg)), list(eg.errors))  # check iteration

        # check msg
        self.assertEqual(eg.message, 'simple EG')
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
        self.assertIsInstance(eg, BaseExceptionGroup)
        fnames = [t.name for t in traceback.extract_tb(eg.__traceback__)]
        all_excs = list(ExceptionGroupHelper.flatten(eg))

        match, rest = eg.split(types)
        subgroup = eg.subgroup(types)

        if match is not None:
            self.assertIsInstance(match, BaseExceptionGroup)
            for e in ExceptionGroupHelper.flatten(match):
                self.assertIsInstance(e, types)

            self.assertIsNotNone(subgroup)
            self.assertIsInstance(subgroup, BaseExceptionGroup)
            for e in ExceptionGroupHelper.flatten(subgroup):
                self.assertIsInstance(e, types)

        if rest is not None:
            self.assertIsInstance(rest, BaseExceptionGroup)
            for e in ExceptionGroupHelper.flatten(rest):
                self.assertNotIsInstance(e, types)

        match_len = len(list(ExceptionGroupHelper.flatten(match))) if match is not None else 0
        rest_len = len(list(ExceptionGroupHelper.flatten(rest))) if rest is not None else 0
        subgroup_len = len(list(ExceptionGroupHelper.flatten(subgroup))) if subgroup is not None else 0
        self.assertEqual(len(list(all_excs)), match_len + rest_len)
        self.assertEqual(match_len, subgroup_len)

        for e in all_excs:
            # each exception is in eg and exactly one of match and rest
            self.assertIn(e, ExceptionGroupHelper.flatten(eg))
            self.assertNotEqual(match and e in ExceptionGroupHelper.flatten(match),
                                rest and e in ExceptionGroupHelper.flatten(rest))
            self.assertEqual(match and e in ExceptionGroupHelper.flatten(match),
                             subgroup and e in ExceptionGroupHelper.flatten(subgroup))

        for part in [match, rest, subgroup]:
            if part is not None:
                self.assertEqual(eg.message, part.message)
                for e in ExceptionGroupHelper.flatten(part):
                    self.assertEqual(
                        extract_traceback(e, eg),
                        extract_traceback(e, part))

        return match, rest

    def test_split_by_type(self):
        try:
            raise newNestedEG(25)
        except ExceptionGroup as e:
            eg = e

        fnames = ['test_split_by_type', 'newEG']
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
        match, rest = eg.split(ExceptionGroup)
        self.assertIs(match, eg)
        self.assertIsNone(rest)

        # Match MyExceptionGroup (ExceptionGroup subclass)
        match, rest = eg.split(MyExceptionGroup)
        self.assertMatchesTemplate(match, [eg_template[0]])
        self.assertMatchesTemplate(rest, [eg_template[1]])

    def test_split_BaseExceptionGroup(self):
        def exc(ex):
            try:
                raise ex
            except BaseException as e:
                return e

        try:
            raise BaseExceptionGroup("beg", [exc(ValueError(1)), exc(KeyboardInterrupt(2))])
        except BaseExceptionGroup as e:
            beg = e

        # Match Nothing
        match, rest = self._split_exception_group(beg, TypeError)
        self.assertIsNone(match)
        self.assertMatchesTemplate(rest, [ValueError(1), KeyboardInterrupt(2)])
        self.assertFalse(isinstance(rest, ExceptionGroup))

        # Match Everything
        match, rest = self._split_exception_group(beg, (ValueError, KeyboardInterrupt))
        self.assertMatchesTemplate(match, [ValueError(1), KeyboardInterrupt(2)])
        self.assertIsNone(rest)
        self.assertFalse(isinstance(match, ExceptionGroup))

        # Match ValueErrors
        match, rest = self._split_exception_group(beg, ValueError)
        self.assertMatchesTemplate(match, [ValueError(1)])
        self.assertMatchesTemplate(rest, [KeyboardInterrupt(2)])
        self.assertTrue(isinstance(match, ExceptionGroup))
        self.assertFalse(isinstance(rest, ExceptionGroup))

        # Match KeyboardInterrupts
        match, rest = self._split_exception_group(beg, KeyboardInterrupt)
        self.assertMatchesTemplate(match, [KeyboardInterrupt(2)])
        self.assertMatchesTemplate(rest, [ValueError(1)])
        self.assertFalse(isinstance(match, ExceptionGroup))
        self.assertTrue(isinstance(rest, ExceptionGroup))

    def test_split_ExceptionGroup_subclass_no_derive_new_override(self):
        class EG(ExceptionGroup):
            pass

        try:
            try:
                try:
                    raise TypeError(2)
                except TypeError as te:
                    raise EG("nested", [te])
            except EG as nested:
                try:
                    raise ValueError(1)
                except ValueError as ve:
                    raise EG("eg", [ve, nested])
        except EG as e:
            eg = e

        # Match Nothing
        match, rest = self._split_exception_group(eg, OSError)
        self.assertIsNone(match)
        self.assertMatchesTemplate(rest, [ValueError(1), [TypeError(2)]])
        self.assertFalse(isinstance(rest, EG))
        self.assertTrue(isinstance(rest, ExceptionGroup))

        # Match Everything
        match, rest = self._split_exception_group(eg, (ValueError, TypeError))
        self.assertMatchesTemplate(match, [ValueError(1), [TypeError(2)]])
        self.assertIsNone(rest)
        self.assertFalse(isinstance(match, EG))
        self.assertTrue(isinstance(match, ExceptionGroup))

        # Match ValueErrors
        match, rest = self._split_exception_group(eg, ValueError)
        self.assertMatchesTemplate(match, [ValueError(1)])
        self.assertMatchesTemplate(rest, [[TypeError(2)]])
        for e in [match, rest]:
            self.assertFalse(isinstance(e, EG))
            self.assertTrue(isinstance(e, ExceptionGroup))

        # Match TypeErrors
        match, rest = self._split_exception_group(eg, TypeError)
        self.assertMatchesTemplate(match, [[TypeError(2)]])
        self.assertMatchesTemplate(rest, [ValueError(1)])
        for e in [match, rest]:
            self.assertFalse(isinstance(e, EG))
            self.assertTrue(isinstance(e, ExceptionGroup))

    def test_split_ExceptionGroup_subclass_derive_new_override(self):
        class EG(ExceptionGroup):
            def __new__(cls, message, excs, code):
                obj = super().__new__(cls, message, excs)
                obj.code = code
                return obj

            def derive_new(self, excs):
                return EG(self.message, excs, self.code)

        try:
            try:
                try:
                    raise TypeError(2)
                except TypeError as te:
                    raise EG("nested", [te], 101)
            except EG as nested:
                try:
                    raise ValueError(1)
                except ValueError as ve:
                    raise EG("eg", [ve, nested], 42)
        except EG as e:
            eg = e

        # Match Nothing
        match, rest = self._split_exception_group(eg, OSError)
        self.assertIsNone(match)
        self.assertMatchesTemplate(rest, [ValueError(1), [TypeError(2)]])
        self.assertTrue(isinstance(rest, EG))
        self.assertEqual(rest.code, 42)
        self.assertEqual(rest.errors[1].code, 101)

        # Match Everything
        match, rest = self._split_exception_group(eg, (ValueError, TypeError))
        self.assertMatchesTemplate(match, [ValueError(1), [TypeError(2)]])
        self.assertIsNone(rest)
        self.assertTrue(isinstance(match, EG))
        self.assertEqual(match.code, 42)
        self.assertEqual(match.errors[1].code, 101)

        # Match ValueErrors
        match, rest = self._split_exception_group(eg, ValueError)
        self.assertMatchesTemplate(match, [ValueError(1)])
        self.assertMatchesTemplate(rest, [[TypeError(2)]])
        self.assertTrue(isinstance(match, EG))
        self.assertTrue(isinstance(rest, EG))
        self.assertEqual(match.code, 42)
        self.assertEqual(rest.code, 42)
        self.assertEqual(rest.errors[0].code, 101)

        # Match TypeErrors
        match, rest = self._split_exception_group(eg, TypeError)
        self.assertMatchesTemplate(match, [[TypeError(2)]])
        self.assertMatchesTemplate(rest, [ValueError(1)])
        self.assertTrue(isinstance(match, EG))
        self.assertTrue(isinstance(rest, EG))
        self.assertEqual(match.code, 42)
        self.assertEqual(rest.code, 42)
        self.assertEqual(match.errors[0].code, 101)


if __name__ == '__main__':
    unittest.main()
