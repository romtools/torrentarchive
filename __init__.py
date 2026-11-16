from .torrentzip import TorrentZip, has_tzip_signature
from .t7zip import T7Zip, has_t7z_signature

def get(filename):
  lower = str(filename).lower()
  if lower.endswith('.7z'):
    return T7Zip(filename)
  elif lower.endswith('.zip'):
    return TorrentZip(filename)
  else:
    print("unknown archive type", filename)
    return False

def has_signature(filename):
  """Whether a .zip or .7z file carries a TorrentZip or T7Z signature. Checks presence only, not validity."""
  lower = str(filename).lower()
  if lower.endswith('.7z'):
    return has_t7z_signature(filename)
  if lower.endswith('.zip'):
    return has_tzip_signature(filename)
  return False

