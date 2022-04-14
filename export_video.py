#!/usr/bin/env python
# coding: utf-8
edtion = 'alpha 1.8.7'

# 外部参数输入

import argparse
import sys
import os

ap = argparse.ArgumentParser(description="Export MP4 video from timeline file.")
ap.add_argument("-l", "--TimeLine", help='Timeline (and break_point with same name), which was generated by replay_generator.py.',type=str)
ap.add_argument("-d", "--MediaObjDefine", help='Definition of the media elements, using real python code.',type=str)
ap.add_argument("-t", "--CharacterTable", help='This program do not need CharacterTable.',type=str)
ap.add_argument("-o", "--OutputPath", help='Choose the destination directory to save the project timeline and break_point file.',type=str,default=None)
# 增加一个，读取时间轴和断点文件的选项！
ap.add_argument("-F", "--FramePerSecond", help='Set the FPS of display, default is 30 fps, larger than this may cause lag.',type=int,default=30)
ap.add_argument("-W", "--Width", help='Set the resolution of display, default is 1920, larger than this may cause lag.',type=int,default=1920)
ap.add_argument("-H", "--Height", help='Set the resolution of display, default is 1080, larger than this may cause lag.',type=int,default=1080)
ap.add_argument("-Z", "--Zorder", help='Set the display order of layers, not recommended to change the values unless necessary!',type=str,
                default='BG3,BG2,BG1,Am3,Am2,Am1,Bb')
ap.add_argument("-Q", "--Quality", help='Choose the quality (ffmpeg crf) of output video.',type=int,default=24)
args = ap.parse_args()

media_obj = args.MediaObjDefine #媒体对象定义文件的路径
char_tab = args.CharacterTable #角色和媒体对象的对应关系文件的路径
stdin_log = args.TimeLine #log路径
output_path = args.OutputPath #保存的时间轴，断点文件的目录

screen_size = (args.Width,args.Height) #显示的分辨率
frame_rate = args.FramePerSecond #帧率 单位fps
zorder = args.Zorder.split(',') #渲染图层顺序

crf = args.Quality # 导出视频的质量值

try:
    for path in [stdin_log,media_obj]:
        if path == None:
            print(path)
            raise OSError("[31m[ArgumentError]:[0m Missing principal input argument!")
        if os.path.isfile(path) == False:
            raise OSError("[31m[ArgumentError]:[0m Cannot find file "+path)

    if output_path == None:
        pass 
    elif os.path.isdir(output_path) == False:
        try:
            os.makedirs(output_path)
        except:
            raise OSError("[31m[SystemError]:[0m Cannot make directory "+output_path)
    output_path = output_path.replace('\\','/')

    # FPS
    if frame_rate <= 0:
        raise ValueError("[31m[ArgumentError]:[0m "+str(frame_rate))
    elif frame_rate>30:
        print("[33m[warning]:[0m",'FPS is set to '+str(frame_rate)+', which may cause lag in the display!')

    if (screen_size[0]<=0) | (screen_size[1]<=0):
        raise ValueError("[31m[ArgumentError]:[0m "+str(screen_size))
    if screen_size[0]*screen_size[1] > 3e6:
        print("[33m[warning]:[0m",'Resolution is set to more than 3M, which may cause lag in the display!')
except Exception as E:
    print(E)
    sys.exit()

import pandas as pd
import numpy as np
import pygame
import ffmpeg
import pydub
import time
import glob # 匹配路径
import re

# 类定义 alpha 1.8.4

# 文字对象
class Text:
    pygame.font.init()
    def __init__(self,fontfile='./media/SourceHanSansCN-Regular.otf',fontsize=40,color=(0,0,0,255),line_limit=20):
        self.text_render = pygame.font.Font(fontfile,fontsize)
        self.color=color
        self.size=fontsize
        self.line_limit = line_limit
    def render(self,tx):
        face = self.text_render.render(tx,True,self.color[0:3])
        if self.color[3] < 255:
            face.set_alpha(self.color[3])
        return face
    def draw(self,text):
        out_text = []
        if ('#' in text) | (text[0]=='^'): #如果有手动指定的换行符 # bug:如果手动换行，但是第一个#在30字以外，异常的显示
            if text[0]=='^': # 如果使用^指定的手动换行，则先去掉这个字符。
                text = text[1:]
            text_line = text.split('#')
            for tx in text_line:
                out_text.append(self.render(tx))
        elif len(text) > self.line_limit: #如果既没有主动指定，字符长度也超限
            for i in range(0,len(text)//self.line_limit+1):#较为简单粗暴的自动换行
                out_text.append(self.render(text[i*self.line_limit:(i+1)*self.line_limit]))
        else:
            out_text = [self.render(text)]
        return out_text
    def convert(self):
        pass

# 描边文本，是Text的子类。注意，使用这个媒体类可能会影响帧率！
class StrokeText(Text):
    pygame.font.init()
    def __init__(self,fontfile='./media/SourceHanSansCN-Regular.otf',fontsize=40,color=(0,0,0,255),line_limit=20,edge_color=(255,255,255,255)):
        super().__init__(fontfile=fontfile,fontsize=fontsize,color=color,line_limit=line_limit) # 继承
        self.edge_color=edge_color
    def render(self,tx):
        edge = self.text_render.render(tx,True,self.edge_color[0:3])
        face = self.text_render.render(tx,True,self.color[0:3])
        if self.edge_color[3] < 255:
            edge.set_alpha(self.edge_color[3])
        if self.color[3] < 255:
            face.set_alpha(self.color[3])
        canvas = pygame.Surface((edge.get_size()[0]+2,edge.get_size()[1]+2),pygame.SRCALPHA)
        for pos in [(0,0),(0,1),(0,2),(1,0),(1,2),(2,0),(2,1),(2,2)]:
            canvas.blit(edge,pos)
        canvas.blit(face,(1,1))
        return canvas

# 对话框、气泡、文本框
class Bubble:
    def __init__(self,filepath,Main_Text=Text(),Header_Text=None,pos=(0,0),mt_pos=(0,0),ht_pos=(0,0),align='left',line_distance=1.5):
        self.media = pygame.image.load(filepath)
        self.pos = pos
        self.MainText = Main_Text
        self.mt_pos = mt_pos
        self.Header = Header_Text
        self.ht_pos = ht_pos
        if line_distance > 1:
            self.line_distance = line_distance
        elif line_distance > 0:
            print("[33m[warning]:[0m",'Line distance is set to less than 1!')
        else:
            raise MediaError('[31m[BubbleError]:[0m', 'Invalid line distance:',line_distance)
        if align in ('left','center'):
            self.align = align
        else:
            raise MediaError('[31m[BubbleError]:[0m', 'Unsupported align:',align)
    def display(self,surface,text,header='',alpha=100,adjust='NA'):
        if adjust in ['0,0','NA']:
            render_pos = self.pos
        else:
            adx,ady = split_xy(adjust)
            render_pos = (self.pos[0]+adx,self.pos[1]+ady)
        temp = self.media.copy()
        if (self.Header!=None) & (header!=''):    # Header 有定义，且输入文本不为空
            temp.blit(self.Header.draw(header)[0],self.ht_pos)
        x,y = self.mt_pos
        for i,s in enumerate(self.MainText.draw(text)):
            if self.align == 'left':
                temp.blit(s,(x,y+i*self.MainText.size*self.line_distance))
            else: # 就只可能是center了
                word_w,word_h = s.get_size()
                temp.blit(s,(x+(self.MainText.size*self.MainText.line_limit - word_w)//2,y+i*self.MainText.size*self.line_distance))
        if alpha !=100:
            temp.set_alpha(alpha/100*255)            
        surface.blit(temp,render_pos)
    def convert(self):
        self.media = self.media.convert_alpha()

# 背景图片
class Background:
    def __init__(self,filepath,pos = (0,0)):
        if filepath in cmap.keys(): #添加了，对纯色定义的背景的支持
            self.media = pygame.surface.Surface(screen_size)
            self.media.fill(cmap[filepath])
        else:
            self.media = pygame.image.load(filepath)
        self.pos = pos
    def display(self,surface,alpha=100,adjust='NA'):
        if adjust in ['0,0','NA']:
            render_pos = self.pos
        else:
            adx,ady = split_xy(adjust)
            render_pos = (self.pos[0]+adx,self.pos[1]+ady)
        if alpha !=100:
            temp = self.media.copy()
            temp.set_alpha(alpha/100*255)
            surface.blit(temp,render_pos)
        else:
            surface.blit(self.media,render_pos)
    def convert(self):
        self.media = self.media.convert_alpha()

# 这个是真的动画了，用法和旧版的amination是一样的！
class Animation:
    def __init__(self,filepath,pos = (0,0),tick=1,loop=True):
        file_list = np.frompyfunc(lambda x:x.replace('\\','/'),1,1)(glob.glob(filepath))
        self.length = len(file_list)
        if self.length == 0:
            raise MediaError('[31m[AnimationError]:[0m','Cannot find file match',filepath)
        self.media = np.frompyfunc(pygame.image.load,1,1)(file_list)
        self.pos = pos
        self.loop = loop
        self.this = 0
        self.tick = tick
    def display(self,surface,alpha=100,adjust='NA',frame=0):
        self.this = frame
        if adjust in ['0,0','NA']:
            render_pos = self.pos
        else:
            adx,ady = split_xy(adjust)
            render_pos = (self.pos[0]+adx,self.pos[1]+ady)
        if alpha !=100:
            temp = self.media[int(self.this)].copy()
            temp.set_alpha(alpha/100*255)
            surface.blit(temp,render_pos)
        else:
            surface.blit(self.media[int(self.this)],render_pos)
    def get_tick(self,duration): # 1.8.0
        if self.length > 1: # 如果length > 1 说明是多帧的动画！
            tick_lineline = (np.arange(0,duration if self.loop else self.length,1/self.tick)[0:duration]%(self.length))
            tick_lineline = np.hstack([tick_lineline,(self.length-1)*np.ones(duration-len(tick_lineline))]).astype(int)
        else:
            tick_lineline = np.zeros(duration).astype(int)
        return tick_lineline
    def convert(self):
        self.media = np.frompyfunc(lambda x:x.convert_alpha(),1,1)(self.media)

# a1.7.5 内建动画，Animation类的子类
class BuiltInAnimation(Animation):
    def __init__(self,anime_type='hitpoint',anime_args=('0',0,0,0),screensize = (1920,1080),layer=0):
        BIA_text = Text('./media/SourceHanSerifSC-Heavy.otf',fontsize=int(0.0521*screensize[0]),color=(255,255,255,255),line_limit=10)
        if anime_type == 'hitpoint': # anime_args=('0',0,0,0)
            # 载入图片
            heart = pygame.image.load('./media/heart.png')
            heart_shape = pygame.image.load('./media/heart_shape.png')
            hx,hy = heart.get_size()
            # 重设图片尺寸，根据screensize[0]
            if screensize[0]!=1920:
                multip = screensize[0]/1920
                heart = pygame.transform.scale(heart,(int(hx*multip),int(hy*multip)))
                heart_shape = pygame.transform.scale(heart_shape,(int(hx*multip),int(hy*multip)))
                hx,hy = heart.get_size()
            # 动画参数
            name_tx,heart_max,heart_begin,heart_end = anime_args

            if (heart_end==heart_begin)|(heart_max<max(heart_begin,heart_end)):
                raise MediaError('[31m[BIAnimeError]:[0m','Invalid argument',name_tx,heart_max,heart_begin,heart_end,'for BIAnime hitpoint!')
            elif heart_end > heart_begin: # 如果是生命恢复
                temp = heart_end
                heart_end = heart_begin
                heart_begin = temp # 则互换顺序 确保 begin一定是小于end的
                heal_heart = True
            else:
                heal_heart = False

            distance = int(0.026*screensize[0]) # default = 50

            total_heart = int(heart_max/2 * hx + max(0,np.ceil(heart_max/2-1)) * distance) #画布总长
            left_heart = int(heart_end/2 * hx + max(0,np.ceil(heart_end/2-1)) * distance) #画布总长
            lost_heart = int((heart_begin-heart_end)/2 * hx + np.floor((heart_begin-heart_end)/2) * distance)

            nametx_surf = BIA_text.draw(name_tx)[0] # 名牌
            nx,ny = nametx_surf.get_size() # 名牌尺寸
            # 开始制图
            if layer==0: # 底层 阴影图
                self.pos = ((screensize[0]-max(nx,total_heart))/2,(4/5*screensize[1]-hy-ny)/2)
                canvas = pygame.Surface((max(nx,total_heart),hy+ny+screensize[1]//5),pygame.SRCALPHA)
                canvas.fill((0,0,0,0))
                if nx > total_heart:
                    canvas.blit(nametx_surf,(0,0))
                    posx = (nx-total_heart)//2
                else:
                    canvas.blit(nametx_surf,((total_heart-nx)//2,0))
                    posx = 0
                posy = ny+screensize[1]//5
                self.tick = 1
                self.loop = 1
                for i in range(1,heart_max+1): # 偶数，低于最终血量
                    if i%2 == 0:
                        canvas.blit(heart_shape,(posx,posy))
                        posx = posx + hx + distance
                    else:
                        pass
                if heart_max%2 == 1: # max是奇数
                    left_heart_shape = heart_shape.subsurface((0,0,int(hx/2),hy))
                    canvas.blit(left_heart_shape,(total_heart-int(hx/2),posy))
            elif layer==1: # 剩余的血量
                self.pos = ((screensize[0]-total_heart)/2,3/5*screensize[1]+ny/2-hy/2)
                canvas = pygame.Surface((left_heart,hy),pygame.SRCALPHA)
                canvas.fill((0,0,0,0))
                posx,posy = 0,0
                self.tick = 1
                self.loop = 1
                for i in range(1,heart_end+1): # 偶数，低于最终血量
                    if i%2 == 0:
                        canvas.blit(heart,(posx,posy))
                        posx = posx + hx + distance
                    else:
                        pass
                if heart_end%2 == 1: # end是奇数
                    left_heart = heart.subsurface((0,0,int(hx/2),hy))
                    canvas.blit(left_heart,(heart_end//2*(hx + distance),0))
            elif layer==2: # 损失/恢复的血量
                self.pos = (heart_end//2*(hx + distance)+(heart_end%2)*int(hx/2)+(screensize[0]-total_heart)/2,3/5*screensize[1]+ny/2-hy/2)
                canvas = pygame.Surface((lost_heart,hy),pygame.SRCALPHA)
                canvas.fill((0,0,0,0))
                posx,posy = 0,0
                self.tick = 1
                self.loop = 1
                for i in range(1,heart_begin-heart_end+1): 
                    if (i == 1)&(heart_end%2 == 1): # 如果end是奇数，先来半个右边
                        right_heart = heart.subsurface((int(hx/2),0,int(hx/2),hy))
                        canvas.blit(right_heart,(posx,posy))
                        posx = posx + int(hx/2) + distance
                    elif ((i - heart_end%2)%2 == 0): # 如果和end的差值是
                        canvas.blit(heart,(posx,posy))
                        posx = posx + hx + distance
                    elif (i == heart_begin-heart_end)&(heart_begin%2 == 1): # 如果最右边边也是半个心
                        left_heart = heart.subsurface((0,0,int(hx/2),hy))
                        canvas.blit(left_heart,(posx,posy))
                    else:
                        pass
            else:
                pass
            if (heal_heart == True)&(layer == 2): # 恢复动画
                crop_timeline = sigmoid(0,lost_heart,frame_rate).astype(int) # 裁剪时间线
                self.media = np.frompyfunc(lambda x:canvas.subsurface(0,0,x,hy),1,1)(crop_timeline) # 裁剪动画
            else:
                self.media=np.array([canvas]) # 正常的输出，单帧
            #剩下的需要定义的
            self.this = 0
            self.length=len(self.media)
        if anime_type == 'dice': # anime_args=('name',max,check,face) #骰子
            def get_possible_digit(dice_max):
                dice_max = 10**(int(np.log10(dice_max))+1)-1
                possible = {}
                for i in range(0,100):
                    if dice_max//(10**i)>=10:
                        possible[i] = list(range(0,10))
                    elif dice_max//(10**i)>=1:
                        possible[i] = list(range(0,1+dice_max//(10**i)))
                    else:
                        break
                dice_value = np.repeat('',10)
                for i in possible.keys():
                    digit = np.array(possible[i])
                    np.random.shuffle(digit) # 乱序
                    if len(digit)<10:
                        digit = np.hstack([digit,np.repeat('',10-len(digit))])
                    dice_value = np.frompyfunc(lambda x,y:x+y,2,1)(digit.astype(str),dice_value)
                return max(possible.keys())+1,dice_value
            # 动画参数
            # 检查参数合法性
            for die in anime_args:
                try:
                    # 转换为int类型，NA转换为-1
                    name_tx,dice_max,dice_check,dice_face = die
                    dice_max,dice_face,dice_check = map(lambda x:-1 if x=='NA' else int(x),(dice_max,dice_face,dice_check))
                except ValueError as E: #too many values to unpack,not enough values to unpack
                    raise MediaError('[31m[BIAnimeError]:[0m','Invalid syntax:',str(die),E)
                if (dice_face>dice_max)|(dice_check<-1)|(dice_check>dice_max)|(dice_face<=0)|(dice_max<=0):
                    raise MediaError('[31m[BIAnimeError]:[0m','Invalid argument',name_tx,dice_max,dice_check,dice_face,'for BIAnime dice!')
            # 最多4个
            N_dice = len(anime_args)
            if N_dice > 4:
                N_dice=4
                anime_args = anime_args[0:4]# 最多4个
            #y_anchor = {4:180,3:270,2:360,1:450}[N_dice] # sep=180 x[600,1400]
            y_anchor = {4:int(0.1667*screensize[1]),3:int(0.25*screensize[1]),2:int(0.3333*screensize[1]),1:int(0.4167*screensize[1])}[N_dice]
            y_unit = int(0.1667*screensize[1])
            if layer==0: # 底层 名字 /检定
                canvas = pygame.Surface(screensize,pygame.SRCALPHA)
                for i,die in enumerate(anime_args): 
                    name_tx,dice_max,dice_check,dice_face = die
                    dice_max,dice_face,dice_check = map(lambda x:-1 if x=='NA' else int(x),(dice_max,dice_face,dice_check))
                    # 渲染
                    name_surf = BIA_text.render(name_tx)
                    nx,ny = name_surf.get_size()
                    canvas.blit(name_surf,(int(0.3125*screensize[0])-nx//2,y_anchor+i*y_unit+(y_unit-ny)//2)) # 0.3125*screensize[0] = 600
                    if dice_check != -1:
                        check_surf = BIA_text.render('/%d'%dice_check)
                        cx,cy = check_surf.get_size()
                        canvas.blit(check_surf,(int(0.7292*screensize[0]),y_anchor+i*y_unit+(y_unit-ny)//2)) # 0.7292*screensize[0] = 1400
                self.media = np.array([canvas])
                self.pos = (0,0)
                self.tick = 1
                self.loop = 1
            elif layer==1:
                #画布
                canvas = []
                for i in range(0,int(2.5*frame_rate)):
                    canvas_frame = pygame.Surface((int(0.1458*screensize[0]),y_unit*N_dice),pygame.SRCALPHA) # 0.1458*screensize[0] = 280
                    canvas.append(canvas_frame)
                # 骰子
                for l,die in enumerate(anime_args): 
                    name_tx,dice_max,dice_check,dice_face = die
                    dice_max,dice_face,dice_check = map(lambda x:-1 if x=='NA' else int(x),(dice_max,dice_face,dice_check))
                    cols,possible_digit = get_possible_digit(dice_max)
                    dx,dy = BIA_text.render('0'*cols).get_size()
                    # running cols
                    run_surf = pygame.Surface((dx,dy*len(possible_digit)),pygame.SRCALPHA)
                    for i,digit in enumerate(possible_digit):
                        for j,char in enumerate(digit): # alpha 1.8.4 兼容非等宽数字，比如思源宋体
                            char_this = BIA_text.render(char)
                            run_surf.blit(char_this,(j*(dx//cols),dy*i))
                    run_cols = np.frompyfunc(lambda x:run_surf.subsurface(x*(dx//cols),0,dx//cols,dy*10),1,1)(np.arange(0,cols))
                    # range
                    slot_surf = []
                    for i in range(0,int(2.5*frame_rate)):
                        slot_frame = pygame.Surface((dx,dy),pygame.SRCALPHA)
                        slot_surf.append(slot_frame)
                    for i in range(0,cols):
                        if cols == 1:
                            speed_multiplier = 1
                        else:
                            speed_multiplier = np.linspace(2,1,cols)[i]
                        speed = speed_multiplier*dy*11/2.5/frame_rate
                        for t in range(0,int(2.5*frame_rate/speed_multiplier)):
                            slot_surf[t].blit(run_cols[i],(i*dx//cols,int(dy-t*speed)))
                    for t in range(0,int(2.5*frame_rate/speed_multiplier)):
                        #canvas[t].blit(slot_surf[t],(int(0.1458*screensize[0]-dx-0.0278*screensize[1]),(l+1)*y_unit-dy-int(0.0278*screensize[1]))) #0.0278*screensize[1] = 30
                        canvas[t].blit(slot_surf[t],(int(0.1458*screensize[0]-dx-0.0278*screensize[1]),l*y_unit+(y_unit-dy)//2))
                self.media = np.array(canvas)
                self.pos = (int(0.5833*screensize[0]),y_anchor)
                self.tick = 1
                self.loop = 1
            elif layer==2:
                dice_cmap={3:(124,191,85,255),1:(94,188,235,255),0:(245,192,90,255),2:(233,86,85,255),-1:(255,255,255,255)}
                canvas = pygame.Surface((int(0.1458*screensize[0]),y_unit*N_dice),pygame.SRCALPHA)
                for i,die in enumerate(anime_args): 
                    name_tx,dice_max,dice_check,dice_face = die
                    dice_max,dice_face,dice_check = map(lambda x:-1 if x=='NA' else int(x),(dice_max,dice_face,dice_check))
                    # 渲染 0.0651
                    significant = 0.05 # 大成功失败阈值
                    if dice_check == -1:
                        color_flag = -1
                    else:
                        color_flag = ((dice_face/dice_max<=significant)|(dice_face/dice_max>(1-significant)))*2 + (dice_face<=dice_check)
                    BIA_color_Text = Text('./media/SourceHanSerifSC-Heavy.otf',fontsize=int(0.0651*screensize[0]),color=dice_cmap[color_flag],line_limit=10) # 1.25
                    face_surf = BIA_color_Text.render(str(dice_face))
                    fx,fy = face_surf.get_size()
                    #canvas.blit(face_surf,(int(0.1458*screensize[0]-fx-0.0278*screensize[1]),(i+1)*y_unit-fy-int(0.0278*screensize[1])))
                    canvas.blit(face_surf,(int(0.1458*screensize[0]-fx-0.0278*screensize[1]),i*y_unit+(y_unit-fy)//2))
                self.media = np.array([canvas])
                self.pos = (int(0.5833*screensize[0]),y_anchor) # 0.5833*screensize[0] = 1120
                self.tick = 1
                self.loop = 1
            else:
                pass
            self.this = 0
            self.length=len(self.media)

# 音效
class Audio:
    def __init__(self,filepath):
        self.media = pydub.AudioSegment.from_file(filepath)
    def convert(self):
        pass

# 背景音乐
class BGM:
    def __init__(self,filepath,volume=100,loop=True):
        self.media = pydub.AudioSegment.from_file(filepath) + np.log10(volume/100) * 20 # 调整音量
        self.loop = loop
    def convert(self):
        pass

# 异常定义

class ParserError(Exception):
    def __init__(self,*description):
        self.description = ' '.join(map(str,description))
    def __str__(self):
        return self.description

class MediaError(ParserError):
    pass

# 处理bg 和 am 的parser
def parse_timeline(layer):
    global timeline,break_point
    track = render_timeline[[layer]]
    clips = []
    item,begin,end = 'NA',0,0
    for key,values in track.iterrows():
        #如果item变化了，或者进入了指定的断点
        if (values[layer] != item) | (key in break_point.values): 
            if (item == 'NA') | (item!=item): # 如果itme是空 
                pass # 则不输出什么
            else:
                end = key #否则把当前key作为一个clip的断点
                clips.append((item,begin,end)) #并记录下这个断点
            item = values[layer] #无论如何，重设item和begin
            begin = key
        else: #如果不满足断点要求，那么就什么都不做
            pass
    # 循环结束之后，最后检定一次是否需要输出一个clips
    end = key
    if (item == 'NA') | (item!=item):
        pass
    else:
        clips.append((item,begin,end))
    return clips #返回一个clip的列表

def normalized(X):
    if len(X)>=2:
        return (X-X.min())/(X.max()-X.min())
    else:
        return X/X # 兼容 持续时间被设置为0，1等极限情况

def sigmoid(begin,end,dur,K=5):
    return normalized(1/(1+np.exp(np.linspace(K,-K,int(dur)))))*(end-begin)+begin

def split_xy(concated):
    x,y = concated.split(',')
    return int(x),int(y)

def render(this_frame):
    global zorder,media_list
    for layer in zorder:
        # 不渲染的条件：图层为"Na"，或者np.nan
        if (this_frame[layer]=='NA')|(this_frame[layer]!=this_frame[layer]):
            continue
        elif this_frame[layer+'_a']<=0: #或者图层的透明度小于等于0(由于fillna("NA"),出现的异常)
            continue
        elif this_frame[layer] not in media_list:
            raise RuntimeError('[31m[RenderError]:[0m Undefined media object : "'+this_frame[layer]+'".')
            continue
        elif layer[0:2] == 'BG':
            try:
                exec('{0}.display(surface=screen,alpha={1},adjust={2})'.format(this_frame[layer],this_frame[layer+'_a'],'\"'+this_frame[layer+'_p']+'\"'))
            except Exception:
                raise RuntimeError('[31m[RenderError]:[0m Failed to render "'+this_frame[layer]+'" as Background.')
        elif layer[0:2] == 'Am': # 兼容H_LG1(1)这种动画形式 alpha1.6.3
            try:
                exec('{0}.display(surface=screen,alpha={1},adjust={2},frame={3})'.format(
                                                                                         this_frame[layer],
                                                                                         this_frame[layer+'_a'],
                                                                                         '\"'+this_frame[layer+'_p']+'\"',
                                                                                         this_frame[layer+'_t']))
            except Exception:
                raise RuntimeError('[31m[RenderError]:[0m Failed to render "'+this_frame[layer]+'" as Animation.')
        elif layer == 'Bb':
            try:
                exec('{0}.display(surface=screen,text={2},header={3},alpha={1},adjust={4})'.format(this_frame[layer],
                                                                                                   this_frame[layer+'_a'],
                                                                                                   '\"'+this_frame[layer+'_main']+'\"',
                                                                                                   '\"'+this_frame[layer+'_header']+'\"',
                                                                                                   '\"'+this_frame[layer+'_p']+'\"'))
            except Exception:
                raise RuntimeError('[31m[RenderError]:[0m Failed to render "'+this_frame[layer]+'" as Bubble.')
    return 1

# 被占用的变量名 # 1.7.7
occupied_variable_name = open('./media/occupied_variable_name.list','r',encoding='utf8').read().split('\n')

# Main():

print('[export Video]: Welcome to use exportVideo for TRPG-replay-generator '+edtion)
print('[export Video]: The output mp4 file will be saved at "'+output_path+'"')

# 载入timeline 和 breakpoint
render_timeline = pd.read_pickle(stdin_log)
break_point = pd.read_pickle(stdin_log.replace('timeline','breakpoint'))
bulitin_media = pd.read_pickle(stdin_log.replace('timeline','bulitinmedia'))
stdin_name = stdin_log.replace('\\','/').split('/')[-1]

cmap = {'black':(0,0,0,255),'white':(255,255,255,255),'greenscreen':(0,177,64,255)}

# 载入od文件
try:
    object_define_text = open(media_obj,'r',encoding='utf-8').read()#.split('\n')
except UnicodeDecodeError as E:
    print('[31m[DecodeError]:[0m',E)
    sys.exit()
if object_define_text[0] == '\ufeff': # 139 debug
    print('[33m[warning]:[0m','UTF8 BOM recognized in MediaDef, it will be drop from the begin of file!')
    object_define_text = object_define_text[1:]
object_define_text = object_define_text.split('\n')

media_list=[]
for i,text in enumerate(object_define_text):
    if text == '':
        continue
    elif text[0] == '#':
        continue
    else:
        try:
            exec(text) #对象实例化
            obj_name = text.split('=')[0]
            obj_name = obj_name.replace(' ','')
            if obj_name in occupied_variable_name:
                raise SyntaxError('Obj name occupied')
            elif (len(re.findall('\w+',obj_name))==0)|(obj_name[0].isdigit()):
                raise SyntaxError('Invalid Obj name')
            media_list.append(obj_name) #记录新增对象名称
        except Exception as E:
            print('[31m[SyntaxError]:[0m "'+text+'" appeared in media define file line ' + str(i+1)+' is invalid syntax:',E)
            sys.exit()
black = Background('black')
white = Background('white')
media_list.append('black')
media_list.append('white')
# alpha 1.6.5 载入导出的内建媒体
for key,values in bulitin_media.iteritems():
    exec(values)
    media_list.append(key)

# 合成音轨

print('[export Video]: Start mixing audio tracks')

tracks = ['SE','Voice','BGM']
main_Track = pydub.AudioSegment.silent(duration=int(break_point.values.max()/frame_rate*1000),frame_rate=16000) # 主轨道

for tr in tracks:
    this_Track = pydub.AudioSegment.silent(duration=int(break_point.values.max()/frame_rate*1000),frame_rate=16000)
    if tr == 'BGM':
        BGM_clips = parse_timeline('BGM')
        for i,item in enumerate(BGM_clips):
            voice,begin,drop = item
            if voice == 'stop':
                continue # 遇到stop，直切切到下一段
            elif voice not in media_list: # 如果是路径形式
                temp_BGM = BGM(voice[1:-1]) # 去除引号
                voice = 'temp_BGM'
            try:
                end = BGM_clips[i+1][1]
            except IndexError:
                end = break_point.values.max()
            #print(begin,end)
            this_Track = this_Track.overlay(pydub.AudioSegment.silent(duration=int((end-begin)/frame_rate*1000),
                                                              frame_rate=16000).overlay(eval(voice+'.media')
                                                                                        ,loop=True),
                                    position = int(begin/frame_rate*1000))
    else:
        for item in parse_timeline(tr):
            voice,begin,drop = item
            if voice not in media_list: # 如果是路径形式
                temp_AU = Audio(voice[1:-1]) # 去除引号
                voice = 'temp_AU'
            this_Track = this_Track.overlay(eval(voice+'.media'),position = int(begin/frame_rate*1000))
    main_Track = main_Track.overlay(this_Track) #合成到主音轨

main_Track.export(output_path+'/'+stdin_name+'.mp3',format='mp3',codec='mp3')

print('[export Video]: Audio mixing done!')

# 初始化

print('[export Video]: Start encoding video, using ffmpeg.')

pygame.init()
screen = pygame.display.set_mode(screen_size,pygame.HIDDEN)

# 转换媒体对象
for media in media_list: 
    try:
        exec(media+'.convert()')
    except Exception as E:
        print('[31m[MediaError]:[0m Exception during converting',media,':',E)
        sys.exit()

# ffmpeg输出
output_engine = (
    ffmpeg
    .input('pipe:',format='rawvideo',r=frame_rate,pix_fmt='rgb24', s='{0}x{1}'.format(screen_size[1],screen_size[0])) # 视频来源
    .output(ffmpeg.input(output_path+'/'+stdin_name+'.mp3').audio,
            output_path+'/'+stdin_name+'.mp4',
            pix_fmt='yuv420p',r=frame_rate,crf=crf,
            **{'loglevel':'quiet','vf':'transpose=0'}) # 输出
    .overwrite_output()
    .run_async(pipe_stdin=True)
)

begin_time = time.time()
# 主循环
n=0
while n < break_point.max():
    try:
        if n in render_timeline.index:
            this_frame = render_timeline.loc[n]
            render(this_frame)
            obyte = pygame.surfarray.array3d(screen).tobytes()
        else:
            pass # 节约算力
        output_engine.stdin.write(obyte) # 写入视频
        n = n + 1 #下一帧
    except Exception as E:
        print(E)
        print('[31m[RenderError]:[0m','Render exception at frame:',n)
        output_engine.stdin.close()
        pygame.quit()
        sys.exit()
    if n%frame_rate == 1:
        finish_rate = n/break_point.values.max()
        print('[export Video]:','[{0}] {1},\t{2}'.format(int(finish_rate*50)*'#'+(50-int(50*finish_rate))*' ',
                                                        '%.1f'%(finish_rate*100)+'%','{0}/{1}'.format(n,'%d'%break_point.values.max())),
        end = "\r"
        )
    elif n == break_point.values.max():
        print('[export Video]:','[{0}] {1},\t{2}'.format(50*'#',
                                                        '%.1f'%100+'%','{0}/{1}'.format(n,n)))
output_engine.stdin.close()
pygame.quit()

used_time = time.time()-begin_time

print('[export Video]: Export time elapsed : '+time.strftime("%H:%M:%S", time.gmtime(used_time)))
print('[export Video]: Mean frames rendered per second : '+'%.2f'%(break_point.max()/used_time)+' FPS')
print('[export Video]: Encoding finished! Video path :',output_path+'/'+stdin_name+'.mp4')

sys.exit()
