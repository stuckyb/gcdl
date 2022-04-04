
from pathlib import Path
import os.path
import uuid


class UploadDataCache:
    """
    Implements an on-disk cache for uploaded geospatial data.
    """
    def __init__(
        self, cachedir, max_file_size, retention_time=14400, chunk_size=1024
    ):
        """
        cachedir (str or Path): The on-disk storage location.
        max_file_size (int): Maximum file size to accept, in bytes.
        retention_time (int): Maximum file retention time, in seconds (default:
            4 hours).
        chunk_size (int): The chunk size, in bytes, for reading uploaded data
            (default: 1 KB).
        """
        self.cachedir = Path(cachedir)
        self.maxsize = max_file_size
        self.maxtime = retention_time
        self.chunk_size = chunk_size

    def addFile(self, fdata, fname):
        """
        Saves uploaded data in the cache and returns a GUID for the uploaded
        data.

        fdata: A file-like object.
        fname: The name of the original file.
        """
        guid = str(uuid.uuid4())
        ext = os.path.splitext(fname)[1]
        fpath = self.cachedir / (guid + ext)

        byte_cnt = 0

        with open(fpath, 'wb') as fout:
            while chunk := fdata.read(self.chunk_size):
                byte_cnt += len(chunk)
                if byte_cnt > self.maxsize:
                    break

                fout.write(chunk)

        if byte_cnt > self.maxsize:
            fpath.unlink()
            raise Exception(
                'Uploaded file size exceeded maximum file size.'
            )

        return guid

    def getPolygon(self, guid):
        pass

    def getMultiPoint(self, guid):
        pass

    def cleanCache(self):
        pass

    def getCacheStats(self):
        pass

