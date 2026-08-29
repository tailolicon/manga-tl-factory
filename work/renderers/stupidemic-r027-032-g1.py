from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import cv2, numpy as np, hashlib, json, os

ROOT=Path(os.environ['RELAY_DIR'])
OUT=Path(os.environ['OUT_DIR']); OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
FONT_I='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-BoldOblique.ttf'

PAGES={
27:[
(255,75,510,195,'Cậu đang chạy việc cho Aeyeong à?',False),
(505,250,690,350,'À, vâng...',False),
(255,1135,515,1285,'À, Aeyeong... cô ấy thật sự muốn trở thành một trong số bọn tôi, dân văn phòng.',False),
(345,1740,670,1900,'Ơ, ừm... cứ dùng máy lọc nước ở đây là tự nhiên thành nhân viên văn phòng à?',False),
(225,2035,485,2170,'Chắc chị ấy mê văn phòng lắm.',True),
(350,3420,650,3590,'Phải có sự phân biệt chứ.',False),
(285,3985,525,4085,'Người làm ngoài công trường...',False),
(430,4210,665,4335,'đâu giống người làm trong văn phòng.',False),
],
28:[
(180,325,535,445,'Nhưng chị nói nghe như thể bọn tôi chẳng khác gì nhau ấy. Ha ha.',False),
(425,1740,640,1870,'Thôi, làm việc tốt nhé.',False),
(215,2300,490,2460,'Chị cũng vậy.',False),
(325,3460,610,3610,'Phù... Giá mà cấp trên của mình cũng tử tế như chị ấy.',True),
(395,4095,620,4240,'Nhưng sao mình lại thấy bị xúc phạm thế nhỉ...?',True),
],
29:[
(180,105,490,315,'Hmm... chị ấy nói với mình bằng nụ cười rất tươi. Chắc không có ý xúc phạm.',True),
(335,2295,600,2480,'Sao giờ mới về?',False),
(160,2510,445,2675,'Cậu đi pha cà phê hay gì mà lâu thế?',False),
(265,3290,525,3450,'Máy lọc nước hoạt động không ổn nên tôi mới chậm.',False),
(315,3990,555,4140,'Hả? Pha cà phê thì cần nước làm gì?',False),
(465,4865,700,4995,'Cậu không thấy xấu hổ vì vừa phí thời gian à?',False),
],
30:[
(365,475,625,620,'Hả? Cô đang nói gì vậy?',False),
(105,1000,505,1200,'Tôi cho bột cà phê vào như bình thường rồi thêm nước nóng...',False),
(395,2040,625,2185,'Cô ta bị gì vậy?',True),
(380,2590,625,2730,'Trước giờ cậu vẫn cho nước nóng vào à?',False),
(150,2800,455,2970,'Sao cậu còn vênh váo vì phá đồ uống của tôi thế?',False),
(130,4120,235,4225,'???',False),
(185,4300,485,4460,'Bột cà phê thì sao lại không cho nước?',False),
],
31:[
(395,45,610,165,'Sao lại cho nước vào?',False),
(390,1035,640,1175,'Sao cậu còn dám nghịch đồ uống của tôi?',False),
(195,1590,520,1750,'Giờ cô ta tới mức kiếm chuyện chửi bới vô cớ luôn à?',True),
(280,2780,485,2900,'Muốn gây sự chứ gì?',True),
(250,3395,370,3495,'Ha...',False),
(350,4295,645,4470,'Giờ cô bịa chuyện để đối xử với tôi như con chó của cô à?',False),
(245,4870,555,5000,'Bịa chuyện?',False),
],
32:[
(390,115,590,230,'Cậu ngu à?',False),
(455,315,665,455,'Cậu cũng đổ nước vào nước ngọt à?',False),
(185,1030,350,1140,'Hả...?',False),
(180,1735,530,1900,'Cậu phá đồ uống của tôi mà còn chẳng biết xấu hổ.',False),
(375,3405,605,3550,'Mẹ cậu dạy cậu như thế à?',False),
(245,4470,500,4625,'Hôm nay cô ta thật sự quá giới hạn rồi.',True),
],
}

SFX={
27:[(115,300,'NGHIÊNG'),(300,4615,'NẮM')],
28:[(420,3140,'VÚT')],
29:[(435,1390,'CẠCH')],
31:[(225,2295,'THỞ DÀI')],
}

EXTRAS={28:[(142,2525,305,2700,'CHỈ DÀNH CHO\nNHÂN VIÊN\nVĂN PHÒNG')]}

CLEAN_PATCHES={
27:[(190,2065,235,2110),(445,4195,585,4228)],
29:[(135,130,185,230),(445,4905,490,4985)],
30:[(325,2595,390,2695)],
31:[(375,20,545,65),(350,1080,395,1125)],
32:[(350,3410,390,3480),(195,4485,255,4570)],
}

def inpaint_box(im,box):
    x1,y1,x2,y2=box
    arr=np.array(im)
    roi=arr[y1:y2,x1:x2]
    gray=cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY)
    mask=(gray<185).astype(np.uint8)*255
    mask=cv2.dilate(mask,np.ones((3,3),np.uint8),iterations=1)
    cleaned=cv2.inpaint(cv2.cvtColor(roi,cv2.COLOR_RGB2BGR),mask,3,cv2.INPAINT_TELEA)
    arr[y1:y2,x1:x2]=cv2.cvtColor(cleaned,cv2.COLOR_BGR2RGB)
    return Image.fromarray(arr)

def wrap_lines(draw,text,font,maxw):
    words=text.split(); lines=[]; cur=''
    for w in words:
        test=w if not cur else cur+' '+w
        if draw.textbbox((0,0),test,font=font)[2] <= maxw: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def fit_draw(im,box,text,italic=False,minsize=13,maxsize=34):
    x1,y1,x2,y2=box; maxw=x2-x1; maxh=y2-y1
    draw=ImageDraw.Draw(im); fpath=FONT_I if italic else FONT; best=None
    for size in range(maxsize,minsize-1,-1):
        font=ImageFont.truetype(fpath,size); lines=wrap_lines(draw,text,font,maxw-8)
        bbox=draw.textbbox((0,0),'Ag',font=font); lh=(bbox[3]-bbox[1])+4; h=lh*len(lines)
        if h<=maxh-6: best=(font,lines,lh); break
    if best is None:
        font=ImageFont.truetype(fpath,minsize); lines=wrap_lines(draw,text,font,maxw-4); lh=minsize+4
    else: font,lines,lh=best
    total=lh*len(lines); y=y1+(maxh-total)//2
    for line in lines:
        bb=draw.textbbox((0,0),line,font=font); w=bb[2]-bb[0]; x=x1+(maxw-w)//2
        draw.text((x,y),line,font=font,fill='black',stroke_width=1,stroke_fill='white'); y+=lh

def draw_sfx(im,x,y,text):
    d=ImageDraw.Draw(im); font=ImageFont.truetype(FONT,22)
    d.text((x,y),text,font=font,fill='white',stroke_width=3,stroke_fill='black')

def draw_extra(im,box,text):
    d=ImageDraw.Draw(im); d.rounded_rectangle(box,radius=4,fill=(245,245,245),outline=None)
    fit_draw(im,box,text,False,11,20)

manifest=[]
for p,items in PAGES.items():
    im=Image.open(ROOT/f'{p:04d}.jpg').convert('RGB')
    for x1,y1,x2,y2,text,thought in items:
        im=inpaint_box(im,(x1,y1,x2,y2)); fit_draw(im,(x1,y1,x2,y2),text,thought)
    for x,y,t in SFX.get(p,[]): draw_sfx(im,x,y,t)
    for x1,y1,x2,y2,t in EXTRAS.get(p,[]): draw_extra(im,(x1,y1,x2,y2),t)
    for box in CLEAN_PATCHES.get(p,[]): im=inpaint_box(im,box)
    out=OUT/f'page-{p:03d}.webp'; im.save(out,'WEBP',quality=82,method=6)
    b=out.read_bytes(); manifest.append({'page':p,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'width':im.width,'height':im.height})
print(json.dumps(manifest,ensure_ascii=False,indent=2))
