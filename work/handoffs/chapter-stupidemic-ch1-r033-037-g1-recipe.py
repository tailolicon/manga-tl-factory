#!/usr/bin/env python3
"""Checkpoint recipe for Stupidemic ch1 range r033-037 g1.

Reproduces the QA-reviewed page 34-37 candidates from the chapter relay.
Page 33 is intentionally NOT generated/accepted: its artwork-overlaid SFX
still requires a cleaner redraw before range completion.
"""
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--source-dir", required=True, help="Relay chapter dir containing 0034.jpg..0037.jpg")
parser.add_argument("--out-dir", required=True)
args = parser.parse_args()
root = Path(args.source_dir)
out = Path(args.out_dir)
out.mkdir(parents=True, exist_ok=True)

# Base pass: pages 34-37
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np, os
from pathlib import Path

font_bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def wrap_fit(draw,text,box,max_size=30,min_size=13,spacing=3):
    x0,y0,x1,y1=box
    for sz in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(font_bold,sz)
        lines=[]
        for para in text.split("\n"):
            words=para.split(); cur=""
            for w in words:
                cand=w if not cur else cur+" "+w
                b=draw.textbbox((0,0),cand,font=f)
                if b[2]-b[0] <= x1-x0:
                    cur=cand
                else:
                    if cur: lines.append(cur)
                    cur=w
            if cur: lines.append(cur)
        bbs=[draw.textbbox((0,0),l,font=f) for l in lines]
        ws=[b[2]-b[0] for b in bbs]; hs=[b[3]-b[1] for b in bbs]
        if sum(hs)+spacing*max(0,len(lines)-1)<=y1-y0 and max(ws or [0])<=x1-x0:
            return f,lines,ws,hs
    f=ImageFont.truetype(font_bold,min_size)
    b=draw.textbbox((0,0),text,font=f)
    return f,[text],[b[2]-b[0]],[b[3]-b[1]]

def replace_bubble_text(im,box,text,max_size=28):
    d=ImageDraw.Draw(im)
    d.rectangle(box,fill='white')
    x0,y0,x1,y1=box
    f,lines,ws,hs=wrap_fit(d,text,(x0+3,y0+3,x1-3,y1-3),max_size=max_size)
    total=sum(hs)+3*max(0,len(lines)-1)
    y=y0+(y1-y0-total)/2
    for l,w,h in zip(lines,ws,hs):
        d.text((x0+(x1-x0-w)/2,y),l,font=f,fill='black')
        y+=h+3

def inpaint_mask(im,roi,mode,dilate=7):
    arr=np.array(im)
    x0,y0,x1,y1=roi
    sub=arr[y0:y1,x0:x1].astype(np.int16)
    if mode=='white':
        m=((sub[:,:,0]>215)&(sub[:,:,1]>215)&(sub[:,:,2]>215)).astype(np.uint8)*255
    elif mode=='black':
        m=((sub[:,:,0]<70)&(sub[:,:,1]<70)&(sub[:,:,2]<70)).astype(np.uint8)*255
    elif mode=='red':
        R,G,B=sub[:,:,0],sub[:,:,1],sub[:,:,2]
        m=((R>75)&(R<230)&((R-G)>25)&((R-B)>20)&(G<160)).astype(np.uint8)*255
    else:
        raise ValueError
    m=cv2.dilate(m,np.ones((dilate,dilate),np.uint8),iterations=1)
    mask=np.zeros(arr.shape[:2],np.uint8)
    mask[y0:y1,x0:x1]=m
    res=cv2.inpaint(cv2.cvtColor(arr.astype(np.uint8),cv2.COLOR_RGB2BGR),mask,3,cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(res,cv2.COLOR_BGR2RGB))

def overlay_sfx(im,box,text,size=36,fill='black',stroke='white',sw=4,angle=0):
    x0,y0,x1,y1=box
    lay=Image.new('RGBA',(x1-x0,y1-y0),(0,0,0,0))
    d=ImageDraw.Draw(lay)
    f=ImageFont.truetype(font_bold,size)
    b=d.textbbox((0,0),text,font=f,stroke_width=sw)
    w,h=b[2]-b[0],b[3]-b[1]
    d.text(((lay.width-w)//2,(lay.height-h)//2),text,font=f,fill=fill,stroke_fill=stroke,stroke_width=sw)
    if angle:
        lay=lay.rotate(angle,expand=False,resample=Image.Resampling.BICUBIC)
    im.paste(lay,(x0,y0),lay)
    return im

# PAGE 34
im=Image.open(root/'0034.jpg').convert('RGB')
replace_bubble_text(im,(190,705,530,900),"Địt mẹ, cô không biết\nlúc nào nên dừng à,\ncon khốn?!",28)
im=inpaint_mask(im,(150,1400,440,1685),'red',9)
im=overlay_sfx(im,(165,1410,440,1675),"BỐP!",54,fill='#8b1e1e',stroke='white',sw=4,angle=-8)
im.save(out/'page-034.webp','WEBP',quality=90,method=6)

# PAGE 35
im=Image.open(root/'0035.jpg').convert('RGB')
replace_bubble_text(im,(235,1515,490,1655),"Ôi... chết rồi...\nmình toi rồi.",28)
replace_bubble_text(im,(315,3490,560,3655),"“Con khốn...?”\nCậu vừa tát tôi đấy à...?",23)
replace_bubble_text(im,(190,4860,525,5000),"Khỉ thật...\ncô ta định gọi...",22)
im.save(out/'page-035.webp','WEBP',quality=90,method=6)

# PAGE 36
im=Image.open(root/'0036.jpg').convert('RGB')
replace_bubble_text(im,(175,0,445,95),"cảnh sát tới bắt mình à?",24)
replace_bubble_text(im,(245,840,505,970),"Ha... ở đây có\ncamera an ninh...\nchết tiệt...",23)
replace_bubble_text(im,(180,1380,460,1535),"Mình không thể mất việc này.\nGiờ phải làm sao đây?!",23)
replace_bubble_text(im,(240,1965,480,2095),"Hay quỳ xuống\nvan xin luôn!",24)
replace_bubble_text(im,(120,3270,360,3435),"À... ha ha! Ờm...\nlà con... muỗi mùa đông\nmới xuất hiện ấy...!",20)
replace_bubble_text(im,(355,3560,610,3740),"Tôi nghe nói chúng có thể\ngiết người! Tôi chỉ đang cố\nbắt con muỗi đó...!",19)
replace_bubble_text(im,(160,4580,370,4700),"Tôi xin lỗi!",27)
replace_bubble_text(im,(280,4880,520,5000),"Cậu đang nói cái quái gì vậy,\nđồ ngốc?!",19)
im.save(out/'page-036.webp','WEBP',quality=90,method=6)

# PAGE 37
im=Image.open(root/'0037.jpg').convert('RGB')
replace_bubble_text(im,(190,315,475,470),"Ai mà tin nổi chuyện nhảm đó?!\nSao mình không nghĩ ra cái cớ\nkhá hơn chứ...?!",21)
im=inpaint_mask(im,(455,1040,590,1140),'white',7)
im=overlay_sfx(im,(455,1040,590,1140),"XOA",29,angle=-8)
replace_bubble_text(im,(320,1430,540,1555),"Con mụ này...\nchúng có thể giết\nngười thật à...?",20)
replace_bubble_text(im,(190,1640,510,1765),"Này, lẽ ra cậu phải\nnói sớm hơn chứ.",22)
im=inpaint_mask(im,(45,1960,315,2130),'black',5)
im=overlay_sfx(im,(50,1970,250,2135),"HẢ?",44,angle=-4)
replace_bubble_text(im,(220,3030,455,3155),"Khỉ thật...\náo tôi bẩn mất rồi.",22)
replace_bubble_text(im,(300,3230,555,3375),"Cậu bắt được con muỗi rồi chứ?\nLoại muỗi đó phải giết hết.",19)
im.save(out/'page-037.webp','WEBP',quality=90,method=6)

# Refined page 34 SFX repair
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np
font_bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
orig=np.array(Image.open(f'{root}/0034.jpg').convert('RGB'))
im=Image.fromarray(orig.copy())
d=ImageDraw.Draw(im); box=(190,705,530,900); d.rectangle(box,fill='white')
f=ImageFont.truetype(font_bold,26)
lines=["Địt mẹ, cô không biết","lúc nào nên dừng à,","con khốn?!"]
bbs=[d.textbbox((0,0),l,font=f) for l in lines]
hs=[b[3]-b[1] for b in bbs]; ws=[b[2]-b[0] for b in bbs]
y=box[1]+(box[3]-box[1]-(sum(hs)+8))/2
for l,w,h in zip(lines,ws,hs):
    d.text((box[0]+(box[2]-box[0]-w)/2,y),l,font=f,fill='black'); y+=h+4
arr=np.array(im)
x0,y0,x1,y1=(145,1390,445,1695)
subsrc=orig[y0:y1,x0:x1]
s=subsrc.astype(np.int16); R,G,B=s[:,:,0],s[:,:,1],s[:,:,2]
red=((R>70)&(R<235)&((R-G)>20)&((R-B)>15)&(G<175)).astype(np.uint8)*255
white=((subsrc[:,:,0]>215)&(subsrc[:,:,1]>215)&(subsrc[:,:,2]>215)).astype(np.uint8)*255
n,labels,stats,cents=cv2.connectedComponentsWithStats(white,8)
sel=np.zeros_like(white)
for i in range(1,n):
    x,y,w,h,area=stats[i]
    if 300 <= area <= 1800 and x < 240 and y > 40:
        sel[labels==i]=255
filled=np.zeros_like(sel)
contours,_=cv2.findContours(sel,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(filled,contours,-1,255,thickness=cv2.FILLED)
maskroi=np.maximum(red,filled)
maskroi=cv2.dilate(maskroi,np.ones((7,7),np.uint8),1)
mask=np.zeros(arr.shape[:2],np.uint8); mask[y0:y1,x0:x1]=maskroi
res=cv2.inpaint(cv2.cvtColor(arr,cv2.COLOR_RGB2BGR),mask,3,cv2.INPAINT_TELEA)
im=Image.fromarray(cv2.cvtColor(res,cv2.COLOR_BGR2RGB))
lay=Image.new('RGBA',(305,290),(0,0,0,0)); ld=ImageDraw.Draw(lay); ff=ImageFont.truetype(font_bold,54)
b=ld.textbbox((0,0),"BỐP!",font=ff,stroke_width=4); w,h=b[2]-b[0],b[3]-b[1]
ld.text(((305-w)//2,(290-h)//2),"BỐP!",font=ff,fill='#8b1e1e',stroke_fill='white',stroke_width=4)
lay=lay.rotate(-8,expand=False,resample=Image.Resampling.BICUBIC)
im.paste(lay,(150,1400),lay)
im.save(f'{out}/page-034.webp','WEBP',quality=90,method=6)

# Refined page 36 masks
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os
font_bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def fit(draw,text,box,max_size=28,min_size=13):
    x0,y0,x1,y1=box
    for sz in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(font_bold,sz); lines=[]
        for para in text.split("\n"):
            words=para.split(); cur=""
            for w in words:
                cand=w if not cur else cur+" "+w
                b=draw.textbbox((0,0),cand,font=f)
                if b[2]-b[0] <= x1-x0: cur=cand
                else:
                    if cur: lines.append(cur)
                    cur=w
            if cur: lines.append(cur)
        bbs=[draw.textbbox((0,0),l,font=f) for l in lines]
        ws=[b[2]-b[0] for b in bbs]; hs=[b[3]-b[1] for b in bbs]
        if sum(hs)+3*max(0,len(lines)-1)<=y1-y0 and max(ws or [0])<=x1-x0:
            return f,lines,ws,hs
    f=ImageFont.truetype(font_bold,min_size)
    b=draw.textbbox((0,0),text,font=f)
    return f,[text],[b[2]-b[0]],[b[3]-b[1]]
def repl(im,box,text,max_size):
    d=ImageDraw.Draw(im); d.rectangle(box,fill='white')
    x0,y0,x1,y1=box; f,lines,ws,hs=fit(d,text,(x0+3,y0+3,x1-3,y1-3),max_size)
    total=sum(hs)+3*max(0,len(lines)-1); y=y0+(y1-y0-total)/2
    for l,w,h in zip(lines,ws,hs):
        d.text((x0+(x1-x0-w)/2,y),l,font=f,fill='black'); y+=h+3
im=Image.open(root/'0036.jpg').convert('RGB')
repl(im,(175,0,445,95),"cảnh sát tới bắt mình à?",24)
repl(im,(230,830,550,985),"Ha... ở đây có\ncamera an ninh...\nchết tiệt...",23)
repl(im,(180,1380,460,1535),"Mình không thể mất việc này.\nGiờ phải làm sao đây?!",23)
repl(im,(240,1965,480,2095),"Hay quỳ xuống\nvan xin luôn!",24)
repl(im,(120,3270,360,3435),"À... ha ha! Ờm...\nlà con... muỗi mùa đông\nmới xuất hiện ấy...!",20)
repl(im,(355,3560,610,3740),"Tôi nghe nói chúng có thể\ngiết người! Tôi chỉ đang cố\nbắt con muỗi đó...!",19)
repl(im,(130,4540,430,4760),"Tôi xin lỗi!",27)
repl(im,(280,4880,520,5000),"Cậu đang nói cái quái gì vậy,\nđồ ngốc?!",19)
im.save(out/'page-036.webp','WEBP',quality=90,method=6)
