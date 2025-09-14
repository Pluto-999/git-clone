import os
import hashlib

GIT_DIR = ".git-clone"

def init():
    os.makedirs(GIT_DIR, exist_ok=True) # create the ".git-clone" directory for the "init" command
    os.makedirs(f'{GIT_DIR}/objects', exist_ok=True)


# each object will have a type tag, the default being "blob" since by default an object is just a collection of bytes with no further semantic meaning
def hash_object(data, type_="blob"):
    obj = type_.encode() + b'\x00' + data # prefix the file data with the type (which is converted into a sequence of bytes with encode()) before hashing and storing
    oid = hashlib.sha1(obj).hexdigest() # object id is the filename which is the SHA-1 hash of the given data (content-addressable)
    # store the raw data in ".git-clone/objects/<oid>"
    with open(f'{GIT_DIR}/objects/{oid}', "wb") as out:
        out.write(obj)
    return oid # return the object id to be printed in cli.py


def get_object(oid, expected="blob"):
    with open(f'{GIT_DIR}/objects/{oid}', "rb") as f:
        obj = f.read()

    type_, _, content = obj.partition(b'\x00')
    type_ = type_.decode()

    if expected is not None: # we can pass expected=None if we don't want to verify the type - useful for cat-file which is a debug for printing all objects
        assert type_ == expected, f'Expected {expected}, got {type_}'

    return content