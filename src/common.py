#    FlyBack
#    Copyright (C) 2007 Derek Anderson
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import math, os, sys


RUN_FROM_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + '/'
VERSION = 'v0.5.0'
GPL = open( RUN_FROM_DIR + 'GPL.txt', 'r' ).read()
USER = os.popen('whoami').read().strip()

if os.popen('which gksu').read(): SU_COMMAND = 'gksu'
elif os.popen('which kdesu').read(): SU_COMMAND = 'kdesu'
else: SU_COMMAND = 'su'

DEFAULT_EXCLUDES = [
    '.thumbnails/',
    '.mozilla/**/Cache/',
    '.cache/tracker/',
    '.Trash/',
    '.emerald/themecache/',
    '.fontconfig/*.cache*',
    '.java/deployment/cache/',
    'amarok/albumcovers/cache/',
    'amarok/albumcovers/large/',
    '.liferea*/mozilla/liferea/Cache/',
    '.liferea*/cache/',
    '.macromedia/Flash_Player/*SharedObjects/',
    '.macromedia/Macromedia/Flash\ Player/*SharedObjects/',
    '.metacity/sessions/',
    '.nautilus/saved*',
    '.mythtv/osdcache/',
    '.mythtv/themecache/',
    '/var/cache/',
    'workspace/.metadata/',
    '.openoffice.org2/user/registry/cache/',
    '.openoffice.org2/user/uno_packages/cache/',
    '.grails/*/scriptCache/',
    '.wine/drive_c/windows/temp/',
    'cdrom',
    'dev/',
    'proc/',
    'sys/',
    'tmp/',
]


if True:
    try:
        import gconf
    except:
        print 'error: could not find python module gconf'
        sys.exit()
    try:
        import pygtk
    except:
        print 'error: could not find python module pygtk'
        sys.exit()
    try:
        pygtk.require("2.0")
    except:
        print 'error: pygtk v2.0 or later is required'
        sys.exit()
    try:
        import gobject
    except:
        print 'error: could not find python module gobject'
        sys.exit()
    try:
        import gtk
        import gtk.glade
    except:
        print 'error: could not find python module gtk'
        sys.exit()
    try:
        import gnome.ui
    except:
        print 'error: could not find python module gnome'
        sys.exit()

def init_gtk():
#    load_gtk()
    gobject.threads_init()
    gtk.gdk.threads_init()


def humanize_timedelta(td):
    s = td.seconds
    if s<60:
        return humanize_count( s, 'second', 'seconds' )
    m = s/60.0
    if m<60:
        return humanize_count( m, 'minute', 'minutes' )
    h = m/60.0
    if h<24:
        return humanize_count( h, 'hour', 'hours' )
    d = h/24.0
    return humanize_count( d, 'day', 'days' )

def humanize_bytes(x):
    x = float(x)
    if x > math.pow(2,30):
        return humanize_count(x/math.pow(2,30),'GB','GB')
    if x > math.pow(2,20):
        return humanize_count(x/math.pow(2,20),'MB','MB')
    if x > math.pow(2,10):
        return humanize_count(x/math.pow(2,10),'KB','KB')
    return humanize_count( x, 'byte', 'bytes' )

def humanize_count(x, s, p, places=1):
    x = float(x)*math.pow(10, places)
    x = round(x)
    x = x/math.pow(10, places)
    if x-int(x)==0:
        x = int(x)
    if x==1:
        return str(x) +' ' + s
    else:
        return str(x) +' ' + p

