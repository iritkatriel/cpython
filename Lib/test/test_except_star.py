
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
                raise ExceptionGroup("eg", ValueError(42))
            except *(TypeError, ExceptionGroup):
                pass


class TestExceptStarSplitSemantics(unittest.TestCase):

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
            self.assertEqual(exc.msg, template.msg)
            self.assertEqual(len(exc.excs), len(template.excs))
            for e, t in zip(exc.excs, template.excs):
                self.assertExceptionIsLike(e, t)

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
            ExceptionGroup("eg", ValueError("V"), TypeError("T")),
            SyntaxError,
            None,
            ExceptionGroup("eg", ValueError("V"), TypeError("T")))

    def test_match_single_type(self):
        self.doSplitTest(
            ExceptionGroup("eg", ValueError("V1"), ValueError("V2")),
            ValueError,
            ExceptionGroup("eg", ValueError("V1"), ValueError("V2")),
            None)

    def test_match_single_type_partial_match(self):
        self.doSplitTest(
            ExceptionGroup(
                "eg",
                ValueError("V1"),
                OSError("OS"),
                ValueError("V2")),
            ValueError,
            ExceptionGroup("eg", ValueError("V1"), ValueError("V2")),
            ExceptionGroup("eg", OSError("OS")))

    def test_match_single_type_nested(self):
        self.doSplitTest(
            ExceptionGroup(
                "g1",
                ValueError("V1"),
                OSError("OS1"),
                ExceptionGroup(
                    "g2", OSError("OS2"), ValueError("V2"), TypeError("T"))),
            ValueError,
            ExceptionGroup(
                "g1",
                ValueError("V1"),
                ExceptionGroup("g2", ValueError("V2"))),
            ExceptionGroup(
                "g1",
                OSError("OS1"),
                ExceptionGroup("g2", OSError("OS2"), TypeError("T"))))

    def test_match_type_tuple_nested(self):
        self.doSplitTest(
            ExceptionGroup(
                "g1",
                ValueError("V1"),
                OSError("OS1"),
                ExceptionGroup(
                    "g2", OSError("OS2"), ValueError("V2"), TypeError("T"))),
            (ValueError, TypeError),
            ExceptionGroup(
                "g1",
                ValueError("V1"),
                ExceptionGroup("g2", ValueError("V2"), TypeError("T"))),
            ExceptionGroup(
                "g1",
                OSError("OS1"),
                ExceptionGroup("g2", OSError("OS2"))))

    def test_empty_groups_removed(self):
        self.doSplitTest(
            ExceptionGroup(
                "eg",
                ExceptionGroup("g1", ValueError("V1")),
                ExceptionGroup("g2", ValueError("V2"), TypeError("T1")),
                ExceptionGroup("g3", TypeError("T2"))),
            TypeError,
            ExceptionGroup("eg",
                ExceptionGroup("g2", TypeError("T1")),
                ExceptionGroup("g3", TypeError("T2"))),
            ExceptionGroup("eg",
                    ExceptionGroup("g1", ValueError("V1")),
                    ExceptionGroup("g2", ValueError("V2"))))

    def test_singleton_groups_are_kept(self):
        self.doSplitTest(
            ExceptionGroup(
            "g1",
            ExceptionGroup(
                "g2",
                ExceptionGroup("g3", ValueError("V1")),
                ExceptionGroup("g4", TypeError("T")))),
            TypeError,
            ExceptionGroup(
                "g1",
                ExceptionGroup("g2", ExceptionGroup("g4", TypeError("T")))),
            ExceptionGroup(
                "g1",
                ExceptionGroup("g2", ExceptionGroup("g3", ValueError("V1")))))

    def test_plain_exceptions_matched(self):
        self.doSplitTest(
            ValueError("V"),
            ValueError,
            ExceptionGroup("", ValueError("V")),
            None)

    def test_plain_exceptions_not_matched(self):
        self.doSplitTest(
            ValueError("V"),
            TypeError,
            None,
            ValueError("V"))

    def test_match__supertype(self):
        self.doSplitTest(
            ExceptionGroup("eg", BlockingIOError("io"), TypeError("T")),
            OSError,
            ExceptionGroup("eg", BlockingIOError("io")),
            ExceptionGroup("eg", TypeError("T")))

    def test_first_match_wins_named(self):
        try:
            raise ExceptionGroup("eg", BlockingIOError("io"))
        except *OSError as e:
            self.assertExceptionIsLike(e,
                ExceptionGroup("eg", BlockingIOError("io")))
        except *BlockingIOError:
            self.fail("Should have been matched as OSError")
        else:
            self.fail("Exception not raised")

    def test_first_match_wins_unnamed(self):
        try:
            raise ExceptionGroup("eg", BlockingIOError("io"))
        except *OSError:
            e = sys.exc_info()[1]
            self.assertExceptionIsLike(e,
                ExceptionGroup("eg", BlockingIOError("io")))
        except *BlockingIOError:
            pass
        else:
            self.fail("Exception not raised")

    def test_nested_except_stars(self):
        try:
            raise ExceptionGroup("eg", BlockingIOError("io"))
        except *BlockingIOError:
            try:
                raise ExceptionGroup("eg", ValueError("io"))
            except* ValueError:
                pass
            else:
                self.fail("Exception not raised")
        else:
            self.fail("Exception not raised")

    def test_nested_in_loop(self):
        for _ in range(2):
            try:
                raise ExceptionGroup("eg", BlockingIOError("io"))
            except *BlockingIOError:
                pass
            else:
                self.fail("Exception not raised")


class TestExceptStarReraise(unittest.TestCase):
    pass


class TestExceptStarChaining(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
