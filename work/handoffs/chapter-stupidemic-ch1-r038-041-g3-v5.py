from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import cv2, numpy as np, hashlib, json
SRC=Path('/mnt/data/stupidemic_relay/ch-200c8c840df0'); OUT=Path('/mnt/data/r038_041_g3_v5'); OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSans-ExtraCondensedBold.ttf'
P={
38:[
('C-cái quái gì vậy?!\nThật sự có muỗi độc à?',(320,325,585,435),(225,285,610,465),28,'white'),
('Khoan... dù thật sự có...\nmình vừa tát cô ta\nmột cú trời giáng...',(205,1330,455,1465),(175,1295,505,1515),25,'white'),
('ĐỒ ĂN!!!\nCỨT!!!\nVÚ!!!',(405,2115,655,2405),(400,2110,650,2415),38,'sfx38'),
('Đúng là kiểu người\ndù bảo ngày mai tận thế\ncũng tin sái cổ.',(325,3045,575,3190),(245,3020,610,3230),24,'gray'),
('Hả...? Cô ta\nnhiễm virus rồi à?',(275,3595,480,3720),(235,3560,535,3750),25,'white'),
('Này, lấy cho tôi\ncái gì để lau đi.',(185,4610,375,4730),(145,4585,435,4775),25,'white'),
],
39:[
('Chắc không...?\nTrông cô ta vẫn bình thường...',(315,780,520,890),(240,730,565,925),24,'white'),
('Không... nãy cô ta còn\nlàm ầm lên chuyện mình\ncho nước vào cà phê...',(250,1240,470,1420),(205,1200,485,1460),22,'white'),
('Giờ cô ta cũng đang\nhành xử kỳ quặc.',(420,1480,585,1620),(390,1450,620,1665),22,'white'),
('Nếu cô ta thật sự\nnhiễm virus...',(315,2500,500,2630),(245,2470,545,2670),24,'white'),
('Cô Kim! Nó bay vào\ngiữa hai chân cô rồi!!',(285,3300,500,3470),(220,3240,550,3520),25,'white'),
('C-cái gì?!\nỞ đâu?!',(135,3635,290,3760),(100,3595,320,3805),26,'white'),
('Nó bay lên trong...',(265,4905,515,5000),(200,4880,555,5000),25,'white'),
],
40:[
('váy của cô! Dang chân ra!\nTôi bắt nó cho!!',(205,0,525,110),(135,0,590,210),25,'white'),
('Cậu thấy nó không? Thấy không?\nMau bắt nó đi!!',(360,575,585,760),(300,525,620,810),23,'white'),
('Ơ, tôi không thấy!\nDang rộng hơn nữa\nđể tôi tìm!!',(185,1945,525,2135),(115,1900,595,2205),24,'white'),
('Ha...!',(380,2875,530,2995),(335,2835,555,3025),25,'white'),
('CƯỜI NHẾCH',(380,3000,550,3180),(360,2995,565,3195),27,'smirk'),
('Nhìn cô ta kìa...',(275,3855,495,4005),(220,3810,545,4030),25,'white'),
('Cậu làm gì thế?!\nMau bắt nó đi!!!',(205,4435,445,4635),(145,4400,495,4670),24,'white'),
],
41:[
('Con mụ này nhiễm virus thật rồi.\nKhà khà.',(255,1375,500,1530),(170,1320,555,1585),25,'white'),
]
}

def erase(im, box, mode):
    arr=np.array(im)
    x1,y1,x2,y2=box; roi=arr[y1:y2,x1:x2].copy()
    if mode=='white':
        gray=cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY)
        m=(gray<248).astype(np.uint8)*255
        m=cv2.dilate(m,np.ones((3,3),np.uint8),iterations=1)
        roi[m>0]=255
        arr[y1:y2,x1:x2]=roi
        return Image.fromarray(arr)
    if mode=='gray':
        gray=cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY)
        m=(gray<170).astype(np.uint8)*255
        m=cv2.dilate(m,np.ones((3,3),np.uint8),iterations=1)
        roi[m>0]=np.array([183,183,183],dtype=np.uint8)
        arr[y1:y2,x1:x2]=roi
        return Image.fromarray(arr)
    bgr=cv2.cvtColor(arr,cv2.COLOR_RGB2BGR); roi_b=bgr[y1:y2,x1:x2]
    if mode=='sfx38':
        g=cv2.cvtColor(roi_b,cv2.COLOR_BGR2GRAY)
        m=((g<170)|(g>240)).astype(np.uint8)*255
        m=cv2.dilate(m,np.ones((5,5),np.uint8),iterations=2)
    else:
        hsv=cv2.cvtColor(roi_b,cv2.COLOR_BGR2HSV)
        m=(hsv[:,:,1]>38).astype(np.uint8)*255
        m=cv2.dilate(m,np.ones((7,7),np.uint8),iterations=2)
    mask=np.zeros(bgr.shape[:2],np.uint8); mask[y1:y2,x1:x2]=m
    out=cv2.inpaint(bgr,mask,4,cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(out,cv2.COLOR_BGR2RGB))

def fit(draw,text,box,maxs,stroke=0):
    x1,y1,x2,y2=box; bw=x2-x1; bh=y2-y1
    for s in range(maxs,14,-1):
        f=ImageFont.truetype(FONT,s); lines=[]
        for para in text.split('\n'):
            cur=''
            for w in para.split():
                cand=(cur+' '+w).strip(); bb=draw.textbbox((0,0),cand,font=f,stroke_width=stroke)
                if bb[2]-bb[0] <= bw*.93: cur=cand
                else:
                    if cur: lines.append(cur)
                    cur=w
            if cur: lines.append(cur)
        sp=max(2,int(s*.15)); hs=[]; ws=[]
        for ln in lines:
            bb=draw.textbbox((0,0),ln,font=f,stroke_width=stroke); ws.append(bb[2]-bb[0]); hs.append(bb[3]-bb[1])
        th=sum(hs)+sp*max(0,len(lines)-1)
        if max(ws or [0])<=bw*.95 and th<=bh*.76: return f,lines,sp,hs,th
    f=ImageFont.truetype(FONT,15); lines=text.split('\n'); hs=[draw.textbbox((0,0),ln,font=f)[3] for ln in lines]; return f,lines,2,hs,sum(hs)+2*(len(lines)-1)

def render(i):
    im=Image.open(SRC/f'{i:04d}.jpg').convert('RGB')
    for t,e,b,ms,m in P[i]: im=erase(im,e,m)
    d=ImageDraw.Draw(im)
    for t,e,b,ms,m in P[i]:
        sfx=m in ('sfx38','smirk'); stroke=2 if sfx else 0; fill='white' if sfx else 'black'; sf='black' if sfx else None
        f,lines,sp,hs,th=fit(d,t,b,ms,stroke); x1,y1,x2,y2=b; y=y1+(y2-y1-th)//2
        for ln,h in zip(lines,hs):
            bb=d.textbbox((0,0),ln,font=f,stroke_width=stroke); w=bb[2]-bb[0]; x=x1+(x2-x1-w)//2
            d.text((x,y),ln,font=f,fill=fill,stroke_width=stroke,stroke_fill=sf); y+=h+sp
    out=OUT/f'page-{i:03d}.webp'; im.save(out,'WEBP',quality=55,method=6)
    data=out.read_bytes(); return {'page_index':i,'file':str(out),'width':im.width,'height':im.height,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
print(json.dumps([render(i) for i in (38,39,40,41)],ensure_ascii=False,indent=2))
