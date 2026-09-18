"""Bilinear terrain sampling in local geographic metres (Blender compatible)."""
import math
class TerrainGrid:
 def __init__(self, data):
  self.grid=data['grid'];self.z=self.grid['heights'];self.datum=data.get('trackDatumMeters',0)
 def height(self,x,y):
  g=self.grid;u=(x-g['x0'])/g['step'];v=(y-g['y0'])/g['step'];u=max(0,min(len(self.z[0])-1.000001,u));v=max(0,min(len(self.z)-1.000001,v));i,j=math.floor(u),math.floor(v);u-=i;v-=j
  return (self.z[j][i]*(1-u)*(1-v)+self.z[j][i+1]*u*(1-v)+self.z[j+1][i]*(1-u)*v+self.z[j+1][i+1]*u*v)-self.datum
