from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np, os
SRC='/mnt/data/stupidemic-relay/ch-200c8c840df0'
OUT='/mnt/data/rendered-r015-020-v4'
os.makedirs(OUT,exist_ok=True)
FONT='/usr/share/fonts/truetype/noto/NotoSansDisplay-ExtraCondensedSemiBold.ttf'
BOLD='/usr/share/fonts/truetype/noto/NotoSansDisplay-ExtraCondensedBlack.ttf'
if not os.path.exists(BOLD): BOLD=FONT

def inpaint_rect(im,roi,radius=3):
    x0,y0,x1,y1=roi
    arr=np.array(im)
    mask=np.zeros(arr.shape[:2],np.uint8); mask[y0:y1,x0:x1]=255
    out=cv2.inpaint(cv2.cvtColor(arr,cv2.COLOR_RGB2BGR),mask,radius,cv2.INPAINT_TELEA)
    im.paste(Image.fromarray(cv2.cvtColor(out,cv2.COLOR_BGR2RGB)))

def clear_white(im,roi):
    ImageDraw.Draw(im).rectangle(roi,fill=(255,255,255))

def fit(draw,text,box,max_size,min_size,font_path=FONT):
    x0,y0,x1,y1=box; W=x1-x0; H=y1-y0
    words=text.split()
    for sz in range(max_size,min_size-1,-1):
        font=ImageFont.truetype(font_path,sz)
        lines=[]; cur=''
        for w in words:
            t=w if not cur else cur+' '+w
            if draw.textbbox((0,0),t,font=font)[2] <= W:
                cur=t
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
        s='\n'.join(lines)
        bb=draw.multiline_textbbox((0,0),s,font=font,spacing=max(2,int(sz*.12)),align='center')
        if bb[2]-bb[0] <= W and bb[3]-bb[1] <= H:
            return s,font
    return text,ImageFont.truetype(font_path,min_size)

def add(im,box,text,fg,max_size=24,min_size=11,bold=False,stroke_width=0,stroke_fill=None):
    d=ImageDraw.Draw(im); s,font=fit(d,text,box,max_size,min_size,BOLD if bold else FONT)
    x0,y0,x1,y1=box
    d.multiline_text(((x0+x1)/2,(y0+y1)/2),s,font=font,fill=fg,anchor='mm',align='center',spacing=max(2,int(font.size*.12)),stroke_width=stroke_width,stroke_fill=stroke_fill)

specs={
15:[
 ('whitebubble',(185,5,430,92),(235,8,475,95),'...NGƯỜI PHẢI CHỊU MỌI PHIỀN PHỨC ĐÂY NÀY...',22),
 ('whitebubble',(410,205,590,285),(385,205,625,305),'CẢM ƠN CÔ VÌ TẤT CẢ.',24),
 ('whitebubble',(150,995,330,1065),(150,940,405,1060),'ANH CÓ BIẾT DÙNG NÃO KHÔNG VẬY?',24),
 ('whitebubble',(355,1235,545,1330),(345,1220,585,1340),'TÔI CŨNG KHÔNG CHẮC.',24),
 ('whitebubble',(165,1930,375,2045),(100,1890,435,2040),'LÚC NHẬN LƯƠNG THÌ NHỚ TIẾT KIỆM LẠI ĐI.',24),
 ('sfx_art',(510,2215,665,2320),(520,2220,660,2305),'QUAY NGƯỜI',24),
 ('whitebubble',(250,3660,510,3810),(205,3615,575,3820),'VÌ DÙ ANH LÀ MỘT THẰNG NGU CHẾT TIỆT, ANH VẪN ĐƯỢC TRẢ LƯƠNG NGANG VỚI MỌI NGƯỜI.',23),
 ('whitebubble',(160,4365,475,4465),(95,4360,495,4540),'QUAY LẠI LÀM VIỆC ĐI. TRÊN ĐƯỜNG VỀ NHỚ RỬA CỐC CỦA TÔI RỒI RÓT ĐẦY CÀ PHÊ.',22)],
16:[
 ('whitebubble',(240,315,375,365),(215,300,405,375),'VÂNG, THƯA CÔ.',24),
 ('sfx_white',(80,1798,220,1862),(80,1800,225,1860),'NHỒM NHOÀM',19),
 ('sfx_art',(420,1890,715,2010),(470,1915,710,1995),'NHỒM NHOÀM',20),
 ('whitebubble',(300,2875,480,2990),(260,2860,515,3000),'ĐỜI THẾ NÀY ĐẾN CHÓ CŨNG THẤY KHỐN NẠN NHỈ?',23),
 ('sfx_art',(60,3290,180,3390),(75,3305,165,3370),'VẪY VẪY',15),
 ('sfx_art',(0,3415,95,3500),(0,3430,85,3490),'VẪY VẪY',14),
 ('whitebubble',(240,3690,475,3825),(175,3655,535,3845),'KHÔNG THỂ TIN NỔI MỘT CON MỤ ĐI LÀM CHỈ ĐỂ MUA SẮM ONLINE LẠI LÀ CẤP TRÊN CỦA MÌNH.',22),
 ('whitebubble',(175,4275,435,4415),(110,4245,510,4420),'NẾU LÀ MÌNH NGÀY TRƯỚC, MÌNH ĐÃ ĐỊT CÔ TA ĐẾN MẤT HỒN RỒI BIẾN MẤT VÀO MỘT BUỔI SÁNG NÀO ĐÓ.',21)],
17:[
 ('whitebubble',(355,775,565,845),(305,775,575,900),'CHẮC CÔ TA NGHĨ MÌNH DỄ BẮT NẠT VÌ MÌNH CỨ NHỊN CÔ TA.',23),
 ('whitebubble',(230,1415,505,1535),(195,1385,520,1575),'HA... MÌNH CHỈ CÒN CÁCH CHỊU ĐỰNG THÔI. CHỈ CẦN TRỤ Ở ĐÂY MỘT NĂM LÀ MỌI KHOẢN NỢ SẼ ĐƯỢC TRẢ HẾT.',22),
 ('whitebubble',(410,2450,565,2535),(375,2420,605,2560),'CHỈ CÒN 11 THÁNG NỮA...',23),
 ('whitebubble',(270,3215,480,3275),(225,3190,535,3360),'ĐỊT MẸ!!! MỚI CÓ MỘT THÁNG THÔI Á?!',24),
 ('sfx_mixed',(335,4180,705,4335),(420,4230,625,4310),'KENG!',30),
 ('whitebubble',(300,4865,445,4940),(245,4795,520,4930),'LÃO GIÀ KEO KIỆT CHẾT TIỆT...',22)],
18:[
 ('whitebubble',(120,5,400,170),(125,25,395,170),'ÔNG ẤY ĐÃ BẢO SẼ TRẢ HẾT MÀ, SAO KHÔNG TRẢ LUÔN MỘT LẦN ĐI CHỨ?',22),
 ('sfx_art',(555,340,715,470),(575,380,700,455),'BỊCH!',24),
 ('whitebubble',(100,1160,375,1310),(95,1150,375,1300),'ÔNG ẤY NÓI GÌ NHỈ? CHỈ CẦN SỐNG CHO RA CON NGƯỜI TRONG MỘT NĂM?',22),
 ('darkbubble',(265,2685,465,2765),(260,2655,495,2800),'CHÚ ƠI, XIN CHÚ... CỨU THẰNG CHÁU NÀY VỚI.',19),
 ('darkbubble',(365,3360,540,3445),(320,3355,535,3485),'NẾU CỨ ĐI RA THẾ NÀY THÌ CHÁU SẼ BỊ GIẾT MẤT...',18),
 ('darkbubble',(225,3615,505,3735),(205,3570,495,3760),'BỌN Ở NGOÀI ĐANG CHỜ NHÉT CHÁU LÊN XE RỒI LÔI ĐI ĐÂU ĐÓ.',18)],
19:[
 ('darkbubble',(210,190,385,265),(220,155,450,275),'CHÁU NÓI THẬT! BỌN CHÚNG ĐANG CHỜ Ở NGOÀI!',19),
 ('darkbubble',(315,400,495,470),(285,350,520,490),'CHÁU CHỈ CẦN MƯỜI... KHÔNG, HAI MƯƠI NGHÌN THÔI...!',18),
 ('darkbubble',(195,1038,380,1090),(205,985,430,1125),'DAEHO, CHÁU CHẮC CHỨ?',20),
 ('darkbubble',(525,1375,605,1410),(510,1400,630,1490),'VÂNG!!!',20),
 ('darkbubble',(270,2150,485,2265),(205,2125,520,2290),'NẾU CHÚ CHO CHÁU VAY, CHÁU NHẤT ĐỊNH SẼ TRẢ...',18),
 ('darkbubble',(285,2918,440,3010),(215,2845,510,3025),'KHÔNG, KHÔNG PHẢI CHUYỆN ĐÓ. CHÁU CHẮC... MÌNH BỎ CỜ BẠC ĐƯỢC CHỨ?',17),
 ('darkbubble',(365,4180,565,4320),(275,4155,545,4345),'NẾU CHÁU BỎ CỜ BẠC MỘT NĂM VÀ HỨA TỪ NAY KHÔNG GÂY CHUYỆN NỮA...',17),
 ('darkbubble',(225,4490,525,4610),(180,4440,565,4645),'TRONG MỘT NĂM ĐÓ CHÚ SẼ TRẢ HẾT NỢ CHO CHÁU. THẾ NÀO? CHÁU LÀM ĐƯỢC KHÔNG?',17)],
20:[
 ('darkbubble',(180,205,395,260),(160,170,430,280),'VÂNG Ạ!!!',22),
 ('darkbubble',(320,1572,485,1607),(205,1565,520,1690),'CHÁU LÀM ĐƯỢC!!!',21),
 ('darkbubble',(245,2298,475,2360),(170,2265,520,2415),'CHÁU SẼ KHÔNG BAO GIỜ CỜ BẠC NỮA!',19),
 ('darkbubble',(210,3752,545,3842),(175,3735,560,3900),'NẾU CHÁU CÒN BƯỚC VÀO SÒNG BẠC LẦN NỮA THÌ CHÁU TỰ KẾT LIỄU ĐỜI MÌNH LUÔN!',17),
 ('darkbubble',(300,4555,425,4610),(260,4530,465,4650),'ĐƯỢC.',21),
 ('darkbubble',(395,4945,545,4998),(330,4900,630,4998),'CHO CHÚ THẤY CHÁU LÀ NGƯỜI THẾ NÀO ĐI.',16)]
}
for pg,items in specs.items():
    im=Image.open(f'{SRC}/{pg:04d}.jpg').convert('RGB')
    for kind,erase,textbox,text,sz in items:
        if kind=='whitebubble':
            clear_white(im,erase); add(im,textbox,text,(15,15,15),max_size=sz)
        elif kind=='darkbubble':
            inpaint_rect(im,erase,3); add(im,textbox,text,(255,255,255),max_size=sz)
        elif kind=='sfx_white':
            clear_white(im,erase); add(im,textbox,text,(20,20,20),max_size=sz,bold=True,stroke_width=1,stroke_fill=(255,255,255))
        elif kind=='sfx_art':
            inpaint_rect(im,erase,3); add(im,textbox,text,(255,255,255),max_size=sz,bold=True,stroke_width=2,stroke_fill=(20,20,20))
        elif kind=='sfx_mixed':
            inpaint_rect(im,erase,3); add(im,textbox,text,(20,20,20),max_size=sz,bold=True,stroke_width=2,stroke_fill=(255,255,255))
    out=f'{OUT}/page-{pg:03d}.webp'; im.save(out,'WEBP',quality=95,method=6); print(out,os.path.getsize(out))
