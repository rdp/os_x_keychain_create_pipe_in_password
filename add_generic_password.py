import contextlib
import ctypes
from ctypes import c_void_p, c_uint16, c_uint32, c_int32, c_char_p, POINTER

sec_keychain_ref = sec_keychain_item_ref = c_void_p
OS_status = c_int32

class error:
    item_not_found = -25300

fw = '/System/Library/Frameworks/{name}.framework/Versions/A/{name}'.format
_sec = ctypes.CDLL(fw(name='Security'))
_core = ctypes.CDLL(fw(name='CoreServices'))

SecKeychainOpen = _sec.SecKeychainOpen
SecKeychainOpen.argtypes = (c_char_p, POINTER(sec_keychain_ref),)
SecKeychainOpen.restype = OS_status

SecKeychainCopyDefault = _sec.SecKeychainCopyDefault
SecKeychainCopyDefault.argtypes = POINTER(sec_keychain_ref),
SecKeychainCopyDefault.restype = OS_status

SecKeychainItemFreeContent = _sec.SecKeychainItemFreeContent
SecKeychainItemFreeContent.argtypes = (c_void_p, c_void_p,)
SecKeychainItemFreeContent.restype = OS_status

class Error(Exception):
    @classmethod
    def raise_for_status(cls, status, msg):
        if status == 0:
            return
        raise cls(status, msg)

class NotFound(Error):
    @classmethod
    def raise_for_status(cls, status, msg):
        if status == error.item_not_found:
            raise cls(status, msg)
        Error.raise_for_status(status, msg)

@contextlib.contextmanager
def open(name):
    ref = sec_keychain_ref()
    if name is None:
        status = SecKeychainCopyDefault(ref)
        msg = "Unable to open default keychain"
    else:
        status = SecKeychainOpen(name.encode('utf-8'), ref)
        msg = "Unable to open keychain {name}".format(**locals())
    Error.raise_for_status(status, msg)
    try:
        yield ref
    finally:
        _core.CFRelease(ref)

SecKeychainFindGenericPassword = _sec.SecKeychainFindGenericPassword
SecKeychainFindGenericPassword.argtypes = (
    sec_keychain_ref,
    c_uint32,
    c_char_p,
    c_uint32,
    c_char_p,
    POINTER(c_uint32),
    POINTER(c_void_p),
    POINTER(sec_keychain_item_ref))
SecKeychainFindGenericPassword.restype = OS_status

def find_generic_password(kc_name, service, username):
        username = username.encode('utf-8')
        service = service.encode('utf-8')
        with open(kc_name) as keychain:
            length = c_uint32()
            data = c_void_p()
            status = SecKeychainFindGenericPassword(
                keychain,
                len(service),
                service,
                len(username),
                username,
                length,
                data,
                None)

        msg = "Can't fetch password from Keychain"
        NotFound.raise_for_status(status, msg)

        password = ctypes.create_string_buffer(length.value)
        ctypes.memmove(password, data.value, length.value)
        SecKeychainItemFreeContent(None, data)
        return password.raw.decode('utf-8')

SecKeychainAddGenericPassword = _sec.SecKeychainAddGenericPassword
SecKeychainAddGenericPassword.argtypes = (
    sec_keychain_ref,
    c_uint32,
    c_char_p,
    c_uint32,
    c_char_p,
    c_uint32,
    c_char_p,
    POINTER(sec_keychain_item_ref))
SecKeychainAddGenericPassword.restype = OS_status

SecKeychainItemModifyAttributesAndData = _sec.SecKeychainItemModifyAttributesAndData
SecKeychainItemModifyAttributesAndData.argtypes = (
    sec_keychain_item_ref,
    c_void_p,
    c_uint32,
    c_void_p)
SecKeychainItemModifyAttributesAndData.restype = OS_status

def set_generic_password(kc_name, service, username, password):
    username = username.encode('utf-8')
    service = service.encode('utf-8')
    password = password.encode('utf-8')
    with open(kc_name) as keychain:
        item = sec_keychain_item_ref()
        status = SecKeychainFindGenericPassword(
            keychain,
            len(service),
            service,
            len(username),
            username,
            None,
            None,
            item)
        if status:
            if status == error.item_not_found:
                status = SecKeychainAddGenericPassword(
                    keychain,
                    len(service),
                    service,
                    len(username),
                    username,
                    len(password),
                    password,
                    None)
        else:
            status = SecKeychainItemModifyAttributesAndData(
                item,
                None,
                len(password),
                password)
            _core.CFRelease(item)

        NotFound.raise_for_status(status, "Unable to set password in Keychain")


import sys

if len(sys.argv) != 3:
  print "syntax: service, username/account [and pipe the password in] expected 2 passed in ", len(sys.argv)
  sys.exit(2)

import os

if os.isatty(0):
  print "need to pipe in password"
  sys.exit(2)

password = sys.stdin.read()

if len(password) == 0:
  print "no password piped in? assuming this is unexpected, exiting"
  sys.exit(2)

# sys.argv[0] is the python filename [?]

kc_name = None # if you want a specific keychain, change this I guess?
service = sys.argv[1]
username = sys.argv[2] # I think this is account from security add-generic-password [?]

set_generic_password(kc_name, service, username, password) 
# not sure how to set other stuff like comment, label, app path (I think label defaults to service)
# not sure if specifying "-T" style app paths is even helpful though :| ? https://apple.stackexchange.com/questions/270070/keychain-application-still-requesting-access-with-entry-created-via-security-a

print("created new one " + service + " " + username)

