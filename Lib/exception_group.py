
import sys
import textwrap
import traceback


class ExceptionGroup(BaseException):
    def __init__(self, message, *excs):
        """ Construct a new ExceptionGroup

        message: The exception Group's error message
        excs: sequence of exceptions
        """
        assert message is None or isinstance(message, str)
        assert all(isinstance(e, BaseException) for e in excs)

        self.message = message
        self.excs = excs
        super().__init__(self.message)

    @staticmethod
    def project(exc, condition, with_complement=False):
        """ Split an ExceptionGroup based on an exception predicate

        returns a new ExceptionGroup, match, of the exceptions of exc
        for which condition returns true. If with_complement is true,
        returns another ExceptionGroup for the exception for which
        condition returns false.  Note that condition is checked for
        exc and nested ExceptionGroups as well, and if it returns true
        then the whole ExceptionGroup is considered to be matched.

        match and rest have the same nested structure as exc, but empty
        sub-exceptions are not included. They have the same message,
        __traceback__, __cause__ and __context__ fields as exc.

        condition: BaseException --> Boolean
        with_complement: Bool  If True, construct also an EG of the non-matches
        """

        if condition(exc):
            return exc, None
        elif not isinstance(exc, ExceptionGroup):
            return None, exc if with_complement else None
        else:
            # recurse into ExceptionGroup
            match_exc = rest_exc = None
            match = []
            rest = [] if with_complement else None
            for e in exc.excs:
                e_match, e_rest = ExceptionGroup.project(
                    e, condition, with_complement=with_complement)

                if e_match is not None:
                    match.append(e_match)
                if with_complement and e_rest is not None:
                    rest.append(e_rest)

            def copy_metadata(src, target):
                target.__traceback__ = src.__traceback__
                target.__context__ = src.__context__
                target.__cause__ = src.__cause__

            if match:
                match_exc = ExceptionGroup(exc.message, *match)
                copy_metadata(exc, match_exc)
            if with_complement and rest:
                rest_exc = ExceptionGroup(exc.message, *rest)
                copy_metadata(exc, rest_exc)
            return match_exc, rest_exc

    def split(self, type):
        """ Split an ExceptionGroup to extract exceptions of type E

        type: An exception type
        """
        return self.project(
            self, lambda e: isinstance(e, type), with_complement=True)

    def subgroup(self, keep):
        """ Split an ExceptionGroup to extract only exceptions in keep

        keep: List[BaseException]
        """
        match, _ = self.project(self, lambda e: e in keep)
        return match

    def __iter__(self):
        ''' iterate over the individual exceptions (flattens the tree) '''
        for e in self.excs:
            if isinstance(e, ExceptionGroup):
                for e_ in e:
                    yield e_
            else:
                yield e

    def __repr__(self):
        return f"ExceptionGroup({self.message}, {self.excs})"

    @staticmethod
    def catch(types, handler):
        return ExceptionGroupCatcher(types, handler)


class ExceptionGroupCatcher:
    """ Based on trio.MultiErrorCatcher """

    def __init__(self, types, handler):
        """ Context manager to catch and handle ExceptionGroups

        types: the exception types that this handler is interested in
        handler: a function that takes an ExceptionGroup of the
        matched type and does something with them

        Any rest exceptions are raised at the end as another
        exception group
        """
        self.types = types
        self.handler = handler

    def __enter__(self):
        pass

    def __exit__(self, etype, exc, tb):
        if exc is not None and isinstance(exc, ExceptionGroup):
            match, rest = exc.split(self.types)

            if match is None:
                # Let the interpreter reraise the exception
                return False

            naked_raise = False
            handler_excs = None
            try:
                naked_raise = self.handler(match)
            except (Exception, ExceptionGroup) as e:
                handler_excs = e

            if naked_raise or handler_excs is match:
                # handler reraised all of the matched exceptions.
                # reraise exc as is.
                return False

            if handler_excs is None:
                if rest is None:
                    # handled and swallowed all exceptions
                    # do not raise anything.
                    return True
                else:
                    # raise the rest exceptions
                    to_raise = rest
            elif rest is None:
                to_raise = handler_excs  # raise what handler returned
            else:
                # Merge handler's exceptions with rest
                # to_keep: EG subgroup of exc with only those to reraise
                # (either not matched or reraised by handler)
                to_keep = exc.subgroup(
                    list(rest) + [e for e in handler_excs if e in match])
                # to_add: new exceptions raised by handler
                to_add = handler_excs.subgroup(
                    [e for e in handler_excs if e not in match])
                if to_add is not None:
                    to_raise = ExceptionGroup(exc.message, to_keep, to_add)
                else:
                    to_raise = to_keep

            # When we raise to_raise, Python will unconditionally blow
            # away its __context__ attribute and replace it with the original
            # exc we caught. So after we raise it, we have to pause it while
            # it's in flight to put the correct __context__ back.
            old_context = to_raise.__context__
            try:
                raise to_raise
            finally:
                _, value, _ = sys.exc_info()
                assert value is to_raise
                value.__context__ = old_context
