// Provider-coordinate map: one completed lap defines the circuit, live samples share its frame.
export function circuitBounds(points) {
  const valid=points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
  if(valid.length<10)return null;
  const xs=valid.map(p=>p.x),ys=valid.map(p=>p.y);
  const bounds={minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)};
  return bounds.maxX-bounds.minX>0&&bounds.maxY-bounds.minY>0?bounds:null;
}
export class CircuitDisplay {
 constructor(canvas,onSelect){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.onSelect=onSelect;this.points=[];this.cars=new Map();this.selected=null;this.hits=[];this.active=true;this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;canvas.addEventListener('click',e=>{const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;const hit=this.hits.find(h=>Math.hypot(h.x-x,h.y-y)<22);if(hit)this.onSelect(hit.id);});this.observer=new ResizeObserver(()=>this.draw());this.observer.observe(canvas);this.frame=()=>{if(this.active&&!document.hidden)this.draw();this.raf=requestAnimationFrame(this.frame);};this.frame();}
 reset(){this.points=[];this.bounds=null;this.cars.clear();this.hits=[];}
 setTrack(points){this.points=points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));this.bounds=circuitBounds(this.points);}
 update(samples,drivers,selected){this.selected=String(selected);for(const p of samples){if(!Number.isFinite(p.x)||!Number.isFinite(p.y))continue;const id=String(p.driver_number),old=this.cars.get(id);if(old?.date===p.date)continue;const d=drivers.find(d=>String(d.driver_number)===id);this.cars.set(id,{...p,id,label:d?.name_acronym??id,color:/^[a-f\d]{6}$/i.test(d?.team_colour??'')?'#'+d.team_colour:'#32f5ed',from:old?this.position(old):p,received:performance.now()});}}
 position(car){const t=this.reduced?1:Math.min(1,(performance.now()-car.received)/700);return{x:car.from.x+(car.x-car.from.x)*t,y:car.from.y+(car.y-car.from.y)*t};}
 draw(){const c=this.canvas,ctx=this.ctx,w=c.clientWidth,h=c.clientHeight,dpr=Math.min(devicePixelRatio||1,2);if(!w||!h)return;if(c.width!==Math.round(w*dpr)||c.height!==Math.round(h*dpr)){c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);ctx.strokeStyle='#18294c';ctx.lineWidth=.5;for(let x=0;x<w;x+=32){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(let y=0;y<h;y+=32){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}if(!this.bounds){ctx.fillStyle='#89a8c6';ctx.font='13px Trebuchet MS';ctx.textAlign='center';ctx.fillText('ACQUIRING CIRCUIT COORDINATES',w/2,h/2);return;}
 const b=this.bounds,pad=46,scale=Math.min((w-pad*2)/(b.maxX-b.minX),(h-pad*2)/(b.maxY-b.minY));const project=p=>({x:w/2+(p.x-(b.minX+b.maxX)/2)*scale,y:h/2-(p.y-(b.minY+b.maxY)/2)*scale});
 const path=()=>{ctx.beginPath();this.points.forEach((p,i)=>{const q=project(p);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y);});};ctx.lineJoin='round';ctx.lineCap='round';path();ctx.strokeStyle='#152c4e';ctx.lineWidth=18;ctx.stroke();path();ctx.strokeStyle='#2de6e1';ctx.shadowColor='#20e8ef';ctx.shadowBlur=12;ctx.lineWidth=3;ctx.stroke();ctx.shadowBlur=0;path();ctx.strokeStyle='#bafff6';ctx.lineWidth=.8;ctx.stroke();
 const start=project(this.points[0]);ctx.fillStyle='#f5f78c';ctx.fillRect(start.x-4,start.y-4,8,8);this.hits=[];
 for(const car of [...this.cars.values()].sort((a,b)=>(a.id===this.selected)-(b.id===this.selected))){const p=project(this.position(car));if(p.x<0||p.y<0||p.x>w||p.y>h)continue;const chosen=car.id===this.selected,stale=Date.now()-Date.parse(car.date)>15000;ctx.globalAlpha=stale?.4:1;ctx.beginPath();ctx.arc(p.x,p.y,chosen?9:5,0,Math.PI*2);ctx.fillStyle=chosen?'#f4ff62':car.color;ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=chosen?18:6;ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle='#06101e';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle=chosen?'#f4ff62':'#e8f8ff';ctx.font=`${chosen?'bold ':''}11px Trebuchet MS`;ctx.textAlign='left';ctx.fillText(chosen?car.label:car.id,p.x+11,p.y-9);ctx.globalAlpha=1;this.hits.push({id:car.id,x:p.x,y:p.y});}
 }
}
