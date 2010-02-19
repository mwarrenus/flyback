import datetime, os, pickle, sys, tempfile, traceback
import uuid as uuidlib

import settings
import util

UUID_GVFS = uuidlib.uuid5(uuidlib.NAMESPACE_DNS, 'gvfs.flyback.org')

def get_known_backups():
  backups = []
  for uuid in get_all_devices():
    path = get_mount_point_for_uuid(uuid)
    if path:
      fbdbs = [ x for x in os.listdir(path) if x.startswith('.flybackdb') ]
      for fbdb in fbdbs:
        try:
          f = open( os.path.join(path, fbdb, 'flyback_properties.pickle'), 'rb' )
          o = pickle.load(f)
          f.close()
          backups.append(o)
          print 'discovered backup:', uuid, path
        except:
          print 'failed to read:', os.path.join(path, fbdb, 'flyback_properties.pickle')
  return backups

  
def is_dev_present(uuid):
  # handle gfvs
  for x,y in get_gvfs_devices_and_paths():
    if uuid==x:
      return True
  # handle local devices
  return os.path.exists( os.path.join( '/dev/disk/by-uuid/', uuid ) )
  
def get_device_type(uuid):
  # handle gfvs
  for x,y in get_gvfs_devices_and_paths():
    if uuid==x:
      return 'gvfs'
  # handle local devices
  if os.path.exists( os.path.join( '/dev/disk/by-uuid/', uuid ) ):
    return 'local'
  return None
  
def get_hostname():
  import socket
  return socket.gethostname()
  
def get_gvfs_devices():
  return [ x[0] for x in get_gvfs_devices_and_paths() ]
  
def get_gvfs_devices_and_paths():
  l = []
  gvfs_dir = os.path.join( os.path.expanduser('~'), '.gvfs')
  if os.path.exists(gvfs_dir):
    for x in os.listdir(gvfs_dir):
      mount_point = os.path.join( gvfs_dir, x )
      uuid = str(uuidlib.uuid5(UUID_GVFS, mount_point))
      l.append( (uuid, mount_point) )
  return l
  
def get_local_devices():
  devices = [ os.path.basename(x) for x in os.listdir('/dev/disk/by-uuid/') ]
  return devices
  
def get_all_devices():
  return get_local_devices() + get_gvfs_devices()
  
def get_writable_devices():
  writable_uuids = []
  for uuid in get_all_devices():
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
  
def test_backup_assertions(uuid, host, path, test_exists=True):
  if not is_dev_present(uuid): 
    print 'not is_dev_present("%s")' % uuid
    return False
  if not get_hostname()==host:
    print 'get_hostname()!="%s"' % host
    return False
  if not os.path.exists(path):
    print 'not os.path.exists("%s")' % path
    return False
  if test_exists:
    if not os.path.exists( get_git_dir(uuid, host, path) ):
      print 'not os.path.exists("%s")' % get_git_dir(uuid, host, path)
      return False
  return True

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
  # handle gfvs
  for x,y in get_gvfs_devices_and_paths():
    if uuid==x:
      return y
  # handle local devices
  dev_paths = get_dev_paths_for_uuid(uuid)
  f = os.popen('mount')
  s = f.read()
  f.close()
  for line in s.split('\n'):
    x = line.strip().split(' ')
    if x:
      dev_path = x[0]
      if dev_path in dev_paths:
        mount_path = ' '.join(x[2:x.index('type')])
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
  cmd = 'df "%s"' % path
  print '$', cmd
  f = os.popen(cmd)
  s = f.read()
  f.close()
  line = s.split('\n',1)[1]
  x = line.strip().split()
  print x
  if int(x[1])==0: return -1 # unknown amount of space
  return int(x[3])*1024
      
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
  assert test_backup_assertions(uuid, host, path, test_exists=False)

  tmp = tempfile.mkdtemp(suffix='_flyback')
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
  f = open( os.path.join(git_dir, 'flyback_properties.pickle'), 'wb' )
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
  os.chdir(util.RUN_FROM_DIR)
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
  for line in f:
    sys.stdout.write(line)
  f.close()

  # repack
  cmd = git_cmd + 'repack -A -d --max-pack-size=2000'
  print '$', cmd
  f = os.popen(cmd)
  for line in f:
    sys.stdout.write(line)
  f.close()


def get_preferences(uuid, host, path):
  preferences = dict(settings.DEFAULT_PREFERENCES)
  git_dir = get_git_dir(uuid, host, path)
  try:
    f = open( os.path.join(git_dir, 'flyback_preferences.pickle'), 'rb' )
    o = pickle.load(f)
    f.close()
    if o:
      preferences.update(o)
  except:
    print traceback.print_exc()
  return preferences


def save_preferences(uuid, host, path, preferences):
  preferences_diff = {}
  for k,v in preferences.iteritems():
    if settings.DEFAULT_PREFERENCES.get(k)!=v:
      preferences_diff[k] = v
  git_dir = get_git_dir(uuid, host, path)
  try:
    f = open( os.path.join(git_dir, 'flyback_preferences.pickle'), 'wb' )
    pickle.dump(preferences_diff, f)
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
  tmp = tempfile.mkdtemp(suffix='_flyback')
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
  
  # load verification history
  try:
    f = open( os.path.join(git_dir, 'revision_verifications.pickle'), 'rb' )
    revision_verifications = pickle.load(f)
    f.close()
  except:
    revision_verifications = {}
  
  log = []
  if s:
    entry = None
    for line in s.split('\n'):
      if line.startswith('commit'):
        if entry:
          entry['verified'] = revision_verifications.get(entry['commit'])
          log.append(entry)
        entry = {'commit':line[line.index(' '):].strip(), 'message':''}
      elif line.startswith('Author: '):
        entry['author'] = line[line.index(' '):].strip()
      elif line.startswith('Date: '):
        entry['date'] = line[line.index(' '):].strip()
      else:
        entry['message'] += line
    if entry:
      entry['verified'] = revision_verifications.get(entry['commit'])
      log.append(entry)

  rmdir(tmp)
  os.chdir(util.RUN_FROM_DIR)
  print 'log', log
  return log


def get_files_for_revision(uuid, host, path, rev):
  tmp = tempfile.mkdtemp(suffix='_flyback')
  os.chdir(tmp)
  git_dir = get_git_dir(uuid, host, path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="%s" git ' % (git_dir,tmp)
  cmd = git_cmd + 'ls-tree -r --name-only ' + rev
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
  f.close()
  s = ''.join(s)
  rmdir(tmp)
  os.chdir(util.RUN_FROM_DIR)
  return [ x.strip('"') for x in s.split('\n') ]


def export_revision(uuid, host, path, rev, target_path):
  tmp = tempfile.mkdtemp(suffix='_flyback')
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
  os.chdir(util.RUN_FROM_DIR)
  return fn


def verify_revision(uuid, host, path, rev):
  tmp = tempfile.mkdtemp(suffix='_flyback')
  os.chdir(tmp)
  git_dir = get_git_dir(uuid, host, path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="%s" git ' % (git_dir,tmp)
  cmd = git_cmd + 'archive %s > /dev/null' % (rev)
  print '$', cmd
  f = os.popen(cmd)
  s = []
  for line in f:
    s.append(line)
    sys.stdout.write(line)
  f.close()
  s = ''.join(s)
  rmdir(tmp)
  os.chdir(util.RUN_FROM_DIR)

  # save verification history
  print 1
  try:
    f = open( os.path.join(git_dir, 'revision_verifications.pickle'), 'rb' )
    revision_verifications = pickle.load(f)
    print 2
    f.close()
  except:
    revision_verifications = {}
  print 3
  revision_verifications[rev] = datetime.datetime.now()
  f = open( os.path.join(git_dir, 'revision_verifications.pickle'), 'wb' )
  pickle.dump(revision_verifications,f)
  f.close()
  print 4


def get_status(uuid, host, path):
  assert test_backup_assertions(uuid, host, path)
  added = []
  modified = []
  deleted = []

  os.chdir(path)
  git_dir = get_git_dir(uuid, host, path)
  git_cmd = 'GIT_DIR="%s" GIT_WORK_TREE="%s" git ' % (git_dir,path)
  cmd = git_cmd + 'status'
  print '$', cmd
  f = os.popen(cmd)
  rest_are_added = False
  for line in f:
    sys.stdout.write(line)
    if not line.startswith('#'):
      continue
    if line.startswith('#	modified:'):
      fn = line[ line.index(':')+1: ].strip()
      modified.append(fn)
    if line.startswith('#	deleted:'):
      fn = line[ line.index(':')+1: ].strip()
      deleted.append(fn)
    if line.startswith('#   (use "git'):
      if line.startswith('#   (use "git add'):
        rest_are_added = True
      else:
        rest_are_added = False
      continue
    if rest_are_added:
      fn = line.lstrip('#').strip()
      if fn:
        added.append(fn)
  f.close()
  os.chdir(util.RUN_FROM_DIR)

  return added, modified, deleted


def delete_backup(uuid, host, path):
  git_dir = get_git_dir(uuid, host, path)
  cmd = 'rm -Rf "%s"' % git_dir
  print '$', cmd
  f = os.popen(cmd)
  for line in f:
    sys.stdout.write(line)
  f.close()
  

