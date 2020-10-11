'''
process response # ! edit
'''

import os
import pandas as pd 
import plotly
import plotly.graph_objects as go
import datetime
import dash
import dash_html_components as html
import dash_core_components as dcc
import re
from collections import defaultdict, OrderedDict
import requests 
import plotly.graph_objects as go
import numpy as np
import plotly_express as px
import time
from get_response import get_response

file = open('creds.txt')
lines = file.readlines()

if len(lines) == 0:
    get_response()
else:
    email = lines[1].split(":")[1][:-1]
    token = lines[2].split(":")[1][:-1]
    workspace_id = lines[3].split(":")[1][:-1]

class Response():
    '''
    Inputs: email, token workspace_id, start_date, end_date

    '''
    def __init__(self, email, token, workspace_id,  start_date, end_date):
        self.email = email
        self.token = token
        self.workspace_id = workspace_id
        self.sd = start_date
        self.ed = end_date
    
        URL = 'https://api.track.toggl.com/reports/api/v2/details?workspace_id={}&since={}&until={}&user_agent={}'.format(
            str(self.workspace_id), str(self.sd), str(self.ed), self.email
        )
        username = token # also the token
        password = 'api_token'
        cols = ['description', 'start', 'end', 'updated', 'dur', 'project', 'project_hex_color']
        df_raw = defaultdict(list)
        ind, data, data_in = 1, [], [0]

        while len(data_in) != 0:
            
            URL = URL + '&page=' + str(ind)
            response = requests.get(URL, auth = (username, password)).json()

            data_in = response['data']
            data += data_in
            for col in cols:
                for item in data_in:
                    df_raw[col].append(item[col]) # * fix this linting error
            ind += 1

        detailed_df = pd.DataFrame.from_dict(df_raw)

        URL = 'https://api.track.toggl.com/reports/api/v2/summary?workspace_id=4482767&since={}&until={}&user_agent={}'.format(
            str(self.sd), str(self.ed), self.email
        )
        response = requests.get(URL, auth = (username, password)).json()

        df = defaultdict(list)
        data = response['data']
        for project in data:
            tasks = project['items'] 
            for task in tasks:

                df['task'].append(task['title']['time_entry'])
                df['task time duration'].append(task['time'])
                df['project'].append(project['title']['project'])
                df['project time duration'].append(project['time'])
                df['project color'].append(project['title']['hex_color'])
        df = pd.DataFrame.from_dict(df)
        summary_df = df.dropna()

        self.summary_df = summary_df
        self.detailed_df = detailed_df
        

    def get_processed_df(self):
        '''
        process the detailed df
        '''
        # self.collect_response()
        df = self.detailed_df

        df['start'] = df['start'].apply(lambda x: datetime.datetime.strptime(x.split("+")[0], '%Y-%m-%dT%H:%M:%S'))
        df['end'] = df['end'].apply(lambda x: datetime.datetime.strptime(x.split("+")[0], '%Y-%m-%dT%H:%M:%S'))
        df['updated'] = df['updated'].apply(lambda x: datetime.datetime.strptime(x.split("+")[0], '%Y-%m-%dT%H:%M:%S'))
        df['start_day'] = df['start'].apply(lambda x: x.date())
        df['end_day'] = df['end'].apply(lambda x: x.date())
        
        rows = []

        for index, row in df.iterrows():
            if row['start_day'] != row['end_day']:
                row1, row2 = row.to_dict(), row.to_dict()
                start, end = row['start'], row['end']

                mid =  (datetime.datetime.combine(row['end_day'], datetime.datetime.min.time()))
                dur1, dur2 = (mid - start).seconds * 1000, (end - mid).seconds * 1000
                
                row1['dur'], row2['dur'] = dur1, dur2

                row1['end'] = pd.Timestamp((datetime.datetime.combine(row['start_day'], datetime.datetime.max.time())))
                row2['start'] = pd.Timestamp(mid)

                row1['end_day'] = row1['end'].date()
                row2['start_day'] = mid.date()
                rows.append([index, row1, row2])

        tmp = df
        for item in rows:
            tmp = pd.DataFrame(np.insert(df.values, item[0],values = list(item[1].values()), axis = 0 ))
            tmp = pd.DataFrame(np.insert(tmp.values, item[0]+1,values = list(item[2].values()), axis = 0 ))
            tmp.drop(item[0] + 2, inplace = True)
        tmp.columns = df.columns

        self.processed_detailed_df = tmp
        return tmp

    def get_daily_work(self):
        '''
        df should be processed
        '''
        self.get_processed_df()
        df = self.processed_detailed_df
        net_work = dict()

        for _, row in df.iterrows():
            day = row['end_day'] # doesnt matter, both days are equal
            tmp_df = df[df['end_day'] == day]
            net_work[day]  =round(sum(tmp_df['dur'].tolist())/3600000, 2) # in hrs 
        
        tmp = pd.DataFrame.from_dict({
            'day': list(net_work.keys()),
            'work done': list(net_work.values())
        })
        fig = px.bar(tmp, x =  'day', y = 'work done')
        fig.update_layout(height = 600, width = 1050)

        self.daily_df, self.daily_df_fig = tmp, fig
        return tmp, fig


    def build_stacked_bar(self):
        '''
        returns stacked bar chart,
        input should be processed
        '''
        try:
            df = self.processed_detailed_df
        except: 
            print('in except')
            self.get_processed_df()
            df = self.processed_detailed_df

        # there have to multiple traces equal to the number of projects
        df['project'] = ['Empty Project' if item is None else item for item in df['project'].tolist()]
        projects = list(set(df['project'].tolist()))
        days = sorted(list(set(df['end_day'].tolist())))
        trace_dict = defaultdict(dict)
        
        for project in projects:
            for day in days:
                tmp = df[df['project'] == project][df['end_day'] == day]
                if len(tmp) == 0: # no work done on that project on that day
                    trace_dict[project][day] = 0
                else:
                    trace_dict[project][day] = sum(tmp['dur'].tolist())/3600000
                    
        trace_dict2 = dict() 
        for k, _ in trace_dict.items():
            trace_dict2[k] = OrderedDict(sorted(trace_dict[k].items()))

        fig = go.Figure()
        for key in trace_dict.keys():
            y = list(trace_dict[key].values())
            fig.add_trace(go.Bar(
                x = days,
                y = y, name = key
            ))
        fig.update_layout(width  =1500, barmode = 'stack')

        self.detailed_stacked_bar = fig

        return fig


    def build_sunburst_data(self, df, parents, labels,values, string = 'total'):
        
        main_parents = list(set(parents))
        main_values = []
        
        for main_parent in  main_parents:
            tmp = []
            for parent, _, value in zip(parents, labels, values):
                if parent == main_parent:
                    tmp.append(value)
            main_values.append(sum(tmp))
        
        parents += [string] * len(main_parents)
        labels += main_parents
        values += main_values
        
        parents.append("")
        labels.append(string)
        values.append(0.5*sum(values))
        values = [item/3600000 for item in values] 
        return parents, labels, values


    def main_sunburst(self):
        df = self.summary_df
        
        parents, labels, values = self.build_sunburst_data(df, df['project'].tolist(), df['task'].tolist(),df['task time duration'].tolist(), string = 'total')
        fig = go.Figure()
        fig.add_trace(
            go.Sunburst(
                values = values,
                parents = parents,
                labels = labels,
                branchvalues = 'total', 
                maxdepth = 2,
                textinfo = "label",
                insidetextorientation = "radial"
            )
        )
        fig.update_layout(height = 600, width = 500, margin = {
            'l': 80, 
            'r': 80, 
            
        })
        self.sunburst_fig = fig
        return fig


res = Response(email=email, 
    token=token, 
    workspace_id=workspace_id, 
    start_date=str(datetime.datetime(2020, 8, 10).date()), 
    end_date=str(datetime.datetime(2020, 10, 5).date()))
daily_df, fig = res.get_daily_work()
fig.show()

fig = res.build_stacked_bar()
fig.show()
fig = res.main_sunburst()
fig.show()