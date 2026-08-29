from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import cv2, numpy as np, hashlib, json
SRC=Path('/mnt/data/stupidemic_relay/ch-200c8c840df0'); OUT=Path('/mnt/data/r038_041_g3_v6'); OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSans-ExtraCondensedBold.ttf'
P={40:[
('váy của cô! Dang chân ra!\nTôi bắt nó cho!!',(210,0,555,55),(135,0,590,210),25,'whitebox'),
('Cậu thấy nó không? Thấy không?\nMau bắt nó đi!!',(350,605,565,710),(300,525,620,810),23,'whitebox'),
('Ơ, tôi không thấy!\nDang rộng hơn nữa\nđể tôi tìm!!',(185,1975,445,2090),(115,1900,595,2205),24,'whitebox'),
('Ha...!',(400,2865,500,2925),(335,2835,555,3025),25,'whitebox'),
('CƯỜI NHẾCH',(380,3000,550,3180),(360,2995,565,3195),27,'smirk'),
('Nhìn cô ta kìa...',(330,3890,490,3960),(220,3810,545,4030),25,'whitebox'),
('Cậu làm gì thế?!\nMau bắt nó đi!!!',(200,4510,470,4595),(145,4400,495,4670),24,'whitebox'),
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
print(json.dumps([render(40)],ensure_ascii=False,indent=2))
