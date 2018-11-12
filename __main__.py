import torrentarchive

testfiles = ['torrentarchive/test.zip', 'torrentarchive/test.7z']

for testfile in testfiles:
  print("opening archive:", testfile)
  t = torrentarchive.get(testfile)
  print("archive contents:", t.get_archive_contents())
  print("signature is present:", t.signature_is_present())
  print("signature valid:", t.signature_is_valid())


#t = torrentarchive.get('torrentarchive/test.zip')
#t.rename_files([('bing.iso', 'ting.iso')], 'torrentarchive/test-renamed.zip')

t = torrentarchive.get('torrentarchive/test.7z')
t.rename_files([('Namco Museum (USA).iso', 'piggy.iso')], 'torrentarchive/test-renamed.7z')

