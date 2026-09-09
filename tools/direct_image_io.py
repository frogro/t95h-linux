"""Aligned regular-file I/O with repeated source and destination verification."""
import hashlib
import mmap
import os
import stat
from pathlib import Path

CHUNK=1048576

def chunks(path):
    path=Path(path)
    fd=os.open(path,os.O_RDONLY|os.O_DIRECT|os.O_NOFOLLOW)
    buf=mmap.mmap(-1,CHUNK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size % 4096:
            raise ValueError('Expected an aligned regular image file: '+str(path))
        for offset in range(0,info.st_size,CHUNK):
            want=min(CHUNK,info.st_size-offset)
            n=os.preadv(fd,[memoryview(buf)[:want]],offset)
            if n!=want:raise ValueError('Short direct read: '+str(path))
            yield bytes(buf[:want])
    finally:
        buf.close();os.close(fd)

def digest(path):
    h=hashlib.sha256()
    for data in chunks(path):h.update(data)
    return h.hexdigest()

def concatenate(sources,destination):
    sources=[Path(p) for p in sources]
    expected={str(p):digest(p) for p in sources}
    combined=hashlib.sha256()
    fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_DIRECT,0o644)
    buf=mmap.mmap(-1,CHUNK)
    try:
        for source in sources:
            h=hashlib.sha256()
            for data in chunks(source):
                n=len(data);buf[:n]=data;h.update(data);combined.update(data)
                if os.write(fd,memoryview(buf)[:n])!=n:raise ValueError('Short direct image write')
            if h.hexdigest()!=expected[str(source)]:raise ValueError('Source changed while copying: '+str(source))
        os.fsync(fd)
    finally:
        buf.close();os.close(fd)
    reads=[digest(destination),digest(destination)]
    if reads!=[combined.hexdigest()]*2:raise ValueError('Repeated direct image readback differs')
    for source in sources:
        if digest(source)!=expected[str(source)]:raise ValueError('Source changed after image copy: '+str(source))
    return {'sha256':combined.hexdigest(),'source_sha256':expected,'direct_readback_count':2}
