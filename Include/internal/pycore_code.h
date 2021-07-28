#ifndef Py_INTERNAL_CODE_H
#define Py_INTERNAL_CODE_H
#ifdef __cplusplus
extern "C" {
#endif
 
typedef struct {
    PyObject *ptr;  /* Cached pointer (borrowed reference) */
    uint64_t globals_ver;  /* ma_version of global dict */
    uint64_t builtins_ver; /* ma_version of builtin dict */
} _PyOpcache_LoadGlobal;

struct _PyOpcache {
    union {
        _PyOpcache_LoadGlobal lg;
    } u;
    char optimized;
};

/* Private API */
PyCodeObject * _PyCode_Update(PyCodeObject *,
               int argcount, int posonlyargcount, int kwonlyargcount,
               int nlocals, int stacksize, int flags,
               PyObject *code, PyObject *consts, PyObject *names,
               PyObject *varnames, PyObject *freevars, PyObject *cellvars,
               PyObject *filename, PyObject *name, int firstlineno,
               PyObject *lnotab);
int _PyCode_InitOpcache(PyCodeObject *co);

/* Hydration */

static inline int
_PyCode_IsHydrated(PyCodeObject *code)
{
    return code->co_code != NULL;
}

PyCodeObject *_PyCode_Hydrate(PyCodeObject *code);


#ifdef __cplusplus
}
#endif
#endif /* !Py_INTERNAL_CODE_H */
