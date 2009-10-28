from __future__ import division
import datetime, os, threading, time


def pango_escape(message):
	assert isinstance(message, basestring)
	message = "&amp;".join(message.split("&"))
	message = "&lt;".join(message.split("<"))
	message = "&gt;".join(message.split(">"))
	return message


def open_file(fn):
  import os
  os.system( 'gnome-open "%s"' % fn )
  
  
def humanize_bytes(bytes):
  if bytes < 1024:
    return '%dB' % bytes
  if bytes < 1024*1024:
    return '%.1fKB' % (bytes/1024)
  if bytes < 1024*1024*1024:
    return '%.1fMB' % (bytes/1024/1024)
  if bytes < 1024*1024*1024*1024:
    return '%.1fGB' % (bytes/1024/1024/1024)
  return '%.1fTB' % (bytes/1024/1024/1024/1024)
    

class DeviceMonitorThread(threading.Thread):
  def run(self):
    print 'starting dbus-monitor...'
    self.add_callbacks = []
    self.remove_callbacks = []
    last_add_event = datetime.datetime.now()
    last_remove_event = datetime.datetime.now()
    f = os.popen('dbus-monitor --system "interface=org.freedesktop.Hal.Manager"')
    while True:
      line = f.readline()
      #print line
      if 'member=DeviceRemoved' in line:
        if (datetime.datetime.now() - last_remove_event).seconds > 1:
          last_remove_event = datetime.datetime.now()
          time.sleep(1)
          print 'device removed'
          for callback in self.remove_callbacks:
            callback()
      if 'member=DeviceAdded' in line:
        if (datetime.datetime.now() - last_add_event).seconds > 1:
          last_add_event = datetime.datetime.now()
          time.sleep(1)
          print 'device added'
          for callback in self.add_callbacks:
            callback()
        
        
device_monitor_thread = DeviceMonitorThread()
device_monitor_thread.daemon = True
device_monitor_thread.start()
def register_device_added_removed_callback(callback):
  device_monitor_thread.add_callbacks.append(callback)
  device_monitor_thread.remove_callbacks.append(callback)
  
