
#include "Python.h"
#include "pycore_code.h"
#include "pycore_interp.h"

/* Common constants which can be loaded from the interpreter's pre-initialized
   list via the LOAD_COMMON_CONST opcode
 */


/* This function steals a reference to obj */
static int
add_common_const(PyInterpreterState *interp, int index, PyObject *obj)
{
    PyObject *key = NULL, *value = NULL;
    int ret = 0;

    if (!obj)
        return -1;
    assert(index >= 0 && index < 256);

    /* Add to interpreter's list */
    Py_INCREF(obj);
    interp->common_consts[index] = obj;

    /* Add to the object-to-index mapping */
    key = _PyCode_ConstantKey(obj);
    if (!key) {
        ret = -1;
        goto done;
    }
    value = PyLong_FromLong(index);
    if (!value) {
        ret = -1;
        goto done;
    }
    ret = PyDict_SetItem(interp->common_const_to_index, key, value);

done:
    Py_DECREF(obj);
    Py_XDECREF(key);
    Py_XDECREF(value);
    return ret;
}

static int
add_common_int(PyInterpreterState *interp, int index, int v)
{
    PyObject *obj = PyLong_FromLong(v);
    if (!obj)
        return -1;
    return add_common_const(interp, index, obj);
}

static int
add_common_float(PyInterpreterState *interp, int index, double v)
{
    assert(!Py_IS_NAN(v));
    assert(!Py_IS_INFINITY(v));
    PyObject *obj = PyFloat_FromDouble(v);
    if (!obj)
        return -1;
    return add_common_const(interp, index, obj);
}

static int
add_common_string(PyInterpreterState *interp, int index, const char *s)
{
    PyObject *obj = PyUnicode_InternFromString(s);
    if (!obj)
        return -1;
    return add_common_const(interp, index, obj);
}

int
_Py_InitCommonConsts(PyInterpreterState *interp)
{
    int index = 0;
    int num_ints, j;
    int ret = 0;

    interp->common_const_to_index = PyDict_New();
    if (!interp->common_const_to_index) {
        return -1;
    }

    ret += add_common_const(interp, index++, Py_NewRef(Py_None));
    ret += add_common_const(interp, index++, Py_NewRef(Py_True));
    ret += add_common_const(interp, index++, Py_NewRef(Py_False));
    ret += add_common_const(interp, index++, Py_NewRef(Py_Ellipsis));
    ret += add_common_const(interp, index++, Py_NewRef(PyExc_AssertionError));

    ret += add_common_string(interp, index++, "");
    ret += add_common_string(interp, index++, " ");
    ret += add_common_string(interp, index++, "a");
    ret += add_common_string(interp, index++, "b");
    ret += add_common_string(interp, index++, "c");
    ret += add_common_string(interp, index++, "x");
    ret += add_common_string(interp, index++, "A");
    ret += add_common_string(interp, index++, "B");
    ret += add_common_string(interp, index++, "foo");
    ret += add_common_string(interp, index++, "bar");
    ret += add_common_string(interp, index++, "data");
    ret += add_common_string(interp, index++, "id");
    ret += add_common_string(interp, index++, "name");
    ret += add_common_string(interp, index++, "return");
    ret += add_common_string(interp, index++, "utf-8");
    ret += add_common_string(interp, index++, "__main__");
    ret += add_common_string(interp, index++, "/");
    ret += add_common_string(interp, index++, ".");
    ret += add_common_string(interp, index++, "\n");

    ret += add_common_float(interp, index++, 0.0);
    ret += add_common_float(interp, index++, 0.5);
    ret += add_common_float(interp, index++, 1.0);
    ret += add_common_float(interp, index++, 2.0);

    /* The tuples:
           (), (None,), ('dtype',), ('match',), ('index',),
           ('name',), ('axis',), ('primary_key',), (1, 2, 3)
    */
    ret += add_common_const(interp, index++, PyTuple_New(0));
    ret += add_common_const(interp, index++, Py_BuildValue("(O)", Py_None));
    ret += add_common_const(interp, index++, Py_BuildValue("(s)", "dtype"));
    ret += add_common_const(interp, index++, Py_BuildValue("(s)", "match"));
    ret += add_common_const(interp, index++, Py_BuildValue("(s)", "index"));
    ret += add_common_const(interp, index++, Py_BuildValue("(s)", "name"));
    ret += add_common_const(interp, index++, Py_BuildValue("(s)", "axis"));
    ret += add_common_const(interp, index++, Py_BuildValue("(s)", "primary_key"));
    ret += add_common_const(interp, index++, Py_BuildValue("(iii)", 1, 2, 3));

    for(j=1; j < 6; j++) {
        ret += add_common_int(interp, index++, -j);
    }
    num_ints = 256 - index;
    assert(num_ints > 10); // ensure we don't fill it up with other consts
    for(j=0; j<num_ints; j++) {
        ret += add_common_int(interp, index++, j);
    }

    return ret < 0 ? -1: 0;
}

void
_Py_ClearCommonConsts(PyInterpreterState *interp)
{
    assert(interp->common_const_to_index);
    for (int i=0; i<256; i++) {
        Py_DECREF(interp->common_consts[i]);
        interp->common_consts[i] = NULL;
    }
    Py_CLEAR(interp->common_const_to_index);
}

/* Returns the index of obj in the common constants array.
   Returns -1 if obj is not a common constant, or if an
   error has occurred (use PyErr_Occurred() to disambiguate).
*/
Py_ssize_t
_Py_GetCommonConstIndex(PyObject* obj)
{
    Py_ssize_t index = -1;
    PyObject *value;
    PyInterpreterState *interp = PyInterpreterState_Get();
    PyObject *key = _PyCode_ConstantKey(obj);

    if (key) {
        value = PyDict_GetItemWithError(interp->common_const_to_index, key);
        Py_DECREF(key);
        if (value) {
            assert(PyLong_CheckExact(value));
            index = PyLong_AsLong(value);
        }
    }
    return index;
}

PyObject*
_Py_GetCommonConstValue(Py_ssize_t index)
{
    PyInterpreterState *interp = PyInterpreterState_Get();
    assert(index >= 0 && index < 256);
    PyObject *obj = interp->common_consts[index];
    assert(obj);
    Py_INCREF(obj);
    return obj;
}

