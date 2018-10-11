"""The Thunk Layer is used for planning computations. Sending out thunk-requests will determine, if
it is possible to compute a result, and how to execute a computation regarding to the required effort"""

from .BasicThunkLayer import BasicThunkLayer