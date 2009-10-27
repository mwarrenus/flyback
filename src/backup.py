import os, pickle, sys, tempfile, traceback

import settings

RUN_FROM_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))


def get_known_backups():
  backups = []
  for uuid in get_devices():
    print 'uuid', uuid
    path = get_mount_point_for_uuid(uuid)
    if path:
      print 'path', path
      fbdbs = [ x for x in os.listdir(path) if x.startswith('.flybackdb') ]
      for fbdb in fbdbs:
        try:
          f = open( os.path.join(path, fbdb, 'flyback_properties.pickle') )
          o = pickle.load(f)
          f.close()
          backups.append(o)
        except:
          print 'failed to read:', os.path.join(path, fbdb, 'flyback_properties.pickle')
  return backups

  return [
    { 'uuid':'46D7-429E', 'host':'newyork', 'path':'/home/derek/testfb' },
    { 'uuid':'46D7-429E', 'host':'malcolm', 'path':'/home/derek/testfb' },
    { 'uuid':'46D7-429E', 'host':'kaylee', 'path':'/home/derek/testfb' },
    { 'uuid':'46D7-XXXX', 'host':'kaylee', 'path':'/home/derek/testfb' },
  ]

  
def is_dev_present(uuid):
  return os.path.exists( os.path.join( '/dev/disk/by-uuid/', uuid ) )
  
def get_hostname():
  import socket
  return socket.gethostname()
  
def get_devices():
  return [ os.path.basename(x) for x in os.listdir('/dev/disk/by-uuid/') ]
  
def get_writable_devices():
  writable_uuids = []
  for uuid in get_devices():
    path = get_mount_point_for_uuid(uuid)
    if path:
      try:
        fn = os.path.join(path,'.flyback_write_test.txt')
        f = open(fn, 'w')
        f.write('delete me!')
        f.close()
        os.remove(fn)
        writable_uuids.append(uuid)
      except:
        print 'could not write to:', path
  return writable_uuids
  
def test_backup_assertions(uuid, host, path):
  return is_dev_present(uuid) and get_hostname()==host and os.path.exists(path)

def get_dev_paths_for_uuid(uuid):
  dev_path = os.path.join( '/dev/disk/by-uuid/', uuid )
  f = os.popen('udevadm info -q all -n "%s"' % dev_path)
  s = f.read()
  f.close()
  dev_paths = set()
  for line in s.split('\n'):
    if line.startswith('E: DEVNAME='):
      dev_paths.add( line[line.index('=')+1:].strip() )
    if line.startswith('E: DEVLINKS='):
      for path in line[line.index('=')+1:].strip().split():
        dev_paths.add(path)
  return dev_paths

def get_mount_point_for_uuid(uuid):
  dev_paths = get_dev_paths_for_uuid(uuid)
  f = os.popen('mount')
  s = f.read()
  f.close()
  for line in s.split('\n'):
    x = line.strip().split()
    if x:
      dev_path = x[0]
      if dev_path in dev_paths:
        mount_path = x[2]
        return mount_path
      
def get_drive_name(uuid):
  paths = get_dev_paths_for_uuid(uuid)
  drive_name = 'UUID: '+ uuid
  for path in paths:
    if 'disk/by-id' in path:
      drive_name = path[path.index('disk/by-id')+11:]
  return drive_name

def get_free_space(uuid):
  path = get_mount_point_for_uuid(uuid)
  f = os.popen('df')
  s = f.read()
  f.close()
  for line in s.split('\n'):
    x = line.split()
    if x[-1]==path:
      return int(x[-3])*1024
      
def get_git_db_name(uuid, host, path):
  import hashlib
  s = ':'.join( (uuid, host, path) )
  print s
  return '.flybackdb_%s' % hashlib.sha1(s).hexdigest()
  
def get_git_dir(uuid, host, path):
  mount_point = get_mount_point_for_uuid(uuid)
  git_db = get_git_db_name(uuid, host, path)
  git_db_dir = os.path.join( mount_point, git_db )
  print 'git_db_dir', git_db_dir
  return git_db_dir
  
  
def rmdir(tmp):
  f = os.popen('rm -Rf "%s"' % tmp)
  s = f.read().strip()
  f.close()
  if s:  print s


def init_backup(uuid, host, path):
  assert test_backup_assertions(uuid, host, path)

  tmp = tempfile.mkdtemp()
  os.chdir(tmp)
  git_dir = get_git_dir(uuid, host, path)
  print 'initializing repository...', git_dir
  cmd = 'GIT_DIR="%s" git init' % (git_dir,)
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)
  
  # write config info
  f = open( os.path.join(git_dir, 'flyback_properties.pickle'), 'w' )
  o = {
    'uuid':uuid,
    'host':host,
    'path':path,
    'version':settings.PROGRAM_VERSION,
  }
  pickle.dump(o,f)
  f.close()
  
  # save default preferences
  preferences = get_preferences(uuid, host, path)
  save_preferences(uuid, host, path, preferences)
  
  rmdir(tmp)
  os.chdir(RUN_FROM_DIR)
  return
  

def backup(uuid, host, path):
  assert test_backup_assertions(uuid, host, path)

  git_dir = get_git_dir(uuid, host, path)
  if not os.path.exists(git_dir):
    init_backup(uuid, host, path)
  os.chdir(path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="." git ' % (git_dir,)
  
  # add any new files
  cmd = git_cmd + 'add -v *'
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)
  
  # commit
  cmd = git_cmd + 'commit -v . -m "commited by: %s v%s"' % (settings.PROGRAM_NAME, settings.PROGRAM_VERSION)
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)


def get_preferences(uuid, host, path):
  preferences = {
    'exclude_audio': True,
    'exclude_video': True,
    'exclude_trash': True,
    'exclude_cache': True,
    'exclude_vms': True,
    'exclude_iso': True,
  }
  git_dir = get_git_dir(uuid, host, path)
  try:
    f = open( os.path.join(git_dir, 'flyback_preferences.pickle'), 'r' )
    o = pickle.load(f)
    f.close()
    if o:
      preferences.update(o)
  except:
    print traceback.print_exc()
  return preferences


def save_preferences(uuid, host, path, preferences):
  git_dir = get_git_dir(uuid, host, path)
  try:
    f = open( os.path.join(git_dir, 'flyback_preferences.pickle'), 'w' )
    pickle.dump(preferences, f)
    f.close()
  except:
    print traceback.print_exc()
    
  # gen exclude file
  exclude_map = {
    'exclude_audio': ['*.mp3','*.aac','*.wma'],
    'exclude_video': ['*.mp4','*.avi','*.mpeg',],
    'exclude_trash': ['Trash/','.Trash*/',],
    'exclude_cache': ['Cache/','.cache/',],
    'exclude_vms': ['*.vmdk',],
    'exclude_iso': ['*.iso',],
  }
  try:
    f = open( os.path.join(git_dir, 'info', 'exclude'), 'w' )
    for k,v in exclude_map.iteritems():
      if preferences.get(k):
        for x in v:
          f.write('%s\n' % x)
          print 'excluding:', x
    f.close()
  except:
    print traceback.print_exc()
  


def get_revisions(uuid, host, path):
  tmp = tempfile.mkdtemp()
  os.chdir(tmp)
  git_dir = get_git_dir(uuid, host, path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="%s" git ' % (git_dir,tmp)
  cmd = git_cmd + 'log'
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)
  
  log = []
  if s:
    entry = None
    for line in s.split('\n'):
      if line.startswith('commit'):
        if entry:
          log.append(entry)
        entry = {'commit':line[line.index(' '):].strip(), 'message':''}
      elif line.startswith('Author: '):
        entry['author'] = line[line.index(' '):].strip()
      elif line.startswith('Date: '):
        entry['date'] = line[line.index(' '):].strip()
      else:
        entry['message'] += line
    if entry:
      log.append(entry)

  rmdir(tmp)
  os.chdir(RUN_FROM_DIR)
  print 'log', log
  return log


def get_files_for_revision(uuid, host, path, rev):
  tmp = tempfile.mkdtemp()
  os.chdir(tmp)
  git_dir = get_git_dir(uuid, host, path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="%s" git ' % (git_dir,tmp)
  cmd = git_cmd + 'ls-tree -r --name-only ' + rev
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)
  rmdir(tmp)
  os.chdir(RUN_FROM_DIR)
  return [ x.strip('"') for x in s.split('\n') ]


def export_revision(uuid, host, path, rev, target_path):
  tmp = tempfile.mkdtemp()
  os.chdir(tmp)
  git_dir = get_git_dir(uuid, host, path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="%s" git ' % (git_dir,tmp)
  fn = '%s/flyback-archive_r%s.tar.gz' % (target_path, rev)
  cmd = git_cmd + 'archive %s | gzip > "%s"' % (rev, fn)
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)
  rmdir(tmp)
  os.chdir(RUN_FROM_DIR)
  return fn

