"""Resumable landscape movie batch. Keeps source/QA; deletes only verified frame intermediates.
Usage: python render_grand_prix_season.py SCENE_DIR OUTPUT_DIR [--ids ID ...]
"""
import argparse,json,subprocess,time,shutil,hashlib,traceback,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('scenes',type=Path);p.add_argument('output',type=Path);p.add_argument('--ids',nargs='*');p.add_argument('--status-name',default='status.json');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
tools=Path(__file__).parent;blender='/Applications/Blender.app/Contents/MacOS/Blender';ffmpeg=shutil.which('ffmpeg');probe=shutil.which('ffprobe');catalog=json.loads((tools.parent/'Sources/Resources/Season2026.json').read_text());statusfile=a.output/a.status_name;status=json.loads(statusfile.read_text()) if statusfile.exists() else {}
names=dict(albert_park='Melbourne',shanghai='Shanghai',suzuka='Suzuka',miami='Miami',villeneuve='Montreal',monaco='Monaco',catalunya='Barcelona',red_bull_ring='Spielberg',silverstone='Silverstone',spa='Spa',hungaroring='Hungaroring',zandvoort='Zandvoort',monza='Monza',madring='Madrid',baku='Baku',sepang='Sepang',marina_bay='Singapore',americas='Austin',rodriguez='Mexico City',interlagos='Interlagos',vegas='Las Vegas',losail='Lusail',yas_marina='Yas Marina')
def stage(cid,phase,**kw):
 status[cid]={'stage':phase,'updated':time.strftime('%Y-%m-%d %H:%M:%S'),**kw};tmp=statusfile.with_suffix('.tmp');tmp.write_text(json.dumps(status,indent=2));tmp.replace(statusfile);print(cid,phase,flush=True)
def run(cmd,log):
 with log.open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
def verify(path):
 d=json.loads(subprocess.check_output([probe,'-v','error','-show_entries','format=duration,size:stream=codec_type,width,height,nb_frames,r_frame_rate','-of','json',str(path)]));v=next(x for x in d['streams'] if x['codec_type']=='video');assert (v['width'],v['height'],v['nb_frames'],v['r_frame_rate'])==(1280,720,'1440','24/1'),d;assert abs(float(d['format']['duration'])-60)<.02;return d
order={cid:i for i,cid in enumerate(a.ids or [])}
for c in sorted(catalog,key=lambda c:order.get(c['id'],len(catalog)) if a.ids else (c['round']<15,c['round'])):
 cid=c['id']
 if a.ids and cid not in a.ids:continue
 d=a.output/names[cid];d.mkdir(exist_ok=True);video=d/'Grand Prix - Landscape.mp4';frames=Path(tempfile.gettempdir())/'pitwall-grand-prix-frames'/cid;source=a.scenes/(cid+'.json');signature=hashlib.sha256(source.read_bytes()+b''.join((tools/n).read_bytes() for n in ['build_grand_prix_movie.py','build_season_blender.py','build_monaco_blender.py','scenery_blender.py','terrain_grid.py'])).hexdigest()
 try:
  if video.exists() and (d/'verification.json').exists():
   old=json.loads((d/'verification.json').read_text())
   if old.get('signature')==signature:verify(video);stage(cid,'verified',file=str(video));continue
  if shutil.disk_usage(d).free<5*1024**3:raise RuntimeError('Less than 5GB free; protect existing outputs')
  frames.mkdir(parents=True,exist_ok=True)
  stamp=frames/'signature.txt'
  if not stamp.exists() or stamp.read_text()!=signature:
   for f in frames.glob('frame-*.png'):f.unlink()
   stamp.write_text(signature)
  # Validate resumed PNGs after an interrupted write before Blender skips them.
  from PIL import Image
  for f in frames.glob('frame-*.png'):
   try:
    with Image.open(f) as im:im.verify()
   except Exception:f.unlink()
  stage(cid,'building');shutil.copy2(source,d/'scene-source.json')
  production=d/'production';production.mkdir(exist_ok=True)
  for name in ['build_grand_prix_movie.py','build_season_blender.py','build_monaco_blender.py','scenery_blender.py','terrain_grid.py']:shutil.copy2(tools/name,production/name)
  run([blender,'--background','--factory-startup','--python-exit-code','1','--threads','4','--python',str(tools/'build_grand_prix_movie.py'),'--',str(d/'scene-source.json'),str(d),'preview'],d/'build.log')
  assert (d/'Grand Prix Lap.blend').exists() and (d/'preview-500.png').exists(), 'Blender scene build failed'
  run([blender,'--background','--factory-startup','--python-exit-code','1','--threads','2',str(d/'Grand Prix Lap.blend'),'--python',str(tools/'check_movie_camera.py')],d/'camera-check.log')
  stage(cid,'rendering',frames=1440)
  run([blender,'--background','--factory-startup','--threads','4',str(d/'Grand Prix Lap.blend'),'-a'],d/'render.log')
  assert len(list(frames.glob('frame-*.png')))==1440, 'Incomplete frame sequence'
  stage(cid,'encoding')
  temp=d/'Grand Prix - Landscape.partial.mp4'
  run([ffmpeg,'-y','-framerate','24','-i',str(frames/'frame-%04d.png'),'-vf','fade=t=in:st=0:d=0.4,fade=t=out:st=59:d=1','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],d/'encode.log');v=verify(temp)
  run([ffmpeg,'-v','error','-i',str(temp),'-f','null','-'],d/'decode.log');temp.replace(video)
  run([ffmpeg,'-y','-i',str(video),'-vf','fps=1/6,scale=384:-1,tile=5x2','-frames:v','1',str(d/'contact-sheet.jpg')],d/'contact.log')
  (d/'verification.json').write_text(json.dumps({'signature':signature,'probe':v,'fullDecode':'passed','sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'visualReview':'pending'},indent=2))
  for f in frames.glob('frame-*.png'):f.unlink()
  stage(cid,'rendered-awaiting-visual-review',file=str(video))
 except Exception as e:stage(cid,'failed',error=str(e));(d/'failure.txt').write_text(traceback.format_exc())
print('BATCH FINISHED',flush=True)
