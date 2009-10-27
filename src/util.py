from __future__ import division


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
    
