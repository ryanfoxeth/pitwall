"""Render circuit assets with Blender. python build_season_assets.py OUTPUT_DIR [circuit ...]
Uses at most two independent Blender processes; keeps source .blend and PNG previews.
"""
from pathlib import Path
import subprocess,concurrent.futures,sys,os
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
ids=sys.argv[2:] or ["baku","sepang","marina_bay","americas","rodriguez","interlagos","vegas","losail","yas_marina"]
blender=os.environ.get("BLENDER","/Applications/Blender.app/Contents/MacOS/Blender")
def build(job):
 name,style=job;log=out/(name+"-"+style+".log")
 with log.open("w") as f:
  p=subprocess.run([blender,"-b","-t","3","--python",str(root/"tools/build_season_blender.py"),"--",str(root/"Assets/Season"/(name+".json")),str(out/(name+"-"+style+".usdz")),str(out/(name+"-"+style+".png")),style],stdout=f,stderr=subprocess.STDOUT)
 success=p.returncode==0 and "COMPLETE" in log.read_text();print(name,style,"OK" if success else "FAILED",flush=True);return success
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(build,[(i,t) for i in ids for t in ["grandPrix","tron","kart"]]))
if not all(results):raise SystemExit(1)
