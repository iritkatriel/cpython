
import sys
import unittest

class TestInvalidExceptStar(unittest.TestCase):
    def test_mixed_except_and_except_star_is_syntax_error(self):
        errors = [
            "try: pass\nexcept ValueError: pass\nexcept* TypeError: pass\n",
            "try: pass\nexcept* ValueError: pass\nexcept TypeError: pass\n",
            "try: pass\nexcept ValueError as e: pass\nexcept* TypeError: pass\n",
            "try: pass\nexcept* ValueError as e: pass\nexcept TypeError: pass\n",
            "try: pass\nexcept ValueError: pass\nexcept* TypeError as e: pass\n",
            "try: pass\nexcept* ValueError: pass\nexcept TypeError as e: pass\n",
            "try: pass\nexcept ValueError: pass\nexcept*: pass\n",
            "try: pass\nexcept* ValueError: pass\nexcept: pass\n",
        ]

        for err in errors:
            with self.assertRaises(SyntaxError):
                compile(err, "<string>", "exec")

    def test_except_star_ExceptionGroup_is_runtime_error_single(self):
        with self.assertRaises(TypeError):
            try:
                raise OSError("blah")
            except *ExceptionGroup as e:
                pass

    def test_except_star_ExceptionGroup_is_runtime_error_tuple(self):
        with self.assertRaises(TypeError):
            try:
                raise ExceptionGroup("eg", [ValueError(42)])
            except *(TypeError, ExceptionGroup):
                pass


class ExceptStarTest(unittest.TestCase):
    def assertExceptionIsLike(self, exc, template):
        if exc is None and template is None:
            return

        if template is None:
            self.fail(f"unexpected exception: {exc}")

        if exc is None:
            self.fail(f"expected an exception like {template!r}, got None")

        if not isinstance(exc, ExceptionGroup):
            self.assertEqual(exc.__class__, template.__class__)
            self.assertEqual(exc.args[0], template.args[0])
        else:
            self.assertEqual(exc.message, template.message)
            self.assertEqual(len(exc.errors), len(template.errors))
            for e, t in zip(exc.errors, template.errors):
                self.assertExceptionIsLike(e, t)

    def assertMetadataEqual(self, e1, e2):
        if e1 is None or e2 is None:
            self.assertTrue(e1 is None and e2 is None)
        else:
            self.assertEqual(e1.__context__, e2.__context__)
            self.assertEqual(e1.__cause__, e2.__cause__)
            self.assertEqual(e1.__traceback__, e2.__traceback__)

    def assertMetadataNotEqual(self, e1, e2):
        return not self.assertMetadataEqual(e2, e2)



class TestExceptStarSplitSemantics(ExceptStarTest):
    def doSplitTestNamed(self, exc, T, match_template, rest_template):
        exc_info = match = rest = None
        try:
            try:
                raise exc
            except *T as e:
                exc_info = sys.exc_info()
                match = e
        except BaseException as e:
            rest = e

        self.assertExceptionIsLike(match, match_template)
        if match_template:
            self.assertEqual(exc_info[0], type(match_template))
        self.assertExceptionIsLike(rest, rest_template)
        self.assertEqual(sys.exc_info(), (None, None, None))

    def doSplitTestUnnamed(self, exc, T, match_template, rest_template):
        exc_info = match = rest = None
        try:
            try:
                raise exc
            except *T:
                exc_info = sys.exc_info()
                match = sys.exc_info()[1]
            else:
                if rest_template:
                    self.fail("Exception not raised")
        except BaseException as e:
            rest = e

        self.assertExceptionIsLike(match, match_template)
        if match_template:
            self.assertEqual(exc_info[0], type(match_template))
        self.assertExceptionIsLike(rest, rest_template)
        self.assertEqual(sys.exc_info(), (None, None, None))

    def doSplitTest(self, exc, T, match_template, rest_template):
        self.doSplitTestNamed(exc, T, match_template, rest_template)
        self.doSplitTestUnnamed(exc, T, match_template, rest_template)

    def test_no_match_single_type(self):
        self.doSplitTest(
            ExceptionGroup("test1", [ValueError("V"), TypeError("T")]),
            SyntaxError,
            None,
            ExceptionGroup("test1", [ValueError("V"), TypeError("T")]))

    def test_match_single_type(self):
        self.doSplitTest(
            ExceptionGroup("test2", [ValueError("V1"), ValueError("V2")]),
            ValueError,
            ExceptionGroup("test2", [ValueError("V1"), ValueError("V2")]),
            None)

    def test_match_single_type_partial_match(self):
        self.doSplitTest(
            ExceptionGroup(
                "test3",
                [ValueError("V1"), OSError("OS"), ValueError("V2")]),
            ValueError,
            ExceptionGroup("test3", [ValueError("V1"), ValueError("V2")]),
            ExceptionGroup("test3", [OSError("OS")]))

    def test_match_single_type_nested(self):
        self.doSplitTest(
            ExceptionGroup(
                "g1", [
                ValueError("V1"),
                OSError("OS1"),
                ExceptionGroup(
                    "g2", [
                    OSError("OS2"),
                    ValueError("V2"),
                    TypeError("T")])]),
            ValueError,
            ExceptionGroup(
                "g1", [
                ValueError("V1"),
                ExceptionGroup("g2", [ValueError("V2")])]),
            ExceptionGroup("g1", [
                OSError("OS1"),
                ExceptionGroup("g2", [
                    OSError("OS2"), TypeError("T")])]))

    def test_match_type_tuple_nested(self):
        self.doSplitTest(
            ExceptionGroup(
                "h1", [
                ValueError("V1"),
                OSError("OS1"),
                ExceptionGroup(
                    "h2", [OSError("OS2"), ValueError("V2"), TypeError("T")])]),
            (ValueError, TypeError),
            ExceptionGroup(
                "h1", [
                ValueError("V1"),
                ExceptionGroup("h2", [ValueError("V2"), TypeError("T")])]),
            ExceptionGroup(
                "h1", [
                OSError("OS1"),
                ExceptionGroup("h2", [OSError("OS2")])]))

    def test_empty_groups_removed(self):
        self.doSplitTest(
            ExceptionGroup(
                "eg", [
                ExceptionGroup("i1", [ValueError("V1")]),
                ExceptionGroup("i2", [ValueError("V2"), TypeError("T1")]),
                ExceptionGroup("i3", [TypeError("T2")])]),
            TypeError,
            ExceptionGroup("eg", [
                ExceptionGroup("i2", [TypeError("T1")]),
                ExceptionGroup("i3", [TypeError("T2")])]),
            ExceptionGroup("eg", [
                    ExceptionGroup("i1", [ValueError("V1")]),
                    ExceptionGroup("i2", [ValueError("V2")])]))

    def test_singleton_groups_are_kept(self):
        self.doSplitTest(
            ExceptionGroup("j1", [
                ExceptionGroup("j2", [
                    ExceptionGroup("j3", [ValueError("V1")]),
                    ExceptionGroup("j4", [TypeError("T")])])]),
            TypeError,
            ExceptionGroup(
                "j1",
                [ExceptionGroup("j2", [ExceptionGroup("j4", [TypeError("T")])])]),
            ExceptionGroup(
                "j1",
                [ExceptionGroup("j2", [ExceptionGroup("j3", [ValueError("V1")])])]))

    def test_plain_exceptions_matched(self):
        self.doSplitTest(
            ValueError("V"),
            ValueError,
            ExceptionGroup("", [ValueError("V")]),
            None)

    def test_plain_exceptions_not_matched(self):
        self.doSplitTest(
            ValueError("V"),
            TypeError,
            None,
            ValueError("V"))

    def test_match__supertype(self):
        self.doSplitTest(
            ExceptionGroup("st", [BlockingIOError("io"), TypeError("T")]),
            OSError,
            ExceptionGroup("st", [BlockingIOError("io")]),
            ExceptionGroup("st", [TypeError("T")]))

    def test_multiple_matches_named(self):
        try:
            raise ExceptionGroup("mmn", [OSError("os"), BlockingIOError("io")])
        except *BlockingIOError as e:
            self.assertExceptionIsLike(e,
                ExceptionGroup("mmn", [BlockingIOError("io")]))
        except *OSError as e:
            self.assertExceptionIsLike(e,
                ExceptionGroup("mmn", [OSError("os")]))
        else:
            self.fail("Exception not raised")

    def test_multiple_matches_unnamed(self):
        try:
            raise ExceptionGroup("mmu", [OSError("os"), BlockingIOError("io")])
        except *BlockingIOError:
            e = sys.exc_info()[1]
            self.assertExceptionIsLike(e,
                ExceptionGroup("mmu", [BlockingIOError("io")]))
        except *OSError:
            e = sys.exc_info()[1]
            self.assertExceptionIsLike(e,
                ExceptionGroup("mmu", [OSError("os")]))
        else:
            self.fail("Exception not raised")

    def test_first_match_wins_named(self):
        try:
            raise ExceptionGroup("fst", [BlockingIOError("io")])
        except *OSError as e:
            self.assertExceptionIsLike(e,
                ExceptionGroup("fst", [BlockingIOError("io")]))
        except *BlockingIOError:
            self.fail("Should have been matched as OSError")
        else:
            self.fail("Exception not raised")

    def test_first_match_wins_unnamed(self):
        try:
            raise ExceptionGroup("fstu", [BlockingIOError("io")])
        except *OSError:
            e = sys.exc_info()[1]
            self.assertExceptionIsLike(e,
                ExceptionGroup("fstu", [BlockingIOError("io")]))
        except *BlockingIOError:
            pass
        else:
            self.fail("Exception not raised")

    def test_nested_except_stars(self):
        try:
            raise ExceptionGroup("n", [BlockingIOError("io")])
        except *BlockingIOError:
            try:
                raise ExceptionGroup("n", [ValueError("io")])
            except* ValueError:
                pass
            else:
                self.fail("Exception not raised")
        else:
            self.fail("Exception not raised")

    def test_nested_in_loop(self):
        for _ in range(2):
            try:
                raise ExceptionGroup("nl", [BlockingIOError("io")])
            except *BlockingIOError:
                pass
            else:
                self.fail("Exception not raised")


class TestExceptStarReraise(ExceptStarTest):
    def test_reraise_all_named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", [TypeError(1), ValueError(2), OSError(3)])
            except *TypeError as e:
                raise
            except *ValueError as e:
                raise
            # OSError not handled
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc,
            ExceptionGroup("eg", [TypeError(1), ValueError(2), OSError(3)]))

    def test_reraise_all_unnamed(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", [TypeError(1), ValueError(2), OSError(3)])
            except *TypeError:
                raise
            except *ValueError:
                raise
            # OSError not handled
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc,
            ExceptionGroup("eg", [TypeError(1), ValueError(2), OSError(3)]))

    def test_reraise_some_handle_all_named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", [TypeError(1), ValueError(2), OSError(3)])
            except *TypeError as e:
                raise
            except *ValueError as e:
                pass
            # OSError not handled
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("eg", [TypeError(1), OSError(3)]))

    def test_reraise_partial_handle_all_unnamed(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", [TypeError(1), ValueError(2)])
            except *TypeError:
                raise
            except *ValueError:
                pass
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("eg", [TypeError(1)]))

    def test_reraise_partial_handle_some_named(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", [TypeError(1), ValueError(2), OSError(3)])
            except *TypeError as e:
                raise
            except *ValueError as e:
                pass
            # OSError not handled
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("eg", [TypeError(1), OSError(3)]))

    def test_reraise_partial_handle_some_unnamed(self):
        try:
            try:
                raise ExceptionGroup(
                    "eg", [TypeError(1), ValueError(2), OSError(3)])
            except *TypeError:
                raise
            except *ValueError:
                pass
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("eg", [TypeError(1), OSError(3)]))

    def test_reraise_plain_exception_named(self):
        try:
            try:
                raise ValueError(42)
            except *ValueError as e:
                raise
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [ValueError(42)]))

    def test_reraise_plain_exception_unnamed(self):
        try:
            try:
                raise ValueError(42)
            except *ValueError:
                raise
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [ValueError(42)]))


class TestExceptStarRaise(ExceptStarTest):
    def test_raise_named(self):
        orig = ExceptionGroup("eg", [ValueError(1), OSError(2)])
        try:
            try:
                raise orig
            except *OSError as e:
                raise TypeError(3)
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc,
            ExceptionGroup(
                "", [TypeError(3), ExceptionGroup("eg", [ValueError(1)])]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [OSError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)

    def test_raise_unnamed(self):
        orig = ExceptionGroup("eg", [ValueError(1), OSError(2)])
        try:
            try:
                raise orig
            except *OSError:
                raise TypeError(3)
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc,
            ExceptionGroup(
                "", [TypeError(3), ExceptionGroup("eg", [ValueError(1)])]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [OSError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)

    def test_raise_handle_all_raise_one_named(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *(TypeError, ValueError) as e:
                raise SyntaxError(3)
        except BaseException as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1), ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)

    def test_raise_handle_all_raise_one_unnamed(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *(TypeError, ValueError) as e:
                raise SyntaxError(3)
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1), ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)

    def test_raise_handle_all_raise_two_named(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *TypeError as e:
                raise SyntaxError(3)
            except *ValueError as e:
                raise SyntaxError(4)
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3), SyntaxError(4)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1)]))

        self.assertExceptionIsLike(
            exc.errors[1].__context__,
            ExceptionGroup("eg", [ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[1].__context__)

    def test_raise_handle_all_raise_two_unnamed(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *TypeError:
                raise SyntaxError(3)
            except *ValueError:
                raise SyntaxError(4)
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3), SyntaxError(4)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1)]))

        self.assertExceptionIsLike(
            exc.errors[1].__context__,
            ExceptionGroup("eg", [ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[1].__context__)

class TestExceptStarRaiseFrom(ExceptStarTest):
    def test_raise_named(self):
        orig = ExceptionGroup("eg", [ValueError(1), OSError(2)])
        try:
            try:
                raise orig
            except *OSError as e:
                raise TypeError(3) from e
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc,
            ExceptionGroup(
                "", [TypeError(3), ExceptionGroup("eg", [ValueError(1)])]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [OSError(2)]))

        self.assertExceptionIsLike(
            exc.errors[0].__cause__,
            ExceptionGroup("eg", [OSError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[0].__cause__)
        self.assertMetadataNotEqual(orig, exc.errors[1].__context__)
        self.assertMetadataNotEqual(orig, exc.errors[1].__cause__)

    def test_raise_unnamed(self):
        orig = ExceptionGroup("eg", [ValueError(1), OSError(2)])
        try:
            try:
                raise orig
            except *OSError:
                e = sys.exc_info()[1]
                raise TypeError(3) from e
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc,
            ExceptionGroup(
                "", [TypeError(3), ExceptionGroup("eg", [ValueError(1)])]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [OSError(2)]))

        self.assertExceptionIsLike(
            exc.errors[0].__cause__,
            ExceptionGroup("eg", [OSError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[0].__cause__)
        self.assertMetadataNotEqual(orig, exc.errors[1].__context__)
        self.assertMetadataNotEqual(orig, exc.errors[1].__cause__)

    def test_raise_handle_all_raise_one_named(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *(TypeError, ValueError) as e:
                raise SyntaxError(3) from e
        except BaseException as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1), ValueError(2)]))

        self.assertExceptionIsLike(
            exc.errors[0].__cause__,
            ExceptionGroup("eg", [TypeError(1), ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[0].__cause__)

    def test_raise_handle_all_raise_one_unnamed(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *(TypeError, ValueError) as e:
                e = sys.exc_info()[1]
                raise SyntaxError(3) from e
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1), ValueError(2)]))

        self.assertExceptionIsLike(
            exc.errors[0].__cause__,
            ExceptionGroup("eg", [TypeError(1), ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[0].__cause__)

    def test_raise_handle_all_raise_two_named(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *TypeError as e:
                raise SyntaxError(3) from e
            except *ValueError as e:
                raise SyntaxError(4) from e
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3), SyntaxError(4)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1)]))

        self.assertExceptionIsLike(
            exc.errors[0].__cause__,
            ExceptionGroup("eg", [TypeError(1)]))

        self.assertExceptionIsLike(
            exc.errors[1].__context__,
            ExceptionGroup("eg", [ValueError(2)]))

        self.assertExceptionIsLike(
            exc.errors[1].__cause__,
            ExceptionGroup("eg", [ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[0].__cause__)

    def test_raise_handle_all_raise_two_unnamed(self):
        orig = ExceptionGroup("eg", [TypeError(1), ValueError(2)])
        try:
            try:
                raise orig
            except *TypeError:
                e = sys.exc_info()[1]
                raise SyntaxError(3) from e
            except *ValueError:
                e = sys.exc_info()[1]
                raise SyntaxError(4) from e
        except ExceptionGroup as e:
            exc = e

        self.assertExceptionIsLike(
            exc, ExceptionGroup("", [SyntaxError(3), SyntaxError(4)]))

        self.assertExceptionIsLike(
            exc.errors[0].__context__,
            ExceptionGroup("eg", [TypeError(1)]))

        self.assertExceptionIsLike(
            exc.errors[0].__cause__,
            ExceptionGroup("eg", [TypeError(1)]))

        self.assertExceptionIsLike(
            exc.errors[1].__context__,
            ExceptionGroup("eg", [ValueError(2)]))

        self.assertExceptionIsLike(
            exc.errors[1].__cause__,
            ExceptionGroup("eg", [ValueError(2)]))

        self.assertMetadataNotEqual(orig, exc)
        self.assertMetadataEqual(orig, exc.errors[0].__context__)
        self.assertMetadataEqual(orig, exc.errors[0].__cause__)
        self.assertMetadataEqual(orig, exc.errors[1].__context__)
        self.assertMetadataEqual(orig, exc.errors[1].__cause__)


if __name__ == '__main__':
    unittest.main()
