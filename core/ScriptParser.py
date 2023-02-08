#!/usr/bin/env python
# coding: utf-8
# 标记语言 <-> json{dic}

import numpy as np
import pandas as pd

import os
import json

from .Exceptions import DecodeError,ParserError,WarningPrint,SyntaxsError
from .Regexs import *
from .Formulas import *
from .Medias import Text,StrokeText,Bubble,Balloon,DynamicBubble,ChatWindow,Animation,GroupedAnimation,BuiltInAnimation,Background,BGM,Audio
from .FreePos import Pos,FreePos,PosGrid
from .FilePaths import Filepath
from .ProjConfig import Config
from .Motion import MotionMethod

# 输入文件，基类
class Script:
    # 类型名对应的Class
    Media_type = {
        'Pos':Pos,'FreePos':FreePos,'PosGrid':PosGrid,
        'Text':Text,'StrokeText':StrokeText,
        'Bubble':Bubble,'Balloon':Balloon,'DynamicBubble':DynamicBubble,'ChatWindow':ChatWindow,
        'Animation':Animation,'GroupedAnimation':GroupedAnimation,'BuiltInAnimation':BuiltInAnimation,
        'Background':Background,
        'BGM':BGM,'Audio':Audio
        }
    # 类型名对应的参数列表
    type_keyword_position = {'Pos':['pos'],'FreePos':['pos'],'PosGrid':['pos','end','x_step','y_step'],
                            'Text':['fontfile','fontsize','color','line_limit','label_color'],
                            'StrokeText':['fontfile','fontsize','color','line_limit','edge_color','edge_width','projection','label_color'],
                            'Bubble':['filepath','scale','Main_Text','Header_Text','pos','mt_pos','ht_pos','ht_target','align','line_distance','label_color'],
                            'Balloon':['filepath','scale','Main_Text','Header_Text','pos','mt_pos','ht_pos','ht_target','align','line_distance','label_color'],
                            'DynamicBubble':['filepath','scale','Main_Text','Header_Text','pos','mt_pos','mt_end','ht_pos','ht_target','fill_mode','fit_axis','line_distance','label_color'],
                            'ChatWindow':['filepath','scale','sub_key','sub_Bubble','sub_Anime','sub_align','pos','sub_pos','sub_end','am_left','am_right','sub_distance','label_color'],
                            'Background':['filepath','scale','pos','label_color'],
                            'Animation':['filepath','scale','pos','tick','loop','label_color'],
                            'Audio':['filepath','label_color'],
                            'BGM':['filepath','volume','loop','label_color']}
    # 初始化
    def __init__(self,string_input=None,dict_input=None,file_input=None,json_input=None) -> None:
        # 字符串输入
        if string_input is not None:
            self.struct:dict = self.parser(script=string_input)
        # 字典 输入：不安全的方法
        elif dict_input is not None:
            self.struct:dict = dict_input
        # 如果输入了脚本文件
        elif file_input is not None:
            self.struct:dict = self.parser(script=self.load_file(filepath=file_input))
        # 如果输入了json文件：不安全的方法
        elif json_input is not None:
            self.struct:dict = self.load_json(filepath=json_input)
        # 如果没有输入
        else:
            self.struct:dict = {}
    # 读取文本文件
    def load_file(self,filepath:str)->str:
        try:
            stdin_text = open(filepath,'r',encoding='utf-8').read()
        except UnicodeDecodeError as E:
            raise DecodeError('DecodeErr',E)
        # 清除 UTF-8 BOM
        if stdin_text[0] == '\ufeff':
            print(WarningPrint('UFT8BOM'))
            stdin_text = stdin_text[1:]
        return stdin_text
    # 将读取的文本文件解析为json
    def load_json(self,filepath:str)->dict:
        return json.loads(self.load_file(filepath=filepath))
    # 保存为文本文件
    def dump_file(self,filepath:str)->None:
        list_of_scripts = self.export()
        with open(filepath,'w',encoding='utf-8') as of:
            of.write(list_of_scripts)
    # 保存为json
    def dump_json(self,filepath:str)->None:
        with open(filepath,'w',encoding='utf-8') as of:
            of.write(json.dumps(self.struct,indent=4))
    # 待重载的：
    def parser(self,script:str)->dict:
        return {}
    def export(self)->str:
        return ''

# 媒体定义文件
class MediaDef(Script):
    def __init__(self, string_input=None, dict_input=None, file_input=None, json_input=None) -> None:
        super().__init__(string_input, dict_input, file_input, json_input)
        # 媒体的相对位置@
        if file_input is not None:
            Filepath.Mediapath = os.path.dirname(file_input.replace('\\','/'))
        elif json_input is not None:
            Filepath.Mediapath = os.path.dirname(json_input.replace('\\','/'))
    # MDF -> struct
    def list_parser(self,list_str:str)->list:
        # 列表，元组，不包含外括号
        list_str = list_str.replace(' ','')
        values = re.findall("(\w+\(\)|\[[-\w,.\ ]+\]|\([-\d,.\ ]+\)|\w+\[[\d\,]+\]|[^,()]+)",list_str)
        this_list = []
        for value in values:
            this_list.append(self.value_parser(value))
        return this_list
    def subscript_parser(self,obj_name:str,sub_indexs:str)->dict:
        # Object[1,2]
        this_subscript = {'type':'subscript','object':'$'+obj_name}
        this_subscript['index'] = self.list_parser(sub_indexs)
        return this_subscript
    def value_parser(self,value:str):
    # 数值、字符串、列表、实例化、subs、对象
        # 1. 是数值
        if re.match('^-?[\d\.]+(e-?\d+)?$',value):
            if '.' in value:
                return float(value)
            else:
                return int(value)
        # 2. 是字符串
        elif re.match('^(\".+\"|\'.+\')$',value):
            return value[1:-1]
        # 3. 是列表或者元组：不能嵌套！
        elif re.match('^\[.+\]|\(.+\)$',value):
            return self.list_parser(value[1:-1])
        # 4. 是另一个实例化: Class()
        elif re.match('^[a-zA-Z_]\w*\(.*\)$',value):
            obj_type,obj_value = re.findall('^([a-zA-Z_]\w*)\((.*)\)$',string=value)[0]
            return self.instance_parser(obj_type,obj_value)
        # 5. 是一个subscript: Obj[1]
        elif re.match('^\w+\[[\d\, ]+\]$',value):
            obj_name,sub_indexs = re.findall('(\w+)\[([\d\, ]+)\]$',string=value)[0]
            return self.subscript_parser(obj_name,sub_indexs)
        # 6. 是特殊的常量
        elif value in ('False','True','None'):
            return {'False':False,'True':True,'None':None}[value]
        # 7. 是一个对象名 Obj
        elif re.match('^\w*$',value) and value[0].isdigit()==False:
            return '$' + value
        else:
            raise SyntaxsError('InvExp',value)
    def instance_parser(self,obj_type:str,obj_args:str)->dict:
        # 实例化
        this_instance = {'type':obj_type}
        # Pos 类型
        if obj_type in ['Pos','FreePos']:
            this_instance['pos'] = self.list_parser(obj_args)
            return this_instance
        # 其他类型
        else:
            args_list = RE_mediadef_args.findall(obj_args)
            allow_position_args = True
            for i,arg in enumerate(args_list):
                keyword,value = arg
                # 关键字
                if keyword == '':
                    if allow_position_args == True:
                        try:
                            keyword = self.type_keyword_position[obj_type][i]
                        except IndexError:
                            # 给媒体指定了过多的参数
                            SyntaxsError('ToMuchArgs',obj_type)
                    else:
                        # 非法使用的顺序参数
                        print(args_list)
                        raise SyntaxsError('BadPosArg')
                else:
                    allow_position_args = False
                # 值
                this_instance[keyword] = self.value_parser(value)
            return this_instance
    def parser(self,script:str) -> dict:
        # 分割小节
        object_define_text = script.split('\n')
        # 结构体
        struct = {}
        # 逐句读取小节
        for i,text in enumerate(object_define_text):
            # 空行
            if text == '':
                struct[str(i)] = {'type':'blank'}
                continue
            # 备注
            elif text[0] == '#':
                struct[str(i)] = {'type':'comment','content':text[1:]}
                continue
            # 有内容的
            try:
                # 尝试解析媒体定义文件
                obj_name,obj_type,obj_args = RE_mediadef.findall(text)[0]
            except:
                # 格式不合格的行直接报错
                try:
                    obj_name,value_obj = RE_subscript_def.findall(text)[0]
                    struct[obj_name] = self.value_parser(value_obj)
                    continue
                except Exception:
                    raise SyntaxsError('MediaDef',text,str(i+1))
            else:
                # 格式合格的行开始解析
                try:
                    # 如果是非法的标识符
                    if (len(re.findall('\w+',obj_name))==0)|(obj_name[0].isdigit()):
                        raise SyntaxsError('InvaName')
                    else:
                        this_section = self.instance_parser(obj_type,obj_args[1:-1])
                except Exception as E:
                    print(E)
                    raise SyntaxsError('MediaDef',text,str(i+1))
                struct[obj_name] = this_section
        return struct
    # struct -> MDF
    def instance_export(self,media_object:dict)->str:
        type_this = media_object['type']
        if type_this == 'subscript':
            return media_object['object'] + self.list_export(media_object['index'],is_tuple=False)
        elif type_this in ['Pos','FreePos']:
            return type_this + self.list_export(media_object['pos'],is_tuple=True)
        else:
            argscript_list = []
            for key in media_object.keys():
                if key == 'type':
                    continue
                else:
                    argscript_list.append(key + '=' + self.value_export(media_object[key]))
            return type_this + '(' + ','.join(argscript_list) + ')'
    def list_export(self,list_object:list,is_tuple=True)->str:
        list_unit = []
        for unit in list_object:
            if type(unit) not in [int,float]:
                is_tuple = False
            list_unit.append(self.value_export(unit))
        # 注意：纯数值组成的列表使用tuple
        if is_tuple:
            return '(' + ','.join(list_unit) + ')'
        # 反之必须使用list，源于解析的要求
        else:
            return '[' + ','.join(list_unit) + ']'
    def value_export(self,unit:object)->str:
        # 常量
        if type(unit) in [int,float]:
            return str(unit)
        elif type(unit) is bool:
            return {False:'False',True:'True'}[unit]
        elif unit is None:
            return 'None'
        # 字符串
        elif type(unit) is str:
            # 如果是一个引用对象
            if unit[0] == '$':
                return unit[1:]
            else:
                if "'" in unit:
                    unit.replace("'","\\'")
                return "'" + unit + "'"
        # 列表
        elif type(unit) is list:
            return self.list_export(unit)
        # 对象
        elif type(unit) is dict:
            return self.instance_export(unit)
        # 其他
        else:
            return ''       
    def export(self)->str:
        list_of_scripts = []
        for key in self.struct.keys():
            obj_this:dict = self.struct[key]
            type_this:str = obj_this['type']
            # 空行
            if type_this == 'blank':
                this_script = ''
            # 备注
            elif type_this == 'comment':
                this_script = '#' + obj_this['content']
            # 实例化
            else:
                this_script = key + ' = ' + self.instance_export(obj_this)
            # 添加到列表
            list_of_scripts.append(this_script)
        # 返回
        return '\n'.join(list_of_scripts)
    # 执行：实例化媒体定义文件中的媒体类，并保存在 self.Medias:dict
    def instance_execute(self,instance_dict:dict)->object:
        # 本行的类型
        type_this:str  = instance_dict['type']
        if type_this in ['blank','comment']:
            # 如果是空行或者备注
            return None
        elif type_this == 'subscript':
            # 如果是subscript
            object_this = self.reference_object_execute(instance_dict['object'])
            index_this:list = instance_dict['index']
            # 借用魔法方法
            return object_this.__getitem__(index_this)
        elif type_this in ['Pos','FreePos']:
            # 如果是采取特殊实例化
            ClassThis:type = self.Media_type[type_this]
            pos_this:list = self.list_execute(instance_dict['pos'])
            return ClassThis(*pos_this)
        else:
            # 建立关键字字典
            ClassThis:type = self.Media_type[type_this]
            this_instance_args = {}
            # 遍历元素
            for key in instance_dict.keys():
                if key == 'type':
                    continue
                else:
                    value_this = instance_dict[key]
                    this_instance_args[key] = self.value_execute(value_this)
            # 实例化
            return ClassThis(**this_instance_args)       
    def list_execute(self,list_object:list)->list:
        this_list_unit = []
        for unit in list_object:
            this_list_unit.append(self.value_execute(unit))
        return this_list_unit
    def value_execute(self,unit:object)->object:
        if type(unit) is str:
            if unit[0] == '$':
                return self.reference_object_execute(unit)
            else:
                return unit
        elif type(unit) is dict:
            # 递归调用 instance_execute
            return self.instance_execute(unit)
        elif type(unit) is list:
            # 是列表
            return self.list_execute(unit)
        else:
            # 是值
            return unit
    def reference_object_execute(self,reference_name:str)->object:
        # 根据 $媒体名 返回 媒体对象
        try:
            return self.Medias[reference_name[1:]]
        except KeyError:
            raise SyntaxsError('UndefName',reference_name[1:])
    def execute(self) -> dict:
        self.Medias = {}
        # 每一个媒体类
        for i,obj_name in enumerate(self.struct.keys()):
            # 来自结构体
            obj_dict_this:dict = self.struct[obj_name]
            # 实例化
            try:
                object_this = self.instance_execute(obj_dict_this)
            except Exception as E:
                print(E)
                text = self.instance_export(obj_dict_this)
                raise SyntaxsError('MediaDef',text,str(i+1)) # TODO:改改这个SyntaxsError的输出文本吧
            # 保存:
            if object_this is None:
                pass
            else:
                self.Medias[obj_name] = object_this

# 角色配置文件
class CharTable(Script):
    # 初始化
    def __init__(self,table_input=None,dict_input=None,file_input=None,json_input=None) -> None:
        # DataFrame 输入
        if table_input is not None:
            self.struct:dict = self.parser(table=table_input)
        # 字典 输入
        elif dict_input is not None:
            self.struct:dict = dict_input
        # 如果输入了 tsv、xlsx、xls
        elif file_input is not None:
            self.struct:dict = self.parser(table=self.load_table(filepath=file_input))
        # 如果输入了json文件：不安全的方法
        elif json_input is not None:
            self.struct:dict = self.load_json(filepath=json_input)
        # 如果没有输入
        else:
            self.struct:dict = {}
    # 从文件读取表格
    def load_table(self, filepath: str) -> pd.DataFrame:
        # 读取表格，并把表格中的空值处理为 "NA"
        try:
            if filepath.split('.')[-1] in ['xlsx','xls']:
                # 是excel表格
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore') # 禁用读取excel时报出的：UserWarning: Data Validation extension is not supported and will be removed
                    # 支持excel格式的角色配置表，默认读取sheet1
                    charactor_table:pd.DataFrame = pd.read_excel(filepath,dtype = str).fillna('NA')
            else:
                # 是tsv
                charactor_table:pd.DataFrame = pd.read_csv(filepath,sep='\t',dtype = str).fillna('NA')
            charactor_table.index = charactor_table['Name']+'.'+charactor_table['Subtype']
            if charactor_table.index.is_unique == False:
                duplicate_subtype_name = charactor_table.index[charactor_table.index.duplicated()][0]
                raise ParserError('DupSubtype',duplicate_subtype_name)
        except Exception as E:
            raise SyntaxsError('CharTab',E)
        # 如果角色表缺省关键列
        if ('Animation' not in charactor_table.columns) | ('Bubble' not in charactor_table.columns):
            raise SyntaxsError('MissCol')
        # 返回角色表格
        return charactor_table
    # 将DataFrame 解析为 dict：
    def parser(self, table: pd.DataFrame) -> dict:
        # 正常是to_dict 是以列为key，需要转置为以行为key
        return table.T.to_dict()
    # 将 dict 转为 DataFrame
    def export(self)->pd.DataFrame:
        # dict -> 转为 DataFrame，把潜在的缺失值处理为'NA'
        return pd.DataFrame(self.struct).T.fillna('NA')
    # 保存为文本文件 (tsv)
    def dump_file(self,filepath:str)->None:
        charactor_table = self.export()
        charactor_table.to_csv(filepath,sep='\t',index=False)
    # 执行：角色表哪儿有需要执行的哦，直接返回自己的表就行了
    def execute(self) -> pd.DataFrame:
        return self.export().copy()

# log文件
class RplGenLog(Script):
    # RGL -> struct
    def charactor_parser(self,cr:str,i=0)->dict: # [CH1,CH2,CH3]
        list_of_CR = RE_characor.findall(cr)
        this_charactor_set = {}
        if len(list_of_CR) > 3:
            # 角色不能超过3个!
            raise ParserError('2muchChara',str(i+1))
        for k,charactor in enumerate(list_of_CR[0:3]):
            this_charactor = {}
            # 名字 (透明度) .差分
            this_charactor['name'],alpha,subtype= charactor
            if subtype == '':
                this_charactor['subtype'] = 'default'
            else:
                this_charactor['subtype'] = subtype[1:] # 去除首字符.
            if alpha == '':
                this_charactor['alpha'] = None
            else:
                this_charactor['alpha'] = int(alpha[1:-1]) # 去掉首尾括号
            this_charactor_set[str(k)] = this_charactor
        return this_charactor_set
    def method_parser(self,method:str)->dict: # <method=0>
        this_section = {}
        if method == '':
            this_section['method'] = 'default'
            this_section['method_dur'] = 'default'
        else:
            this_section['method'],method_dur =RE_modify.findall(method)[0]
            if method_dur == '':
                this_section['method_dur'] = 'default'
            else:
                this_section['method_dur'] = int(method_dur[1:])
        return this_section
    def sound_parser(self,sound:str,i=0)->dict: # {SE;30}
        this_sound_set = {}
        if sound == '':
            return this_sound_set
        else:
            # 星标列表 {*}
            list_of_AS = RE_asterisk.findall(sound)
            # 没检测到星标
            if len(list_of_AS) == 0:  
                pass
            # 检查到一个星标
            elif len(list_of_AS) == 1:
                # obj;  time
                this_asterisk = {}
                # 音效
                if list_of_AS[0][1] == '':
                    this_asterisk['sound'] = None
                else:
                    this_asterisk['sound'] = list_of_AS[0][1][:-1] # 去除最后存在的分号
                # 时间
                if list_of_AS[0][-1] == '':
                    this_asterisk['time'] = None
                else:
                    try:
                        this_asterisk['time'] = float(list_of_AS[0][-1])
                    except Exception:
                        this_asterisk['time'] = None
                        if this_asterisk['sound'] is None:
                            # 指定发言内容
                            this_asterisk['specified_speech'] = list_of_AS[0][-1]
                if this_asterisk['sound'] is None or this_asterisk['time'] is None:
                    # 如果是待合成的
                    this_sound_set['{*}'] = this_asterisk
                else:
                    # 如果是合规的
                    this_sound_set['*'] = this_asterisk
            # 检测到复数个星标
            else:
                raise ParserError('2muchAster',str(i+1))
            # 音效列表 {}
            list_of_SE = RE_sound_simple.findall(sound)
            for k,se in enumerate(list_of_SE): #this_sound = ['{SE_obj;30}','{SE_obj;30}']
                this_soundeff = {}
                if ';' in se:
                    this_soundeff['sound'],delay = se[1:-1].split(';')
                    try:
                        this_soundeff['delay'] = int(delay)
                    except Exception:
                        this_soundeff['delay'] = 0
                else:
                    this_soundeff['sound'] = se[1:-1]
                    this_soundeff['delay'] = 0
                this_sound_set[str(k)] = this_soundeff
            # 给到上一层
            return this_sound_set
    def bubble_parser(self,bubble_exp:str,i=0)->dict: # Bubble("header_","main_text",<w2w=1>)
        # 解析
        try:
            this_bb,this_hd,this_tx,this_method_label,this_tx_method,this_tx_dur = RE_bubble.findall(bubble_exp)[0]
        except IndexError:
            raise ParserError('InvaPBbExp',bubble_exp,str(i+1))
        # 结构
        this_bubble = {}
        # 对象
        this_bubble['bubble'] = this_bb
        # 文字
        this_bubble['header_text'] = this_hd
        this_bubble['main_text'] = this_tx
        # 文字效果
        this_bubble['tx_method'] = self.method_parser(this_method_label)
        # 返回
        return this_bubble
    def parser(self,script:str) -> dict:
        # 分割小节
        stdin_text = script.split('\n')
        # 结构体
        struct = {}
        # 逐句读取小节
        for i,text in enumerate(stdin_text):
            # 本行的结构体
            this_section = {}
            # 空白行
            if text == '':
                this_section['type'] = 'blank'
            # 注释行 格式： # word
            elif text[0] == '#':
                this_section['type'] = 'comment'
                this_section['content'] = text[1:]
            # 对话行 格式： [角色1,角色2(30).happy]<replace=30>:巴拉#巴拉#巴拉<w2w=1>
            elif (text[0] == '[') & (']' in text):
                # 类型
                this_section['type'] = 'dialog'
                # 拆分为：[角色框]、<效果>、:文本、<文本效果>、{音效}
                try:
                    cr,cre,ts,tse,se = RE_dialogue.findall(text)[0]
                except IndexError:
                    raise ParserError('UnableDial')
                # [角色框]
                this_section['charactor_set'] = self.charactor_parser(cr=cr,i=1)
                # <效果>
                this_section['ab_method'] =  self.method_parser(cre)
                # :文本
                this_section['content'] = ts
                # <文本效果>
                this_section['tx_method'] = self.method_parser(tse)
                # {音效}
                this_section['sound_set'] = self.sound_parser(sound=se,i=i)
            # 背景设置行，格式： <background><black=30>:BG_obj
            elif text[0:12] == '<background>':
                # 解析
                try:
                    obj_type,obje,objc = RE_placeobj.findall(text)[0]
                    # 类型
                    this_section['type'] = obj_type
                except IndexError:
                    raise ParserError('UnablePlace')
                # <效果>
                this_section['bg_method'] = self.method_parser(obje)
                # 对象
                this_section['object'] = objc
            # 常驻立绘设置行，格式：<animation><black=30>:(Am_obj,Am_obj2)
            elif text[0:11] == '<animation>':
                # 解析
                try:
                    obj_type,obje,objc = RE_placeobj.findall(text)[0]
                    # 类型
                    this_section['type'] = obj_type
                except IndexError:
                    raise ParserError('UnablePlace')
                # <效果>
                this_section['am_method'] = self.method_parser(obje)
                # 对象
                if objc == 'NA' or objc == 'None':
                    this_section['object'] = None
                elif (objc[0] == '(') and (objc[-1] == ')'):
                    # 如果是一个集合
                    this_GA_set = {} # GA
                    animation_list = objc[1:-1].split(',')
                    for k,am in enumerate(animation_list):
                        this_GA_set[str(k)] = am
                    this_section['object'] = this_GA_set
                else:
                    this_section['object'] = objc
            # 常驻气泡设置行，格式：<bubble><black=30>:Bubble_obj("Header_text","Main_text",<text_method>)
            elif text[0:8] == '<bubble>':
                # 解析
                try:
                    obj_type,obje,objc = RE_placeobj.findall(text)[0]
                    # 类型
                    this_section['type'] = obj_type
                except IndexError:
                    raise ParserError('UnablePlace')
                # <效果>
                this_section['bb_method'] = self.method_parser(obje)
                # 对象
                if objc == 'NA' or objc == 'None':
                    this_section['object'] = None
                else:
                    this_section['object'] = self.bubble_parser(bubble_exp=objc,i=i)
            # 参数设置行，格式：<set:speech_speed>:220
            elif (text[0:5] == '<set:') & ('>:' in text):
                try:
                    target,args = RE_setting.findall(text)[0]
                except IndexError:
                    raise ParserError('UnableSet')
                # 类型
                this_section['type'] = 'set'
                this_section['target'] = target
                # 类型1：整数型
                if target in ['am_dur_default','bb_dur_default','bg_dur_default','tx_dur_default','speech_speed','asterisk_pause','secondary_alpha']:
                    this_section['value_type'] = 'digit' # natural number
                    try:
                        this_section['value'] = int(args)
                    except:
                        print(WarningPrint('Set2Invalid',target,args))
                        this_section['value'] = args
                # 类型2：method
                elif target in ['am_method_default','bb_method_default','bg_method_default','tx_method_default']:
                    this_section['value_type'] = 'method'
                    try:
                        this_section['value'] = self.method_parser(args)
                    except IndexError:
                        raise ParserError('SetInvMet',target,args)
                # 类型3：BGM
                elif target == 'BGM':
                    this_section['value_type'] = 'music'
                    this_section['value'] = args
                # 类型4：函数
                elif target == 'formula':
                    this_section['value_type'] = 'function'
                    if args in formula_available.keys() or args[0:6] == 'lambda':
                        this_section['value'] = args
                    else:
                        raise ParserError('UnspFormula',args,str(i+1))
                # 类型5：枚举
                elif target == 'inline_method_apply':
                    this_section['value_type'] = 'enumerate'
                    this_section['value'] = args
                # 类型6：角色表
                elif '.' in target:
                    this_section['value_type'] = 'chartab'
                    this_target = {}
                    target_split = target.split('.')
                    if len(target_split) == 2:
                        this_target['name'],this_target['column'] = target_split
                        this_target['subtype'] = None
                    elif len(target_split) == 3:
                        this_target['name'],this_target['subtype'],this_target['column'] = target_split
                    # 如果超过4个指定项目，无法解析，抛出ParserError(不被支持的参数)
                    else:
                        raise ParserError('UnsuppSet',target,str(i+1))
                    this_section['target'] = this_target
                    this_section['value'] = args
                # 类型7：尚且无法定性的，例如FreePos
                else:
                    this_section['value_type'] = 'unknown'
                    this_section['value'] = args
            # 清除行，仅适用于ChatWindow
            elif (text[0:8] == '<clear>:'):
                this_section['type'] = 'clear'
                this_section['object'] = text[8:]
            # 预设动画，损失生命
            elif text[0:11] == '<hitpoint>:':
                this_section['type'] = 'hitpoint'
                name_tx,heart_max,heart_begin,heart_end = RE_hitpoint.findall(text)[0]
                this_section['content'] = name_tx
                try:
                    this_section['hp_max'] = int(heart_max)
                    this_section['hp_begin'] = int(heart_begin)
                    this_section['hp_end'] = int(heart_end)
                except Exception as E:
                    print(E)
                    raise ParserError('ParErrHit',str(i+1))
            # 预设动画，骰子
            elif text[0:7] == '<dice>:':
                this_section['type'] = 'dice'
                dice_args = RE_dice.findall(text[7:])
                if len(dice_args) == 0:
                    raise ParserError('NoDice')
                else:
                    try:
                        this_dice_set = {}
                        for k,dice in enumerate(dice_args):
                            this_dice = {}
                            tx,dicemax,check,face = dice
                            this_dice['content'] = tx
                            this_dice['dicemax'] = int(dicemax)
                            this_dice['face'] = int(face)
                            if check == 'NA':
                                this_dice['check'] = None
                            else:
                                this_dice['check'] = int(check)
                            this_dice_set[str(k)] = this_dice
                        this_section['dice_set'] = this_dice_set
                    except Exception as E:
                        print(E)
                        raise ParserError('ParErrDice',str(i+1))
            # 等待行，停留在上一个小节的结束状态，不影响S图层
            elif text[0:7] == '<wait>:':
                this_section['type'] = 'wait'
                try:
                    this_section['time'] = int(RE_wait.findall(text)[0])
                except Exception as E:
                    raise ParserError('InvWaitArg',E)
            # 异常行，报出异常
            else:
                raise ParserError('UnrecLine',str(i+1))
            struct[str(i)] = this_section
        # 返回值
        return struct
    # struct -> RGL
    def method_export(self,method_obj:dict)->str:
        if method_obj['method'] == 'default':
            return ''
        else:
            if method_obj['method_dur'] == 'default':
                return '<'+ method_obj['method'] +'>'
            else:
                return '<'+ method_obj['method'] + '=' + str(method_obj['method_dur']) +'>'
    def sound_export(self,sound_obj_set:dict)->str:
        sound_script_list = []
        for key in sound_obj_set.keys():
            sound_obj = sound_obj_set[key]
            if key == '*': # {sound;*50}
                sound_script_list.append('{' + sound_obj['sound'] + ';*' + str(sound_obj['time']) + '}')
            elif key == '{*}':
                if 'specified_speech' not in sound_obj.key(): # {*abc}
                    sound_script_list.append('{*' + str(sound_obj['specified_speech']) + '}')
                elif sound_obj['sound'] is not None: # {sound;*}
                    sound_script_list.append('{' + str(sound_obj['sound']) + ';*}')
                else:
                    sound_script_list.append('{*}') # {*}
            else:
                if sound_obj['delay'] != 0: # {sound;5}
                    sound_script_list.append('{' + str(sound_obj['sound']) +';'+ str(sound_obj['delay']) +'}')
                else: # {sound}
                    sound_script_list.append('{' + str(sound_obj['sound']) + '}')
        return ''.join(sound_script_list)
    def export(self) -> str:
        list_of_scripts = []
        for key in self.struct.keys():
            this_section:dict = self.struct[key]
            type_this:str = this_section['type']
            # 空行
            if type_this == 'blank':
                this_script = ''
            # 备注
            elif type_this == 'comment':
                this_script = '#' + this_section['content']
            # 对话行
            elif this_section['type'] == 'dialog':
                # 角色
                charactor_set:dict = this_section['charactor_set']
                charactor_script_list:list = []
                for key in charactor_set.keys():
                    charactor = charactor_set[key]
                    charactor_script = charactor['name']
                    if charactor['alpha'] is not None:
                        charactor_script = charactor_script + '(%d)'%charactor['alpha']
                    if charactor['subtype'] != 'default':
                        charactor_script = charactor_script + '.' + charactor['subtype']
                    charactor_script_list.append(charactor_script)
                CR = '[' + ','.join(charactor_script_list) + ']'
                # 媒体效果
                MM = self.method_export(this_section['ab_method'])
                TM = self.method_export(this_section['tx_method'])
                SE = self.sound_export(this_section['sound_set'])
                this_script = CR + MM + ':' + this_section['content'] + TM + SE
            # 背景
            elif this_section['type'] == 'background':
                MM = self.method_export(this_section['bg_method'])
                this_script = '<background>' + MM + ':' + this_section['object']
            # 立绘
            elif this_section['type'] == 'animation':
                MM = self.method_export(this_section['am_method'])
                if this_section['object'] is None:
                    OB = 'NA'
                elif type(this_section['object']) is str:
                    OB =  this_section['object']
                else:
                    OB = '(' + ','.join(this_section['object'].values()) + ')'
                this_script = '<animation>' + MM + ':' + OB
            # 气泡
            elif this_section['type'] == 'bubble':
                MM = self.method_export(this_section['bb_method'])
                if this_section['object'] is None:
                    OB = 'NA'
                else:
                    bubble_object = this_section['object']
                    TM = self.method_export(bubble_object['tx_method'])
                    OB = '{}("{}","{}"{})'.format(
                        bubble_object['bubble'],
                        bubble_object['header_text'],
                        bubble_object['main_text'],TM)
                this_script = '<bubble>' + MM + ':' + OB
            # 设置
            elif this_section['type'] == 'set':
                if this_section['value_type'] == 'digit':
                    value = str(this_section['value'])
                    target = this_section['target']
                elif this_section['value_type'] in ['music','function','enumerate','unknown']:
                    value = this_section['value']
                    target = this_section['target']
                elif this_section['value_type'] == 'method':
                    value = self.method_export(this_section['value'])
                    target = this_section['target']
                elif this_section['value_type'] == 'chartab':
                    value = this_section['value']
                    if this_section['target']['subtype'] is None:
                        target = this_section['target']['name'] +'.'+ this_section['target']['column']
                    else:
                        target = this_section['target']['name'] +'.'+ this_section['target']['subtype'] +'.'+ this_section['target']['column']
                else:
                    continue
                this_script = '<set:{}>:{}'.format(target,value)
            # 清除
            elif this_section['type'] == 'clear':
                this_script = '<clear>:' + this_section['object']
            # 生命值
            elif this_section['type'] == 'hitpoint':
                this_script = '<hitpoint>:({},{},{},{})'.format(
                    this_section['content'],
                    this_section['hp_max'],
                    this_section['hp_begin'],
                    this_section['hp_end']
                )
            # 骰子
            elif this_section['type'] == 'dice':
                list_of_dice_express = []
                for key in this_section['dice_set'].keys():
                    this_dice = this_section['dice_set'][key]
                    if this_dice['check'] is None:
                        CK = 'NA'
                    else:
                        CK = int(this_dice['check'])
                    list_of_dice_express.append(
                        '({},{},{},{})'.format(
                            this_dice['content'],
                            this_dice['dicemax'],
                            CK,
                            this_dice['face']))
                    this_script = '<dice>:' + ','.join(list_of_dice_express)
            elif this_section['type'] == 'wait':
                this_script = '<wait>:{}'.format(this_section['time'])
            else:
                this_script = ''
            # 添加到列表
            list_of_scripts.append(this_script)
        # 返回
        return '\n'.join(list_of_scripts)
    # 执行解析 -> (timeline:pd.DF,breakpoint:pd.Ser,builtin_media:dict?<方便在其他模块实例化>
    def tx_method_execute(self,content:str,tx_method:dict,line_limit:int,this_duration:int,i=0) -> np.ndarray:
        content_length:int = len(content)
        # 全部显示
        if tx_method['method'] == 'all':
            if tx_method['method_dur'] >= this_duration:
                main_text_eff = np.zeros(this_duration)
            else:
                main_text_eff = np.hstack([
                    np.zeros(tx_method['method_dur']),
                    content_length*np.ones(this_duration-tx_method['method_dur'])
                    ])
            return main_text_eff
        # 逐字显示
        elif tx_method['method'] == 'w2w':
            return np.frompyfunc(lambda x:x if x<=content_length else content_length,1,1)(np.arange(0,this_duration,1)//tx_method['method_dur'])
        # 逐行显示
        elif tx_method['method'] == 'l2l':
            if ((content[0]=='^')|('#' in content)): #如果是手动换行的列
                lines = content.split('#')
                wc_list = []
                len_this = 0
                for x,l in enumerate(lines): #x是井号的数量
                    len_this = len_this +len(l)+1 #当前行的长度
                    #print(len_this,len(l),x,ts[0:len_this])
                    wc_list.append(np.ones(tx_method['method_dur']*len(l))*len_this)
                try:
                    wc_list.append(np.ones(this_duration - (len(content)-x)*tx_method['method_dur'])*len(content)) #this_duration > est # 1.6.1 update
                    word_count_timeline = np.hstack(wc_list)
                except Exception: 
                    word_count_timeline = np.hstack(wc_list) # this_duration < est
                    word_count_timeline = word_count_timeline[0:this_duration]
                return word_count_timeline.astype(int)
            else:
                return (np.arange(0,this_duration,1)//(tx_method['method_dur']*line_limit)+1)*line_limit
        # 逐句显示
        elif tx_method['method'] == 's2s':
            pass
        # 聊天窗滚动
        elif tx_method['method'] == 'run':
            pass
        else:
            raise ParserError('UnrecTxMet', self.method_export(tx_method), str(i+1))
    def execute(self,media_define:MediaDef,char_table:CharTable,config:Config)->tuple:
        # 媒体和角色
        self.medias:dict = media_define.Medias
        self.charactors:pd.DataFrame = char_table.execute()
        # section:小节号, BG: 背景，Am：立绘，Bb：气泡，BGM：背景音乐，Voice：语音，SE：音效
        render_arg = [
        'section',
        'BG1','BG1_a','BG1_c','BG1_p','BG2','BG2_a','BG2_c','BG2_p',
        'Am1','Am1_t','Am1_a','Am1_c','Am1_p','Am2','Am2_t','Am2_a','Am2_c','Am2_p','Am3','Am3_t','Am3_a','Am3_c','Am3_p',
        'AmS','AmS_t','AmS_a','AmS_c','AmS_p',
        'Bb','Bb_main','Bb_main_e','Bb_header','Bb_a','Bb_c','Bb_p',
        'BbS','BbS_main','BbS_main_e','BbS_header','BbS_a','BbS_c','BbS_p',
        'BGM','Voice','SE'
        ]
        # 断点文件: index + 1 == section, 因为还要包含尾部，所以总长比section长1
        break_point = pd.Series(0,index=range(0,len(self.struct.keys())+1),dtype=int)
        # 视频+音轨 时间轴
        timeline = pd.DataFrame(dtype=str,columns=render_arg)
        # 内建的媒体，主要指BIA # 保存为另外的一个Media文件
        bulitin_media = MediaDef()
        # 背景音乐队列
        BGM_queue = []
        # 初始化的背景、放置立绘、放置气泡
        this_background = "black"
        # 放置的立绘
        last_placed_animation_section = 0
        this_placed_animation = ('NA','replace',0,'NA') # am,method,method_dur,center
        # 放置的气泡
        last_placed_bubble_section = 0
        this_placed_bubble = ('NA','replace',0,'','','all',0,'NA') # bb,method,method_dur,HT,MT,tx_method,tx_dur,center
        # 当前对话小节的am_bb_method
        last_dialog_method = {'Am':None,'Bb':None,'A1':0,'A2':0,'A3':0}
        this_dialog_method = {'Am':None,'Bb':None,'A1':0,'A2':0,'A3':0}
        # 动态变量
        self.dynamic = {
            #默认切换效果（立绘）
            'am_method_default' : {'method':'replace','method_dur':0},
            #默认切换效果持续时间（立绘）
            'am_dur_default' : 10,
            #默认切换效果（文本框）
            'bb_method_default' : {'method':'replace','method_dur':0},
            #默认切换效果持续时间（文本框）
            'bb_dur_default' : 10,
            #默认切换效果（背景）
            'bg_method_default' : {'method':'replace','method_dur':0},
            #默认切换效果持续时间（背景）
            'bg_dur_default' : 10,
            #默认文本展示方式
            'tx_method_default' : {'method':'all','method_dur':0},
            #默认单字展示时间参数
            'tx_dur_default' : 5,
            #语速，单位word per minute
            'speech_speed' : 220,
            #默认的曲线函数
            'formula' : linear,
            # 星标音频的句间间隔 a1.4.3，单位是帧，通过处理delay
            'asterisk_pause' : 20,
            # a 1.8.8 次要立绘的默认透明度
            'secondary_alpha' : 60,
            # 对话行内指定的方法的应用对象：animation、bubble、both、none
            'inline_method_apply' : 'both'
        }
        # 开始遍历
        for key in self.struct.keys():
            # 保留前一行的切换效果参数，重置当前行的参数
            last_dialog_method = this_dialog_method
            this_dialog_method = {'Am':None,'Bb':None,'A1':0,'A2':0,'A3':0}
            # 本小节：
            i = str(key)
            this_section = self.struct[key]
            # 空白行
            if this_section['type'] == 'blank':
                break_point[i+1]=break_point[i]
                continue
            # 注释行
            elif this_section['type'] == 'comment':
                break_point[i+1]=break_point[i]
                continue
            # 对话行
            elif this_section['type'] == 'dialog':
                # 这个小节的持续时长
                if '*' in this_section['sound_set'].keys():
                    # 如果存在星标音效：持续时长 = 星标间隔 + ceil(秒数时间*帧率)
                    this_duration:int = self.dynamic['asterisk_pause'] + np.ceil(this_section['sound_set']['*']['time'] * config.frame_rate).astype(int)
                elif '{*}' in this_section['sound_set'].keys():
                    # 如果存在待处理星标：举起伊可
                    raise ParserError('UnpreAster', str(i+1))
                else:
                    # 如果缺省星标：持续时间 = 字数/语速 + 星标间隔
                    this_duration:int = self.dynamic['asterisk_pause'] + int(len(this_section['content'])/(self.dynamic['speech_speed']/60/config.frame_rate))
                # 本小节的切换效果：am_method，bb_method
                if this_section['ab_method']['method'] == 'default' | self.dynamic['inline_method_apply'] == 'none':
                    # 未指定
                    am_method:dict = self.dynamic['am_method_default'].copy()
                    bb_method:dict = self.dynamic['bb_method_default'].copy()
                else:
                    # 有指定
                    if self.dynamic['inline_method_apply'] in ['animation','both']:
                        am_method:dict = this_section['ab_method'].copy()
                    else:
                        am_method:dict = self.dynamic['am_method_default'].copy()
                    if self.dynamic['inline_method_apply'] in ['bubble','both']:
                        bb_method:dict = this_section['ab_method'].copy()
                    else:
                        bb_method:dict = self.dynamic['bb_method_default'].copy()
                # 是否缺省时长
                if am_method['method_dur'] == 'default':
                    am_method['method_dur'] = self.dynamic['am_dur_default']
                if bb_method['method_dur'] == 'default':
                    bb_method['method_dur'] = self.dynamic['bb_dur_default']
                # 小节持续时长是否低于切换效果的持续时长？
                method_dur = max(am_method['method_dur'],bb_method['method_dur'])
                if this_duration<(2*method_dur+1):
                    this_duration = 2*method_dur+1
                # 建立本小节的timeline文件
                this_timeline=pd.DataFrame(index=range(0,this_duration),dtype=str,columns=render_arg)
                this_timeline['BG2'] = this_background
                this_timeline['BG2_a'] = 100
                # 载入切换效果
                am_method_obj = MotionMethod(am_method['method'],am_method['method_dur'],self.dynamic['formula'],i)
                bb_method_obj = MotionMethod(bb_method['method'],bb_method['method_dur'],self.dynamic['formula'],i)
                this_dialog_method['Am'] = am_method_obj
                this_dialog_method['Bb'] = bb_method_obj
                # 遍历角色
                for chara_key in this_section['charactor_set'].keys():
                    this_charactor:dict = this_section['charactor_set'][chara_key]
                    # 获取角色配置
                    name:str = this_charactor['name']
                    subtype:str = this_charactor['subtype']
                    alpha:int = this_charactor['subtype']
                    try:
                        this_charactor_config = self.charactors.loc[name+':'+subtype]
                    except KeyError as E: # 在角色表里面找不到name，raise在这里！
                        raise ParserError('UndefName',name+subtype,str(i+1),E)
                    # 立绘：'Am1','Am1_t','Am1_a','Am1_c','Am1_p
                    this_layer:str = 'Am%d' % (int(chara_key) + 1)
                    AN = this_layer.replace('m','')
                    this_am:str = this_charactor_config['Animation']
                    # 立绘的名字
                    this_timeline[this_layer] = this_am
                    if this_am == 'NA':
                        # 如果立绘缺省
                        this_timeline[this_layer+'_t'] = 0
                        this_timeline[this_layer+'_c'] = 'NA'
                        this_timeline[this_layer+'_a'] = 0
                        this_timeline[this_layer+'_p'] = 'NA'
                        this_dialog_method[AN] = 0
                    elif this_am not in self.medias.keys():
                        # 如果媒体名未定义
                        raise ParserError('UndefAnime', this_am, name+':'+subtype)
                    elif media_define.struct[this_am]['type'] not in ['Animation','GroupedAnimation','BuiltInAnimation']:
                        # 如果媒体不是一个立绘类
                        raise ParserError('NotAnime', this_am, name+':'+subtype)
                    else:
                        # 立绘的对象、帧顺序、中心位置
                        this_am_obj:Animation = self.medias[this_am]
                        this_timeline[this_layer+'_t'] = this_am_obj.get_tick(this_duration)
                        this_timeline[this_layer+'_c'] = str(this_am_obj.pos)
                        # 立绘的透明度
                        if (alpha >= 0)&(alpha <= 100):
                            # 如果有指定合法的透明度，则使用指定透明度
                            this_timeline[this_layer+'_a']=am_method_obj.alpha(this_duration,alpha)
                            this_dialog_method[AN] = alpha
                        else:
                            # 如果指定是None（默认），或者其他非法值
                            if chara_key == '0': # 如果是首要角色，透明度为100
                                this_timeline[this_layer+'_a']=am_method_obj.alpha(this_duration,100)
                                this_dialog_method[AN] = 100
                            else: # 如果是次要角色，透明度为secondary_alpha，默认值60
                                this_timeline[this_layer+'_a']=am_method_obj.alpha(this_duration,self.dynamic['secondary_alpha'])
                                this_dialog_method[AN] = self.dynamic['secondary_alpha']
                        # 立绘的运动
                        this_timeline[this_layer+'_p'] = am_method_obj.motion(this_duration)
                    # 气泡参数: 'Bb','Bb_main','Bb_main_e','Bb_header','Bb_a','Bb_c','Bb_p',
                    if chara_key == '0':
                        # 仅考虑首要角色的气泡
                        this_layer = 'Bb'
                        this_bb_key:str = this_charactor_config['Bubble']
                        # 是否是 ChatWindow:key 的形式？
                        if ':' in this_bb:
                            this_bb:str = this_bb_key.split(':')[0]
                        else:
                            this_bb:str = this_bb_key
                        if this_bb == 'NA':
                            # 气泡是否缺省？
                            this_timeline[this_layer] = 'NA'
                            this_timeline[this_layer+'_main'] = ''
                            this_timeline[this_layer+'_main_e'] = 0
                            this_timeline[this_layer+'_header'] = ''
                            this_timeline[this_layer+'_c'] = 'NA'
                            this_timeline[this_layer+'_a'] = 0
                            this_timeline[this_layer+'_p'] = 'NA'
                        elif this_bb not in self.medias.keys():
                            # 如果媒体名未定义
                            raise ParserError('UndefBubble', this_bb, name+':'+subtype)
                        elif media_define.struct[this_bb]['type'] not in ['Bubble','Balloon','DynamicBubble','ChatWindow']:
                            # 如果媒体不是一个气泡类
                            raise ParserError('NotBubble', this_bb, name+':'+subtype)
                        else:
                            # 气泡的对象
                            this_bb_obj:Bubble = self.medias[this_bb]
                            # 头文本
                            try:
                                if type(this_bb_obj) is ChatWindow:
                                    # ChatWindow 类：只有一个头文本，头文本不能包含|和#，还需要附上key
                                    if this_bb_key == this_bb:
                                        # 如果聊天窗没有key，在单独使用
                                        raise ParserError('CWUndepend', this_bb)
                                    cw_key = this_bb_key.split(':')[1]
                                    # 获取当前key的子气泡的target，target是角色表的列
                                    try:
                                        targets:str = this_bb_obj.sub_Bubble[cw_key].target
                                    except KeyError:
                                        raise ParserError('InvalidKey', cw_key, this_bb)
                                    # 获取target的文本内容
                                    if ('|' in this_charactor_config[targets]) | ('#' in this_charactor_config[targets]):
                                        # 如果包含了非法字符：| #
                                        raise ParserError('InvSymbpd',name+':'+subtype)
                                    else:
                                        target_text = cw_key+'#'+this_charactor_config[targets]
                                elif type(this_bb_obj) is Balloon:
                                    # Balloon 类：有若干个头文本，targets是一个list,用 | 分隔
                                    targets:list = this_bb_obj.target
                                    target_text = '|'.join(this_charactor_config[targets].values)
                                else: #  type(this_bb_obj) in [Bubble,DynamicBubble]:
                                    # Bubble,DynamicBubble类：只有一个头文本
                                    targets:str = this_bb_obj.target
                                    target_text = this_charactor_config[targets]
                            except KeyError as E:
                                raise ParserError('TgNotExist', E, this_bb)
                            # 主文本
                            content_text = this_section['content']
                            if type(this_bb_obj) is ChatWindow:
                                mainText_this = this_bb_obj.sub_Bubble[cw_key].MainText
                            else:
                                mainText_this = this_bb_obj.MainText
                            if mainText_this is None:
                                # 气泡如果缺失主文本
                                raise ParserError('MissMainTx',this_bb)
                            else:
                                this_line_limit:int = mainText_this.line_limit
                            # 主头文本有非法字符，双引号，反斜杠
                            if ('"' in target_text) | ('\\' in target_text) | ('"' in content_text) | ('\\' in content_text):
                                raise ParserError('InvSymbqu',str(i+1))
                            # 未声明手动换行
                            if ('#' in content_text)&(content_text[0]!='^'):
                                content_text = '^' + content_text # 补齐申明符号
                                print(WarningPrint('UndeclMB',str(i+1)))
                            #行数过多的警告
                            if (len(content_text)>this_line_limit*4) | (len(content_text.split('#'))>4):
                                print(WarningPrint('More4line',str(i+1)))
                            # 手动换行的字数超限的警告
                            if ((content_text[0]=='^')|('#' in content_text))&(np.frompyfunc(len,1,1)(content_text.replace('^','').split('#')).max()>this_line_limit):
                                print(WarningPrint('MBExceed',str(i+1)))
                            # 赋值给当前时间轴的Bb轨道
                            this_timeline['Bb'] = this_bb
                            this_timeline['Bb_a'] = bb_method_obj.alpha(this_duration,100)
                            this_timeline['Bb_p'] = bb_method_obj.motion(this_duration)
                            this_timeline['Bb_c'] = str(this_bb_obj.pos)
                            if type(this_bb_obj) is ChatWindow:
                                # 如果是聊天窗对象，更新timeline对象，追加历史记录
                                this_timeline['Bb_header'] = this_bb_obj.UF_add_header_text(target_text)
                                this_timeline['Bb_main'] = this_bb_obj.UF_add_main_text(content_text)
                                # 更新bubble对象的历史记录
                                this_bb_obj.append(content_text,target_text)
                            else:
                                this_timeline['Bb_main'] = content_text
                                this_timeline['Bb_header'] = target_text
                            # 文字显示效果
                            if this_section['tx_method']['method'] == 'default':
                                # 未指定
                                tx_method:dict = self.dynamic['tx_method_default'].copy()
                            else:
                                # 有指定
                                tx_method:dict = this_section['tx_method'].copy()
                            # 是否缺省时长
                            if tx_method['method_dur'] == 'default':
                                tx_method['method_dur'] = self.dynamic['tx_dur_default']
                            # 效果
                            content_length = len(content_text)
                            this_timeline['Bb_main_e'] = self.tx_method_execute(
                                content=content_text,
                                tx_method=tx_method,
                                line_limit=this_line_limit,
                                this_duration=this_duration,
                                i=i)