"""Drives KWin's pointer through its libei server (org.kde.KWin.EIS.RemoteDesktop), for tests that need a
right-click or a hover in the headless session.

Usage: eis_pointer.py STEP...   where a STEP is move:X,Y  press:left|right  release:left|right  click:left|right
or wait:SECONDS. Coordinates are in the compositor's logical pixels.
"""

import ctypes
import sys
import time

import dbus
from dbus.mainloop.glib import DBusGMainLoop

POINTER_ABSOLUTE, BUTTON = 1 << 1, 1 << 5
SEAT_ADDED, DEVICE_ADDED, DEVICE_RESUMED = 3, 5, 8
BUTTONS = {"left": 0x110, "right": 0x111}
LIBEI = ctypes.CDLL("libei.so.1")
for name in ("ei_new_sender", "ei_get_event", "ei_event_get_seat", "ei_event_get_device"):
    getattr(LIBEI, name).restype = ctypes.c_void_p
LIBEI.ei_now.restype = ctypes.c_uint64
LIBEI.ei_device_pointer_motion_absolute.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double]
LIBEI.ei_device_button_button.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_bool]
LIBEI.ei_device_frame.argtypes = [ctypes.c_void_p, ctypes.c_uint64]


def connect():
    DBusGMainLoop(set_as_default=True)
    remote = dbus.SessionBus().get_object("org.kde.KWin", "/org/kde/KWin/EIS/RemoteDesktop")
    descriptor, _cookie = remote.connectToEIS(dbus.Int32(7), dbus_interface="org.kde.KWin.EIS.RemoteDesktop")
    context = ctypes.c_void_p(LIBEI.ei_new_sender(None))
    LIBEI.ei_setup_backend_fd(context, descriptor.take())
    return context


def resumed_pointer(context):
    deadline = time.time() + 10
    while time.time() < deadline:
        LIBEI.ei_dispatch(context)
        event = LIBEI.ei_get_event(context)
        while event:
            kind = LIBEI.ei_event_get_type(ctypes.c_void_p(event))
            device = LIBEI.ei_event_get_device(ctypes.c_void_p(event))
            if kind == SEAT_ADDED:
                LIBEI.ei_seat_bind_capabilities(ctypes.c_void_p(LIBEI.ei_event_get_seat(ctypes.c_void_p(event))), POINTER_ABSOLUTE, BUTTON, 0)
            if kind == DEVICE_ADDED:
                LIBEI.ei_device_ref(ctypes.c_void_p(device))
            if kind == DEVICE_RESUMED and LIBEI.ei_device_has_capability(ctypes.c_void_p(device), POINTER_ABSOLUTE):
                return ctypes.c_void_p(device)
            LIBEI.ei_event_unref(ctypes.c_void_p(event))
            event = LIBEI.ei_get_event(context)
        time.sleep(0.05)
    raise RuntimeError("KWin offered no absolute pointer")


def emit(context, device, action):
    action(device)
    LIBEI.ei_device_frame(device, LIBEI.ei_now(context))
    LIBEI.ei_dispatch(context)


def run_step(context, device, step):
    verb, _, argument = step.partition(":")
    if verb == "wait":
        time.sleep(float(argument))
        return
    if verb == "move":
        x, y = map(float, argument.split(","))
        emit(context, device, lambda d: LIBEI.ei_device_pointer_motion_absolute(d, x, y))
        return
    buttons = {"press": [True], "release": [False], "click": [True, False]}[verb]
    for pressed in buttons:
        emit(context, device, lambda d, pressed=pressed: LIBEI.ei_device_button_button(d, BUTTONS[argument], pressed))
        time.sleep(0.05)


def main(steps):
    context = connect()
    device = resumed_pointer(context)
    LIBEI.ei_device_start_emulating(device, 1)
    for step in steps:
        run_step(context, device, step)
    LIBEI.ei_dispatch(context)


if __name__ == "__main__":
    main(sys.argv[1:])
