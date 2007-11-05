import dircache
from datetime import datetime
from time import strptime
import os
import gconf
import pickle




parent_backup_dir = '/home/backups/malcolm'
dirs_to_backup = [
    '/home/derek',
]

client = gconf.client_get_default()
client.add_dir ("/apps/flyback", gconf.CLIENT_PRELOAD_NONE)

def get_available_backups():
    parent_backup_dir = client.get_string("/apps/flyback/external_storage_location")
    try:
        dirs = dircache.listdir(parent_backup_dir)
        dir_datetimes = []
        for dir in dirs:
            dir_datetimes.append( datetime(*strptime(dir, "%Y-%m-%d %H:%M:%S")[0:6]) )
        dir_datetimes.sort(reverse=True)
        return dir_datetimes
    except:
        return []
    

def get_latest_backup_dir():
    try:
        return get_available_backups()[0]
    except:
        return None
        
def backup():
    print 'parent_backup_dir', parent_backup_dir
    latest_backup_dir = get_latest_backup_dir()
    s = client.get_string("/apps/flyback/included_dirs")
    if s:
        dirs_to_backup = pickle.loads(s)
    print 'dirs_to_backup', dirs_to_backup
    new_backup = parent_backup_dir +'/'+ datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if latest_backup_dir:
        last_backup = parent_backup_dir +'/'+ latest_backup_dir.strftime("%Y-%m-%d %H:%M:%S")
        for dir in dirs_to_backup:
            os.system("mkdir -p '%s'" % new_backup + dir)
            os.system("rsync -av --delete --link-dest='%s' '%s/' '%s/'" % (last_backup + dir, dir, new_backup + dir))
    else:
        for dir in dirs_to_backup:
            os.system("mkdir -p '%s'" % new_backup + dir)
            os.system("rsync -av --delete '%s/' '%s/'" % (dir, new_backup + dir))
    os.system(" chmod -R -w '%s'" % new_backup)

if __name__ == "__main__":
    backup()
