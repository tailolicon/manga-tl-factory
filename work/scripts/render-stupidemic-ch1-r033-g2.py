#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np
from pathlib import Path
import argparse
p=argparse.ArgumentParser(); p.add_argument('--source-dir',required=True); p.add_argument('--out-dir',required=True); a=p.parse_args()
SRC=Path(a.source_dir)/'0033.jpg'; OUT=Path(a.out_dir)/'page-033.webp'; OUT.parent.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
im=Image.open(SRC).convert('RGB')

def cv_inpaint_mask(mask,radius=3):
    global im
    arr=np.array(im); out=cv2.inpaint(cv2.cvtColor(arr,cv2.COLOR_RGB2BGR),mask,radius,cv2.INPAINT_TELEA)
    im=Image.fromarray(cv2.cvtColor(out,cv2.COLOR_BGR2RGB))

def inpaint_dark(box,threshold=185,dilate=3):
    global im
    arr=np.array(im); x0,y0,x1,y1=box; sub=arr[y0:y1,x0:x1]
    gray=cv2.cvtColor(sub,cv2.COLOR_RGB2GRAY); m=(gray<threshold).astype(np.uint8)*255
    m=cv2.dilate(m,np.ones((dilate,dilate),np.uint8),1)
    mask=np.zeros(arr.shape[:2],np.uint8); mask[y0:y1,x0:x1]=m; cv_inpaint_mask(mask,3)

def inpaint_rect(box,radius=5):
    global im
    arr=np.array(im); x0,y0,x1,y1=box; mask=np.zeros(arr.shape[:2],np.uint8); mask[y0:y1,x0:x1]=255; cv_inpaint_mask(mask,radius)

def inpaint_white_dark(box,white=215,dark=75,dilate=5):
    global im
    arr=np.array(im); x0,y0,x1,y1=box; sub=arr[y0:y1,x0:x1]; gray=cv2.cvtColor(sub,cv2.COLOR_RGB2GRAY)
    m=((gray>white)|(gray<dark)).astype(np.uint8)*255; m=cv2.dilate(m,np.ones((dilate,dilate),np.uint8),1)
    mask=np.zeros(arr.shape[:2],np.uint8); mask[y0:y1,x0:x1]=m; cv_inpaint_mask(mask,3)

def fit_lines(draw,text,box,max_size=30,min_size=14,spacing=4):
    x0,y0,x1,y1=box
    for sz in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(FONT,sz); lines=[]
        for para in text.split('\n'):
            words=para.split(); cur=''
            for w in words:
                cand=w if not cur else cur+' '+w; bb=draw.textbbox((0,0),cand,font=f)
                if bb[2]-bb[0] <= x1-x0: cur=cand
                else:
                    if cur: lines.append(cur)
                    cur=w
            if cur: lines.append(cur)
        bbs=[draw.textbbox((0,0),l,font=f) for l in lines]; ws=[b[2]-b[0] for b in bbs]; hs=[b[3]-b[1] for b in bbs]
        if sum(hs)+spacing*max(0,len(lines)-1)<=y1-y0 and max(ws or [0])<=x1-x0: return f,lines,ws,hs,spacing
    f=ImageFont.truetype(FONT,min_size); bb=draw.textbbox((0,0),text,font=f); return f,[text],[bb[2]-bb[0]],[bb[3]-bb[1]],spacing

def draw_text(box,text,max_size=30):
    d=ImageDraw.Draw(im); x0,y0,x1,y1=box; f,lines,ws,hs,sp=fit_lines(d,text,box,max_size=max_size)
    total=sum(hs)+sp*max(0,len(lines)-1); y=y0+(y1-y0-total)/2
    for l,w,h in zip(lines,ws,hs): d.text((x0+(x1-x0-w)/2,y),l,font=f,fill='black'); y+=h+sp

def bubble(src_box,draw_box,text,max_size=30): inpaint_dark(src_box); draw_text(draw_box,text,max_size)

def overlay_sfx(box,text,size,fill='black',stroke='white',sw=5,angle=0):
    global im
    x0,y0,x1,y1=box; lay=Image.new('RGBA',(x1-x0,y1-y0),(0,0,0,0)); d=ImageDraw.Draw(lay); f=ImageFont.truetype(FONT,size)
    bb=d.multiline_textbbox((0,0),text,font=f,stroke_width=sw,spacing=0,align='center'); w,h=bb[2]-bb[0],bb[3]-bb[1]
    d.multiline_text(((lay.width-w)//2,(lay.height-h)//2),text,font=f,fill=fill,stroke_fill=stroke,stroke_width=sw,spacing=0,align='center')
    if angle: lay=lay.rotate(angle,expand=False,resample=Image.Resampling.BICUBIC)
    im.paste(lay,(x0,y0),lay)

bubble((420,230,555,325),(380,215,585,340),'Phù...\nbỏ qua đi...',28)
bubble((110,445,350,575),(85,420,375,600),'À, khoan.\nMẹ cậu chết rồi,\nphải không?',27)
bubble((135,1095,235,1165),(110,1080,260,1180),'Đừng quên...',26)
bubble((390,1385,590,1520),(350,1360,625,1555),'Mình là chó...\nkhông phải\ncon người...',25)
bubble((175,2485,350,2580),(145,2460,425,2625),'Vậy chắc\ncha cậu dạy.',27)
bubble((390,3230,585,3315),(350,3190,625,3350),'Đừng nổi nóng...\nkhông thì mất tiền.',24)
bubble((205,3820,500,3910),(165,3780,545,3945),'À, nhắc mới nhớ.\nCha cậu cũng chết rồi nhỉ?',22)
inpaint_rect((488,762,582,825),4); overlay_sfx((480,755,605,855),'GIẬT\nMÌNH',24,fill='#8b1e2c',stroke='white',sw=4,angle=-5)
inpaint_rect((525,1735,665,1825),5); overlay_sfx((520,1722,685,1840),'HẤT',40,fill='white',stroke='black',sw=5,angle=-5)
inpaint_white_dark((495,1998,660,2075),white=210,dark=85,dilate=5)
d=ImageDraw.Draw(im); d.rectangle((470,2059,719,2120),fill='white'); d.line((57,2057,660,2057),fill='black',width=3)
overlay_sfx((500,1980,675,2053),'HẤT',38,fill='white',stroke='black',sw=5,angle=-5)
for box in [(420,2635,545,2695),(475,2775,575,2835),(45,2870,200,2945),(105,3040,255,3110)]: inpaint_rect(box,4)
overlay_sfx((395,2620,590,2720),'LỤC BỤC',27,fill='#a52b37',stroke='white',sw=4,angle=6)
overlay_sfx((455,2755,625,2855),'LỤC BỤC',23,fill='#a52b37',stroke='white',sw=4,angle=6)
overlay_sfx((25,2850,245,2960),'LỤC BỤC',27,fill='#a52b37',stroke='white',sw=4,angle=-5)
overlay_sfx((85,3015,300,3130),'LỤC BỤC',25,fill='#a52b37',stroke='white',sw=4,angle=-5)
im.save(OUT,'WEBP',quality=90,method=6)
