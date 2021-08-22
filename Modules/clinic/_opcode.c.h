/*[clinic input]
preserve
[clinic start generated code]*/

PyDoc_STRVAR(_opcode_stack_effect__doc__,
"stack_effect($module, opcode, oparg=None, /, *, jump=None)\n"
"--\n"
"\n"
"Compute the stack effect of the opcode.");

#define _OPCODE_STACK_EFFECT_METHODDEF    \
    {"stack_effect", (PyCFunction)(void(*)(void))_opcode_stack_effect, METH_FASTCALL|METH_KEYWORDS, _opcode_stack_effect__doc__},

static int
_opcode_stack_effect_impl(PyObject *module, int opcode, PyObject *oparg,
                          PyObject *jump);

static PyObject *
_opcode_stack_effect(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", "", "jump", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "stack_effect", 0};
    PyObject *argsbuf[3];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 1;
    int opcode;
    PyObject *oparg = Py_None;
    PyObject *jump = Py_None;
    int _return_value;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 2, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    opcode = _PyLong_AsInt(args[0]);
    if (opcode == -1 && PyErr_Occurred()) {
        goto exit;
    }
    if (nargs < 2) {
        goto skip_optional_posonly;
    }
    noptargs--;
    oparg = args[1];
skip_optional_posonly:
    if (!noptargs) {
        goto skip_optional_kwonly;
    }
    jump = args[2];
skip_optional_kwonly:
    _return_value = _opcode_stack_effect_impl(module, opcode, oparg, jump);
    if ((_return_value == -1) && PyErr_Occurred()) {
        goto exit;
    }
    return_value = PyLong_FromLong((long)_return_value);

exit:
    return return_value;
}

PyDoc_STRVAR(_opcode_get_common_const_value__doc__,
"get_common_const_value($module, /, i)\n"
"--\n"
"\n"
"Return the interpreter\'s i-th common const");

#define _OPCODE_GET_COMMON_CONST_VALUE_METHODDEF    \
    {"get_common_const_value", (PyCFunction)(void(*)(void))_opcode_get_common_const_value, METH_FASTCALL|METH_KEYWORDS, _opcode_get_common_const_value__doc__},

static PyObject *
_opcode_get_common_const_value_impl(PyObject *module, Py_ssize_t i);

static PyObject *
_opcode_get_common_const_value(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"i", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "get_common_const_value", 0};
    PyObject *argsbuf[1];
    Py_ssize_t i;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 1, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    {
        Py_ssize_t ival = -1;
        PyObject *iobj = _PyNumber_Index(args[0]);
        if (iobj != NULL) {
            ival = PyLong_AsSsize_t(iobj);
            Py_DECREF(iobj);
        }
        if (ival == -1 && PyErr_Occurred()) {
            goto exit;
        }
        i = ival;
    }
    return_value = _opcode_get_common_const_value_impl(module, i);

exit:
    return return_value;
}

PyDoc_STRVAR(_opcode_is_common_const__doc__,
"is_common_const($module, /, obj)\n"
"--\n"
"\n"
"Return True if obj is a common const, False otherwise");

#define _OPCODE_IS_COMMON_CONST_METHODDEF    \
    {"is_common_const", (PyCFunction)(void(*)(void))_opcode_is_common_const, METH_FASTCALL|METH_KEYWORDS, _opcode_is_common_const__doc__},

static PyObject *
_opcode_is_common_const_impl(PyObject *module, PyObject *obj);

static PyObject *
_opcode_is_common_const(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"obj", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "is_common_const", 0};
    PyObject *argsbuf[1];
    PyObject *obj;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 1, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    obj = args[0];
    return_value = _opcode_is_common_const_impl(module, obj);

exit:
    return return_value;
}

PyDoc_STRVAR(_opcode_get_specialization_stats__doc__,
"get_specialization_stats($module, /)\n"
"--\n"
"\n"
"Return the specialization stats");

#define _OPCODE_GET_SPECIALIZATION_STATS_METHODDEF    \
    {"get_specialization_stats", (PyCFunction)_opcode_get_specialization_stats, METH_NOARGS, _opcode_get_specialization_stats__doc__},

static PyObject *
_opcode_get_specialization_stats_impl(PyObject *module);

static PyObject *
_opcode_get_specialization_stats(PyObject *module, PyObject *Py_UNUSED(ignored))
{
    return _opcode_get_specialization_stats_impl(module);
}
/*[clinic end generated code: output=a4443c0dba53c55f input=a9049054013a1b77]*/
