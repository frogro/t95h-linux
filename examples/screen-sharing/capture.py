#!/usr/bin/python3
"""User-approved Wayland screen -> linear NV12 -> Intel VAAPI H264 -> local go2rtc."""
import os,signal,subprocess,uuid,shutil,time
from pathlib import Path
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gio,GLib,Gst
Gst.init(None)
if not shutil.which('ffmpeg'):raise SystemExit('Bitte zuerst sudo apt install ffmpeg ausführen.')
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
dest='org.freedesktop.portal.Desktop';obj='/org/freedesktop/portal/desktop';iface='org.freedesktop.portal.ScreenCast'
session=None;pipeline=None;encoder=None;remote_fd=None

def request(method,signature,args,options):
 token='t95h_'+uuid.uuid4().hex
 options['handle_token']=GLib.Variant('s',token)
 path='/org/freedesktop/portal/desktop/request/'+bus.get_unique_name()[1:].replace('.','_')+'/'+token
 loop=GLib.MainLoop();result=[]
 def response(*v):result.append(v[5].unpack());loop.quit()
 sub=bus.signal_subscribe(dest,'org.freedesktop.portal.Request','Response',path,None,Gio.DBusSignalFlags.NONE,response)
 try:
  bus.call_sync(dest,obj,iface,method,GLib.Variant(signature,(*args,options)),None,Gio.DBusCallFlags.NONE,-1,None)
  loop.run()
 finally:bus.signal_unsubscribe(sub)
 code,data=result[0]
 if code:raise RuntimeError('Bildschirmfreigabe abgebrochen: '+str(code))
 return data

try:
 session=request('CreateSession','(a{sv})',(),{'session_handle_token':GLib.Variant('s','t95h_'+uuid.uuid4().hex)})['session_handle']
 request('SelectSources','(oa{sv})',(session,),{'types':GLib.Variant('u',1),'multiple':GLib.Variant('b',False),'cursor_mode':GLib.Variant('u',2)})
 print('Bitte im Desktopdialog den Bildschirm auswählen.',flush=True)
 data=request('Start','(osa{sv})',(session,''),{})
 node,properties=data['streams'][0]
 result,fdlist=bus.call_with_unix_fd_list_sync(dest,obj,iface,'OpenPipeWireRemote',GLib.Variant('(oa{sv})',(session,{})),GLib.VariantType.new('(h)'),Gio.DBusCallFlags.NONE,-1,None,None)
 remote_fd=fdlist.get(result.unpack()[0])
 cmd=['ffmpeg', '-hide_banner', '-loglevel', 'info', '-vaapi_device', '/dev/dri/renderD128', '-f', 'rawvideo', '-pixel_format', 'nv12', '-video_size', '1920x1080', '-framerate', '60', '-i', 'pipe:0', '-an', '-vf', 'hwupload', '-c:v', 'h264_vaapi', '-profile:v', 'constrained_baseline', '-b:v', '12M', '-maxrate', '12M', '-bufsize', '1200k', '-g', '60', '-bf', '0', '-async_depth', '1', '-flush_packets', '1', '-rtsp_transport', 'tcp', '-f', 'rtsp', 'rtsp://127.0.0.1:8554/desktop']
 encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 pipeline=Gst.parse_launch(f'pipewiresrc name=capture fd={remote_fd} path={node} do-timestamp=true ! queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! videoconvert ! videoscale ! videorate drop-only=true ! video/x-raw,format=NV12,width=1920,height=1080,framerate=60/1 ! fdsink name=encoder_input fd={encoder.stdin.fileno()} sync=false')
 counts={'capture':0,'encoder_input':0}; previous={'capture':0,'encoder_input':0}; measured=[time.monotonic()]
 def count_frame(pad,info,name):
  counts[name]+=1
  return Gst.PadProbeReturn.OK
 for name,padname in [('capture','src'),('encoder_input','sink')]:
  pipeline.get_by_name(name).get_static_pad(padname).add_probe(Gst.PadProbeType.BUFFER,count_frame,name)
 def report():
  now=time.monotonic(); elapsed=now-measured[0]
  rates={k:round((counts[k]-previous[k])/elapsed,2) for k in counts}
  caps=pipeline.get_by_name('capture').get_static_pad('src').get_current_caps()
  print('MEASURE',rates,'SOURCE_CAPS',caps.to_string() if caps else 'pending',flush=True)
  previous.update(counts);measured[0]=now
  return True
 GLib.timeout_add_seconds(5,report)
 loop=GLib.MainLoop();gstbus=pipeline.get_bus();gstbus.add_signal_watch()
 def message(b,m):
  if m.type==Gst.MessageType.ERROR:
   print('Capture error:',m.parse_error(),flush=True);loop.quit()
  elif m.type==Gst.MessageType.EOS:loop.quit()
 gstbus.connect('message',message)
 def stop(*_):loop.quit()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 def health():
  if encoder.poll() is not None:print('FFmpeg exited',encoder.returncode,flush=True);loop.quit();return False
  return True
 GLib.timeout_add_seconds(1,health)
 pipeline.set_state(Gst.State.PLAYING)
 print('1080p60 H264 VAAPI streaming; no audio; Ctrl+C stops.',flush=True)
 loop.run()
finally:
 if encoder and encoder.poll() is None:encoder.terminate()
 if pipeline:pipeline.set_state(Gst.State.NULL)
 if encoder:
  try:encoder.wait(timeout=5)
  except subprocess.TimeoutExpired:encoder.kill();encoder.wait()
 if session:
  bus.call_sync(dest,session,'org.freedesktop.portal.Session','Close',None,None,Gio.DBusCallFlags.NONE,-1,None)
 if remote_fd is not None:os.close(remote_fd)
