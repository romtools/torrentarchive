import subprocess
import traceback

class TorrentArchiveSignatureError(Exception):
  pass

"""
Base class

Methods that must be implemented by children:
  get_archive_contents
  signature_is_valid
  signature_is_present
  sign

Optional overrides
  rename_files (must call super().rename_files eventually)

Common private methods
  _generate_signature
  _strip_signature

"""
class TorrentArchive:
  def __init__(self, archive_filename):
    self.archive_filename = archive_filename

  def get_archive_contents(self):
    pass

  def signature_is_valid(self):
    pass
  
  def signature_is_present(self):
    pass

  def rename_replace(self, old_str, new_str, new_archive_filename=None, tmpdir=None):
    contents = self.get_archive_contents()
    renames = []
    for e in contents['entries']:
      if e['path'].find(old_str) != -1:
        old_name = e['path']
        new_name = e['path'].replace(old_str, new_str)
        print("Pattern matched: %s -> %s" % (old_name, new_name))
        renames.append((old_name, new_name))

    if len(renames):
      return self.rename_files(renames, new_archive_filename, tmpdir)

    return False

  def _is_7za_recent(self):
    s = subprocess.run(['7za'], stdout=subprocess.PIPE).stdout
    return s.find(b"Rename files in archive") != -1

  def rename_files(self, filename_map, new_archive_filename):
    if not self._is_7za_recent():
      print("Error: cannot rename files in archives without a recent (>=9.30) version of 7za installed and in PATH")
      return False

    if not self.rename_files_check(filename_map):
      return False

    if os.path.exists(new_archive_filename):
      print("Error: target archive already exists")
      return False

    try:
      # new_archive_filename may be a posixpath object which apparently can't be concatenated to a string
      # without throwing an exception. it makes sense generally but thanks to 7za's weird command line 
      # flags we end up needing to do it. also sprinkled a str cast on the 3rd arg for no good reason
      cmd_list = ['7za', 'rn', str(self.archive_filename), '-u-', '-u!'+str(new_archive_filename)]
      for old_filename, new_filename in filename_map:
        cmd_list.extend([old_filename, new_filename])
      print("Running cmd", cmd_list)
      s = subprocess.run(cmd_list, stdout=subprocess.PIPE)
      if s.returncode != 0:
        print("7za rn returned unexpected code %d" % s.returncode)
        print("7za output:\n%s" % s.stdout)
    except Exception as e:
      print("Error running 7za rn:")
      traceback.print_stack()
      traceback.print_exc()
      return False

    # Sign new archive (implemented in T7Zip and TorrentZip subclasses)
    return self.sign(path=new_archive_filename)

  def rename_files_check(self, filename_map):
    if not filename_map:
      return True

    archive_contents = self.get_archive_contents()
    old_archive_filenames = []
    for e in archive_contents['entries']:
      old_archive_filenames.append(e['path'])

    # Make a copy for adjustment and sorting
    new_archive_filenames = old_archive_filenames[:]

    # First confirm that filename adjustment will not result in a change in archive record order.
    # 7zip by default orders alphabetically(?); torrentzip uses lower alpha sort. If renaming changes
    # the order, then the archive will no longer match an archive made from scratch and is unusable.
    # TODO: Confirm that python's sort() behaves the same way, and confirm UTF-8 behavior of t7z/trrntzip
    #
    for old_filename, new_filename in filename_map:
      try:
        i = old_archive_filenames.index(old_filename)
      except ValueError:
        print("Error: filename map refers to a filename not present in archive. Missing filename: %s" % old_filename)
        return False

      new_archive_filenames[i] = new_filename

    if sorted(new_archive_filenames) != new_archive_filenames:
      print("Error: new filenames would cause this archive to have an unexpected ordering (t7z archive members must be sorted alphabetically).")
      # TODO: In these cases, give user option to fully decompress/recompress (non-solid archives could be manually reordered?
      print("The current archive is in this order:\n  %s" % "\n  ".join(old_archive_filenames))
      print("Avoided writing this:\n  %s" % "\n  ".join(new_archive_filenames))
      print("\n\nIn these scenarios, the archive must be decompressed, renamed as needed, and recompressed. This task may be automated in the future.")
      return False
     
    return True


