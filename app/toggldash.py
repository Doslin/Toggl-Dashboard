"""
this file launches a dashboard at http://127.0.0.1:8050/
imports a response class from process_response.py in the bin folder.

first creds are collected. if not present already, its asked from the command line
and saved in creds.txt

the app is cereated and launched then. 
data is recieved and then graphs are created.

"""

import datetime
import logging

import dash
import dash_html_components as html
import dash_core_components as dcc
import re
import time
import response.process_response as getRes
import warnings
import plotly.io as ploio
from expiringdict import ExpiringDict

warnings.filterwarnings("ignore")
ExpireCache = ExpiringDict(max_len=100, max_age_seconds=120)

email, token, workspace_id = getRes.fetch_creds()  # collecting all the creds!

end_date = datetime.datetime.now().date() - datetime.timedelta(days=0)
start_date = end_date - datetime.timedelta(days=1)

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
external_stylesheets = ["/Users/zhilin/code/pycharm/Toggl-Dashboard/app/BwLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    dcc.Loading(  # for the loading screen
                        id="loading",
                        # what's children?
                        loading_state={"component_name": "main sunburst,daily"},
                        # fullscreen = True, # uncomment if all your details are saved in creds.txt
                        type="default",
                    )
                ),
                html.Div(
                    dcc.Graph(
                        id="main sunburst"
                    ),  # the sunburst and the daily bar plot (next)
                    style={"width": "30%", "display": "inline-block", "margin-top": "-120px"},
                ),  # the daily blue graph is inline with sunburst
                html.Div(
                    dcc.Graph(id="daily"),
                    style={"width": "70%", "display": "inline-block"},
                ),
            ]
        ),
        dcc.Graph(id="details-seg"),  # the daily segs graph below that
        html.Div(
            [
                html.Div(
                    html.H1(children="daily work done on an average: "),
                    style={
                        "width": "60%",
                        "display": "inline-block",
                        "fontFamily": "Lucida Console",
                    },
                ),
                html.Div(
                    html.H1(id="daily-avg-work"),
                    style={
                        "width": "40%",
                        "display": "inline-block",
                        "fontFamily": "Lucida Console",
                    },
                ),
            ]
        ),
        html.Div(
            [
                # the toggl dashboard logo is 'inline block' with these threee: date picker, password and email text boxes
                # what that means is that the logo is side by side with date picker, pass and email text boxes
                html.P(
                    "    Toggl Dashboard",
                    style={
                        "fontSize": "2px",
                        "fontFamily": "Lucida Console",
                        "width": "70%",
                        "display": "inline-block",
                    },  # look at the width
                ),
                html.Div(
                    [
                        html.Div(
                            dcc.DatePickerRange(
                                id="my-date-picker-range",
                                min_date_allowed=datetime.datetime(2015, 12, 1),
                                max_date_allowed=datetime.datetime(2025, 12, 30),
                                initial_visible_month=datetime.datetime(2023, 2, 5),
                                start_date=start_date,
                                end_date=end_date,
                                display_format="MMM Do, YY",
                                style={
                                    "fontSize": "1px",
                                    "fontFamily": "Lucida Console",
                                },
                            )
                        ),
                        html.Div(
                            dcc.Input(
                                id="token input",
                                placeholder="enter toggl token",
                                value=token,
                                type="password",
                                style={
                                    "fontSize": "2px",
                                    "fontFamily": "Lucida Console",
                                },
                            ),
                        ),
                        html.Div(
                            dcc.Input(
                                id="email input",
                                placeholder="enter email address",
                                value=email,
                                style={
                                    "fontSize": "2px",
                                    "fontFamily": "Lucida Console",
                                },
                            )
                        ),
                    ],
                    style={"width": "30%", "display": "inline-block"},
                ),  # look at the width here
            ]  # this inline block ends here, then come the graphs
        ),

    ]
)


@app.callback(
    # this is for the loading screen, just displays that for 10 secs. The data is recieved and processed by that time I guess
    dash.dependencies.Output("loading", "children"),
    [dash.dependencies.Input("loading", "fullscreen")],
)
def pause(value):
    time.sleep(10)  # shows that rectangle thing for 10 seconds
    return


@app.callback(  # for the figures and graphs
    [
        dash.dependencies.Output("main sunburst", "figure"),
        dash.dependencies.Output("daily", "figure"),
        dash.dependencies.Output("details-seg", "figure"),
        dash.dependencies.Output("daily-avg-work", "children"),
    ],
    [
        dash.dependencies.Input("my-date-picker-range", "start_date"),
        dash.dependencies.Input("my-date-picker-range", "end_date"),
        dash.dependencies.Input("token input", "value"),
        dash.dependencies.Input("email input", "value"),
    ],
)
def update_output(start_date, end_date, token, mail):
    Flag = False

    if start_date is not None:
        start_date = str(
            datetime.datetime.strptime(re.split("T| ", start_date)[0], "%Y-%m-%d")
        )
        Flag = True
    if end_date is not None:
        end_date = str(
            datetime.datetime.strptime(re.split("T| ", end_date)[0], "%Y-%m-%d")
        )
        Flag = True
    if not Flag:
        pass  # ! raise error
    else:
        pass
    cache_key = start_date + end_date + token
    t = ['12345', '54321', 'hello!', '']

    if cache_key in ExpireCache:
        # 是可以通过反序列化的数据生成的，所以我们可以使用这个框架来定时更新程序内 map，自己去读 map 就行
        logging.info("use cache {}", ExpireCache.ttl(cache_key))
        return ExpireCache[cache_key][0], ExpireCache[cache_key][1], ExpireCache[cache_key][2], ExpireCache[cache_key][
            3]

    res = getRes.Response(
        email=email,  # calling the response class
        token=token,
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
    )

    daily_df, daily_bar = res.get_daily_work()

    projects_seg = res.build_stacked_bar()
    _ = res.main_sunburst()
    sunburst = res.sunburst_fig

    avg_work = (
            str(round(sum(daily_df["work done"].tolist()) / len(daily_df), 2)) + "hrs"
    )
    # 将获取的数据存盘，以提供下次获取
    with open('data.txt', 'a') as f:
        f.write(sunburst.to_json())
        f.write("______split______")
        f.write(daily_bar.to_json())
        f.write("______split______")
        f.write(projects_seg.to_json())
        f.write("______split______")
        f.write(avg_work)
        f.write("\n")
    t[0] = sunburst
    t[1] = daily_bar
    t[2] = projects_seg
    t[3] = avg_work
    if cache_key not in ExpireCache:
        ExpireCache[cache_key] = t
    return sunburst, daily_bar, projects_seg, avg_work


def run():
    app.run_server(debug=False)


if __name__ == "__main__":
    run()
    # TODO: find a better way to kill the server
