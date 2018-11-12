import os, zlib, struct
import libarchive.public

if __name__ == '__main__':
  from torrentarchive import TorrentArchive
else:
  from .torrentarchive import TorrentArchive

class T7Zip(TorrentArchive):
  def __init__(self, archive_filename):
    super().__init__(archive_filename)
    
    # Populate contents, maintaining sort order in archive
    entries = []
    dir_count = 0
    file_count = 0
    with libarchive.public.file_reader(self.archive_filename) as e:
      for entry in e:
        if entry.filetype.IFDIR:
          type = 'dir'
          dir_count += 1
        elif entry.filetype.IFREG:
          type = 'reg'
          file_count += 1
        else:
          print("Error: unknown filetype in archive, skipping. Path: %s" % entry.pathname)
          continue

        entries.append({'path' : entry.pathname, 'size': entry.size, 'type': type})

    self.single_file = file_count == 1
    self.contents = {'dir_count' : dir_count, 'file_count' : file_count, 'entries' : entries}

  def _generate_signature(self, first_bytes, last_bytes, filesize, unicode=True, strip_filenames=False):
    bitmask = 0
    if unicode:
      bitmask |= 1
    if self.single_file:
      bitmask |=2
    if strip_filenames:
      bitmask |=4

    sig = b"\xa9\x9f\xd1\x57\x08\xa9\xd7\xea\x29\x64\xb2\x36\x1b\x83\x52\x33" + bytes([bitmask]) + b"torrent7z_0.9beta"
    crc = zlib.crc32(first_bytes + last_bytes + struct.pack("<Q", filesize) + b"\xff\xff\xff\xff" + sig).to_bytes(4, 'little')
    return crc + sig

  def signature_is_valid(self, path=None):

    if not path:
      path = self.archive_filename

    if not self.signature_is_present(path):
      print("Error: verify_signature called on an archive without a t7z signature")
      return False

    size = os.path.getsize(path)

    with open(path, "rb") as f:
      print("Verifying signature...")
      # read first 128 bytes
      first_bytes = f.read(128)

      f.seek(size - 128 - 38)
      # read last 128 bytes + 38 bytes of t7z sig
      last_bytes = f.read(128)  
      signature = f.read(38)
    
    generated_signature = self._generate_signature(first_bytes, last_bytes, size - 38)
    if generated_signature == signature:
      print("Verify OK")
      return True
    else:
      print("Verification failed")
      return False

  def signature_is_present(self, path=None):
    if not path:
      path = self.archive_filename

    with open(path, "rb") as f:
      f.seek(-38, os.SEEK_END)
      return f.read(38).endswith(b"torrent7z_0.9beta")

  def _strip_signature(self, path=None):
    if not path:
      path = self.archive_filename

    if not self.signature_is_present(path):
      print("Error: strip_signature called on an archive without a t7z signature")
      return False
    try:
      with open(path, "r+b") as f:
        print("Stripping signature from %s" % path)
        # remove signature (leave archive intact)
        f.seek(-38, os.SEEK_END)
        f.truncate()
        return True
    except:
      return False

  def sign(self, path=None):
    if not path:
      path = self.archive_filename

    filesize = os.path.getsize(path)

    if self.signature_is_present(path):
      print("Error: called sign on an archive that already has a signature; stripping existing signature")
      if not self._strip_signature():
        return False

    with open(path, "r+b") as f:
      print("Signing 7z as t7z...")
      first_bytes = f.read(128)
      f.seek(-128, os.SEEK_END)
      last_bytes = f.read(128)
      sig = self._generate_signature(first_bytes, last_bytes, filesize)
      f.write(sig)
    
    return self.signature_is_valid(path)

  def rename_files(self, filename_map, new_archive_filename):
    # 7za rn will not work on 7z archives that already have a signature at the end
    #
    # strip the signature on the source file, then re-sign it afterwards
    if not self._strip_signature():
      return False
    try:
      ret = super().rename_files(filename_map, new_archive_filename)
    finally:
      # re-sign the source archive
      print("Re-signing stripped source archive...")
      self.sign()
      # the target archive will be signed automatically by the parent class
      return ret

  def get_archive_contents(self):
    return self.contents

