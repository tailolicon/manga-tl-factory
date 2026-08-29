from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import hashlib
SRC=Path('relay/ch-200c8c840df0')
OUT=Path('projects/mangadistrict-com-title-stupidemic-uncensored/chapters/ch-200c8c840df0/rendered'); OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSans-CondensedBold.ttf'
S={
1:[((210,2190,500,2380),'Trên mảnh đất rẻ nhất và hẻo lánh nhất đất nước này...',25),((375,3430,610,3600),'Một nhà máy đã được xây dựng.',25),((280,4090,620,4350),'Đây là bộ phận quản lý sản xuất của Tập đoàn Best Wood, một công ty chết tiệt... à nhầm, một công ty nhỏ...',20)],
2:[((180,100,540,340),'Công ty này tin rằng chỉ những kẻ không tin nhau mới cần viết hợp đồng.',24),((215,1050,510,1230),'Haizz... Sao ông ta không thể cử mình đến thành phố chứ...?',22),((100,1300,390,1510),'Cái vùng quê chết tiệt này... Không thể tin được là mình phải ở đây tận một năm.',20),((260,2490,620,2735),'Một cuộc sống chẳng có chút tiến triển nào, chỉ biết cắn răng chịu đựng... Ừ, đó chính là đời mình.',20),((135,3190,470,3450),'Mình cứ tưởng khi dịch bệnh kết thúc thì mình sẽ được tự do.',21),((370,3930,630,4110),'Rốt cuộc đời mình đã thành ra thế quái nào vậy?',20)],
3:[((160,585,390,770),'Ồ, chào! Daeho!',24),((65,1070,400,1320),'Hôm nay cậu định trốn việc ở đây à?',23),((405,1910,685,2150),'Bà chủ bảo tôi đi cho chó ăn. Cậu làm xong việc chưa?',20),((135,2410,395,2640),'Chưa. Tôi bỏ ra đây vì mệt quá thôi.',21),((350,2580,680,2840),'Thằng nhóc này... cậu mắc cái virus gây ra “CID” à?',20),((305,3530,640,3740),'Cậu sẽ chọc giận bà chủ đấy.',22),((140,4070,420,4310),'Con mụ sếp ấy hả? Chỉ cần tôi nói thế này là bà ta bỏ qua ngay...',19),((45,4250,275,4460),'Em xin lũiii!',24)],
4:[((185,30,385,190),'Ừ, phải rồi. Hahaha.',22),((320,370,670,620),'Rõ ràng là bà ấy chỉ tránh cậu vì trông cậu giống bệnh nhân CID thôi.',20),((300,990,570,1170),'Thôi nào ông anh. CID xảy ra từ đời nào rồi.',21),((230,1810,545,1970),'Với lại, cậu chưa từng thấy bệnh nhân CID à?',20),((360,2030,625,2190),'Trông họ bình thường vãi ra.',21),((235,2430,500,2580),'Cậu từng thấy rồi à?',21),((80,2600,400,2790),'Bị nhiễm virus là nhà chức trách đưa đi ngay mà, đúng không?',19),((365,3630,665,3870),'Tôi nghe nói bệnh nhân CID bắt đầu chảy dãi rồi nói nhảm...',20),((185,4280,535,4500),'Ồ... cậu chưa từng thấy ai thật à? Họ không chảy dãi.',20),((85,4520,420,4760),'Còn vụ nói nhảm... chỉ là cảm giác như họ không biết mình đang nói gì thôi.',19)],
5:[((340,805,660,970),'Loại virus đó làm suy giảm nhận thức.',22),((180,1050,540,1260),'Vì thế họ rất dễ tin vào những chuyện vô lý.',22),((140,1620,380,1770),'Ý cậu là sao?',24),((155,2730,445,2940),'Nói tiếng người đi, nhóc.',22),((345,4220,595,4410),'Nhớ ông đó không?',22),((165,4400,590,4660),'Ông già trước đây làm bên xây dựng ấy? Một hôm, ông ta đến gặp bà chủ rồi nói...',19)],
6:[((100,50,600,280),'Tôi sẽ đưa cô cả ngày lương! Đổi lại cho tôi làm tình với cô!',23),((60,480,335,660),'Rồi ông ta chộp lấy cặp vú bự của bà ấy!',21),((360,1480,665,1730),'Cái đéo gì vậy?! Hahahahaha! Thế mới gọi là đàn ông chứ! Haha!',20),((185,2140,545,2360),'Bà chủ hét đến khản cả giọng rồi gọi cảnh sát.',21),((375,2430,600,2580),'Lúc đó náo loạn cả lên.',22),((65,3470,400,3690),'Thế ông già đó có bị bắt không?',22),((100,3970,550,4240),'À, bà ấy không kiện vì sếp lớn bảo nên bỏ qua cho ông ta.',20),((190,4270,630,4540),'Nhưng ông ta vẫn bị đuổi việc. Thế mà hôm sau, vợ ông ta tới, nhìn thẳng vào bà chủ rồi nói...',19)],
7:[((135,710,435,865),'“Ừ, ngực cô bự thật đấy!”',22),((195,900,580,1125),'“Đến tôi còn muốn sờ nữa! Tha cho ông ấy đi nhé?!” Haha!',20),((175,1620,380,1765),'Kekekeke. Buồn cười thật.',21),((380,1800,690,1970),'Ừ, và hóa ra...',21),((240,2010,590,2240),'hai người đó cư xử như vậy vì đã nhiễm virus.',20),((100,2790,420,3040),'Tôi vẫn không hiểu loại virus này hoạt động kiểu gì.',21),((275,4240,545,4460),'Hả?! Anh ta vừa cúp máy với mình à?',20),((115,4790,620,5000),'Đừng bảo tôi là cậu mắc...',20)],
8:[((90,10,360,150),'...virus nhé, ông anh.',21),((270,725,565,955),'Bệnh nhân CID gặp khó khăn trong việc hiểu—',20),((80,1400,290,1560),'Địt mẹ cậu. Hahaha.',22),((380,2030,655,2240),'Tôi đời nào mắc thứ virus như thế.',21),((95,2720,415,2990),'Nhưng... cách những người này suy nghĩ là...',21),((260,4010,570,4260),'Dù có bảo ngày mai tận thế, họ cũng sẽ tin cậu.',20),((225,4650,640,4890),'Nghe đơn giản vãi. Cậu nghĩ nếu mắc CID thì bọn mình có bị đuổi việc không?',19)],
}
SFX={2:[(220,4585,'HAIZZ...',48,(105,105,120),7,(255,255,255))]}

def cover_sfx(im,box,text,fill=(20,20,20),stroke=(255,255,255),stroke_width=12):
    x0,y0,x1,y1=box; W=x1-x0; H=y1-y0
    f=ImageFont.truetype(FONT,96)
    tmp=Image.new('RGBA',(800,220),(0,0,0,0)); d=ImageDraw.Draw(tmp)
    bb=d.textbbox((0,0),text.upper(),font=f,stroke_width=stroke_width)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    glyph=Image.new('RGBA',(tw+stroke_width*4,th+stroke_width*4),(0,0,0,0)); gd=ImageDraw.Draw(glyph)
    gd.text((stroke_width*2-bb[0],stroke_width*2-bb[1]),text.upper(),font=f,fill=fill,stroke_width=stroke_width,stroke_fill=stroke)
    glyph=glyph.resize((W,H),Image.Resampling.LANCZOS)
    im.paste(glyph,(x0,y0),glyph)

SFX_COVER={
5:[((475,2018,665,2148),'VÚT',(20,20,20),(255,255,255),14),((160,3248,340,3380),'VÚT',(90,80,80),(255,255,255),14)],
6:[((270,745,475,925),'NGOẮC',(15,15,15),(255,255,255),20),((520,835,710,980),'NGOẮC',(15,15,15),(255,255,255),14),((285,3135,465,3315),'RÈ',(15,15,15),(255,255,255),15),((465,3155,645,3340),'RÈ',(15,15,15),(255,255,255),15),((325,4835,530,5000),'RÈ',(15,15,15),(255,255,255),15)],
7:[((290,0,480,115),'RÈ',(15,15,15),(255,255,255),15),((110,25,310,160),'RÈ',(15,15,15),(255,255,255),15),((465,115,690,285),'RÈ',(15,15,15),(255,255,255),15),((55,205,315,370),'RÈ',(15,15,15),(255,255,255),15),((255,2275,400,2455),'XÌ',(105,55,45),(255,255,255),14),((350,2345,510,2535),'XÌ',(105,55,45),(255,255,255),14),((35,3660,245,3840),'RENG',(40,40,40),(255,255,255),14),((115,3780,270,3930),'RENG',(40,40,40),(255,255,255),14),((205,3915,390,4115),'BÍP',(20,20,20),(255,255,255),14)],
8:[((5,3075,340,3340),'HỪ',(100,95,115),(250,252,255),15),((395,3625,640,3870),'HỪ',(100,95,115),(245,250,255),15)]
}

def fit(draw,text,box,max_size,min_size=13):
    x0,y0,x1,y1=box; W=x1-x0; H=y1-y0; text=text.upper()
    for size in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(FONT,size); words=text.split(); lines=[]; cur=''
        for w in words:
            t=w if not cur else cur+' '+w
            if draw.textlength(t,font=f)<=W: cur=t
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
        a,d=f.getmetrics(); lh=a+d+3; total=lh*len(lines)-3
        if total<=H and all(draw.textlength(l,font=f)<=W for l in lines): return f,lines,lh,total
    f=ImageFont.truetype(FONT,min_size); return f,[text],min_size+5,min_size+5

def block(im,box,text,size):
    d=ImageDraw.Draw(im); d.rectangle(box,fill='white')
    f,lines,lh,total=fit(d,text,box,size); x0,y0,x1,y1=box; y=y0+(y1-y0-total)/2
    for line in lines:
        tw=d.textlength(line,font=f); d.text((x0+(x1-x0-tw)/2,y),line,font=f,fill=(15,15,15)); y+=lh

def sfx(im,it):
    x,y,text,size,fill,sw,sfill=it; d=ImageDraw.Draw(im); f=ImageFont.truetype(FONT,size)
    d.text((x,y),text.upper(),font=f,fill=fill,stroke_width=sw,stroke_fill=sfill)

for i in range(1,9):
    im=Image.open(SRC/f'{i:04d}.jpg').convert('RGB')
    for box,text,size in S[i]: block(im,box,text,size)
    if i==7:
        ImageDraw.Draw(im).rectangle((330,0,480,45),fill=(22,22,27))
    if i==8:
        d8=ImageDraw.Draw(im)
        d8.rectangle((135,0,430,64),fill='white')
        d8.rounded_rectangle((10,3140,70,3245),radius=18,fill=(245,250,252))
        d8.rounded_rectangle((385,3735,430,3830),radius=15,fill=(220,240,250))
    if i==7:
        d=ImageDraw.Draw(im); d.rounded_rectangle((285,214,472,274),radius=6,fill=(100,170,205)); f=ImageFont.truetype(FONT,20); t='CON MỤ'; tw=d.textlength(t,font=f); d.text((378-tw/2,228),t,font=f,fill='white')
    if i==8:
        box=(395,3100,715,3500); im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(radius=17)),box)
        d=ImageDraw.Draw(im); f=ImageFont.truetype(FONT,38)
        for t,y in [('ĐỒ ĂN!!!',3140),('CỨT!!!',3250),('VÚ!!!',3360)]: d.text((425,y),t,font=f,fill=(20,20,20),stroke_width=4,stroke_fill='white')
    if i<5:
        for it in SFX.get(i,[]): sfx(im,it)
    else:
        for it in SFX_COVER.get(i,[]): cover_sfx(im,*it)
    out=OUT/f'page-{i:03d}.webp'; im.save(out,'WEBP',quality=82,method=6)
    print(i,out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
