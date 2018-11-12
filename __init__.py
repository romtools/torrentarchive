from .torrentzip import TorrentZip
from .t7zip import T7Zip

def get(filename):
  if filename.endswith('7z'):
    return T7Zip(filename)
  elif filename.endswith('zip'):
    return TorrentZip(filename)
  else:
    print("unknown archive type", filename)
    return False

