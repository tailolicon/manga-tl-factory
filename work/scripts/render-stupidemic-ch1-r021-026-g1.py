from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import numpy as np, cv2, hashlib
SRC=Path('relay/ch-200c8c840df0')
OUT=Path('projects/mangadistrict-com-title-stupidemic-uncensored/chapters/ch-200c8c840df0/rendered'); OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'
def F(n): return ImageFont.truetype(FONT,n)

def fit(draw,text,box,max_size,min_size=11,stroke=0):
    x0,y0,x1,y1=box; W=x1-x0; H=y1-y0; words=text.split()
    for sz in range(max_size,min_size-1,-1):
        f=F(sz); lines=[]; cur=''
        for w in words:
            t=w if not cur else cur+' '+w
            if draw.textbbox((0,0),t,font=f,stroke_width=stroke)[2]<=W: cur=t
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
        a,d=f.getmetrics(); lh=a+d+2; total=lh*len(lines)-2
        if total<=H and all(draw.textbbox((0,0),l,font=f,stroke_width=stroke)[2]<=W for l in lines):
            return f,lines,lh,total
    return F(min_size),[text],min_size+4,min_size+4

def inpaint(im,box,mode='dark',dilate=5):
    arr=np.array(im.convert('RGB')); x0,y0,x1,y1=map(int,box); roi=arr[y0:y1,x0:x1]
    hsv=cv2.cvtColor(roi,cv2.COLOR_RGB2HSV); gray=cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY)
    h,s,v=cv2.split(hsv)
    if mode=='dark': mask=gray<135
    elif mode=='bright': mask=(gray>150)&(s<150)
    elif mode=='orange': mask=(h<25)&(s>70)&(v>90)
    elif mode=='brown': mask=(h<30)&(s>35)&(v>55)&(v<245)
    elif mode=='cyan': mask=(h>75)&(h<110)&(s>45)&(v>80)
    elif mode=='pink': mask=((h<10)|(h>155))&(s>35)&(v>85)
    elif mode=='both': mask=(gray>155)|(gray<85)
    else: mask=np.ones_like(gray,dtype=bool)
    m=(mask.astype('uint8')*255)
    if dilate>1: m=cv2.dilate(m,np.ones((dilate,dilate),np.uint8),iterations=1)
    clean=cv2.inpaint(cv2.cvtColor(roi,cv2.COLOR_RGB2BGR),m,3,cv2.INPAINT_TELEA)
    arr[y0:y1,x0:x1]=cv2.cvtColor(clean,cv2.COLOR_BGR2RGB)
    im.paste(Image.fromarray(arr))

def inpaint_bright_text(im,box,dilate=9):
    arr=np.array(im.convert('RGB')); x0,y0,x1,y1=map(int,box); roi=arr[y0:y1,x0:x1]
    hsv=cv2.cvtColor(roi,cv2.COLOR_RGB2HSV); gray=cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY); h,s,v=cv2.split(hsv)
    mask=((gray>205)&(s<90)).astype('uint8')*255
    if dilate>1: mask=cv2.dilate(mask,np.ones((dilate,dilate),np.uint8),iterations=1)
    clean=cv2.inpaint(cv2.cvtColor(roi,cv2.COLOR_RGB2BGR),mask,3,cv2.INPAINT_TELEA)
    arr[y0:y1,x0:x1]=cv2.cvtColor(clean,cv2.COLOR_BGR2RGB)
    im.paste(Image.fromarray(arr))

def draw_text(im,box,text,max_size,fg,stroke=0,stroke_fill=(255,255,255)):
    d=ImageDraw.Draw(im); f,lines,lh,total=fit(d,text,box,max_size,stroke=stroke); x0,y0,x1,y1=box; y=y0+(y1-y0-total)/2
    for line in lines:
        bb=d.textbbox((0,0),line,font=f,stroke_width=stroke); tw=bb[2]-bb[0]
        d.text((x0+(x1-x0-tw)/2,y),line,font=f,fill=fg,stroke_width=stroke,stroke_fill=stroke_fill); y+=lh

def bubble(im,box,text,max_size=20,fg=(15,15,15),erase='dark',dilate=5):
    inpaint(im,box,erase,dilate); draw_text(im,box,text,max_size,fg,0)

def sfx(im,box,text,max_size,fg,stroke_fill,erase='bright',dilate=9,stroke=4):
    if erase: inpaint(im,box,erase,dilate)
    draw_text(im,box,text,max_size,fg,stroke,stroke_fill)

def fill_text(im,box,text,max_size,fill,fg):
    ImageDraw.Draw(im).rectangle(box,fill=fill); draw_text(im,box,text,max_size,fg)

for pg in range(21,27):
    im=Image.open(SRC/f'{pg:04d}.jpg').convert('RGB')
    if pg==21:
        bubble(im,(215,1390,505,1570),'ĐỪNG GIỐNG CHA CHÁU.',23,(255,255,255),'bright',7)
        bubble(im,(65,2940,390,3210),'Không thể tin ông ấy lại đem mình so với cha... chết tiệt.',18,(15,15,15),'dark',5)
        bubble(im,(345,4160,635,4370),'Lão khốn đó cá ngựa làm cả nhà phá sản, rồi còn treo cổ tự tử.',17,(15,15,15),'dark',5)
        sfx(im,(470,4850,695,5000),'LIẾC',38,(255,255,255),(20,20,20),'bright',15,5)
    elif pg==22:
        bubble(im,(355,120,505,255),'HẢ?',25,(15,15,15),'dark',5)
        sfx(im,(175,815,560,1005),'THẮNG!',60,(255,255,255),(45,80,35),'bright',13,5)
        d=ImageDraw.Draw(im); d.rounded_rectangle((78,1580,662,1825),radius=16,fill=(246,232,214)); draw_text(im,(95,1610,645,1795),'CHÚC MỪNG',47,(240,120,35),2,(255,255,255))
        d.rectangle((25,2240,342,2378),fill=(255,255,255)); draw_text(im,(35,2250,335,2368),'ĐƯỢC RỒI!',41,(165,85,50),0)
        bubble(im,(305,2485,635,2730),'ĐÚNG RỒI!!! MÌNH THẮNG RỒI!!!',20,(15,15,15),'dark',5)
        d=ImageDraw.Draw(im); d.rounded_rectangle((420,3715,690,3875),radius=18,fill=(50,50,58)); draw_text(im,(435,3735,675,3855),'BẬT!',38,(220,220,228),2,(20,20,25))
        bubble(im,(75,4495,420,4745),'Điên thật. Mình đoán đúng ba lần liên tiếp rồi. Vậy nếu đúng thêm lần nữa thì tiền sẽ lại nhân đôi à?',16,(15,15,15),'dark',5)
    elif pg==23:
        bubble(im,(315,700,600,960),'Chết tiệt...! Chú ơi!!! Thằng cháu Lee Daeho này sẽ nhân số tiền ấy lên rồi tự tay trả hết nợ!',15,(15,15,15),'dark',5)
        bubble(im,(145,1785,355,1905),'Làm sao đây? Hay cược 100 đô thôi?',17,(255,255,255),'bright',7)
        bubble(im,(365,2550,625,2690),'Nhưng đoán đúng thì tiền nhân đôi. Hay chơi luôn 1.000 đô?',16,(255,255,255),'bright',7)
        bubble(im,(205,3590,455,3720),'Mày còn chẳng có nổi 1.000 đô.',18,(15,15,15),'dark',5)
        bubble(im,(345,3800,630,4020),'Cứ an toàn, cược 100 đô thôi! Đúng thì 100 cũng thành 200 mà.',16,(15,15,15),'dark',5)
        d=ImageDraw.Draw(im); d.rectangle((10,3968,350,4098),fill=(255,255,255)); draw_text(im,(20,3980,340,4088),'KHÀ KHÀ KHÀ',29,(25,25,25),3,(255,255,255))
        d.rectangle((475,4130,715,4258),fill=(50,115,198)); draw_text(im,(485,4140,705,4248),'KHÀ KHÀ',27,(25,25,25),3,(255,255,255))
        fill_text(im,(218,4445,302,4518),'CHẠM',19,(90,43,88),(255,255,255))
        d=ImageDraw.Draw(im); d.polygon([(315,4785),(545,4785),(615,4870),(545,4955),(320,4955),(275,4870)],fill=(185,255,190)); draw_text(im,(315,4810,575,4930),'THẮNG!',45,(255,255,255),4,(70,120,70))
    elif pg==24:
        bubble(im,(105,475,530,735),'ARGH!!! CHẾT TIỆT!!! Lẽ ra mình phải cược 1.000 đô!',22,(15,15,15),'dark',5)
        bubble(im,(215,1915,635,2195),'Mình đã có thể thắng 2.000 đô! Thế là vừa mất toi 1.000 đô!',19,(15,15,15),'dark',5)
        for box in [(330,2600,485,2715),(145,2740,280,2848),(42,2900,185,3008),(82,3110,215,3215),(492,3325,635,3440),(365,3410,515,3520)]:
            inpaint_bright_text(im,box,9); draw_text(im,box,'RÈ',29,(240,240,245),4,(65,65,80))
        bubble(im,(320,3650,600,3865),'Hừ. Ai phá chuỗi may mắn của mình thế?',18,(15,15,15),'dark',5)
        bubble(im,(145,4315,465,4535),'Con mụ chết tiệt. Để xem rồi biết tay.',18,(15,15,15),'dark',5)
        bubble(im,(380,4700,455,4780),'NÀY!',15,(15,15,15),'dark',4)
        bubble(im,(440,4740,555,4840),'CẬU ĐANG Ở—',14,(15,15,15),'dark',4)
    elif pg==25:
        bubble(im,(425,25,680,180),'Vâng, cô Kim! Tôi đang tới đây! Vâng, tôi lấy cà phê rồi—',16,(15,15,15),'dark',5)
        bubble(im,(150,915,575,1180),'Mình sẽ ăn một mẻ lớn rồi chuồn khỏi chỗ này trước khi phải mục xương ở đây đủ một năm.',17,(15,15,15),'dark',5)
        bubble(im,(245,2480,625,2760),'Sao cô ta dùng cái cốc quê mùa này nhỉ? Đằng nào cà phê cũng nguội. Dùng cốc giấy luôn có phải hơn không.',15,(15,15,15),'dark',5)
        sfx(im,(155,2740,395,2920),'LẦM BẦM',26,(60,60,70),(255,255,255),'dark',11,3)
        bubble(im,(150,3900,370,4025),'Cô nghĩ tôi sẽ rửa cốc cho cô chắc?',17,(15,15,15),'dark',5)
        bubble(im,(315,4125,530,4265),'Uống thứ được phục vụ đi, con mụ.',17,(15,15,15),'dark',5)
        sfx(im,(165,4625,415,4745),'RÓC RÁCH',27,(80,190,210),(255,255,255),'cyan',11,3)
        d=ImageDraw.Draw(im); d.rectangle((320,4780,545,4915),fill=(242,241,238)); draw_text(im,(327,4790,538,4905),'CHỈ DÀNH CHO NHÂN VIÊN VĂN PHÒNG',14,(205,85,100),0)
    elif pg==26:
        sfx(im,(380,125,570,285),'BƯỚC',29,(230,230,235),(50,50,55),'bright',13,4)
        bubble(im,(150,515,420,690),'Hửm? Daeho? Cậu đang dùng máy lọc nước à?',18,(15,15,15),'dark',5)
        bubble(im,(295,1070,620,1290),'Nhưng cái này dành cho nhân viên văn phòng mà.',18,(15,15,15),'dark',5)
        sfx(im,(490,1495,680,1635),'RẠNG RỠ',25,(245,125,165),(255,255,255),'dark',7,3)
        bubble(im,(165,2660,550,2910),'Là chị kế toán. Cứ gặp chị ấy là cả ngày mình gặp may.',18,(15,15,15),'dark',5)
        bubble(im,(95,3370,410,3600),'À, máy lọc nước bên công trường không ra nước nóng nên tôi mới qua đây.',16,(15,15,15),'dark',5)
        bubble(im,(365,3615,595,3790),'Ra vậy. Cậu nên sửa nó đi.',17,(15,15,15),'dark',5)
        bubble(im,(80,4460,390,4670),'Không biết hôm nay mình sẽ gặp may kiểu gì đây.',17,(15,15,15),'dark',5)
    out=OUT/f'page-{pg:03d}.webp'; im.save(out,'WEBP',quality=84,method=6)
    print(pg,out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
