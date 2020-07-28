student_province_code=41
project_type=1 #1理科,2文科
university_province_codes=[11,12,31,32,33,41,44] #11北京 12天津 31上海 32江苏 33浙江 41河南 44广东
selected_levels=[2001] #2001本科 2002专科（高职）
selected_batch= [8] #6本科提前批 7本科一批 8本科二批
selected_zslx=[0] #0普通类
selected_nature=[36000] #36000公办
selected_year=[2019,2018,2017]
import urllib.request
import json
import time
import pandas as pd
import math
import os
from concurrent.futures import ThreadPoolExecutor,as_completed

def schoolprovince(school_code=459):
    def get_schoolprovince_data(page_num):
        schoolprovince_url='https://static-data.eol.cn/www/2.0/schoolprovinceindex/detial/%d/%d/%d/%d.json' % (school_code,student_province_code,project_type,page_num)
        r = urllib.request.urlopen(schoolprovince_url)
        dict_data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
        if not dict_data=='':
            if not dict_data['message']=='成功':
                time.sleep(1)
                r = urllib.request.urlopen(schoolprovince_url)
                dict_data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
        else:
            time.sleep(1)
            r = urllib.request.urlopen(schoolprovince_url)
            dict_data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
        if not dict_data == '':
            if not dict_data['message']=='成功':
                print('Unable to get %s' % schoolprovince_url)
                return None
        else:
            print('Unable to get %s' % schoolprovince_url)
            return None
        return dict_data

    dict_data = get_schoolprovince_data(1)
    if dict_data==None:
        total_pages = 0
        dict_datas=[]
    else:
        total_pages= math.ceil(dict_data['data']['numFound']/10)
        dict_datas = [dict_data]

    if total_pages>1:
        for page_num in range (2,total_pages+1):
            dict_datas.append(get_schoolprovince_data(page_num))

    score_lists = []
    for dict_data in dict_datas:
        score_lists = score_lists + dict_data['data']['item']
    return score_lists

def schoolinfo():
    def get_schoollist_data(page_num,university_province_code):
        schoollist_url='https://api.eol.cn/gkcx/api/?page=%d&province_id=%d&request_type=1&size=30&uri=apigkcx/api/school/hotlists' % (page_num,university_province_code)
        req = urllib.request.Request(schoollist_url,data=None, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'
        })
        r = urllib.request.urlopen(req)
        dict_data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
        if not dict_data['message']=='获取列表成功':
            time.sleep(1)
            r = urllib.request.urlopen(schoollist_url)
            dict_data = json.loads(r.read().decode(r.info().get_param('charset') or 'utf-8'))
        if not dict_data['message']=='获取列表成功':
            print('Unable to get %s' % schoollist_url)
        return dict_data
    school_lists=[]
    for university_province_code in university_province_codes:
        dict_data = get_schoollist_data(1,university_province_code)
        dict_datas=[dict_data]
        total_pages= math.ceil(dict_data['data']['numFound']/30)
        #total_pages= 3
        if total_pages>1:
            for page_num in range (2,total_pages+1):
                dict_datas.append(get_schoollist_data(page_num,university_province_code))
        for dict_data in dict_datas:
            school_lists = school_lists + dict_data['data']['item']

    pd_schoolsname=pd.DataFrame(school_lists,columns=["name","level_name","dual_class_name","province_name","city_name","belong","type_name","nature_name"])
    pd_schoolsname.to_excel('schoolname.xlsx')
    pd_schoolsinfo=pd.DataFrame(school_lists)
    pd_schoolsinfo.to_excel('schoolinfo.xlsx')

def schoolscore(pd_schoolsinfo):
    score_lists = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for school_id in pd_schoolsinfo['school_id']:
            print(school_id)
            futures.append(executor.submit(schoolprovince, school_id))
        for future in as_completed(futures):
            score_lists = score_lists + future.result()
    pd_schoolscore = pd.DataFrame(score_lists)
    pd_schoolscore.to_excel('schoolscore.xlsx')

if __name__ == "__main__":
    if not os.path.exists('schoolinfo.xlsx'):
        schoolinfo()

    pd_schoolsinfo=pd.read_excel('schoolinfo.xlsx')
    pd_schoolsinfo=pd_schoolsinfo[pd_schoolsinfo['level'].isin(selected_levels)]
    pd_schoolsinfo=pd_schoolsinfo[pd_schoolsinfo['nature'].isin(selected_nature)]

    if not os.path.exists('schoolscore.xlsx'):
        schoolscore(pd_schoolsinfo)

    pd_schoolscore=pd.read_excel('schoolscore.xlsx')

    pd_schoolscore=pd_schoolscore[pd.to_numeric(pd_schoolscore['min'], errors = 'coerce').notnull() & pd.to_numeric(pd_schoolscore['proscore'], errors = 'coerce').notnull() ]

    pd_1_batch=pd_schoolscore[pd_schoolscore['batch'].isin([7])]
    pd_1_batch=pd_1_batch.groupby('year').agg(pd.Series.mode)
    pd_1_proscore=pd_1_batch['proscore'].to_dict()

    pd_schoolscore=pd_schoolscore[pd_schoolscore['batch'].isin(selected_batch)]
    pd_schoolscore = pd_schoolscore[pd_schoolscore['zslx'].isin(selected_zslx)]

    diffscore=pd.to_numeric(pd_schoolscore['min'])-pd.to_numeric(pd_schoolscore['proscore'])
    pd_schoolscore['min_diffscore']=diffscore

    pd_schoolscore['1_proscore']=pd_schoolscore['year'].map(pd_1_proscore)
    percent_minscore = pd.to_numeric(pd_schoolscore['min_diffscore']) / (
                pd.to_numeric(pd_schoolscore['1_proscore']) - pd.to_numeric(pd_schoolscore['proscore']))

    pd_schoolscore['percent_minscore']=percent_minscore
    pd_schoolscore=pd_schoolscore[pd_schoolscore['year'].isin(selected_year)]
