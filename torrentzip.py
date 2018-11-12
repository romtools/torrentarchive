import os, struct, zipfile, zlib

if __name__ == '__main__':
  from torrentarchive import TorrentArchive
else:
  from .torrentarchive import TorrentArchive

def log(*args):
  print('[TORRENTZIP]', *args)

def d(s):
  print("DEBUG: %s" % s)

def e(s):
  print("ERROR: %s" % s)

class TorrentZip(TorrentArchive):
  def __init__(self, archive_filename):
    super().__init__(archive_filename)
    
    # Collect contents
    z = zipfile.ZipFile(archive_filename, mode='r')
    entries = []
    dir_count = 0
    file_count = 0
    # infolist() maintains archive order
    for f in z.infolist():
      if f.is_dir():
        dir_count += 1
        type = 'dir'
      else:
        file_count += 1
        type = 'reg'
      entries.append({'path': f.filename, 'size': f.file_size, 'type': type})

    self.contents = {'entries': entries, 'dir_count': dir_count, 'file_count': file_count}

  def signature_is_present(self, filename=None):
    if not filename:
      filename = self.archive_filename
    with open(filename, "rb") as f:
      f.seek(-22, os.SEEK_END)
      buf = f.read(13)
      if not buf:
        return False
      return struct.unpack("<13s", buf)[0] == b'TORRENTZIPPED'

  def signature_is_valid(self, filename=None):
    if not filename:
      filename = self.archive_filename
    current_sig = self._get_tzip_signature(filename)
    actual_sig = self._generate_signature(filename)
    return current_sig == actual_sig

  def get_archive_contents(self):
    return self.contents

  def sign(self, path=None):
    if not path:
      path = self.archive_filename

    current_sig = self._get_tzip_signature(path)
    actual_sig = self._generate_signature(path)

    if current_sig:
      if current_sig == actual_sig:
        print("Existing signature is valid; skipping signing")
        return True
      else:
        print("Signature mismatch! Re-signing.", current_sig, actual_sig)
    else:
      print("No signature present; signing.")

    # update signature
    with open(path, 'r+b') as z:
      z.seek(-22, 2)
      z.write(struct.pack("<22s", actual_sig))

    return True

  def _get_tzip_signature(self, filename):
    with open(filename, 'rb') as z:
      z.seek(-22, 2)
      sig = struct.unpack("<22s", z.read(22))[0]
      if not sig.startswith(b'TORRENTZIPPED-'):
        return False
      return sig

  def _generate_signature(self, filename):
    zip64 = False
    if os.path.getsize(filename) > 0xFFFFFFFF:
      zip64 = True

    z = zipfile.ZipFile(filename, mode='r', allowZip64=True)

    # synthesize the central directory
    entries = z.infolist()
    all_records = b""
    for e in entries:
      cd_file_size = e.file_size
      cd_compress_size = e.compress_size
      cd_header_offset = e.header_offset
      cd_volume = e.volume

      # extra field used for zip64 files (files that are >4G in size
      # or contain fields/offsets that exceed 4G)
      extra = b""

      if e.file_size > 0xFFFFFFFF:
        cd_file_size = 0xFFFFFFFF
        extra += struct.pack("<Q", e.file_size)
        zip64 = True
      if e.compress_size > 0xFFFFFFFF:
        cd_compress_size = 0xFFFFFFFF
        extra += struct.pack("<Q", e.compress_size)
        zip64 = True
      if e.header_offset > 0xFFFFFFFF:
        extra += struct.pack("<Q", e.header_offset)
        cd_header_offset = 0xFFFFFFFF
        zip64 = True
      if e.volume > 0xFFFF:
        cd_volume = 0xFFFF
        extra += struct.pack("<I", e.volume)
        zip64 = True

      if extra:
        # add ID header + data length bytes
        extra_len = 4 + len(extra)
      else:
        extra_len = 0

      # torrentzip archives have a fixed header here (fixed mtime, fixed versions, except for zip64)
      if zip64:
        # zip64 archives have a different minimum version byte
        record = b"\x50\x4b\x01\x02\x00\x00\x2d\x00\x02\x00\x08\x00\x00\xbc\x98\x21"
      else:
        record = b"\x50\x4b\x01\x02\x00\x00\x14\x00\x02\x00\x08\x00\x00\xbc\x98\x21"

      record += struct.pack("<IIIHHHHHII", e.CRC, cd_compress_size, cd_file_size, len(e.filename), extra_len, len(e.comment), cd_volume, e.internal_attr, e.external_attr, cd_header_offset)
      record += struct.pack("<%ds" % len(e.filename), e.filename.encode())
      if extra:
        record += b"\x01\00" + struct.pack("<H", len(extra)) + extra

      all_records += record

    crc = zlib.crc32(all_records) & 0xffffffff

    return b"TORRENTZIPPED-%08X" % crc
