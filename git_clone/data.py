import os
import hashlib

GIT_DIR = ".git-clone"

def init():
    os.makedirs(GIT_DIR, exist_ok=True) # create the ".git-clone" directory for the "init" command
    os.makedirs(f'{GIT_DIR}/objects', exist_ok=True)


def hash_object(data):
    oid = hashlib.sha1(data).hexdigest() # object id is the filename which is the SHA-1 hash of the given data (content-addressable)
    # store the raw data in ".git-clone/objects/<oid>"
    with open(f'{GIT_DIR}/objects/{oid}', "wb") as out:
        out.write(data)
    return oid # return the object id to be printed in cli.py


def get_object(oid):
    with open(f'{GIT_DIR}/objects/{oid}', "rb") as f:
        return f.read()