from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import cv2, numpy as np, hashlib, json
SRC=Path('/mnt/data/stupidemic_relay/ch-200c8c840df0'); OUT=Path('/mnt/data/r038_041_g3_v8'); OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSans-ExtraCondensedBold.ttf'
P={39:[
('Chắc không...?\nTrông cô ta vẫn bình thường...',(320,775,535,850),(240,730,565,925),24,'whitebox'),
('Không... nãy cô ta còn\nlàm ầm lên chuyện mình\ncho nước vào cà phê...',(170,1250,425,1370),(205,1200,485,1460),22,'whitebox'),
('Giờ cô ta cũng đang\nhành xử kỳ quặc.',(375,1470,550,1575),(390,1450,620,1665),22,'whitebox'),
('Nếu cô ta thật sự\nnhiễm virus...',(270,2515,470,2595),(245,2470,545,2670),24,'whitebox'),
('Cô Kim! Nó bay vào\ngiữa hai chân cô rồi!!',(270,3250,500,3355),(220,3240,550,3520),25,'whitebox'),
('C-cái gì?!\nỞ đâu?!',(180,3600,320,3695),(100,3595,320,3805),26,'whitebox'),
('Nó bay lên trong...',(270,4940,500,5000),(200,4880,555,5000),25,'whitebox'),
]}
def erase(im, box, mode):
    if mode=='whitebox':
        ImageDraw.Draw(im).rectangle(box,fill=(255,255,255)); return im
    arr=np.array(im); bgr=cv2.cvtColor(arr,cv2.COLOR_RGB2BGR); x1,y1,x2,y2=box; roi=bgr[y1:y2,x1:x2]
    hsv=cv2.cvtColor(roi,cv2.COLOR_BGR2HSV)
    m=(hsv[:,:,1]>38).astype(np.uint8)*255
    m=cv2.dilate(m,np.ones((7,7),np.uint8),iterations=2)
    mask=np.zeros(bgr.shape[:2],np.uint8); mask[y1:y2,x1:x2]=m
    out=cv2.inpaint(bgr,mask,4,cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(out,cv2.COLOR_BGR2RGB))
def fit(d,text,box,maxs,stroke=0):
    x1,y1,x2,y2=box; bw=x2-x1; bh=y2-y1
    for s in range(maxs,14,-1):
      f=ImageFont.truetype(FONT,s); lines=[]
      for para in text.split('\n'):
        cur=''
        for w in para.split():
          cand=(cur+' '+w).strip(); bb=d.textbbox((0,0),cand,font=f,stroke_width=stroke)
          if bb[2]-bb[0]<=bw*.93: cur=cand
          else:
            if cur: lines.append(cur)
            cur=w
        if cur: lines.append(cur)
      sp=max(2,int(s*.15)); hs=[]; ws=[]
      for ln in lines:
        bb=d.textbbox((0,0),ln,font=f,stroke_width=stroke); ws.append(bb[2]-bb[0]); hs.append(bb[3]-bb[1])
      th=sum(hs)+sp*max(0,len(lines)-1)
      if max(ws or [0])<=bw*.95 and th<=bh*.76: return f,lines,sp,hs,th
    f=ImageFont.truetype(FONT,15); lines=text.split('\n'); hs=[d.textbbox((0,0),ln,font=f)[3] for ln in lines]; return f,lines,2,hs,sum(hs)+2*(len(lines)-1)
def render(i):
    im=Image.open(SRC/f'{i:04d}.jpg').convert('RGB')
    for t,e,b,ms,m in P[i]: im=erase(im,e,m)
    d=ImageDraw.Draw(im)
    for t,e,b,ms,m in P[i]:
      sfx=m=='smirk'; stroke=2 if sfx else 0; fill='white' if sfx else 'black'; sf='black' if sfx else None
      f,lines,sp,hs,th=fit(d,t,b,ms,stroke); x1,y1,x2,y2=b; y=y1+(y2-y1-th)//2
      for ln,h in zip(lines,hs):
        bb=d.textbbox((0,0),ln,font=f,stroke_width=stroke); x=x1+(x2-x1-(bb[2]-bb[0]))//2
        d.text((x,y),ln,font=f,fill=fill,stroke_width=stroke,stroke_fill=sf); y+=h+sp
    out=OUT/f'page-{i:03d}.webp'; im.save(out,'WEBP',quality=55,method=6)
    b=out.read_bytes(); return {'page_index':i,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'width':im.width,'height':im.height,'file':str(out)}
print(json.dumps([render(39)],ensure_ascii=False,indent=2))
